"""Official Arequipa establishments, replacing the demo-only catalog.

The source ``EESS`` table carries the real RENAES code and the SIS ``clave``
(DISA + site) for each site. Only the six rows with a valid, unique RENAES are
promoted; the department placeholders (``EE.SS. DEL DPTO. ...``) and the free
text names are left out. Nothing existing is renamed or removed, so a site a
patient already points at stays untouched.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "20260924_0019_eess_catalog"
down_revision = "20260924_0018_sis_localities"
branch_labels = None
depends_on = None

#: ``(codigo_legacy, nombre, codigo_renaes)`` from the source ``EESS`` table.
#: SIS ``IDEESS`` in the export equals the RENAES code, so it is reused.
ESTABLISHMENTS: tuple[tuple[str, str, str], ...] = (
    ("1", "C.S. ALTO SELVA ALEGRE", "1291"),
    ("2", "P.S. APURIMAC", "1300"),
    ("3", "CS. INDEPENDENCIA", "1302"),
    ("4", "P.S. LEONES DEL MISTI", "1301"),
    ("5", "P.S. SAN JUAN BAUTISTA", "1303"),
    ("6", "P.S. HEROES DEL CENEPA", "1304"),
)


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("establecimientos"):
        return
    table = sa.table(
        "establecimientos",
        sa.column("codigo_legacy", mysql.BIGINT(unsigned=True)),
        sa.column("codigo_renaes", sa.String),
        sa.column("codigo_ideess", sa.String),
        sa.column("nombre", sa.String),
    )
    existing = set(bind.execute(sa.select(table.c.codigo_renaes)).scalars())
    rows = [
        {
            "codigo_legacy": int(legacy),
            "codigo_renaes": renaes,
            "codigo_ideess": renaes,
            "nombre": nombre,
        }
        for legacy, nombre, renaes in ESTABLISHMENTS
        if renaes not in existing
    ]
    if rows:
        op.bulk_insert(table, rows)


def downgrade() -> None:
    """Do not delete a site a patient or attention may already reference."""

    pass
