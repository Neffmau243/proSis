"""Alembic migration environment for the IPRESS MySQL schema.

Importing ``app.models`` registers all SQLAlchemy mappings in one metadata
object.  It does not create tables; only Alembic revision scripts may evolve
the database.
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal, InvalidOperation
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool

# Make `alembic -c <absolute path>` work from any current directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402  # Registers every mapped table.

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
database_url = get_settings().sqlalchemy_database_url


def _normalize_mysql_server_default(value: str | None) -> str | None:
    """Normalize equivalent MySQL default renderings for Alembic autogeneration."""

    if value is None:
        return None

    normalized = re.sub(r"\s+", " ", str(value).strip().casefold())
    while normalized.startswith("(") and normalized.endswith(")"):
        normalized = normalized[1:-1].strip()
    normalized = normalized.replace("now()", "current_timestamp")
    normalized = re.sub(r"^current_timestamp\(\)$", "current_timestamp", normalized)
    normalized = re.sub(
        r"\s+on update current_timestamp(?:\(\))?$", "", normalized
    )

    if normalized in {"true", "1"}:
        return "1"
    if normalized in {"false", "0"}:
        return "0"

    unquoted = normalized.strip("'")
    try:
        return format(Decimal(unquoted).normalize(), "f")
    except InvalidOperation:
        return normalized


def _compare_mysql_server_default(
    _context: object,
    _inspected_column: object,
    _metadata_column: object,
    inspected_default: str | None,
    _metadata_default: object,
    rendered_metadata_default: str | None,
) -> bool | None:
    """Ignore MySQL spelling differences, but delegate genuine changes to Alembic."""

    if _normalize_mysql_server_default(inspected_default) == _normalize_mysql_server_default(
        rendered_metadata_default
    ):
        return False
    return None


def _configure_context(*, connection: Connection | None = None) -> None:
    """Configure shared autogeneration options for online/offline runs."""

    options = {
        "target_metadata": target_metadata,
        "compare_type": True,
        "compare_server_default": _compare_mysql_server_default,
        "transaction_per_migration": True,
    }
    if connection is None:
        context.configure(
            url=database_url,
            literal_binds=True,
            dialect_opts={"paramstyle": "pyformat"},
            **options,
        )
    else:
        context.configure(connection=connection, **options)


def run_migrations_offline() -> None:
    """Generate SQL without connecting to MySQL."""

    _configure_context()
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations through a short-lived, unpooled MySQL connection."""

    connectable = create_engine(database_url, poolclass=NullPool, pool_pre_ping=True)
    with connectable.connect() as connection:
        _configure_context(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
