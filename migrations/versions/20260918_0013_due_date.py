"""Persist the estimated delivery date for a pregnant person.

Revision ID: 20260918_0013_due_date
Revises: 20260918_0012_pregnancy
Create Date: 2026-09-18

For the ``GESTANTES`` care group the admission form replaces the abdominal
perimeter with the estimated delivery date, so it needs its own nullable column.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260918_0013_due_date"
down_revision = "20260918_0012_pregnancy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MySQL DDL is non-transactional: the guard keeps a retry safe if an
    # interrupted deployment added the column before Alembic stamped it.
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("atenciones")
    }
    if "fecha_probable_parto" not in columns:
        op.add_column(
            "atenciones",
            sa.Column("fecha_probable_parto", sa.Date(), nullable=True),
        )


def downgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("atenciones")
    }
    if "fecha_probable_parto" in columns:
        op.drop_column("atenciones", "fecha_probable_parto")
