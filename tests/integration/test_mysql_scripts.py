"""Operational commands against a disposable MySQL database.

``create_admin``, ``bootstrap_database`` and ``seed_demo_data`` are the first
commands an operator runs after a deployment, so they are executed here through
their real entry points instead of being mocked.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.security import verify_password
from app.models.audit import AuditLog
from app.models.organization import Establishment
from app.models.patient import Patient, PatientResponsible
from app.models.security import Professional, Role, User, UserRole
from app.scripts import create_admin as create_admin_module
from app.scripts import create_professional_user as professional_user_module
from app.scripts import seed_demo_data as seed_module
from app.scripts.bootstrap_database import create_database_if_missing, upgrade_to_head
from app.scripts.create_admin import create_admin
from app.scripts.create_professional_user import create_professional_user
from app.scripts.reset_demo_database import drop_configured_database
from app.scripts.seed_demo_data import (
    DEMO_ADMIN_PASSWORD,
    DEMO_PROFESSIONAL_USERNAME,
    SOURCE_DEMO_PATIENTS,
    seed_demo_data,
    seed_real_patients,
)


@pytest.fixture
def test_session_factory(migrated_mysql_engine: Engine) -> sessionmaker[Session]:
    """A session factory bound to the disposable database.

    The scripts build their own sessions from the module-level ``SessionLocal``,
    which points at the configured (real) database.  Rebinding it to the test
    engine is what makes the command itself the unit under test.
    """

    return sessionmaker(bind=migrated_mysql_engine, expire_on_commit=False)


@pytest.fixture
def _script_sessions(
    monkeypatch: pytest.MonkeyPatch, test_session_factory: sessionmaker[Session]
) -> Iterator[None]:
    for module in (create_admin_module, professional_user_module, seed_module):
        monkeypatch.setattr(module, "SessionLocal", test_session_factory)
    yield


def _temporary_settings(url: str, *, environment: str = "development") -> Settings:
    return Settings(database_url=url, environment=environment)


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina TEST_DATABASE_URL para ejecutar integración MySQL.")
    assert "test" in make_url(url).database.lower()
    return url


def _scratch_database_url() -> str:
    """A second disposable schema next to the integration one.

    Creating and dropping it exercises the real ``CREATE/DROP DATABASE`` path
    without ever touching the schema the rest of the suite is using.
    """

    base = make_url(_test_database_url())
    return base.set(database=f"{base.database}_bootstrap").render_as_string(
        hide_password=False
    )


def test_bootstrap_creates_the_configured_database_and_reset_drops_it() -> None:
    url = _scratch_database_url()
    settings = _temporary_settings(url)
    database_name = make_url(url).database

    assert create_database_if_missing(settings) == database_name

    server_url = make_url(url).set(database="")
    server_engine = create_engine(server_url)
    try:
        with server_engine.connect() as connection:
            exists = connection.scalar(
                text(
                    "SELECT COUNT(*) FROM information_schema.schemata "
                    "WHERE schema_name = :name"
                ),
                {"name": database_name},
            )
        assert exists == 1

        # The command is idempotent: the second call must not fail.
        assert create_database_if_missing(settings) == database_name

        assert drop_configured_database(settings) == database_name
        with server_engine.connect() as connection:
            gone = connection.scalar(
                text(
                    "SELECT COUNT(*) FROM information_schema.schemata "
                    "WHERE schema_name = :name"
                ),
                {"name": database_name},
            )
        assert gone == 0
    finally:
        server_engine.dispose()


def test_bootstrap_migrates_the_configured_schema_to_head() -> None:
    # ``upgrade_to_head`` reads the same alembic configuration the application
    # ships; the disposable database is already at head, so this is a no-op.
    upgrade_to_head()


def test_create_admin_creates_an_audited_admin_account(
    _script_sessions: None, db_session: Session
) -> None:
    username = "admin.integracion"

    user_id = create_admin(username, DEMO_ADMIN_PASSWORD)

    db_session.rollback()
    user = db_session.get(User, user_id)
    assert user is not None
    assert user.nombre_usuario == username
    assert user.activo is True
    roles = db_session.scalars(
        select(Role.codigo).join(UserRole, UserRole.rol_id == Role.id).where(
            UserRole.usuario_id == user_id
        )
    ).all()
    assert list(roles) == ["ADMIN"]
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.tabla_nombre == "usuarios",
            AuditLog.registro_id == user_id,
            AuditLog.accion == "BOOTSTRAP",
        )
    )
    assert audit is not None, "El alta de ADMIN debe quedar auditada."
    assert audit.datos_nuevos["roles"] == ["ADMIN"]

    # The account stores a hash of the password it was created with.
    assert verify_password(DEMO_ADMIN_PASSWORD, user.password_hash) is True


def test_create_admin_rejects_duplicates_and_weak_credentials(
    _script_sessions: None,
) -> None:
    create_admin("admin.duplicado", DEMO_ADMIN_PASSWORD)

    with pytest.raises(ValueError, match="ya existe"):
        create_admin("admin.duplicado", DEMO_ADMIN_PASSWORD)
    with pytest.raises(ValueError, match="al menos 3 caracteres"):
        create_admin("ab", DEMO_ADMIN_PASSWORD)
    with pytest.raises(ValueError, match="exactamente 8 dígitos"):
        create_admin("admin.clave-invalida", "1234")


def test_create_admin_reports_a_missing_admin_role(
    _script_sessions: None,
    db_session: Session,
    migrated_mysql_engine: Engine,
) -> None:
    """A database without the seeded ADMIN role must fail loudly, not silently.

    The role is renamed instead of deleted: deleting it would cascade away the
    role assignments of every ADMIN account in the shared disposable schema and
    break unrelated tests that authenticate with those accounts.
    """

    admin_role = db_session.scalar(select(Role).where(Role.codigo == "ADMIN"))
    assert admin_role is not None
    role_id = admin_role.id
    db_session.rollback()

    with migrated_mysql_engine.begin() as connection:
        connection.execute(
            text("UPDATE roles SET codigo = 'ADMIN_RENOMBRADO' WHERE id = :role_id"),
            {"role_id": role_id},
        )

    try:
        with pytest.raises(RuntimeError, match="No existe el rol ADMIN"):
            create_admin("admin.sin-rol", DEMO_ADMIN_PASSWORD)
    finally:
        with migrated_mysql_engine.begin() as connection:
            connection.execute(
                text("UPDATE roles SET codigo = 'ADMIN' WHERE id = :role_id"),
                {"role_id": role_id},
            )
        db_session.rollback()


def test_seed_demo_data_builds_a_repeatable_clinical_scene(
    _script_sessions: None, db_session: Session
) -> None:
    identifiers = seed_demo_data()

    assert identifiers["establishment_id"] > 0
    assert identifiers["demo_patient_count"] > 0
    assert identifiers["adult_patient_id"] > 0
    assert any(key.startswith("attention_") for key in identifiers)

    db_session.rollback()
    origin = db_session.get(Establishment, identifiers["establishment_id"])
    assert origin is not None
    adult = db_session.get(Patient, identifiers["adult_patient_id"])
    assert adult is not None
    assert adult.apellido_paterno and adult.apellido_materno
    responsible = db_session.scalar(
        select(PatientResponsible).where(
            PatientResponsible.paciente_id == identifiers["minor_patient_id"]
        )
    )
    assert responsible is not None
    demo_user = db_session.scalar(
        select(User).where(User.nombre_usuario == DEMO_PROFESSIONAL_USERNAME)
    )
    assert demo_user is not None, "El profesional demo debe poder iniciar sesión."

    # Documented contract: the seed never deletes or overwrites user data.
    second_run = seed_demo_data()

    assert second_run["adult_patient_id"] == identifiers["adult_patient_id"]
    assert second_run["demo_patient_count"] == identifiers["demo_patient_count"]
    assert second_run["attention_1"] == identifiers["attention_1"]


def test_seed_demo_data_refuses_a_non_development_environment(
    _script_sessions: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        seed_module,
        "get_settings",
        lambda: type("_Settings", (), {"environment": "production"})(),
    )

    with pytest.raises(RuntimeError, match="ENVIRONMENT=development"):
        seed_demo_data()


def test_create_professional_user_links_a_real_professional(
    _script_sessions: None, db_session: Session
) -> None:
    """The clinical account is created without loading any fictional patient."""

    user_id = create_professional_user("prof.test", DEMO_ADMIN_PASSWORD)

    db_session.rollback()
    user = db_session.get(User, user_id)
    assert user is not None
    assert user.nombre_usuario == "prof.test"
    assert user.profesional_id is not None
    professional = db_session.get(Professional, user.profesional_id)
    assert professional is not None and professional.numero_documento
    roles = {
        role.codigo
        for role in db_session.scalars(
            select(Role)
            .join(UserRole, UserRole.rol_id == Role.id)
            .where(UserRole.usuario_id == user_id)
        )
    }
    assert roles == {"PROFESIONAL"}


def test_seed_real_patients_loads_only_the_source_rows(
    _script_sessions: None, db_session: Session
) -> None:
    """The ``--real-only`` mode loads the origin patients and no fictional cohort."""

    identifiers = seed_real_patients()

    assert identifiers["real_patient_count"] == len(SOURCE_DEMO_PATIENTS)
    db_session.rollback()
    sample = db_session.scalar(
        select(Patient).where(Patient.numero_documento == "77023409")
    )
    assert sample is not None
    assert sample.sis_diresa == "040" and sample.sis_numero == "77023409"


def test_seed_cli_real_only_branch(
    _script_sessions: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["seed_demo_data", "--real-only"])
    seed_module.main()

    assert "Pacientes reales" in capsys.readouterr().out


def test_seed_cli_default_branch(
    _script_sessions: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["seed_demo_data"])
    seed_module.main()

    output = capsys.readouterr().out
    assert "professional_username" in output
    assert "professional_password" in output


def test_create_professional_user_cli(
    _script_sessions: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_professional_user",
            "--username",
            "cli.user",
            "--password",
            DEMO_ADMIN_PASSWORD,
        ],
    )
    professional_user_module.main()

    assert "Usuario PROFESIONAL creado" in capsys.readouterr().out
