"""Allow diagnostic-only nutritional snapshots.

Revision ID: 20260912_0008_nutrition_tipo
Revises: 20260912_0007_nutrition
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260912_0008_nutrition_tipo"
down_revision = "20260912_0007_nutrition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]: column
        for column in sa.inspect(op.get_bind()).get_columns("evaluaciones_nutricionales")
    }
    tipo = columns.get("tipo")
    if tipo is not None and not tipo["nullable"]:
        op.alter_column(
            "evaluaciones_nutricionales",
            "tipo",
            existing_type=sa.String(length=20),
            nullable=True,
        )


def downgrade() -> None:
    columns = {
        column["name"]: column
        for column in sa.inspect(op.get_bind()).get_columns("evaluaciones_nutricionales")
    }
    tipo = columns.get("tipo")
    if tipo is not None and tipo["nullable"]:
        op.alter_column(
            "evaluaciones_nutricionales",
            "tipo",
            existing_type=sa.String(length=20),
            nullable=False,
        )
