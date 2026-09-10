"""Public exception types and FastAPI handler registration."""

from app.exceptions.domain import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    BusinessRuleViolationError,
    ConflictError,
    DomainError,
    ForbiddenError,
    InfrastructureError,
    NotFoundError,
    ResourceNotFoundError,
    UnauthorizedError,
    ValidationDomainError,
)
from app.exceptions.handlers import register_exception_handlers

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "BusinessRuleError",
    "BusinessRuleViolationError",
    "ConflictError",
    "DomainError",
    "ForbiddenError",
    "InfrastructureError",
    "NotFoundError",
    "ResourceNotFoundError",
    "UnauthorizedError",
    "ValidationDomainError",
    "register_exception_handlers",
]
