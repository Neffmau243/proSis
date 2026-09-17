"""Regression coverage for production authentication safeguards."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import app.scripts.seed_demo_data as demo_seed
import app.services.auth as auth_module
from app.core.config import Settings
from app.exceptions import BusinessRuleError
from app.schemas.auth import LoginRequest, PasswordChangeRequest, UserCreate, UserRolesUpdate
from app.services.auth import AuthenticationService
from app.services.user import UserService


def test_production_rejects_the_documented_secret_placeholder() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY de producción"):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="replace-with-a-unique-secret-key-of-at-least-32-characters",
        )


def test_demo_seed_stops_before_opening_a_session_outside_development(monkeypatch) -> None:
    monkeypatch.setattr(
        demo_seed,
        "get_settings",
        lambda: SimpleNamespace(environment="production"),
    )
    monkeypatch.setattr(
        demo_seed,
        "SessionLocal",
        lambda: pytest.fail("No debe abrir una sesión de base de datos en producción."),
    )

    with pytest.raises(RuntimeError, match="solo pueden ejecutarse"):
        demo_seed.seed_demo_data()


@pytest.mark.parametrize("password", ["1234567", "123456789", "1234abcd"])
def test_password_contract_requires_exactly_eight_ascii_digits(password: str) -> None:
    with pytest.raises(ValidationError, match="exactamente 8 dígitos"):
        LoginRequest(nombre_usuario="medico.demo", password=password)


def test_all_password_entry_contracts_accept_eight_digits() -> None:
    assert LoginRequest(nombre_usuario="medico.demo", password="12345678").password == "12345678"
    assert (
        UserCreate(
            nombre_usuario="medico.demo",
            password="12345678",
            roles=["ADMIN"],
        ).password
        == "12345678"
    )
    assert (
        PasswordChangeRequest(
            current_password="12345678",
            new_password="87654321",
            new_password_confirmation="87654321",
        ).new_password
        == "87654321"
    )


class _RateLimitRepository:
    def __init__(self) -> None:
        self.limiter: object | None = None

    def add_login_rate_limit(self, limiter: object) -> None:
        self.limiter = limiter


class _LoginUsernameRepository:
    @staticmethod
    def list_active_usernames() -> list[str]:
        return ["admin", "medico.demo"]


def test_login_username_directory_returns_active_accounts() -> None:
    service = AuthenticationService(SimpleNamespace())
    service._users = _LoginUsernameRepository()  # type: ignore[assignment]

    assert service.list_active_usernames() == ["admin", "medico.demo"]


def test_login_controls_rate_and_progressive_account_lock(monkeypatch) -> None:
    settings = SimpleNamespace(
        login_rate_limit_attempts=2,
        login_rate_limit_window_seconds=900,
        login_lock_base_seconds=60,
        login_lock_max_seconds=600,
    )
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)
    repository = _RateLimitRepository()
    service = AuthenticationService(SimpleNamespace())
    service._users = repository  # type: ignore[assignment]
    now = datetime(2026, 9, 10, 10, 0)

    assert service._register_limiter_failure(None, "bucket", now) is False
    limiter = repository.limiter
    assert limiter is not None
    assert service._register_limiter_failure(limiter, "bucket", now + timedelta(seconds=1))
    assert limiter.bloqueado_hasta == now + timedelta(seconds=901)

    user = SimpleNamespace(
        activo=True,
        intentos_fallidos_inicio_sesion=0,
        ultimo_intento_fallido_inicio_sesion_at=None,
        bloqueado_inicio_sesion_hasta=None,
    )
    assert service._register_account_failure(user, now) is False
    assert service._register_account_failure(user, now + timedelta(seconds=1))
    assert user.bloqueado_inicio_sesion_hasta == now + timedelta(seconds=61)
    assert service._register_account_failure(user, now + timedelta(seconds=62))
    assert user.bloqueado_inicio_sesion_hasta == now + timedelta(seconds=182)


class _Session:
    def __init__(self) -> None:
        self.rolled_back = False

    def rollback(self) -> None:
        self.rolled_back = True


class _UserRepository:
    def __init__(self, user: object) -> None:
        self.user = user

    @staticmethod
    def lock_active_admin_ids() -> list[int]:
        return [1]

    def find_by_id(self, _: int, *, lock: bool = False) -> object:
        return self.user

    @staticmethod
    def find_roles_by_codes(_: set[str]) -> list[object]:
        return [SimpleNamespace(codigo="PROFESIONAL")]


def test_last_active_admin_cannot_lose_the_admin_role() -> None:
    session = _Session()
    user = SimpleNamespace(
        id=1,
        activo=True,
        profesional_id=10,
        nombre_usuario="admin",
        version_credenciales=0,
        roles=[SimpleNamespace(codigo="ADMIN")],
        roles_usuario=[],
    )
    service = UserService(session)  # type: ignore[arg-type]
    service._users = _UserRepository(user)  # type: ignore[assignment]

    with pytest.raises(BusinessRuleError, match="al menos un usuario ADMIN") as exc_info:
        service.assign_roles(
            1,
            UserRolesUpdate(roles=["PROFESIONAL"]),
            actor_id=2,
            actor_roles={"ADMIN"},
        )

    assert exc_info.value.code == "ULTIMO_ADMIN_ACTIVO"
    assert session.rolled_back is True
