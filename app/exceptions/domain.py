"""Domain-level exceptions shared by services and HTTP exception handlers."""

from __future__ import annotations

from typing import Any, ClassVar


class DomainError(Exception):
    """Base exception for an expected application/domain failure.

    Services can raise these errors without importing FastAPI.  The global
    handler turns them into a stable HTTP error envelope.
    """

    status_code: ClassVar[int] = 400
    error_code: ClassVar[str] = "DOMAIN_ERROR"
    default_message: ClassVar[str] = "No se pudo completar la operación."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Any = None,
        code: str | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details
        self.code = code or self.error_code
        super().__init__(self.message)


class ResourceNotFoundError(DomainError):
    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"
    default_message = "El recurso solicitado no fue encontrado."


class ConflictError(DomainError):
    status_code = 409
    error_code = "RESOURCE_CONFLICT"
    default_message = "La operación entra en conflicto con el estado actual del recurso."


class ValidationDomainError(DomainError):
    status_code = 422
    error_code = "DOMAIN_VALIDATION_ERROR"
    default_message = "Los datos no cumplen las validaciones del dominio."


class BusinessRuleError(DomainError):
    status_code = 422
    error_code = "BUSINESS_RULE_VIOLATION"
    default_message = "La operación infringe una regla de negocio."


class AuthenticationError(DomainError):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"
    default_message = "No se pudieron validar las credenciales."


class AuthorizationError(DomainError):
    status_code = 403
    error_code = "AUTHORIZATION_DENIED"
    default_message = "No tiene permisos para realizar esta operación."


class InfrastructureError(DomainError):
    """Expected temporary infrastructure failure safe to expose generically."""

    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"
    default_message = "El servicio no está disponible temporalmente."


# Readable aliases for teams that use Spring-inspired terminology.
NotFoundError = ResourceNotFoundError
UnauthorizedError = AuthenticationError
ForbiddenError = AuthorizationError
BusinessRuleViolationError = BusinessRuleError
