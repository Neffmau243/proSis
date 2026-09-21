"""Persist the clinical care group an attention was registered for.

Revision ID: 20260918_0011_care_group
Revises: 20260916_0010_locality
Create Date: 2026-09-18

``grupo_etario_codigo`` is derived from the patient's age, so it can never say
whether a female patient was attended as a pregnant or puerperal person. This
migration stores the explicit population chosen during admission. Existing
rows keep the general population, which is the only value they could have been
recorded under before this column existed.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260918_0011_care_group"
down_revision = "20260916_0010_locality"
branch_labels = None
depends_on = None

_CHECK_NAME = "ck_atenciones_grupo_atencion_valido"


def upgrade() -> None:
    # MySQL DDL is non-transactional: the guards keep a retry safe if an
    # interrupted deployment added the column before Alembic stamped it.
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("atenciones")
    }
    if "grupo_atencion_codigo" not in columns:
        op.add_column(
            "atenciones",
            sa.Column(
                "grupo_atencion_codigo",
                sa.String(length=40),
                nullable=False,
                server_default=sa.text("'NINOS_ADOLESCENTES_ADULTOS_MAYORES'"),
            ),
        )
    checks = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_check_constraints("atenciones")
    }
    if _CHECK_NAME not in checks:
        op.create_check_constraint(
            _CHECK_NAME,
            "atenciones",
            "grupo_atencion_codigo IN "
            "('NINOS_ADOLESCENTES_ADULTOS_MAYORES', 'GESTANTES', 'PUERPERAS')",
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
    if "grupo_atencion_codigo" in columns:
        op.drop_column("atenciones", "grupo_atencion_codigo")
