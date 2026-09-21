"""Authentication and user-administration contract exercised over MySQL.

These tests cross the whole stack (router -> controller -> service ->
repository -> MySQL) instead of stubbing the service layer, so a broken
permission dependency or a wrong SQL update is caught here.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.security import User

pytestmark = pytest.mark.integration


def test_health_endpoint_is_public_and_returns_a_request_id(api_client, api_prefix) -> None:
    response = api_client.get(f"{api_prefix}/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_login_returns_token_roles_and_permissions(
    api_client, clinic_scene, api_prefix, scene_password
) -> None:
    response = api_client.post(
        f"{api_prefix}/auth/login",
        json={"nombre_usuario": clinic_scene.admin_username, "password": scene_password},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["usuario_id"] == clinic_scene.admin_id
    assert body["roles"] == ["ADMIN"]
    assert "PACIENTE_DAR_BAJA" in body["permisos"]
    assert "ATENCION_CREAR" not in body["permisos"]
    assert body["expires_in"] > 0
    assert body["access_token"]

    # The issued token must authenticate a protected endpoint.
    authenticated = api_client.get(
        f"{api_prefix}/catalogos/sexos",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert authenticated.status_code == 200


def test_login_answers_the_same_generic_error_for_every_credential_failure(
    api_client, clinic_scene, api_prefix
) -> None:
    unknown = api_client.post(
        f"{api_prefix}/auth/login",
        json={"nombre_usuario": f"fantasma-{uuid4().hex[:8]}", "password": "12345678"},
    )
    wrong_password = api_client.post(
        f"{api_prefix}/auth/login",
        json={"nombre_usuario": clinic_scene.admin_username, "password": "00000000"},
    )

    assert unknown.status_code == 401
    assert wrong_password.status_code == 401
    assert unknown.json()["error"]["message"] == wrong_password.json()["error"]["message"]
    assert wrong_password.headers["WWW-Authenticate"] == "Bearer"
    assert wrong_password.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_login_rejects_a_password_that_breaks_the_credential_contract(
    api_client, clinic_scene, api_prefix
) -> None:
    response = api_client.post(
        f"{api_prefix}/auth/login",
        json={"nombre_usuario": clinic_scene.admin_username, "password": "corta"},
    )

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "REQUEST_VALIDATION_ERROR"
    assert any("password" in detail["field"] for detail in body["details"])


def test_protected_endpoints_require_a_bearer_token(clinic_scene, api_prefix) -> None:
    client = clinic_scene.anonymous_client
    for path in (
        "/catalogos/sexos",
        "/patients",
        "/atenciones",
        "/usuarios",
        "/configuracion/consultorios",
        "/configuracion/profesionales",
        "/configuracion/grupos-etarios",
    ):
        response = client.get(f"{api_prefix}{path}")
        assert response.status_code in {401, 405}, f"{path} -> {response.status_code}"
        if response.status_code == 401:
            assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    # A syntactically invalid token is rejected the same way.
    forged = client.get(
        f"{api_prefix}/catalogos/sexos", headers={"Authorization": "Bearer no-es-un-jwt"}
    )
    assert forged.status_code == 401
    assert forged.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_admin_and_clinical_roles_do_not_overlap(clinic_scene, api_prefix) -> None:
    # ADMIN cannot register clinical activity...
    admin_attempt = clinic_scene.admin_client.post(
        f"{api_prefix}/atenciones",
        json={
            "paciente_id": 1,
            "establecimiento_id": clinic_scene.establecimiento_id,
            "profesional_id": clinic_scene.profesional_id,
            "consultorio_id": clinic_scene.consultorio_id,
            "modalidad_atencion_codigo": "AMBULATORIA",
            "fecha_atencion": "2026-09-01T10:00:00",
        },
    )
    assert admin_attempt.status_code == 403
    assert admin_attempt.json()["error"]["code"] == "AUTHORIZATION_DENIED"
    assert admin_attempt.json()["error"]["details"]["required_permissions"] == ["ATENCION_CREAR"]

    # ...and PROFESIONAL cannot manage administrative catalogs.
    professional_attempt = clinic_scene.professional_client.get(
        f"{api_prefix}/configuracion/consultorios"
    )
    assert professional_attempt.status_code == 403
    assert professional_attempt.json()["error"]["details"]["required_permissions"] == [
        "CONSULTORIO_GESTIONAR"
    ]


def test_login_username_directory_lists_only_login_accounts(
    clinic_scene, api_prefix
) -> None:
    response = clinic_scene.anonymous_client.get(f"{api_prefix}/auth/usuarios-activos")

    assert response.status_code == 200
    usernames = [item["nombre_usuario"] for item in response.json()]
    assert clinic_scene.admin_username in usernames
    assert clinic_scene.professional_username in usernames
    assert all(set(item) == {"nombre_usuario"} for item in response.json())


def test_changing_own_password_invalidates_the_previous_one(
    api_client, clinic_scene, api_prefix, scene_password
) -> None:
    new_password = "87654321"
    before_change = clinic_scene.professional_client.get(f"{api_prefix}/catalogos/sexos")
    assert before_change.status_code == 200

    changed = clinic_scene.professional_client.put(
        f"{api_prefix}/auth/me/password",
        json={
            "current_password": scene_password,
            "new_password": new_password,
            "new_password_confirmation": new_password,
        },
    )
    assert changed.status_code == 204, changed.text

    old_credentials = api_client.post(
        f"{api_prefix}/auth/login",
        json={
            "nombre_usuario": clinic_scene.professional_username,
            "password": scene_password,
        },
    )
    new_credentials = api_client.post(
        f"{api_prefix}/auth/login",
        json={"nombre_usuario": clinic_scene.professional_username, "password": new_password},
    )
    assert old_credentials.status_code == 401
    assert new_credentials.status_code == 200

    # The credential version bump invalidates tokens issued before the change,
    # so a stolen session cannot survive a password rotation.
    stale_token = clinic_scene.professional_client.get(f"{api_prefix}/catalogos/sexos")
    assert stale_token.status_code == 401
    assert stale_token.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_password_change_validates_the_current_secret_and_the_confirmation(
    clinic_scene, api_prefix
) -> None:
    wrong_current = clinic_scene.professional_client.put(
        f"{api_prefix}/auth/me/password",
        json={
            "current_password": "00000000",
            "new_password": "87654321",
            "new_password_confirmation": "87654321",
        },
    )
    assert wrong_current.status_code == 401

    mismatch = clinic_scene.professional_client.put(
        f"{api_prefix}/auth/me/password",
        json={
            "current_password": "12345678",
            "new_password": "87654321",
            "new_password_confirmation": "11111111",
        },
    )
    assert mismatch.status_code == 422


def test_reusing_the_current_password_is_refused(clinic_scene, api_prefix, scene_password) -> None:
    response = clinic_scene.professional_client.put(
        f"{api_prefix}/auth/me/password",
        json={
            "current_password": scene_password,
            "new_password": scene_password,
            "new_password_confirmation": scene_password,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CONTRASENA_REUTILIZADA"


def test_administrator_creates_users_and_enforces_global_rules(
    api_client, clinic_scene, api_prefix, scene_password
) -> None:
    username = f"nuevo-{uuid4().hex[:8]}"
    created = clinic_scene.admin_client.post(
        f"{api_prefix}/usuarios",
        json={
            "nombre_usuario": username,
            "password": scene_password,
            "roles": ["ADMIN"],
        },
    )
    assert created.status_code == 201, created.text
    user = created.json()
    assert user["nombre_usuario"] == username
    assert user["roles"] == ["ADMIN"]
    assert user["activo"] is True
    assert "password" not in user and "password_hash" not in user

    duplicated = clinic_scene.admin_client.post(
        f"{api_prefix}/usuarios",
        json={"nombre_usuario": username, "password": scene_password, "roles": ["ADMIN"]},
    )
    assert duplicated.status_code == 409
    assert duplicated.json()["error"]["code"] == "USUARIO_DUPLICADO"

    # The new account can authenticate immediately.
    login = api_client.post(
        f"{api_prefix}/auth/login", json={"nombre_usuario": username, "password": scene_password}
    )
    assert login.status_code == 200

    updated = clinic_scene.admin_client.put(
        f"{api_prefix}/usuarios/{user['id']}/roles", json={"roles": ["PROFESIONAL"]}
    )
    assert updated.status_code == 422
    assert updated.json()["error"]["code"] == "USUARIO_PROFESIONAL_SIN_VINCULO"


def test_user_creation_rejects_retired_roles_and_unknown_professionals(
    clinic_scene, api_prefix, scene_password
) -> None:
    retired = clinic_scene.admin_client.post(
        f"{api_prefix}/usuarios",
        json={
            "nombre_usuario": f"registro-{uuid4().hex[:8]}",
            "password": scene_password,
            "roles": ["REGISTRO"],
        },
    )
    assert retired.status_code == 422
    assert retired.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"

    unknown_professional = clinic_scene.admin_client.post(
        f"{api_prefix}/usuarios",
        json={
            "nombre_usuario": f"vinculo-{uuid4().hex[:8]}",
            "password": scene_password,
            "roles": ["PROFESIONAL"],
            "profesional_id": 999_999_999,
        },
    )
    assert unknown_professional.status_code == 404
    assert unknown_professional.json()["error"]["code"] == "PROFESIONAL_NO_ACTIVO"


def test_administrator_deactivates_and_resets_another_account(
    api_client, clinic_scene, create_professional, api_prefix, scene_password
) -> None:
    username = f"gestion-{uuid4().hex[:8]}"
    # ``uq_usuarios_profesional`` links one account per professional, so a
    # second account needs its own staff record.
    created = clinic_scene.admin_client.post(
        f"{api_prefix}/usuarios",
        json={
            "nombre_usuario": username,
            "password": scene_password,
            "roles": ["ADMIN"],
            "profesional_id": create_professional().id,
        },
    ).json()

    reset = clinic_scene.admin_client.put(
        f"{api_prefix}/usuarios/{created['id']}/password",
        json={"new_password": "11112222", "new_password_confirmation": "11112222"},
    )
    assert reset.status_code == 204, reset.text
    assert (
        api_client.post(
            f"{api_prefix}/auth/login", json={"nombre_usuario": username, "password": "11112222"}
        ).status_code
        == 200
    )

    own_reset = clinic_scene.admin_client.put(
        f"{api_prefix}/usuarios/{clinic_scene.admin_id}/password",
        json={"new_password": "33334444", "new_password_confirmation": "33334444"},
    )
    assert own_reset.status_code == 422
    assert own_reset.json()["error"]["code"] == "RESTABLECIMIENTO_PROPIO_NO_PERMITIDO"

    deactivated = clinic_scene.admin_client.delete(f"{api_prefix}/usuarios/{created['id']}")
    assert deactivated.status_code == 200
    assert deactivated.json()["activo"] is False
    assert (
        api_client.post(
            f"{api_prefix}/auth/login", json={"nombre_usuario": username, "password": "11112222"}
        ).status_code
        == 401
    )

    # An inactive account cannot receive a new password.
    late_reset = clinic_scene.admin_client.put(
        f"{api_prefix}/usuarios/{created['id']}/password",
        json={"new_password": "55556666", "new_password_confirmation": "55556666"},
    )
    assert late_reset.status_code == 422
    assert late_reset.json()["error"]["code"] == "USUARIO_INACTIVO"


def test_administrator_cannot_deactivate_their_own_account(clinic_scene, api_prefix) -> None:
    response = clinic_scene.admin_client.delete(f"{api_prefix}/usuarios/{clinic_scene.admin_id}")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "AUTOBAJA_NO_PERMITIDA"


def test_professional_role_requires_an_active_professional(
    clinic_scene, create_professional, api_prefix, scene_password
) -> None:
    professional = create_professional()
    with_link = clinic_scene.admin_client.post(
        f"{api_prefix}/usuarios",
        json={
            "nombre_usuario": f"vinculado-{uuid4().hex[:8]}",
            "password": scene_password,
            "roles": ["PROFESIONAL"],
            "profesional_id": professional.id,
        },
    )
    assert with_link.status_code == 201, with_link.text
    assert with_link.json()["profesional_id"] == professional.id
    assert with_link.json()["roles"] == ["PROFESIONAL"]

    inactive = create_professional(activo=False)
    rejected = clinic_scene.admin_client.post(
        f"{api_prefix}/usuarios",
        json={
            "nombre_usuario": f"inactivo-{uuid4().hex[:8]}",
            "password": scene_password,
            "roles": ["PROFESIONAL"],
            "profesional_id": inactive.id,
        },
    )
    assert rejected.status_code == 404
    assert rejected.json()["error"]["code"] == "PROFESIONAL_NO_ACTIVO"


def test_audit_trail_records_login_and_user_administration(
    api_client, clinic_scene, db_session: Session, api_prefix, scene_password
) -> None:
    username = f"auditado-{uuid4().hex[:8]}"
    clinic_scene.admin_client.post(
        f"{api_prefix}/usuarios",
        json={"nombre_usuario": username, "password": scene_password, "roles": ["ADMIN"]},
    )
    api_client.post(
        f"{api_prefix}/auth/login", json={"nombre_usuario": username, "password": scene_password}
    )
    api_client.post(
        f"{api_prefix}/auth/login", json={"nombre_usuario": username, "password": "00000000"}
    )

    actions = set(
        db_session.scalars(
            select(AuditLog.accion).where(AuditLog.tabla_nombre.in_(("usuarios", "autenticacion")))
        ).all()
    )
    assert {"INSERT", "LOGIN_SUCCESS", "LOGIN_FAILURE"} <= actions

    login_failures = db_session.scalars(
        select(AuditLog).where(AuditLog.accion == "LOGIN_FAILURE")
    ).all()
    assert login_failures
    # Neither the raw username nor the submitted password may be persisted.
    for record in login_failures:
        assert "00000000" not in str(record.datos_nuevos)
        assert username not in str(record.datos_nuevos)
        assert {record.datos_nuevos["motivo"]} <= {
            "credenciales_invalidas",
            "cuenta_bloqueada",
            "limite_de_tasa",
        }
        assert record.datos_nuevos["resultado"] == "fallido"


def test_user_administration_requires_the_admin_role(
    clinic_scene, db_session: Session, api_prefix, scene_password
) -> None:
    username = f"intruso-{uuid4().hex[:8]}"
    response = clinic_scene.professional_client.post(
        f"{api_prefix}/usuarios",
        json={"nombre_usuario": username, "password": scene_password, "roles": ["ADMIN"]},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_DENIED"
    # The rejected request must not have persisted anything.
    assert db_session.scalar(select(User).where(User.nombre_usuario == username)) is None
