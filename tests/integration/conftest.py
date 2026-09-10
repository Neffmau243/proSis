"""Opt-in MySQL integration fixture.

Set TEST_DATABASE_URL to a disposable database whose name contains `test`.
This guard ensures the test suite never migrates or drops a production schema.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

from app.core.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def migrated_mysql_engine() -> Engine:
    test_url = os.getenv("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("Defina TEST_DATABASE_URL para ejecutar integración MySQL.")
    parsed = make_url(test_url)
    if not parsed.drivername.startswith("mysql") or not parsed.database or "test" not in parsed.database.lower():
        raise RuntimeError("TEST_DATABASE_URL debe apuntar a una base MySQL desechable cuyo nombre incluya 'test'.")

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url
    get_settings.cache_clear()
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    command.upgrade(config, "head")
    engine = create_engine(test_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        get_settings.cache_clear()
