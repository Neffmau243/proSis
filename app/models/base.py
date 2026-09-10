"""Shared SQLAlchemy declarative base for the IPRESS persistence models."""

from sqlalchemy.orm import DeclarativeBase


MYSQL_TABLE_OPTIONS = {"mysql_engine": "InnoDB"}


class Base(DeclarativeBase):
    """Base class imported by the database/session configuration."""

    pass
