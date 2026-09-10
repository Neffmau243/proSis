"""Consolidate the application into ADMIN and PROFESIONAL roles.

Revision ID: 20260909_0004
Revises: 20260909_0003
Create Date: 2026-09-09

REGISTRO accounts that are already tied to an active professional are safely
converted to PROFESIONAL.  Legacy accounts without a valid professional
association cannot satisfy the current security invariant, so they are
deactivated rather than being granted a clinical identity implicitly.
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260909_0004"
down_revision = "20260909_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace legacy assignments without inventing professional identities."""

    # Preserve the useful previous REGISTRO role only when its account is
    # linked to an active professional. INSERT IGNORE also handles accounts
    # that already hold PROFESIONAL without producing duplicate associations.
    op.execute(
        """
        INSERT IGNORE INTO usuario_roles (usuario_id, rol_id)
        SELECT DISTINCT legacy_assignment.usuario_id, professional_role.id
        FROM usuario_roles AS legacy_assignment
        INNER JOIN roles AS legacy_role ON legacy_role.id = legacy_assignment.rol_id
        INNER JOIN usuarios AS usuario ON usuario.id = legacy_assignment.usuario_id
        INNER JOIN profesionales AS profesional ON profesional.id = usuario.profesional_id
        INNER JOIN roles AS professional_role ON professional_role.codigo = 'PROFESIONAL'
        WHERE legacy_role.codigo = 'REGISTRO'
          AND profesional.activo = TRUE
        """
    )

    op.execute(
        """
        DELETE assignment_row
        FROM usuario_roles AS assignment_row
        INNER JOIN roles AS role_row ON role_row.id = assignment_row.rol_id
        WHERE role_row.codigo IN ('REGISTRO', 'AUDITOR')
        """
    )

    # An account without any allowed role must not remain usable merely
    # because it used to be assigned one of the retired catalog entries.
    op.execute(
        """
        UPDATE usuarios AS usuario
        LEFT JOIN usuario_roles AS assignment_row
            ON assignment_row.usuario_id = usuario.id
        SET usuario.activo = FALSE
        WHERE usuario.activo = TRUE
          AND assignment_row.usuario_id IS NULL
        """
    )

    op.execute("DELETE FROM roles WHERE codigo IN ('REGISTRO', 'AUDITOR')")


def downgrade() -> None:
    """Restore only the catalog rows; prior assignments are not inferable."""

    op.execute(
        """
        INSERT IGNORE INTO roles (codigo, nombre)
        VALUES
            ('REGISTRO', 'Registro de pacientes'),
            ('AUDITOR', 'Auditor de solo lectura')
        """
    )
