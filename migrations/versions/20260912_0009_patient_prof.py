"""Keep the professional who registered or transferred a patient inside its scope.

Revision ID: 20260912_0009_patient_prof
Revises: 20260912_0008_nutrition_tipo
Create Date: 2026-09-12

``alembic_version.version_num`` is ``VARCHAR(32)``, so the revision id must stay
short; a longer identifier fails only at stamp time, after MySQL has already
committed the DDL.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "20260912_0009_patient_prof"
down_revision = "20260912_0008_nutrition_tipo"
branch_labels = None
depends_on = None

_COLUMN = "profesional_registro_id"
_FK = "fk_pacientes_profesional_registro"
_INDEX = "idx_pacientes_profesional_registro"


def _column_names() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("pacientes")}


def _foreign_key_names() -> set[str | None]:
    return {fk["name"] for fk in sa.inspect(op.get_bind()).get_foreign_keys("pacientes")}


def _index_names() -> set[str] | set[str | None]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("pacientes")}


def upgrade() -> None:
    # MySQL DDL is non-transactional. These guards make a retry safe if an
    # interrupted deployment changed the table before Alembic stamped it.
    if _COLUMN not in _column_names():
        op.add_column(
            "pacientes",
            sa.Column(_COLUMN, mysql.BIGINT(unsigned=True), nullable=True),
        )
    if _FK not in _foreign_key_names():
        op.create_foreign_key(
            _FK,
            "pacientes",
            "profesionales",
            [_COLUMN],
            ["id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        )
    if _INDEX not in _index_names():
        op.create_index(_INDEX, "pacientes", [_COLUMN], unique=False)


def downgrade() -> None:
    if _INDEX in _index_names():
        op.drop_index(_INDEX, table_name="pacientes")
    if _FK in _foreign_key_names():
        op.drop_constraint(_FK, "pacientes", type_="foreignkey")
    if _COLUMN in _column_names():
        op.drop_column("pacientes", _COLUMN)
