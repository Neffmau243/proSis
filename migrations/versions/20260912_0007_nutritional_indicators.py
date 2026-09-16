"""Persist server-calculated nutritional indicators for every attention.

Revision ID: 20260912_0007_nutrition
Revises: 20260910_0006_clinical_integrity
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "20260912_0007_nutrition"
down_revision = "20260910_0006_clinical_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MySQL DDL is non-transactional. These guards make a retry safe if an
    # interrupted deployment added a column before Alembic updated its stamp.
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("atenciones")}
    if "imc" not in columns:
        op.add_column("atenciones", sa.Column("imc", mysql.DECIMAL(6, 3), nullable=True))
    if "referencia_nutricional" not in columns:
        op.add_column(
            "atenciones",
            sa.Column("referencia_nutricional", sa.String(80), nullable=True),
        )


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("atenciones")}
    if "referencia_nutricional" in columns:
        op.drop_column("atenciones", "referencia_nutricional")
    if "imc" in columns:
        op.drop_column("atenciones", "imc")
