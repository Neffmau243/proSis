from types import SimpleNamespace
from datetime import datetime, timezone

import pytest
from fastapi.security import HTTPAuthorizationCredentials

import app.core.dependencies as dependencies
from app.core.security import AccessTokenClaims
from app.domain.authorization import RolePermissionPolicy
from app.exceptions import AuthenticationError


def _claims() -> AccessTokenClaims:
    return AccessTokenClaims(
        user_id=7,
        username="old-name",
        roles=frozenset({"ADMIN"}),
        permissions=frozenset({"OUTDATED_PERMISSION"}),
        expires_at=datetime.now(timezone.utc),
    )


def _credentials() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="signed-token")


def test_current_principal_uses_persisted_roles_not_stale_jwt_claims(monkeypatch) -> None:
    persisted_user = SimpleNamespace(
        id=7,
        nombre_usuario="registro.actualizado",
        activo=True,
        roles=[SimpleNamespace(codigo="PROFESIONAL")],
    )

    class Repository:
        def __init__(self, _: object) -> None:
            pass

        def find_by_id(self, _: int) -> object:
            return persisted_user

    monkeypatch.setattr(dependencies, "decode_access_token", lambda _: _claims())
    monkeypatch.setattr(dependencies, "UserRepository", Repository)

    principal = dependencies.get_current_principal(_credentials(), object())

    assert principal.username == "registro.actualizado"
    assert principal.roles == frozenset({"PROFESIONAL"})
    assert principal.permissions == RolePermissionPolicy().resolve(["PROFESIONAL"])


def test_current_principal_rejects_a_user_deactivated_after_token_issue(monkeypatch) -> None:
    class Repository:
        def __init__(self, _: object) -> None:
            pass

        def find_by_id(self, _: int) -> object:
            return SimpleNamespace(activo=False)

    monkeypatch.setattr(dependencies, "decode_access_token", lambda _: _claims())
    monkeypatch.setattr(dependencies, "UserRepository", Repository)

    with pytest.raises(AuthenticationError, match="ya no está activo"):
        dependencies.get_current_principal(_credentials(), object())


def test_current_principal_rejects_a_token_after_password_change(monkeypatch) -> None:
    class Repository:
        def __init__(self, _: object) -> None:
            pass

        def find_by_id(self, _: int) -> object:
            return SimpleNamespace(
                id=7,
                activo=True,
                version_credenciales=1,
                roles=[SimpleNamespace(codigo="PROFESIONAL")],
            )

    monkeypatch.setattr(dependencies, "decode_access_token", lambda _: _claims())
    monkeypatch.setattr(dependencies, "UserRepository", Repository)

    with pytest.raises(AuthenticationError, match="sesión ya no es válida"):
        dependencies.get_current_principal(_credentials(), object())
