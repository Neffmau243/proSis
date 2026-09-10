"""ORM model for append-only audit events."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MYSQL_TABLE_OPTIONS

if TYPE_CHECKING:
    from .security import User


class AuditLog(Base):
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    usuario_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "usuarios.id",
            name="fk_auditoria_usuario",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=True,
    )
    tabla_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    registro_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True), nullable=True
    )
    accion: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    datos_anteriores: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    datos_nuevos: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    usuario: Mapped["User | None"] = relationship(back_populates="auditorias")

    __table_args__ = (
        Index("idx_auditoria_tabla_registro", "tabla_nombre", "registro_id"),
        Index("idx_auditoria_fecha", "fecha"),
        MYSQL_TABLE_OPTIONS,
    )
