"""Request-scoped database session lifecycle.

A leaked or dirty connection is the classic source of "phantom" data between
requests, so the dependency contract is asserted directly.
"""

from __future__ import annotations


import pytest

import app.core.database as database_module
from app.core.config import get_settings
from app.core.database import engine, get_db


class _FakeSession:
    def __init__(self) -> None:
        self.rollbacks = 0
        self.closes = 0

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closes += 1


def test_get_db_yields_one_session_and_always_closes_it(monkeypatch) -> None:
    session = _FakeSession()
    monkeypatch.setattr(database_module, "SessionLocal", lambda: session)

    dependency = get_db()
    assert next(dependency) is session

    with pytest.raises(StopIteration):
        next(dependency)

    assert (session.rollbacks, session.closes) == (0, 1)


def test_get_db_rolls_back_a_failed_request_and_reraises(monkeypatch) -> None:
    session = _FakeSession()
    monkeypatch.setattr(database_module, "SessionLocal", lambda: session)

    dependency = get_db()
    next(dependency)

    # A failure raised by the endpoint must reach the client untouched and
    # leave no open transaction on the pooled connection.
    with pytest.raises(RuntimeError, match="endpoint roto"):
        dependency.throw(RuntimeError("endpoint roto"))

    assert (session.rollbacks, session.closes) == (1, 1)


def test_session_factory_owns_transaction_boundaries() -> None:
    settings = get_settings()

    assert str(engine.url).startswith("mysql+pymysql://")
    assert engine.url.database == settings.mysql_database
    assert engine.pool.size() == settings.db_pool_size  # type: ignore[attr-defined]

    factory = database_module.SessionLocal
    assert factory.kw["autoflush"] is False
    assert factory.kw["autocommit"] is False
    # Services read the aggregate right after committing it.
    assert factory.kw["expire_on_commit"] is False
