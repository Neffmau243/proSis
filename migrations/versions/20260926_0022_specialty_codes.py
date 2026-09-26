"""Normaliza a mayúsculas los códigos de especialidad del catálogo real.

``20260926_0020_real_catalogs`` sembró los códigos como ``origen:codigo`` (por
ejemplo ``Especialidades:003``), pero toda la aplicación normaliza la
especialidad a mayúsculas (``app/schemas/attention.py``, ``office.py`` y
``professional.py``). Sin esta normalización una atención nunca coincidiría con
la especialidad del consultorio (``ESPECIALIDADES:003`` frente a
``Especialidades:003``) y la admisión fallaría con ``ESPECIALIDAD_INCOMPATIBLE``.

Las claves foráneas hacia ``especialidades.codigo`` declaran
``ON UPDATE CASCADE``, así que la actualización propaga a ``consultorios``,
``profesional_especialidades`` y ``atenciones``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260926_0022_specialty_codes"
down_revision = "20260926_0021_real_professionals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("especialidades"):
        return
    # ``UPPER`` es inyectivo para los códigos reales: ninguno difiere de otro
    # sólo por mayúsculas/minúsculas, así que la clave primaria no colisiona.
    bind.execute(sa.text("UPDATE especialidades SET codigo = UPPER(codigo)"))


def downgrade() -> None:
    """No revierte la normalización: la aplicación siempre usa mayúsculas."""

    pass
