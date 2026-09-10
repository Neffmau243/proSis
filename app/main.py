"""FastAPI application factory and HTTP cross-cutting configuration."""

from __future__ import annotations

import re
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.api.router import api_router
from app.core.config import get_settings
from app.exceptions import register_exception_handlers

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _request_id_from(request: Request) -> str:
    supplied = request.headers.get("X-Request-ID", "")
    if _SAFE_REQUEST_ID.fullmatch(supplied):
        return supplied
    return uuid4().hex


def create_app() -> FastAPI:
    """Build the API without opening a database connection at import time."""

    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
    )

    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )

    @application.middleware("http")
    async def attach_request_id(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.request_id = _request_id_from(request)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
