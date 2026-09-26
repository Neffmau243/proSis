# -*- coding: utf-8 -*-
"""Genera la migración de catálogos reales de Arequipa desde el volcado del ETL.

Vive bajo ``etlSis/`` (que no se entrega) y sólo se usa en desarrollo para
"hornear" los catálogos dentro del proyecto. La migración resultante es
autocontenida: no lee el ETL en tiempo de ejecución.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DUMP = ROOT / "etlSis" / "dump" / "20_catalogos.sql"
OUT = ROOT / "migrations" / "versions" / "20260926_0020_real_catalogs.py"

# El ETL no trae nombres de red; se nombran por las provincias que sirven.
NETWORKS = (
    ("01", "RED AREQUIPA"),
    ("04", "RED CARAVELÍ"),
    ("05", "RED CASTILLA-CONDESUYOS-LA UNIÓN"),
    ("06", "RED ISLAY"),
)

# ``cat_especialidad`` no tiene códigos únicos: se usa ``origen:codigo``.
# Áreas de ``cat_consultorio`` -> código de especialidad y código corto.
AREA_CODE = {
    "MEDICINA": "MED",
    "ENFERMERIA": "ENF",
    "ODONTOLOGIA": "ODO",
    "PSICOLOGIA": "PSI",
    "OBSTETRICIA": "OBS",
    "NUTRICION": "NUT",
    "LABORATORIO": "LAB",
}
AREA_SPECIALTY = {
    "MEDICINA": "Especialidades:003",
    "ENFERMERIA": "Especialidades2:001",
    "ODONTOLOGIA": "Especialidades2:006",
    "PSICOLOGIA": "Especialidades:006",
    "OBSTETRICIA": "Especialidades:008",
    "NUTRICION": "Especialidades:005",
    "LABORATORIO": "Especialidades:002",
}

RENAES = ("1291", "1300", "1301", "1302", "1303", "1304")


def _rows(table: str) -> list[tuple]:
    raw = DUMP.read_text(encoding="utf-8")
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", raw)
    out: list[tuple] = []
    for match in re.finditer(r"INSERT INTO `%s`[^)]*\) VALUES\s*(.*?);" % table, raw, re.S):
        for line in match.group(1).splitlines():
            line = line.strip().rstrip(",").strip()
            if not line.startswith("("):
                continue
            try:
                out.append(ast.literal_eval(line.replace("NULL", "None")))
            except Exception:
                pass
    return out


def _literals(rows, indent: int = 4) -> str:
    pad = " " * indent
    return "\n".join(f"{pad}{row!r}," for row in rows)


microredes = [
    (int(r[1]), r[5], r[2]) for r in _rows("cat_microred")  # codigo_legacy, id_red, descripcion
]
especialidades = [
    (f"{r[4]}:{r[1]}", r[2], r[4]) for r in _rows("cat_especialidad")  # origen:codigo, nombre, origen
]
consultorio_areas = [
    (AREA_CODE[r[1]], r[1], AREA_SPECIALTY[r[1]])
    for r in _rows("cat_consultorio")
    if r[1] in AREA_CODE
]

TEMPLATE = '''"""Catálogos operativos reales de Arequipa, en lugar de las filas demo.

El volcado del ETL (``cat_microred``, ``cat_especialidad``, ``cat_consultorio``)
es sólo una guía y NO se entrega con el proyecto, así que sus filas vienen
horneadas aquí. ``cat_establecimiento`` no aporta nada: sólo sus seis sedes con
RENAES válido lo son y ya las sembró ``20260924_0019_eess_catalog``. Los 32
placeholders ``EE.SS. DEL DPTO.`` y las filas de texto libre se ignoran a
propósito.

Los nombres de red no están en el origen; se nombran por las provincias que
sirven sus microredes. Las filas de ``consultorios`` son inferidas: el origen
sólo lista áreas de servicio, así que cada sede real recibe una oficina por área.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "20260926_0020_real_catalogs"
down_revision = "20260924_0019_eess_catalog"
branch_labels = None
depends_on = None

DIRESA = ("040", "DIRESA AREQUIPA")

NETWORKS = (
%(networks)s)

#: ``(codigo_legacy, id_red, nombre)`` de ``cat_microred``.
MICROREDES = (
%(microredes)s)

#: ``(codigo, nombre, grupo)`` de ``cat_especialidad`` con ``origen:codigo``.
SPECIALTIES = (
%(especialidades)s)

#: ``(codigo, nombre, especialidad_codigo)`` de ``cat_consultorio``.
OFFICE_AREAS = (
%(areas)s)

#: Sólo las sedes reales; una oficina por área en cada una.
ESTABLISHMENT_RENAES = (
%(renaes)s)


def _scalar_map(bind, statement):
    return {row[0]: row[1] for row in bind.execute(statement).all()}


def _insert_missing(bind, table, key_columns, rows, label):
    existing = {
        tuple(row)
        for row in bind.execute(sa.select(*[table.c[name] for name in key_columns])).all()
    }
    pending = [
        row for row in rows if tuple(row[name] for name in key_columns) not in existing
    ]
    if pending:
        op.bulk_insert(table, pending)
    return label, len(pending)


def _seed_disa(bind) -> int:
    disa = sa.table(
        "disa",
        sa.column("id", mysql.BIGINT(unsigned=True)),
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
    )
    codigo, nombre = DIRESA
    found = bind.execute(sa.select(disa.c.id).where(disa.c.codigo == codigo)).scalar()
    if found is None:
        # ``sa.table`` no conoce la PK autoincremental, así que se relee el id.
        op.bulk_insert(disa, [{"codigo": codigo, "nombre": nombre}])
        found = bind.execute(sa.select(disa.c.id).where(disa.c.codigo == codigo)).scalar()
    return int(found)


def _seed_networks(bind, disa_id: int) -> dict[str, int]:
    redes = sa.table(
        "redes",
        sa.column("id", mysql.BIGINT(unsigned=True)),
        sa.column("id_disa", mysql.BIGINT(unsigned=True)),
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
    )
    rows = [
        {"id_disa": disa_id, "codigo": codigo, "nombre": nombre}
        for codigo, nombre in NETWORKS
    ]
    _insert_missing(bind, redes, ("id_disa", "codigo"), rows, "redes")
    return _scalar_map(
        bind,
        sa.select(redes.c.codigo, redes.c.id).where(redes.c.id_disa == disa_id),
    )


def _seed_microredes(bind, reds: dict[str, int]) -> None:
    microredes = sa.table(
        "microredes",
        sa.column("id_red", mysql.BIGINT(unsigned=True)),
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
    )
    rows = [
        {"id_red": reds[id_red], "codigo": str(codigo), "nombre": nombre}
        for codigo, id_red, nombre in MICROREDES
        if id_red in reds
    ]
    _insert_missing(bind, microredes, ("id_red", "codigo"), rows, "microredes")


def _seed_specialties(bind) -> None:
    table = sa.table(
        "especialidades",
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
        sa.column("grupo", sa.String),
    )
    rows = [
        {"codigo": codigo, "nombre": nombre, "grupo": grupo}
        for codigo, nombre, grupo in SPECIALTIES
    ]
    _insert_missing(bind, table, ("codigo",), rows, "especialidades")


def _seed_offices(bind) -> None:
    establecimientos = sa.table(
        "establecimientos",
        sa.column("id", mysql.BIGINT(unsigned=True)),
        sa.column("codigo_renaes", sa.String),
    )
    consultorios = sa.table(
        "consultorios",
        sa.column("establecimiento_id", mysql.BIGINT(unsigned=True)),
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
        sa.column("especialidad_codigo", sa.String),
    )
    sites = dict(
        bind.execute(
            sa.select(establecimientos.c.codigo_renaes, establecimientos.c.id).where(
                establecimientos.c.codigo_renaes.in_(ESTABLISHMENT_RENAES)
            )
        ).all()
    )
    rows = [
        {
            "establecimiento_id": sites[renaes],
            "codigo": codigo,
            "nombre": nombre,
            "especialidad_codigo": especialidad,
        }
        for renaes in ESTABLISHMENT_RENAES
        if renaes in sites
        for codigo, nombre, especialidad in OFFICE_AREAS
    ]
    _insert_missing(bind, consultorios, ("establecimiento_id", "codigo"), rows, "consultorios")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("microredes"):
        return
    disa_id = _seed_disa(bind)
    reds = _seed_networks(bind, disa_id)
    _seed_microredes(bind, reds)
    _seed_specialties(bind)
    _seed_offices(bind)


def downgrade() -> None:
    """No borra catálogos: un paciente o una atención pueden referenciarlos."""

    pass
''' % {
    "networks": _literals(NETWORKS),
    "microredes": _literals(microredes),
    "especialidades": _literals(especialidades),
    "areas": _literals(consultorio_areas),
    "renaes": _literals(RENAES),
}

OUT.write_text(TEMPLATE, encoding="utf-8")
print(f"escrito {OUT} ({len(microredes)} microredes, {len(especialidades)} especialidades, "
      f"{len(consultorio_areas)} áreas)")
