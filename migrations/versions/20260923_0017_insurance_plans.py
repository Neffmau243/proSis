"""Insurance catalog completeness: SIS plans and Sanidad as explicit codes.

Source: ``Data_base.mdb`` -> ``EESS_SIS`` (codes 001..009) and the labels already
present in ``Pacientes.Seguro``. The generic ``SIS`` row cannot tell a subsidized
regime from another, so ``Pacientes.Seguro`` values that name a plan keep their
own row. Nothing is renamed and no patient is reassigned: the previous five
codes stay untouched, and a patient with an unknown or empty value keeps
``seguro_id`` NULL instead of being forced into ``SIN_SEGURO``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260923_0017_insurance_plans"
down_revision = "20260921_0016_legacy_archive"
branch_labels = None
depends_on = None

#: (codigo, nombre) — SIS plans observed in the source plus Sanidad (FFAA/Policía).
INSURANCES: tuple[tuple[str, str], ...] = (
    ("SIS_GRATUITO", "S.I.S. Gratuito"),
    ("SIS_PARA_TODOS", "S.I.S. SIS Para Todos"),
    ("SIS_AFILIACION_TEMPORAL", "S.I.S. Afiliación Temporal"),
    ("SIS_SEMI_SUBSIDIADO", "S.I.S. Semi Subsidiado"),
    ("SIS_NRUS", "S.I.S. NRUS"),
    ("SANIDAD", "Sanidad (FFAA / Policía)"),
)


def upgrade() -> None:
    """Insert only the codes that are still missing; safe to retry."""

    bind = op.get_bind()
    table = sa.table("seguros", sa.column("codigo", sa.String), sa.column("nombre", sa.String))
    existing = set(bind.execute(sa.select(table.c.codigo)).scalars())
    rows = [
        {"codigo": codigo, "nombre": nombre}
        for codigo, nombre in INSURANCES
        if codigo not in existing
    ]
    if rows:
        op.bulk_insert(table, rows)


def downgrade() -> None:
    """Do not delete catalog rows: existing patients may already reference them."""

    # Data migrations must not drop a catalog row a patient points at.
    pass
