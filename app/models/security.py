"""ORM models for health professionals, users, and role assignments."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MYSQL_TABLE_OPTIONS

if TYPE_CHECKING:
    from .audit import AuditLog
    from .catalog import Profession, Specialty
    from .clinical import Attention
    from .documents import Certificate
    from .organization import OfficeProfessional


class Professional(Base):
    __tablename__ = "profesionales"

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    codigo_legacy: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True), nullable=True
    )
    numero_documento: Mapped[str | None] = mapped_column(String(30), nullable=True)
    nombre_completo: Mapped[str] = mapped_column(String(200), nullable=False)
    profesion_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "profesiones.id",
            name="fk_profesionales_profesion",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=True,
    )
    colegiatura: Mapped[str | None] = mapped_column(String(50), nullable=True)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("TRUE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    profesion: Mapped["Profession | None"] = relationship(
        back_populates="profesionales"
    )
    especialidades: Mapped[list["ProfessionalSpecialty"]] = relationship(
        back_populates="profesional"
    )
    asignaciones_consultorio: Mapped[list["OfficeProfessional"]] = relationship(
        back_populates="profesional"
    )
    usuario: Mapped["User | None"] = relationship(
        back_populates="profesional", uselist=False
    )
    atenciones: Mapped[list["Attention"]] = relationship(
        back_populates="profesional"
    )
    certificados: Mapped[list["Certificate"]] = relationship(
        back_populates="profesional",
        overlaps="atencion,certificados",
    )

    __table_args__ = (
        UniqueConstraint("codigo_legacy", name="uq_profesionales_legacy"),
        UniqueConstraint("numero_documento", name="uq_profesionales_documento"),
        MYSQL_TABLE_OPTIONS,
    )


class ProfessionalSpecialty(Base):
    __tablename__ = "profesional_especialidades"

    profesional_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "profesionales.id",
            name="fk_profesional_especialidades_profesional",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        primary_key=True,
    )
    especialidad_codigo: Mapped[str] = mapped_column(
        String(20),
        ForeignKey(
            "especialidades.codigo",
            name="fk_profesional_especialidades_especialidad",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        primary_key=True,
    )
    es_principal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )

    profesional: Mapped["Professional"] = relationship(back_populates="especialidades")
    especialidad: Mapped["Specialty"] = relationship(
        "Specialty", back_populates="profesionales_especialidad"
    )

    __table_args__ = (MYSQL_TABLE_OPTIONS,)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)

    asignaciones_usuario: Mapped[list["UserRole"]] = relationship(back_populates="rol")

    __table_args__ = (
        UniqueConstraint("codigo", name="uq_roles_codigo"),
        MYSQL_TABLE_OPTIONS,
    )


class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    profesional_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "profesionales.id",
            name="fk_usuarios_profesional",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=True,
    )
    nombre_usuario: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("TRUE")
    )
    ultimo_acceso_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    intentos_fallidos_inicio_sesion: Mapped[int] = mapped_column(
        mysql.SMALLINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    bloqueado_inicio_sesion_hasta: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    ultimo_intento_fallido_inicio_sesion_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    # Every password change or administrator reset increments this version.
    # Access tokens carry the version issued at login, so stale sessions are
    # rejected immediately without maintaining a token blacklist.
    version_credenciales: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    profesional: Mapped["Professional | None"] = relationship(
        back_populates="usuario"
    )
    roles_usuario: Mapped[list["UserRole"]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    # Role assignment writes belong to the UserRole association entity.  This
    # read-only convenience relationship avoids hiding that persistence rule.
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="usuario_roles",
        viewonly=True,
        overlaps="roles_usuario,usuario,rol,asignaciones_usuario",
    )
    atenciones_creadas: Mapped[list["Attention"]] = relationship(
        back_populates="created_by_usuario"
    )
    auditorias: Mapped[list["AuditLog"]] = relationship(back_populates="usuario")

    __table_args__ = (
        UniqueConstraint("nombre_usuario", name="uq_usuarios_nombre_usuario"),
        UniqueConstraint("profesional_id", name="uq_usuarios_profesional"),
        MYSQL_TABLE_OPTIONS,
    )


class LoginRateLimit(Base):
    """Persisted login-throttle state keyed by non-reversible fingerprints.

    The application stores neither submitted passwords nor raw client IPs in
    this table.  ``clave_hash`` is a HMAC derived from the submitted username
    and source address, which still lets the authentication service enforce a
    rate window across multiple API workers.
    """

    __tablename__ = "limites_inicio_sesion"

    clave_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    ventana_inicio_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    intentos: Mapped[int] = mapped_column(
        mysql.SMALLINT(unsigned=True),
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_limites_inicio_sesion_bloqueado_hasta", "bloqueado_hasta"),
        MYSQL_TABLE_OPTIONS,
    )


class UserRole(Base):
    __tablename__ = "usuario_roles"

    usuario_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "usuarios.id",
            name="fk_usuario_roles_usuario",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        primary_key=True,
    )
    rol_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "roles.id",
            name="fk_usuario_roles_rol",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        primary_key=True,
    )

    usuario: Mapped["User"] = relationship(back_populates="roles_usuario")
    rol: Mapped["Role"] = relationship(back_populates="asignaciones_usuario")

    __table_args__ = (MYSQL_TABLE_OPTIONS,)
