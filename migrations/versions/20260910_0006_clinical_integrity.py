"""Enforce clinical-document states and certificate signer integrity.

Revision ID: 20260910_0006_clinical_integrity
Revises: 20260910_0005_security_auth
Create Date: 2026-09-10

The application already records issued documents rather than draft FUA rows.
This migration normalizes the old draft value, then makes the finite state
sets and certificate-to-attention signer relationship database invariants.
It refuses to silently rewrite a legacy certificate signed by another
professional; that discrepancy needs an auditable manual correction.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = "20260910_0006_clinical_integrity"
down_revision = "20260910_0005_security_auth"
branch_labels = None
depends_on = None


def _assert_legacy_data_is_compatible() -> None:
    """Fail safely instead of changing historical clinical attribution."""

    bind = op.get_bind()
    invalid_statuses = {
        "atenciones": bind.execute(
            sa.text("SELECT COUNT(*) FROM atenciones WHERE estado NOT IN ('ATENDIDO', 'ANULADO')")
        ).scalar_one(),
        "fua": bind.execute(
            sa.text("SELECT COUNT(*) FROM fua WHERE estado NOT IN ('EMITIDO', 'ANULADO')")
        ).scalar_one(),
        "certificados": bind.execute(
            sa.text("SELECT COUNT(*) FROM certificados WHERE estado NOT IN ('EMITIDO', 'ANULADO')")
        ).scalar_one(),
        "referencias": bind.execute(
            sa.text(
                """
                SELECT COUNT(*) FROM referencias
                WHERE estado NOT IN (
                    'PENDIENTE', 'ACEPTADA', 'ATENDIDA',
                    'CONTRARREFERIDA', 'CERRADA', 'ANULADA'
                )
                """
            )
        ).scalar_one(),
    }
    incompatible_tables = [name for name, count in invalid_statuses.items() if count]
    if incompatible_tables:
        raise RuntimeError(
            "No se puede aplicar la integridad clínica: existen estados documentales "
            f"no reconocidos en {', '.join(incompatible_tables)}. Corrija los datos primero."
        )

    signer_mismatches = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM certificados AS certificado
            INNER JOIN atenciones AS atencion ON atencion.id = certificado.atencion_id
            WHERE certificado.profesional_id IS NULL
               OR certificado.profesional_id <> atencion.profesional_id
            """
        )
    ).scalar_one()
    if signer_mismatches:
        raise RuntimeError(
            "No se puede aplicar la integridad clínica: existen certificados sin el "
            "profesional de su atención. Corrija y audite esas filas antes de migrar."
        )


def upgrade() -> None:
    # Earlier application versions created a FUA only when it was issued but
    # persisted the misleading BORRADOR default. This is a semantic migration,
    # not a blanket correction of unknown values.
    op.execute("UPDATE fua SET estado = 'EMITIDO' WHERE estado = 'BORRADOR'")
    _assert_legacy_data_is_compatible()

    op.create_check_constraint(
        "ck_atenciones_estado_valido",
        "atenciones",
        "estado IN ('ATENDIDO', 'ANULADO')",
    )
    op.create_check_constraint(
        "ck_fua_estado_valido",
        "fua",
        "estado IN ('EMITIDO', 'ANULADO')",
    )
    op.create_check_constraint(
        "ck_certificados_estado_valido",
        "certificados",
        "estado IN ('EMITIDO', 'ANULADO')",
    )
    op.create_check_constraint(
        "ck_referencias_estado_valido",
        "referencias",
        "estado IN ('PENDIENTE', 'ACEPTADA', 'ATENDIDA', 'CONTRARREFERIDA', 'CERRADA', 'ANULADA')",
    )

    # MySQL requires an indexed referenced key for the composite foreign key.
    op.create_unique_constraint(
        "uq_atenciones_id_profesional",
        "atenciones",
        ["id", "profesional_id"],
    )
    op.drop_constraint("fk_certificados_atencion", "certificados", type_="foreignkey")
    op.alter_column(
        "certificados",
        "profesional_id",
        existing_type=mysql.BIGINT(unsigned=True),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_certificados_atencion_profesional",
        "certificados",
        "atenciones",
        ["atencion_id", "profesional_id"],
        ["id", "profesional_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.alter_column(
        "fua",
        "estado",
        existing_type=sa.String(length=30),
        existing_nullable=False,
        server_default=sa.text("'EMITIDO'"),
    )


def downgrade() -> None:
    op.alter_column(
        "fua",
        "estado",
        existing_type=sa.String(length=30),
        existing_nullable=False,
        server_default=sa.text("'BORRADOR'"),
    )
    op.drop_constraint(
        "fk_certificados_atencion_profesional",
        "certificados",
        type_="foreignkey",
    )
    op.alter_column(
        "certificados",
        "profesional_id",
        existing_type=mysql.BIGINT(unsigned=True),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_certificados_atencion",
        "certificados",
        "atenciones",
        ["atencion_id"],
        ["id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.drop_constraint("uq_atenciones_id_profesional", "atenciones", type_="unique")
    op.drop_constraint("ck_referencias_estado_valido", "referencias", type_="check")
    op.drop_constraint("ck_certificados_estado_valido", "certificados", type_="check")
    op.drop_constraint("ck_fua_estado_valido", "fua", type_="check")
    op.drop_constraint("ck_atenciones_estado_valido", "atenciones", type_="check")
