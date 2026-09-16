"""ORM models for SIEN surveillance and nutritional assessments."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MYSQL_TABLE_OPTIONS

if TYPE_CHECKING:
    from .clinical import Attention
    from .organization import Establishment
    from .patient import Patient


class SurveillanceSien(Base):
    __tablename__ = "vigilancia_sien"

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    paciente_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "pacientes.id",
            name="fk_sien_paciente",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    atencion_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "atenciones.id",
            name="fk_sien_atencion",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=True,
    )
    establecimiento_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "establecimientos.id",
            name="fk_sien_establecimiento",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    peso_kg: Mapped[Decimal | None] = mapped_column(
        mysql.DECIMAL(6, 2), nullable=True
    )
    talla_cm: Mapped[Decimal | None] = mapped_column(
        mysql.DECIMAL(6, 2), nullable=True
    )
    hemoglobina: Mapped[Decimal | None] = mapped_column(
        mysql.DECIMAL(5, 2), nullable=True
    )
    fecha_hemoglobina: Mapped[date | None] = mapped_column(Date, nullable=True)
    enviado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    estado: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'PENDIENTE'")
    )

    paciente: Mapped["Patient"] = relationship(back_populates="vigilancia_sien")
    atencion: Mapped["Attention | None"] = relationship(
        back_populates="vigilancia_sien"
    )
    establecimiento: Mapped["Establishment"] = relationship(
        back_populates="vigilancia_sien"
    )

    __table_args__ = (
        Index("idx_sien_paciente_fecha", "paciente_id", "fecha"),
        MYSQL_TABLE_OPTIONS,
    )


class NutritionalEvaluation(Base):
    __tablename__ = "evaluaciones_nutricionales"

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    paciente_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "pacientes.id",
            name="fk_nutricion_paciente",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    atencion_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "atenciones.id",
            name="fk_nutricion_atencion",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=True,
    )
    establecimiento_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "establecimientos.id",
            name="fk_nutricion_establecimiento",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    peso_kg: Mapped[Decimal | None] = mapped_column(
        mysql.DECIMAL(6, 2), nullable=True
    )
    talla_cm: Mapped[Decimal | None] = mapped_column(
        mysql.DECIMAL(6, 2), nullable=True
    )
    hemoglobina: Mapped[Decimal | None] = mapped_column(
        mysql.DECIMAL(5, 2), nullable=True
    )
    fecha_hemoglobina: Mapped[date | None] = mapped_column(Date, nullable=True)
    edad_anios: Mapped[int | None] = mapped_column(
        mysql.SMALLINT(unsigned=True), nullable=True
    )
    edad_meses: Mapped[int | None] = mapped_column(
        mysql.TINYINT(unsigned=True), nullable=True
    )
    edad_dias: Mapped[int | None] = mapped_column(
        mysql.TINYINT(unsigned=True), nullable=True
    )
    edad_gestacional_semanas: Mapped[int | None] = mapped_column(
        mysql.SMALLINT(unsigned=True), nullable=True
    )
    perimetro_abdominal_cm: Mapped[Decimal | None] = mapped_column(
        mysql.DECIMAL(6, 2), nullable=True
    )
    imc: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(6, 3), nullable=True)
    whz: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(6, 3), nullable=True)
    haz: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(6, 3), nullable=True)
    waz: Mapped[Decimal | None] = mapped_column(mysql.DECIMAL(6, 3), nullable=True)
    diagnostico_peso_edad: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    diagnostico_talla_edad: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    diagnostico_peso_talla: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    diagnostico: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enviado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )

    paciente: Mapped["Patient"] = relationship(
        back_populates="evaluaciones_nutricionales"
    )
    atencion: Mapped["Attention | None"] = relationship(
        back_populates="evaluaciones_nutricionales"
    )
    establecimiento: Mapped["Establishment"] = relationship(
        back_populates="evaluaciones_nutricionales"
    )

    __table_args__ = (
        Index("idx_nutricion_paciente_fecha", "paciente_id", "fecha"),
        Index("idx_nutricion_tipo_fecha", "tipo", "fecha"),
        MYSQL_TABLE_OPTIONS,
    )
