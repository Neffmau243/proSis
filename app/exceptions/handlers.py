"""Centralized, non-leaking HTTP exception handling."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.domain import AuthenticationError, DomainError

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_body(
    request: Request,
    *,
    code: str,
    message: str,
    details: Any = None,
) -> dict[str, dict[str, Any]]:
    """Build the one error shape exposed by the API."""

    return {
        "error": {
            "code": code,
            "message": message,
            "details": jsonable_encoder(details),
            "request_id": _request_id(request),
        }
    }


def _validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Expose useful validation metadata without echoing submitted values."""

    return [
        {
            "field": ".".join(str(part) for part in error.get("loc", ())),
            "message": error.get("msg", "Valor inválido."),
            "type": error.get("type", "validation_error"),
        }
        for error in exc.errors()
    ]


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers once while the FastAPI application is assembled."""

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        headers: dict[str, str] = {}
        if isinstance(exc, AuthenticationError):
            headers["WWW-Authenticate"] = "Bearer"
        retry_after = getattr(exc, "retry_after_seconds", None)
        if isinstance(retry_after, int) and retry_after > 0:
            headers["Retry-After"] = str(retry_after)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                request,
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
            headers=headers or None,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                request,
                code="REQUEST_VALIDATION_ERROR",
                message="La solicitud contiene datos inválidos.",
                details=_validation_details(exc),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code_by_status = {
            400: "BAD_REQUEST",
            401: "AUTHENTICATION_FAILED",
            403: "AUTHORIZATION_DENIED",
            404: "RESOURCE_NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "RESOURCE_CONFLICT",
            422: "REQUEST_VALIDATION_ERROR",
            429: "RATE_LIMITED",
        }
        detail = exc.detail
        message = detail if isinstance(detail, str) else "La solicitud no pudo procesarse."
        details = None if isinstance(detail, str) else detail
        headers = dict(exc.headers) if exc.headers else None
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                request,
                code=code_by_status.get(exc.status_code, "HTTP_ERROR"),
                message=message,
                details=details,
            ),
            headers=headers,
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        # Do not expose database constraint names, SQL statements, or values.
        logger.warning("Integrity error. request_id=%s", _request_id(request))
        return JSONResponse(
            status_code=409,
            content=error_body(
                request,
                code="PERSISTENCE_CONFLICT",
                message="La operación entra en conflicto con datos existentes.",
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqlalchemy_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error. request_id=%s", _request_id(request))
        return JSONResponse(
            status_code=503,
            content=error_body(
                request,
                code="DATABASE_UNAVAILABLE",
                message="No se pudo completar la operación de datos.",
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error. request_id=%s", _request_id(request))
        return JSONResponse(
            status_code=500,
            content=error_body(
                request,
                code="INTERNAL_SERVER_ERROR",
                message="Ocurrió un error interno. Intente nuevamente más tarde.",
            ),
        )
