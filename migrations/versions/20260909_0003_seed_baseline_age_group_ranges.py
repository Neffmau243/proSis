"""Seed baseline clinical age ranges when the initial catalog is unconfigured.

Revision ID: 20260909_0003
Revises: 20260909_0002
Create Date: 2026-09-09

The original catalog intentionally created named age groups without values.
That makes a fresh Alembic-only installation unable to classify an attention
until an administrator configures it.  These baseline ranges preserve exact
month-level clinical boundaries while never replacing an already configured
range.
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260909_0003"
down_revision = "20260909_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fill only groups whose two range boundaries are still unset."""

    for code, minimum, maximum in (
        ("NINO", 0, 143),
        ("ADOLESCENTE", 144, 215),
        ("ADULTO", 216, 719),
    ):
        op.execute(
            "UPDATE grupos_etarios "
            f"SET edad_minima_meses = {minimum}, edad_maxima_meses = {maximum} "
            f"WHERE codigo = '{code}' "
            "AND edad_minima_meses IS NULL AND edad_maxima_meses IS NULL"
        )
    op.execute(
        "UPDATE grupos_etarios "
        "SET edad_minima_meses = 720, edad_maxima_meses = NULL "
        "WHERE codigo = 'ADULTO_MAYOR' "
        "AND edad_minima_meses IS NULL AND edad_maxima_meses IS NULL"
    )


def downgrade() -> None:
    """Do not erase potentially administrator-configured clinical ranges."""

    # Data migrations should not remove clinical configuration on downgrade.
    pass
