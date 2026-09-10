"""Contracts for authentication and administrator-managed users."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.authorization import ASSIGNABLE_ROLE_CODES


def _validate_assignable_roles(roles: list[str]) -> list[str]:
    """Keep the public user contract aligned with the authorization policy."""

    unsupported = set(roles) - ASSIGNABLE_ROLE_CODES
    if unsupported:
        allowed = ", ".join(sorted(ASSIGNABLE_ROLE_CODES))
        requested = ", ".join(sorted(unsupported))
        raise ValueError(f"Roles no habilitados: {requested}. Roles permitidos: {allowed}.")
    if len(set(roles)) != len(roles):
        raise ValueError("No se puede repetir un rol en la misma solicitud.")
    return roles


def _validate_password_byte_length(password: str) -> str:
    """Mirror bcrypt's byte limit at the HTTP boundary.

    Pydantic's ``max_length`` counts characters, whereas bcrypt truncates by
    UTF-8 bytes. Rejecting oversized input here prevents two distinct Unicode
    values from being silently treated as the same password.
    """

    if len(password.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar 72 bytes UTF-8.")
    return password


class LoginRequest(BaseModel):
    nombre_usuario: Annotated[str, Field(min_length=1, max_length=100)]
    password: Annotated[str, Field(min_length=1, max_length=72)]

    @field_validator("nombre_usuario", mode="before")
    @classmethod
    def normalize_username(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def validate_password_byte_length(cls, value: str) -> str:
        return _validate_password_byte_length(value)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario_id: int
    roles: list[str]
    permisos: list[str]


class UserCreate(BaseModel):
    profesional_id: Annotated[int, Field(gt=0)] | None = None
    nombre_usuario: Annotated[str, Field(min_length=3, max_length=100)]
    password: Annotated[str, Field(min_length=12, max_length=72)]
    roles: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(min_length=1)

    @field_validator("nombre_usuario", "roles", mode="before")
    @classmethod
    def trim_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            return [item.strip().upper() if isinstance(item, str) else item for item in value]
        return value

    @field_validator("roles")
    @classmethod
    def validate_assignable_roles(cls, value: list[str]) -> list[str]:
        return _validate_assignable_roles(value)

    @field_validator("password")
    @classmethod
    def validate_password_byte_length(cls, value: str) -> str:
        return _validate_password_byte_length(value)


class UserRolesUpdate(BaseModel):
    roles: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(min_length=1)

    @field_validator("roles", mode="before")
    @classmethod
    def normalize_roles(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [item.strip().upper() if isinstance(item, str) else item for item in value]
        return value

    @field_validator("roles")
    @classmethod
    def validate_assignable_roles(cls, value: list[str]) -> list[str]:
        return _validate_assignable_roles(value)


class _NewPasswordRequest(BaseModel):
    new_password: Annotated[str, Field(min_length=12, max_length=72)]
    new_password_confirmation: Annotated[str, Field(min_length=12, max_length=72)]

    @field_validator("new_password", "new_password_confirmation")
    @classmethod
    def validate_password_byte_length(cls, value: str) -> str:
        return _validate_password_byte_length(value)

    @model_validator(mode="after")
    def passwords_match(self) -> "_NewPasswordRequest":
        if self.new_password != self.new_password_confirmation:
            raise ValueError("La confirmación de contraseña no coincide.")
        return self


class PasswordChangeRequest(_NewPasswordRequest):
    current_password: Annotated[str, Field(min_length=1, max_length=72)]

    @field_validator("current_password")
    @classmethod
    def validate_current_password_byte_length(cls, value: str) -> str:
        return _validate_password_byte_length(value)


class PasswordResetRequest(_NewPasswordRequest):
    """Administrator-issued credential reset for another active account."""


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profesional_id: int | None
    nombre_usuario: str
    activo: bool
    ultimo_acceso_at: datetime | None
    created_at: datetime
    updated_at: datetime
    roles: list[str] = Field(default_factory=list)
