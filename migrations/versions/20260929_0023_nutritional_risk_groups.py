"""Seed the nutritional risk labels found in the ETLSIS historical data.

ETLSIS does not have a general patient-risk catalog.  Its only risk-like
labels are nutritional assessment outcomes, so this revision exposes those
four labels as optional, dated patient risk periods.  It never assigns a risk
to an existing patient and it never overwrites a catalog row that staff may
already have configured.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260929_0023_nutrition_risks"
down_revision = "20260926_0022_specialty_codes"
branch_labels = None
depends_on = None


#: ``(codigo, nombre, descripcion)``.  These are ETLSIS nutritional labels,
#: not a comprehensive clinical risk taxonomy.
NUTRITIONAL_RISK_GROUPS: tuple[tuple[str, str, str], ...] = (
    (
        "NUT_DELGADEZ",
        "Riesgo a delgadez",
        "Etiqueta nutricional histórica ETLSIS; registrar tras evaluación clínica.",
    ),
    (
        "NUT_DESN_AGUDA",
        "Riesgo de desnutrición aguda",
        "Etiqueta nutricional histórica ETLSIS; registrar tras evaluación clínica.",
    ),
    (
        "NUT_DESN_GLOBAL",
        "Riesgo de desnutrición global",
        "Etiqueta nutricional histórica ETLSIS; registrar tras evaluación clínica.",
    ),
    (
        "NUT_TALLA_BAJA",
        "Riesgo de talla baja",
        "Etiqueta nutricional histórica ETLSIS; registrar tras evaluación clínica.",
    ),
)


def upgrade() -> None:
    """Add only missing codes, preserving the catalogue already in use."""

    bind = op.get_bind()
    table = sa.table(
        "grupos_riesgo",
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
        sa.column("descripcion", sa.String),
    )
    existing = set(bind.execute(sa.select(table.c.codigo)).scalars())
    rows = [
        {"codigo": codigo, "nombre": nombre, "descripcion": descripcion}
        for codigo, nombre, descripcion in NUTRITIONAL_RISK_GROUPS
        if codigo not in existing
    ]
    if rows:
        op.bulk_insert(table, rows)


def downgrade() -> None:
    """Keep catalog rows because patients may already reference them."""

    pass
