"""Unit cover for the administrator user listing added to ``UserService``."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from app.schemas.auth import UserResponse
from app.services.user import UserService


class _UserRepository:
    def __init__(self, users: list[object]) -> None:
        self._users = users

    def list(self, *, include_inactive: bool = False) -> list[object]:
        if include_inactive:
            return self._users
        return [user for user in self._users if user.activo]  # type: ignore[attr-defined]


def _user(user_id: int, username: str, *, activo: bool = True) -> SimpleNamespace:
    now = datetime(2026, 1, 1, 0, 0, 0)
    return SimpleNamespace(
        id=user_id,
        profesional_id=None,
        nombre_usuario=username,
        activo=activo,
        ultimo_acceso_at=None,
        created_at=now,
        updated_at=now,
        roles=[],
        roles_usuario=[],
    )


def test_list_hides_inactive_accounts_by_default() -> None:
    service = UserService(object())  # type: ignore[arg-type]
    service._users = _UserRepository([_user(1, "activo"), _user(2, "inactivo", activo=False)])  # type: ignore[assignment]

    listing = service.list()

    assert [item.nombre_usuario for item in listing] == ["activo"]
    assert all(isinstance(item, UserResponse) for item in listing)


def test_list_includes_inactive_accounts_on_request() -> None:
    service = UserService(object())  # type: ignore[arg-type]
    service._users = _UserRepository([_user(1, "activo"), _user(2, "inactivo", activo=False)])  # type: ignore[assignment]

    listing = service.list(include_inactive=True)

    assert [item.nombre_usuario for item in listing] == ["activo", "inactivo"]
    assert listing[1].activo is False
