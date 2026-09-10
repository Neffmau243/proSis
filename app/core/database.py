"""Synchronous SQLAlchemy engine and per-request session dependency."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.base import Base

# ``Base`` lives with the ORM models so every model shares the same metadata.
# It is re-exported here because infrastructure consumers commonly import it
# from the database module.
__all__ = ["Base", "SessionLocal", "engine", "get_db"]


def _build_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.sqlalchemy_database_url,
        echo=settings.sqlalchemy_echo,
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )


engine = _build_engine()
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield one synchronous session and always release its connection.

    Services own transaction boundaries (normally ``with session.begin():``),
    so this dependency never commits implicitly.  A failed request is rolled
    back to ensure a pooled connection is clean for its next use.

    Schema creation and evolution are intentionally owned by Alembic
    migrations, never by ``Base.metadata.create_all`` at application startup.
    """

    session = SessionLocal()
    try:
        yield session
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
