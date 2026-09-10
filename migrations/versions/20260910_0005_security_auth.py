"""Harden persisted authentication state and login throttling.

Revision ID: 20260910_0005_security_auth
Revises: 20260909_0004
Create Date: 2026-09-10

The account fields enforce progressive lockouts and invalidate pre-password-
change JWTs.  The separate throttle table is keyed only by a server-derived
HMAC fingerprint, never by raw passwords or source IP addresses.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = "20260910_0005_security_auth"
down_revision = "20260909_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "intentos_fallidos_inicio_sesion",
            mysql.SMALLINT(unsigned=True),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "usuarios",
        sa.Column("bloqueado_inicio_sesion_hasta", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "usuarios",
        sa.Column("ultimo_intento_fallido_inicio_sesion_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "usuarios",
        sa.Column(
            "version_credenciales",
            mysql.INTEGER(unsigned=True),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_table(
        "limites_inicio_sesion",
        sa.Column("clave_hash", sa.String(length=64), nullable=False),
        sa.Column("ventana_inicio_at", sa.DateTime(), nullable=False),
        sa.Column(
            "intentos",
            mysql.SMALLINT(unsigned=True),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("bloqueado_hasta", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("clave_hash"),
        mysql_engine="InnoDB",
    )
    op.create_index(
        "idx_limites_inicio_sesion_bloqueado_hasta",
        "limites_inicio_sesion",
        ["bloqueado_hasta"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_limites_inicio_sesion_bloqueado_hasta",
        table_name="limites_inicio_sesion",
    )
    op.drop_table("limites_inicio_sesion")
    op.drop_column("usuarios", "version_credenciales")
    op.drop_column("usuarios", "ultimo_intento_fallido_inicio_sesion_at")
    op.drop_column("usuarios", "bloqueado_inicio_sesion_hasta")
    op.drop_column("usuarios", "intentos_fallidos_inicio_sesion")
