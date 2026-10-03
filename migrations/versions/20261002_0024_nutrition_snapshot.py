"""Preserve the age-appropriate nutritional calculation per encounter."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "20261002_0024_nutrition_snapshot"
down_revision = "20260929_0023_nutrition_risks"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("atenciones", sa.Column("valoracion_calculada", mysql.JSON(), nullable=True))


def downgrade():
    op.drop_column("atenciones", "valoracion_calculada")
