"""OpenAPI-only contract helpers shared by feature routers."""

from __future__ import annotations

from typing import Any

from app.schemas.common import ApiErrorResponse


def documented_error_responses() -> dict[int, dict[str, Any]]:
    """Return fresh error response metadata for every API operation.

    The runtime error envelope is emitted by ``app.exceptions.handlers``.
    Keeping this declaration at router-composition level prevents a new
    endpoint from accidentally publishing FastAPI's default error body.
    """

    return {
        400: {"model": ApiErrorResponse, "description": "Solicitud inválida."},
        401: {"model": ApiErrorResponse, "description": "Autenticación requerida o inválida."},
        403: {"model": ApiErrorResponse, "description": "Operación no autorizada."},
        404: {"model": ApiErrorResponse, "description": "Recurso no encontrado."},
        409: {"model": ApiErrorResponse, "description": "Conflicto con el estado actual."},
        422: {"model": ApiErrorResponse, "description": "Solicitud o regla de dominio inválida."},
        429: {"model": ApiErrorResponse, "description": "Demasiadas solicitudes."},
        500: {"model": ApiErrorResponse, "description": "Error interno seguro."},
        503: {"model": ApiErrorResponse, "description": "Servicio de datos no disponible."},
    }
