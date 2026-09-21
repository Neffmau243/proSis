"""Access-token and credential primitives.

A weak claim check is an authentication bypass, so every rejection path of the
validator is asserted with a token signed by the real configured secret.
"""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    TokenValidationError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def _reencode(token: str, **overrides: object) -> str:
    """Re-sign a valid token with modified claims, using the real secret."""

    settings = get_settings()
    payload = jwt.decode(token, options={"verify_signature": False})
    for key, value in overrides.items():
        if value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    return jwt.encode(
        payload, settings.secret_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def _token() -> str:
    return create_access_token(
        user_id=7,
        username="medico.demo",
        roles=["PROFESIONAL", "PROFESIONAL", " "],
        permissions=["ATENCION_LEER"],
    )


def test_token_round_trip_normalizes_claims() -> None:
    claims = decode_access_token(_token())

    assert claims.user_id == 7
    assert claims.username == "medico.demo"
    assert claims.roles == frozenset({"PROFESIONAL"})
    assert claims.permissions == frozenset({"ATENCION_LEER"})
    assert claims.credential_version == 0
    assert claims.expires_at > claims.expires_at.replace(year=claims.expires_at.year - 1)


def test_single_string_claims_are_accepted_as_one_value() -> None:
    token = create_access_token(user_id=1, roles="ADMIN", permissions="PACIENTE_LEER")

    claims = decode_access_token(token)

    assert claims.roles == frozenset({"ADMIN"})
    assert claims.permissions == frozenset({"PACIENTE_LEER"})


def test_creation_rejects_invalid_identities_and_lifetimes() -> None:
    with pytest.raises(ValueError, match="user_id"):
        create_access_token(user_id=0)
    with pytest.raises(ValueError, match="user_id"):
        create_access_token(user_id=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="credential_version"):
        create_access_token(user_id=1, credential_version=-1)
    with pytest.raises(ValueError, match="duración"):
        create_access_token(user_id=1, expires_delta=timedelta(0))
    with pytest.raises(ValueError, match="reservados"):
        create_access_token(user_id=1, extra_claims={"sub": "999", "nota": "x"})


def test_tampered_expired_and_foreign_tokens_are_rejected() -> None:
    settings = get_settings()
    token = _token()

    assert decode_access_token(token).user_id == 7

    foreign = jwt.encode(
        jwt.decode(token, options={"verify_signature": False}),
        "otro-secreto-de-pruebas-suficientemente-largo",
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenValidationError):
        decode_access_token(foreign)
    with pytest.raises(TokenValidationError):
        decode_access_token(token[:-2] + "xx")
    with pytest.raises(TokenValidationError):
        decode_access_token("no-es-un-jwt")

    with pytest.raises(TokenValidationError):
        decode_access_token(_reencode(token, exp=1))
    with pytest.raises(ValueError, match="reservados"):
        create_access_token(user_id=1, extra_claims={"aud": "otro-audience"})

    with pytest.raises(TokenValidationError):
        decode_access_token(
            jwt.encode(
                {**jwt.decode(token, options={"verify_signature": False}), "aud": "otro-audience"},
                settings.secret_key.get_secret_value(),
                algorithm=settings.jwt_algorithm,
            )
        )
    with pytest.raises(TokenValidationError):
        decode_access_token(
            jwt.encode(
                {**jwt.decode(token, options={"verify_signature": False}), "iss": "otro-emisor"},
                settings.secret_key.get_secret_value(),
                algorithm=settings.jwt_algorithm,
            )
        )


def test_missing_and_malformed_claims_are_rejected() -> None:
    token = _token()

    for missing in ("sub", "iat", "nbf", "exp", "iss", "aud"):
        with pytest.raises(TokenValidationError):
            decode_access_token(_reencode(token, **{missing: None}))

    with pytest.raises(TokenValidationError, match="token de acceso"):
        decode_access_token(_reencode(token, type="refresh"))
    with pytest.raises(TokenValidationError, match="subject"):
        decode_access_token(_reencode(token, sub="abc"))
    with pytest.raises(TokenValidationError, match="subject"):
        decode_access_token(_reencode(token, sub="-3"))
    with pytest.raises(TokenValidationError, match="username"):
        decode_access_token(_reencode(token, username=123))
    with pytest.raises(TokenValidationError, match="roles"):
        decode_access_token(_reencode(token, roles="ADMIN"))
    with pytest.raises(TokenValidationError, match="permissions"):
        decode_access_token(_reencode(token, permissions=[1, 2]))
    # PyJWT validates ``exp`` as an integer before the application-level claim
    # check, so a malformed expiry surfaces as a generic invalid token.
    with pytest.raises(TokenValidationError, match="Token inválido"):
        decode_access_token(_reencode(token, exp="mañana"))
    with pytest.raises(TokenValidationError, match="credenciales"):
        decode_access_token(_reencode(token, credential_version="2"))
    with pytest.raises(TokenValidationError, match="credenciales"):
        decode_access_token(_reencode(token, credential_version=-1))


def test_declared_permissions_are_returned_for_the_principal() -> None:
    token = create_access_token(
        user_id=3, roles=["ADMIN"], permissions=["PACIENTE_LEER", "USUARIO_GESTIONAR"]
    )

    claims = decode_access_token(token)

    assert claims.permissions == frozenset({"PACIENTE_LEER", "USUARIO_GESTIONAR"})
    assert claims.username is None


def test_password_hash_round_trip_and_safe_failures() -> None:
    hashed = hash_password("12345678")

    assert hashed.startswith("$2b$")
    assert hashed != "12345678"
    assert verify_password("12345678", hashed) is True
    assert verify_password("87654321", hashed) is False

    # Malformed, missing or non-ascii inputs answer False instead of raising.
    assert verify_password("12345678", "no-es-un-hash") is False
    assert verify_password("12345678", "") is False
    assert verify_password("1234567", hashed) is False
    assert verify_password("1234abcd", hashed) is False
    assert hash_password("12345678") != hashed
