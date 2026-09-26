# -*- coding: utf-8 -*-
"""Genera la migración de profesionales reales desde ``cat_profesional``.

Vive bajo ``etlSis/`` (que no se entrega) y sólo se usa en desarrollo para
"hornear" los profesionales dentro del proyecto. La migración resultante es
autocontenida: no lee el ETL en tiempo de ejecución.

Decisiones:

* ``cat_profesional.codigo_legacy`` se repite entre orígenes, así que se usa el
  ``id`` de origen como ``codigo_legacy`` (clave estable y única).
* ``OBSTETRA`` y ``OBSTETRIZ`` son la misma profesión: se unifican.
* ``colegiatura`` no numérica (``.``, ``-``) se guarda como ``NULL``.
* El origen no registra la sede de cada profesional; se asigna cada uno a la
  oficina de su área en las seis sedes reales para que cualquier sede pueda
  operar su consulta.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DUMP = ROOT / "etlSis" / "dump" / "20_catalogos.sql"
OUT = ROOT / "migrations" / "versions" / "20260926_0021_real_professionals.py"

# ``cat_profesional.atencion_codigo`` -> área de consultorio (``cat_consultorio``).
AREA_SPECIALTY = {
    "1": "Especialidades:003",   # MEDICINA
    "3": "Especialidades2:006",  # ODONTOLOGIA
    "4": "Especialidades:002",   # LABORATORIO
    "5": "Especialidades:008",   # OBSTETRICIA
    "6": "Especialidades2:001",  # ENFERMERIA
    "8": "Especialidades:006",   # PSICOLOGIA
    "10": "Especialidades:005",  # NUTRICION
}


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


def _profession(value: str) -> str:
    name = value.strip().upper()
    return "OBSTETRIZ" if name in {"OBSTETRIZ", "OBSTETRA"} else name


def _colegiatura(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text.isdigit() else None


def _literals(rows, indent: int = 4) -> str:
    pad = " " * indent
    return "\n".join(f"{pad}{row!r}," for row in rows)


source = _rows("cat_profesional")
professions = sorted({_profession(row[5]) for row in source})
professionals = [
    (
        row[0],                                # id de origen -> codigo_legacy
        row[4],                                # dni
        row[2],                                # nombre
        _profession(row[5]),                   # profesion unificada
        _colegiatura(row[7]),                  # colegiatura numérica o NULL
        str(row[8]),                           # atencion_codigo -> área
    )
    for row in source
]
areas = sorted({row[5] for row in professionals if row[5] in AREA_SPECIALTY})

TEMPLATE = '''"""Profesionales reales de Arequipa, en lugar de las filas demo.

El volcado del ETL (``cat_profesional``) es sólo una guía y NO se entrega con
el proyecto, así que sus filas vienen horneadas aquí. Se siembran las
profesiones, los 62 profesionales, su especialidad principal (deducida de
``atencion_codigo``) y una asignación vigente a cada oficina del área
correspondiente, de modo que la admisión pueda registrar atenciones.

``cat_profesional.codigo_legacy`` se repite entre orígenes, así que se usa el
``id`` de origen como ``codigo_legacy``. ``OBSTETRA`` y ``OBSTETRIZ`` se
unifican. El origen no registra la sede de cada profesional, así que se asigna
a la oficina de su área en las seis sedes reales.
"""

from __future__ import annotations

from datetime import date

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "20260926_0021_real_professionals"
down_revision = "20260926_0020_real_catalogs"
branch_labels = None
depends_on = None

#: ``(nombre,)`` de las profesiones presentes en ``cat_profesional``.
PROFESSIONS = (
%(professions)s)

#: ``(codigo_legacy, numero_documento, nombre_completo, profesion, colegiatura, area)``.
PROFESSIONALS = (
%(professionals)s)

#: ``atencion_codigo`` (área) -> código de especialidad principal.
AREA_SPECIALTY = {
%(areas)s}

#: Fecha de inicio de las asignaciones sembradas (anterior a cualquier atención).
ASSIGNMENT_START = date(2024, 1, 1)


def _seed_professions(bind) -> dict[str, int]:
    table = sa.table(
        "profesiones",
        sa.column("id", mysql.BIGINT(unsigned=True)),
        sa.column("nombre", sa.String),
    )
    existing = set(bind.execute(sa.select(table.c.nombre)).scalars())
    rows = [{"nombre": name} for name in PROFESSIONS if name not in existing]
    if rows:
        op.bulk_insert(table, rows)
    return {
        row[0]: row[1]
        for row in bind.execute(sa.select(table.c.nombre, table.c.id)).all()
    }


def _seed_professionals(bind, professions: dict[str, int]) -> dict[int, int]:
    table = sa.table(
        "profesionales",
        sa.column("id", mysql.BIGINT(unsigned=True)),
        sa.column("codigo_legacy", mysql.BIGINT(unsigned=True)),
        sa.column("numero_documento", sa.String),
        sa.column("nombre_completo", sa.String),
        sa.column("profesion_id", mysql.BIGINT(unsigned=True)),
        sa.column("colegiatura", sa.String),
    )
    existing_legacy = set(bind.execute(sa.select(table.c.codigo_legacy)).scalars())
    existing_doc = set(bind.execute(sa.select(table.c.numero_documento)).scalars())
    rows = []
    for legacy, dni, nombre, profesion, colegiatura, _area in PROFESSIONALS:
        if legacy in existing_legacy or (dni is not None and dni in existing_doc):
            continue
        rows.append(
            {
                "codigo_legacy": legacy,
                "numero_documento": dni,
                "nombre_completo": nombre,
                "profesion_id": professions.get(profesion),
                "colegiatura": colegiatura,
            }
        )
    if rows:
        op.bulk_insert(table, rows)
    return {
        row[0]: row[1]
        for row in bind.execute(sa.select(table.c.codigo_legacy, table.c.id)).all()
    }


def _seed_specialties(bind, professionals: dict[int, int]) -> None:
    table = sa.table(
        "profesional_especialidades",
        sa.column("profesional_id", mysql.BIGINT(unsigned=True)),
        sa.column("especialidad_codigo", sa.String),
        sa.column("es_principal", sa.Boolean),
    )
    existing = {
        (row[0], row[1])
        for row in bind.execute(
            sa.select(table.c.profesional_id, table.c.especialidad_codigo)
        ).all()
    }
    rows = []
    for legacy, _dni, _nombre, _profesion, _colegiatura, area in PROFESSIONALS:
        professional_id, specialty = professionals.get(legacy), AREA_SPECIALTY.get(area)
        if professional_id is None or specialty is None:
            continue
        if (professional_id, specialty) in existing:
            continue
        rows.append(
            {
                "profesional_id": professional_id,
                "especialidad_codigo": specialty,
                "es_principal": True,
            }
        )
        existing.add((professional_id, specialty))
    if rows:
        op.bulk_insert(table, rows)


def _seed_assignments(bind, professionals: dict[int, int]) -> None:
    consultorios = sa.table(
        "consultorios",
        sa.column("id", mysql.BIGINT(unsigned=True)),
        sa.column("especialidad_codigo", sa.String),
    )
    offices: dict[str, list[int]] = {}
    for office_id, specialty in bind.execute(
        sa.select(consultorios.c.id, consultorios.c.especialidad_codigo)
    ).all():
        offices.setdefault(specialty, []).append(office_id)

    table = sa.table(
        "consultorio_profesionales",
        sa.column("consultorio_id", mysql.BIGINT(unsigned=True)),
        sa.column("profesional_id", mysql.BIGINT(unsigned=True)),
        sa.column("fecha_inicio", sa.Date),
        sa.column("fecha_fin", sa.Date),
        sa.column("es_responsable", sa.Boolean),
    )
    existing = {
        (row[0], row[1])
        for row in bind.execute(
            sa.select(table.c.consultorio_id, table.c.profesional_id)
        ).all()
    }
    responsible = set(
        bind.execute(
            sa.select(table.c.consultorio_id).where(
                table.c.fecha_fin.is_(None), table.c.es_responsable.is_(True)
            )
        ).scalars()
    )
    rows = []
    for legacy, _dni, _nombre, _profesion, _colegiatura, area in PROFESSIONALS:
        professional_id, specialty = professionals.get(legacy), AREA_SPECIALTY.get(area)
        if professional_id is None or specialty is None:
            continue
        for office_id in offices.get(specialty, []):
            if (office_id, professional_id) in existing:
                continue
            is_responsible = office_id not in responsible
            rows.append(
                {
                    "consultorio_id": office_id,
                    "profesional_id": professional_id,
                    "fecha_inicio": ASSIGNMENT_START,
                    "fecha_fin": None,
                    "es_responsable": is_responsible,
                }
            )
            existing.add((office_id, professional_id))
            if is_responsible:
                responsible.add(office_id)
    if rows:
        op.bulk_insert(table, rows)


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("profesionales"):
        return
    # Las especialidades que respaldan las asignaciones las siembra
    # ``20260926_0020_real_catalogs``; si faltan, la FK falla y lo hace ver.
    professions = _seed_professions(bind)
    professionals = _seed_professionals(bind, professions)
    _seed_specialties(bind, professionals)
    _seed_assignments(bind, professionals)


def downgrade() -> None:
    """No borra profesionales: una atención o una cuenta pueden referenciarlos."""

    pass
''' % {
    "professions": _literals(professions),
    "professionals": _literals(professionals, indent=4),
    "areas": "\n".join(
        f"    {area!r}: {AREA_SPECIALTY[area]!r}," for area in areas
    ),
}

OUT.write_text(TEMPLATE, encoding="utf-8")
print(
    f"escrito {OUT} ({len(professions)} profesiones, "
    f"{len(professionals)} profesionales, {len(areas)} áreas)"
)
