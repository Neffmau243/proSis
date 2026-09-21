"""Guards of the operational bootstrap command.

``bootstrap_database`` creates a schema with a dynamic ``CREATE DATABASE``
statement, so its identifier validation and dialect checks are security
boundaries and are asserted before any connection is opened.
"""

from __future__ import annotations

import pytest
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.scripts.bootstrap_database import (
    _database_name,
    create_database_if_missing,
    upgrade_to_head,
)


def _settings(**overrides: object) -> Settings:
    return Settings(**overrides)  # type: ignore[arg-type]


def _url(database: str, driver: str = "mysql+pymysql") -> object:
    return make_url(f"{driver}://usuario:clave@localhost:3306/{database}")


@pytest.mark.parametrize(
    "database",
    ["sistema_salud_ipress", "ipress_test", "Base123"],
)
def test_valid_database_names_are_returned_unchanged(database: str) -> None:
    assert _database_name(_settings(), _url(database)) == database  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "database",
    [
        "ipress; DROP DATABASE x",  # statement injection through the identifier
        "ipress-test",
        "ipress test",
        "ipress`test",
        "ñandu",
        "a" * 65,
    ],
)
def test_unsafe_database_names_are_rejected(database: str) -> None:
    with pytest.raises(ValueError, match="letras, números"):
        _database_name(_settings(), _url(database))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "database",
    ["mysql", "MYSQL", "information_schema", "performance_schema", "sys"],
)
def test_mysql_internal_schemas_are_never_initialized(database: str) -> None:
    with pytest.raises(ValueError, match="base de datos interna"):
        _database_name(_settings(), _url(database))  # type: ignore[arg-type]


def test_configuration_database_is_used_when_the_url_omits_it() -> None:
    settings = _settings(mysql_database="ipress_from_settings")

    assert _database_name(settings, make_url("mysql+pymysql://root@localhost/")) == (
        "ipress_from_settings"
    )


def test_bootstrap_refuses_a_non_mysql_url_before_connecting() -> None:
    class _NonMySqlSettings:
        # ``Settings`` itself validates the MySQL prefix, so the dialect guard is
        # asserted with any object that exposes the resolved connection string.
        sqlalchemy_database_url = "postgresql+psycopg://usuario@localhost/ipress_test"
        mysql_database = "ipress_test"

    with pytest.raises(ValueError, match="solo admite una URL de conexión MySQL"):
        create_database_if_missing(_NonMySqlSettings())  # type: ignore[arg-type]


def test_upgrade_to_head_targets_the_configured_alembic_scripts(monkeypatch) -> None:
    calls: list[tuple[object, str]] = []

    def fake_upgrade(config: object, revision: str) -> None:
        calls.append((config, revision))

    monkeypatch.setattr("app.scripts.bootstrap_database.command.upgrade", fake_upgrade)

    upgrade_to_head()

    assert len(calls) == 1
    _, revision = calls[0]
    assert revision == "head"
