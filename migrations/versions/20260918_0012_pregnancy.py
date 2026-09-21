"""Persist the obstetric measurements recorded for a pregnant person.

Revision ID: 20260918_0012_pregnancy
Revises: 20260918_0011_care_group
Create Date: 2026-09-18

When the declared care group is ``GESTANTES`` the admission form collects two
extra values above the standard anthropometry: the weight before the pregnancy
and the gestation plurality. Both are optional because they only apply to that
population.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "20260918_0012_pregnancy"
down_revision = "20260918_0011_care_group"
branch_labels = None
depends_on = None

_CHECK_NAME = "ck_atenciones_tipo_embarazo_valido"


def upgrade() -> None:
    # MySQL DDL is non-transactional: the guards keep a retry safe if an
    # interrupted deployment added a column before Alembic stamped it.
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("atenciones")
    }
    if "peso_antes_embarazo_kg" not in columns:
        op.add_column(
            "atenciones",
            sa.Column("peso_antes_embarazo_kg", mysql.DECIMAL(6, 2), nullable=True),
        )
    if "tipo_embarazo_codigo" not in columns:
        op.add_column(
            "atenciones",
            sa.Column("tipo_embarazo_codigo", sa.String(length=20), nullable=True),
        )
    checks = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_check_constraints("atenciones")
    }
    if _CHECK_NAME not in checks:
        op.create_check_constraint(
            _CHECK_NAME,
            "atenciones",
            "tipo_embarazo_codigo IS NULL "
            "OR tipo_embarazo_codigo IN ('UNICO', 'MULTIPLE')",
        )


def downgrade() -> None:
    checks = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_check_constraints("atenciones")
    }
    if _CHECK_NAME in checks:
        op.drop_constraint(_CHECK_NAME, "atenciones", type_="check")
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("atenciones")
    }
    if "tipo_embarazo_codigo" in columns:
        op.drop_column("atenciones", "tipo_embarazo_codigo")
    if "peso_antes_embarazo_kg" in columns:
        op.drop_column("atenciones", "peso_antes_embarazo_kg")
