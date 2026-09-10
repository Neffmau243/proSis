"""Add locked document-number sequences required by RB-06.

Revision ID: 20260909_0002
Revises: 20260909_0001
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "20260909_0002"
down_revision = "20260909_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documento_series",
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("establecimiento_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("periodo", sa.String(length=20), nullable=False),
        sa.Column(
            "siguiente_numero",
            mysql.BIGINT(unsigned=True),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["establecimiento_id"],
            ["establecimientos.id"],
            name="fk_documento_series_establecimiento",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tipo", "establecimiento_id", "periodo"),
        mysql_engine="InnoDB",
    )


def downgrade() -> None:
    op.drop_table("documento_series")
