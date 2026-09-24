"""Read-only source archive; incomplete historical encounters remain intact."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, MYSQL_TABLE_OPTIONS


class LegacyImport(Base):
    __tablename__ = "importaciones_legado"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    huella_fuente: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    version_etl: Mapped[str] = mapped_column(String(30), nullable=False)
    manifiesto: Mapped[dict] = mapped_column(mysql.JSON, nullable=False)
    resumen: Mapped[dict | None] = mapped_column(mysql.JSON, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (MYSQL_TABLE_OPTIONS,)


class LegacyRecord(Base):
    __tablename__ = "registros_legado"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    importacion_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("importaciones_legado.id", ondelete="RESTRICT"), nullable=False)
    tabla_origen: Mapped[str] = mapped_column(String(64), nullable=False)
    fila_origen: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    huella_fila: Mapped[str] = mapped_column(String(64), nullable=False)
    # ASCII-escaped JSON in LONGTEXT also preserves lone Unicode surrogates
    # and control characters that MySQL's native JSON can reject.
    payload_json: Mapped[str] = mapped_column(mysql.LONGTEXT, nullable=False)
    incidencias: Mapped[list] = mapped_column(mysql.JSON, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    destino_tabla: Mapped[str | None] = mapped_column(String(64), nullable=True)
    destino_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("importacion_id", "tabla_origen", "fila_origen", name="uq_legado_fila"),
        Index("ix_legado_estado", "importacion_id", "estado"),
        MYSQL_TABLE_OPTIONS,
    )


class LegacyAttention(Base):
    __tablename__ = "atenciones_legado"

    id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    registro_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("registros_legado.id", ondelete="RESTRICT"), nullable=False, unique=True)
    paciente_id: Mapped[int | None] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=True)
    paciente_registro_id: Mapped[int | None] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("registros_legado.id", ondelete="RESTRICT"), nullable=True)
    profesional_id: Mapped[int | None] = mapped_column(mysql.BIGINT(unsigned=True), ForeignKey("profesionales.id", ondelete="RESTRICT"), nullable=True)
    fecha_atencion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    historia_clinica: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultorio_texto: Mapped[str | None] = mapped_column(String(150), nullable=True)
    profesional_texto: Mapped[str | None] = mapped_column(String(200), nullable=True)
    datos_clinicos: Mapped[dict] = mapped_column(mysql.JSON, nullable=False)
    vinculo_estado: Mapped[str] = mapped_column(String(30), nullable=False)

    __table_args__ = (
        Index("ix_atenciones_legado_paciente_fecha", "paciente_id", "fecha_atencion", "id"),
        MYSQL_TABLE_OPTIONS,
    )
