"""Reusable FastAPI dependencies with no domain/repository knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenValidationError, decode_access_token
from app.domain.authorization import RolePermissionPolicy
from app.exceptions import AuthenticationError, AuthorizationError
from app.repositories.user import UserRepository


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Current, persisted identity and authorization for an HTTP request.

    The active flag and roles are refreshed from the database for every
    protected request, so a role change or logical deactivation takes effect
    without waiting for an old JWT to expire.
    """

    user_id: int
    username: str | None
    roles: frozenset[str]
    permissions: frozenset[str]


bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="JWT de acceso emitido por el sistema.",
)


def get_current_principal(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> AuthenticatedPrincipal:
    """Validate JWT integrity and refresh the account from persistence."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Se requiere un token Bearer válido.")

    try:
        claims = decode_access_token(credentials.credentials)
    except TokenValidationError as exc:
        raise AuthenticationError("El token de acceso es inválido o venció.") from exc

    user = UserRepository(db).find_by_id(claims.user_id)
    if user is None or not user.activo:
        raise AuthenticationError("El usuario ya no está activo.")
    if claims.credential_version != getattr(user, "version_credenciales", 0):
        raise AuthenticationError(
            "La sesión ya no es válida; inicie sesión nuevamente."
        )
    roles = frozenset(role.codigo for role in user.roles)
    permissions = RolePermissionPolicy().resolve(roles)
    return AuthenticatedPrincipal(
        user_id=user.id,
        username=user.nombre_usuario,
        roles=roles,
        permissions=permissions,
    )


CurrentPrincipal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]


def _normalize_required_values(values: tuple[str, ...], label: str) -> frozenset[str]:
    normalized = frozenset(value.strip() for value in values if value and value.strip())
    if not normalized:
        raise ValueError(f"Debe especificarse al menos un {label}.")
    return normalized


def require_roles(*allowed_roles: str) -> Callable[..., AuthenticatedPrincipal]:
    """Create a dependency that accepts a principal with at least one role."""

    required = _normalize_required_values(allowed_roles, "rol")

    def dependency(
        principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    ) -> AuthenticatedPrincipal:
        if principal.roles.isdisjoint(required):
            raise AuthorizationError(
                "Su rol no permite realizar esta operación.",
                details={"required_roles": sorted(required)},
            )
        return principal

    return dependency


def require_permissions(
    *required_permissions: str,
    require_all: bool = True,
) -> Callable[..., AuthenticatedPrincipal]:
    """Create an action-permission dependency for a router endpoint.

    Permissions are derived from the persisted principal rather than
    hard-coded role checks in controllers.  The authorization policy can map
    changing IPRESS roles to actions without changing HTTP adapters.
    """

    required = _normalize_required_values(required_permissions, "permiso")

    def dependency(
        principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    ) -> AuthenticatedPrincipal:
        granted = principal.permissions
        authorized = required.issubset(granted) if require_all else not granted.isdisjoint(required)
        if not authorized:
            raise AuthorizationError(
                "No tiene permisos para realizar esta operación.",
                details={"required_permissions": sorted(required)},
            )
        return principal

    return dependency


__all__ = [
    "AuthenticatedPrincipal",
    "CurrentPrincipal",
    "bearer_scheme",
    "get_current_principal",
    "get_db",
    "require_permissions",
    "require_roles",
]
