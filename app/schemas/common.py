"""Shared public HTTP contracts.

These models keep collection pagination and error responses consistent across
the API.  They deliberately describe the HTTP representation rather than an
ORM entity or a domain exception.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


ItemT = TypeVar("ItemT")


class PageResponse(BaseModel, Generic[ItemT]):
    """Offset-paginated collection response.

    ``total`` is evaluated with the same filters as ``items`` so a frontend
    can render a reliable pager.  Clients should not infer another page from
    an incomplete result: use ``has_more`` instead.
    """

    items: list[ItemT]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_more: bool


class ApiErrorDetail(BaseModel):
    """Stable inner error envelope emitted by the global exception handlers."""

    code: str = Field(description="Código estable, apto para decisiones del cliente.")
    message: str = Field(description="Mensaje seguro para mostrar al usuario.")
    details: Any | None = Field(
        default=None,
        description="Metadatos seguros del error; nunca contiene SQL ni secretos.",
    )
    request_id: str | None = Field(
        default=None,
        description="Identificador correlacionable con los registros del servidor.",
    )


class ApiErrorResponse(BaseModel):
    """Public error envelope used for all non-success HTTP responses."""

    error: ApiErrorDetail
