"""Password hashing and access-token primitives.

Authentication services use these primitives; routers and repositories should
not implement cryptography themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

import bcrypt
import jwt

from app.core.config import get_settings

PASSWORD_DIGITS_LENGTH = 8
PASSWORD_FORMAT_MESSAGE = "La contraseña debe contener exactamente 8 dígitos."


class TokenValidationError(ValueError):
    """Raised when an access token cannot be trusted."""


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Claims that the application accepts from a validated access token."""

    user_id: int
    username: str | None
    roles: frozenset[str]
    permissions: frozenset[str]
    expires_at: datetime
    credential_version: int = 0


def _normalize_claim_values(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    normalized = {value.strip() for value in values if isinstance(value, str) and value.strip()}
    return sorted(normalized)


def validate_password_format(password: str) -> str:
    """Enforce the team's agreed numeric credential format everywhere."""

    if (
        not isinstance(password, str)
        or len(password) != PASSWORD_DIGITS_LENGTH
        or not password.isascii()
        or not password.isdecimal()
    ):
        raise ValueError(PASSWORD_FORMAT_MESSAGE)
    return password


def _validate_password_input(password: str) -> bytes:
    # The format is far below bcrypt's 72-byte input limit and ASCII keeps
    # the digit count identical to the byte count used for hashing.
    return validate_password_format(password).encode("ascii")


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt using the configured cost."""

    password_bytes = _validate_password_input(password)
    rounds = get_settings().bcrypt_rounds
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether a plaintext password matches a stored bcrypt hash.

    Malformed hashes and invalid password inputs deliberately return ``False``
    instead of revealing which part of the credential was invalid.
    """

    try:
        password_bytes = _validate_password_input(password)
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except (AttributeError, TypeError, UnicodeEncodeError, ValueError):
        return False


def create_access_token(
    *,
    user_id: int,
    username: str | None = None,
    roles: Iterable[str] | str | None = None,
    permissions: Iterable[str] | str | None = None,
    credential_version: int = 0,
    expires_delta: timedelta | None = None,
    extra_claims: Mapping[str, Any] | None = None,
) -> str:
    """Create a short-lived signed JWT for an authenticated active user.

    The authentication service is responsible for loading active status and
    role assignments from ``usuarios``/``usuario_roles`` before invoking this
    function.  Reserved claims cannot be overwritten by callers.
    """

    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id debe ser un entero positivo.")
    if (
        isinstance(credential_version, bool)
        or not isinstance(credential_version, int)
        or credential_version < 0
    ):
        raise ValueError("credential_version debe ser un entero no negativo.")

    settings = get_settings()
    now = datetime.now(timezone.utc)
    # ``timedelta(0)`` is falsy: an explicit zero must be rejected by the check
    # below instead of silently falling back to the configured lifetime.
    lifetime = (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    if lifetime <= timedelta(0):
        raise ValueError("La duración del token debe ser positiva.")

    reserved_claims = {
        "sub",
        "username",
        "roles",
        "permissions",
        "type",
        "iat",
        "nbf",
        "exp",
        "iss",
        "aud",
        "credential_version",
    }
    if extra_claims and reserved_claims.intersection(extra_claims):
        raise ValueError("extra_claims no puede sobrescribir claims reservados.")

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "roles": _normalize_claim_values(roles),
        "permissions": _normalize_claim_values(permissions),
        "type": "access",
        "iat": now,
        "nbf": now,
        "exp": now + lifetime,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "credential_version": credential_version,
    }
    if username is not None:
        payload["username"] = username
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> AccessTokenClaims:
    """Decode and validate a signed access JWT with strict registered claims."""

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "iat", "nbf", "exp", "iss", "aud"]},
        )
    except (jwt.PyJWTError, TypeError, ValueError) as exc:
        raise TokenValidationError("Token inválido o vencido.") from exc

    if payload.get("type") != "access":
        raise TokenValidationError("El token no es un token de acceso.")

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError("El subject del token no es válido.") from exc
    if user_id <= 0:
        raise TokenValidationError("El subject del token no es válido.")

    username = payload.get("username")
    if username is not None and not isinstance(username, str):
        raise TokenValidationError("El username del token no es válido.")

    roles = _read_string_claim(payload, "roles")
    permissions = _read_string_claim(payload, "permissions")
    expires_at = payload.get("exp")
    if isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)):
        raise TokenValidationError("La expiración del token no es válida.")

    credential_version = payload.get("credential_version", 0)
    if (
        isinstance(credential_version, bool)
        or not isinstance(credential_version, int)
        or credential_version < 0
    ):
        raise TokenValidationError("La versión de credenciales no es válida.")

    return AccessTokenClaims(
        user_id=user_id,
        username=username,
        roles=frozenset(roles),
        permissions=frozenset(permissions),
        expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc),
        credential_version=credential_version,
    )


def _read_string_claim(payload: Mapping[str, Any], name: str) -> list[str]:
    value = payload.get(name, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TokenValidationError(f"El claim {name} no es válido.")
    return _normalize_claim_values(value)
