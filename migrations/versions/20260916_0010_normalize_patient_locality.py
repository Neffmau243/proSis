"""Clear legacy locality values that repeat the selected UBIGEO code.

Revision ID: 20260916_0010_locality
Revises: 20260912_0009_patient_prof
Create Date: 2026-09-16
"""

from alembic import op

revision = "20260916_0010_locality"
down_revision = "20260912_0009_patient_prof"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove the old ``localidad = codigo_ubigeo`` placeholder values.

    The district remains referenced by ``ubigeo_residencia_codigo``.  A
    locality is free text describing the sector inside that district, so a
    code is never a meaningful fallback for it.
    """

    op.execute(
        """
        UPDATE pacientes
        SET localidad = NULL
        WHERE localidad IS NOT NULL
          AND localidad = ubigeo_residencia_codigo
        """
    )


def downgrade() -> None:
    """The discarded placeholder values cannot be reconstructed safely."""

