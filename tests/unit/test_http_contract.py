"""HTTP composition and the single public error envelope.

Persistence failures are the ones a user actually sees during an incident, so
they are asserted here instead of being discovered in production.
"""

from __future__ import annotations

import sys
import types

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.router import (
    api_router,
    health_check,
    include_feature_router,
    include_optional_feature_router,
)
from app.exceptions import register_exception_handlers


def test_health_endpoint_and_route_composition() -> None:
    assert health_check() == {"status": "ok"}

    # Every path/method pair must be unique: a duplicated operation would make
    # one of the two definitions unreachable.
    operations = [
        (route.path, method)
        for route in api_router.routes
        for method in getattr(route, "methods", set())
    ]
    assert len(operations) == len(set(operations))
    assert ("/health", "GET") in operations


def test_feature_router_composition() -> None:
    router = APIRouter()

    @router.get("/demo")
    def demo() -> dict[str, str]:
        return {"ok": "si"}

    before = len(api_router.routes)
    try:
        include_feature_router(router, prefix="/demo", tags=["Demo"])
        assert [route.path for route in api_router.routes[before:]] == ["/demo/demo"]
    finally:
        # The composition boundary is global by design; the probe route is
        # removed so no other test sees it.
        del api_router.routes[before:]


def test_optional_feature_router_skips_missing_modules_and_rejects_bad_ones() -> None:
    before = len(api_router.routes)

    # A feature delivered in a later release is normal: it is skipped, and the
    # same is true when one of its parents is missing.
    include_optional_feature_router("app.controllers.no_existe")
    include_optional_feature_router("app.controllers.no_existe.deep")
    assert len(api_router.routes) == before

    # An existing module that forgot to expose an APIRouter is a real error.
    sys.modules["modulo_roto"] = types.ModuleType("modulo_roto")
    try:
        with pytest.raises(TypeError, match="APIRouter"):
            include_optional_feature_router("modulo_roto")
    finally:
        sys.modules.pop("modulo_roto", None)
    assert len(api_router.routes) == before


def _error_app() -> TestClient:
    """Bare application: only the shared handlers must answer."""

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/conflicto")
    def conflicto() -> None:
        raise IntegrityError("INSERT", {}, Exception("Duplicate entry 'x' for key 'uq'"))

    @app.get("/sin-base")
    def sin_base() -> None:
        raise OperationalError("SELECT", {}, Exception("Can't connect to MySQL server"))

    @app.get("/inesperado")
    def inesperado() -> None:
        raise RuntimeError("fallo interno con detalles")

    return TestClient(app, raise_server_exceptions=False)


def test_persistence_failures_never_leak_sql() -> None:
    client = _error_app()

    conflict = client.get("/conflicto")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "PERSISTENCE_CONFLICT"
    assert "Duplicate" not in conflict.text

    unavailable = client.get("/sin-base")
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "MySQL" not in unavailable.text

    unexpected = client.get("/inesperado")
    assert unexpected.status_code == 500
    assert unexpected.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "detalles" not in unexpected.text


def test_unknown_routes_and_methods_use_the_same_envelope() -> None:
    from app.main import app

    client = TestClient(app)

    missing = client.get("/api/v1/no-existe")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    wrong_method = client.delete("/api/v1/health")
    assert wrong_method.status_code == 405
    assert wrong_method.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_request_id_is_echoed_and_untrusted_values_are_replaced() -> None:
    from app.main import app

    client = TestClient(app)

    accepted = client.get("/api/v1/health", headers={"X-Request-ID": "abc-123_ok"})
    assert accepted.headers["X-Request-ID"] == "abc-123_ok"

    # A header with spaces or control characters is replaced by a generated
    # identifier: it is echoed to clients and written to logs.
    untrusted = client.get("/api/v1/health", headers={"X-Request-ID": "no vale con espacios"})
    assert untrusted.headers["X-Request-ID"]
    assert untrusted.headers["X-Request-ID"] != "no vale con espacios"

    generated = client.get("/api/v1/health")
    assert generated.headers["X-Request-ID"]
    assert generated.headers["X-Request-ID"] != accepted.headers["X-Request-ID"]


def test_openapi_documents_the_error_envelope_for_every_operation() -> None:
    from app.main import app

    schema = TestClient(app).get("/openapi.json").json()
    documented = {"400", "401", "403", "404", "409", "422", "429", "500", "503"}

    assert schema["paths"], "La aplicación debe exponer operaciones"
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            responses = set(operation.get("responses", {}))
            assert documented <= responses, f"{method.upper()} {path} documenta {responses}"
