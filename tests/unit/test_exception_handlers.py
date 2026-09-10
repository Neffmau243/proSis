from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.exceptions import BusinessRuleError, register_exception_handlers
from app.services.auth import LoginRateLimitError


def test_domain_errors_have_one_public_envelope() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/falla")
    def fail() -> None:
        raise BusinessRuleError(code="REGLA_DEMO", message="Regla no cumplida.")

    response = TestClient(app).get("/falla")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "REGLA_DEMO",
            "message": "Regla no cumplida.",
            "details": None,
            "request_id": None,
        }
    }


def test_login_rate_limit_exposes_a_safe_retry_after_header() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/login-limitado")
    def fail() -> None:
        raise LoginRateLimitError(42)

    response = TestClient(app).get("/login-limitado")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "42"
    assert response.json()["error"]["code"] == "LOGIN_RATE_LIMITED"
