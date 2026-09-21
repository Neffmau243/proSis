"""Freeze FUA print data with the attention; old records remain explicitly null."""

import sqlalchemy as sa
from alembic import op

revision = "20260919_0014_fua_print"
down_revision = "20260918_0013_due_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("atenciones")}
    if "fua_impresion" not in columns:
        op.add_column("atenciones", sa.Column("fua_impresion", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("atenciones")}
    if "fua_impresion" in columns:
        op.drop_column("atenciones", "fua_impresion")
