"""Safely create the configured MySQL database and apply Alembic revisions.

Run with ``python -m app.scripts.bootstrap_database``.  This command never
drops a database, executes the reference SQL file, or calls ``create_all``.
"""

from __future__ import annotations

from pathlib import Path
import re

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_VALID_DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]{1,64}$")
_SYSTEM_DATABASES = {"information_schema", "mysql", "performance_schema", "sys"}


def _database_name(settings: Settings, database_url: URL) -> str:
    """Return a safe application database identifier from the typed settings."""

    candidate = database_url.database or settings.mysql_database
    if not candidate or not _VALID_DATABASE_NAME.fullmatch(candidate):
        raise ValueError(
            "El nombre de la base debe contener solo letras, números o '_' y tener hasta 64 caracteres."
        )
    if candidate.lower() in _SYSTEM_DATABASES:
        raise ValueError("No se permite inicializar una base de datos interna de MySQL.")
    return candidate


def create_database_if_missing(settings: Settings | None = None) -> str:
    """Create the configured database if necessary, without touching its data."""

    configured_settings = settings or get_settings()
    application_url = make_url(configured_settings.sqlalchemy_database_url)
    if not application_url.drivername.startswith("mysql"):
        raise ValueError("El bootstrap solo admite una URL de conexión MySQL.")

    database_name = _database_name(configured_settings, application_url)
    # ``URL.set(database=None)`` means "do not change this component" in
    # SQLAlchemy.  An empty database produces a server-level MySQL URL (the
    # trailing slash is intentional), which lets this command create a schema
    # that does not exist yet.
    server_url = application_url.set(database="")
    engine = create_engine(
        server_url,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    try:
        with engine.connect() as connection:
            # Identifiers cannot be bind parameters; _database_name constrains
            # the value before it is placed between MySQL identifier quotes.
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
                )
            )
    finally:
        engine.dispose()
    return database_name


def upgrade_to_head() -> None:
    """Apply all revision scripts using the same settings as the application."""

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    command.upgrade(config, "head")


def bootstrap_database() -> None:
    """Create the configured database safely, then migrate it to ``head``."""

    database_name = create_database_if_missing()
    upgrade_to_head()
    print(f"Base de datos '{database_name}' inicializada mediante Alembic.")


if __name__ == "__main__":
    bootstrap_database()
