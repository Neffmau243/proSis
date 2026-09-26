"""Profesionales reales de Arequipa, en lugar de las filas demo.

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
    'BIOLOGO',
    'CIRUJANO DENTISTA',
    'ENFERMERA',
    'MEDICO',
    'NUTRICIONISTA',
    'OBSTETRIZ',
    'PSICOLOGO',)

#: ``(codigo_legacy, numero_documento, nombre_completo, profesion, colegiatura, area)``.
PROFESSIONALS = (
    (1, '29292136', 'ROSALINDA AMPARO DELGADO RODRIGUEZ', 'OBSTETRIZ', None, '5'),
    (2, '30408701', 'MIRYAM ANGELINA FERNANDEZ SANTOS', 'OBSTETRIZ', None, '5'),
    (3, '29690554', 'YURI JULIA DELGADO USNAYO', 'ENFERMERA', None, '6'),
    (4, '01486377', 'EDITH SULMA QUISPE MACHACA', 'ENFERMERA', None, '6'),
    (5, '29610558', 'MIRYAM TORRES QUEQUEZANA', 'NUTRICIONISTA', None, '10'),
    (6, '29294721', 'CLEMENCIA SILVIA MURGUIA VIZCARDO', 'PSICOLOGO', None, '8'),
    (7, '29422686', 'MARTHA CECILIA CARPIO SORIA', 'PSICOLOGO', None, '8'),
    (8, '43149888', 'LADY LIZETH MORALES PIÑARES', 'ENFERMERA', None, '6'),
    (9, '29700483', 'MARIZOL QUISPE SULLO', 'OBSTETRIZ', None, '5'),
    (10, '29292485', 'ELSA GUILLEN TOCCAS', 'MEDICO', None, '1'),
    (11, '04419990', 'LILIANA GUADALUPE VILLEGAS HERRERA', 'OBSTETRIZ', None, '5'),
    (12, '40465561', 'LISSETTE MARGARET MORENO CASAS', 'ENFERMERA', None, '6'),
    (13, '29305799', 'ANGELINA ADELA HERNANI RIVERA', 'PSICOLOGO', None, '8'),
    (14, '42056465', 'ROSA LUCERO VEGA VALENCIA', 'BIOLOGO', None, '4'),
    (15, '44359543', 'FERNANDA PATRICIA LIZARRAGA PEÑALOZA', 'NUTRICIONISTA', None, '10'),
    (16, '45926600', 'DERY JETSY LEON BEGAZO', 'CIRUJANO DENTISTA', None, '3'),
    (17, '45808253', 'DARELLY LUZ QUISPE BUSTINZA', 'ENFERMERA', None, '6'),
    (18, '29712889', 'LUIS ALBERTO SARMIENTO VILLALBA', 'CIRUJANO DENTISTA', None, '3'),
    (19, '42693584', 'ANA BRIGITTE HERRERA ESPINOZA', 'BIOLOGO', None, '4'),
    (20, '29281333', 'SONIA MERCEDES NEVES DE SALAS', 'MEDICO', '15573', '1'),
    (21, '41995774', 'VANESSA STEPHANIE PERALTA MONTESINOS', 'ENFERMERA', '51471', '6'),
    (22, '29224037', 'NATY HUARANCA CERPA', 'ENFERMERA', '11152', '6'),
    (23, '29352346', 'VIVIAN REGINA SANCHEZ PERALTA', 'PSICOLOGO', '8336', '8'),
    (24, '29610971', 'NAYLU MENDOZA PAREDES', 'NUTRICIONISTA', '2984', '10'),
    (25, '29703007', 'ELIZABETH CONCEPCION', 'ENFERMERA', '11187', '6'),
    (26, '29260430', 'PATIÑO QUINTO DOMINGO WIGBERTO', 'CIRUJANO DENTISTA', '4366', '3'),
    (27, '41829818', 'CLAUDIA M. DEL CARMEN TAYPICAHUANA JUAREZ', 'MEDICO', '49521', '1'),
    (28, '29691146', 'MARIELA CONGONA CONCHA', 'OBSTETRIZ', '8081', '5'),
    (29, '29647524', 'MARIA DEL ROSARIO MEDINA CALLA', 'MEDICO', '37938', '1'),
    (30, '29267076', 'ANA MARIA ROJAS PINTO', 'ENFERMERA', '16820', '6'),
    (31, '29646714', 'WOODWARD PAJA CALLO', 'MEDICO', None, '1'),
    (32, '29659875', 'ELIA DELMIRA HUARCA FLORES', 'MEDICO', None, '1'),
    (33, '40896561', 'JOSEFA HERMINIA FUENTES ANGELO', 'MEDICO', None, '1'),
    (34, '29630440', 'JUDITH BERTHA COYA QUIZA', 'MEDICO', None, '1'),
    (35, '31041776', 'LUIS ENRIQUE DEL CARPIO BELLIDO POSTIGO', 'MEDICO', None, '1'),
    (36, '29518189', 'WILFREDO ALBERTO MARES BERNAL', 'CIRUJANO DENTISTA', None, '3'),
    (37, '29250452', 'MARLENI JULIA GALLEGOS ARTEAGA', 'OBSTETRIZ', None, '5'),
    (38, '40937941', 'DALIA FUNES  HUIZA CAYNA', 'ENFERMERA', '40666', '6'),
    (39, '29224035', 'NATY HUARANCA CERPA', 'ENFERMERA', '11152', '6'),
    (40, '46679379', 'ESCARCINA ZEGARRA ARACELI', 'ENFERMERA', '87644', '6'),
    (41, '29407635', 'MAMANI  CCAHUANA JEANETTE', 'ENFERMERA', '24160', '6'),
    (42, '29704465', 'SUSANA MARQUEZ HERRERA', 'BIOLOGO', '3542', '4'),
    (43, '44597153', 'CUEVAS MAYTA EDSON RENE', 'BIOLOGO', '18191', '4'),
    (44, '72439724', 'PACHECO ISASI ALEXANDRA ELENA', 'BIOLOGO', '14638', '4'),
    (45, '29635014', 'COLLANQUI SUCAPUCA ANGELICA YANETT', 'MEDICO', '37061', '1'),
    (46, '01341541', 'SOLIS SOLIS OSCAR GUILLERMO', 'MEDICO', '57565', '1'),
    (47, '70249468', 'VALDIVIA SANCHEZ YURGUEN ALEJANDRO', 'MEDICO', '93812', '1'),
    (48, '29572431', 'ORUE CERVANTES LELIA JULIA', 'MEDICO', '32288', '1'),
    (49, None, 'TACO TAMO JULIA', 'MEDICO', '28394', '1'),
    (50, '29389283', 'FLORES CARPIO MARIA ELENA', 'MEDICO', '34086', '1'),
    (51, '70065403', 'ROMAN MEDINA ELIAS H', 'MEDICO', '106121', '1'),
    (52, '02398738', 'CUEVA ROSSELL MARIA LUZ', 'NUTRICIONISTA', '0991', '10'),
    (53, '41132893', 'YESICA MAGALI APAZA CAÑAPATAÑA', 'OBSTETRIZ', '26509', '5'),
    (54, '29313852', 'VALDIVIA GONZALES BEATRIZ', 'OBSTETRIZ', '7940', '5'),
    (55, '43105612', 'MAMANI VELEZ YIRAYME HEIDI', 'OBSTETRIZ', '23659', '5'),
    (56, '04646869', 'PAMO CASTILLO NADIA MARIELIN', 'OBSTETRIZ', '8023', '5'),
    (57, '29282291', 'CASQUINO SALCEDO ELIZABETH', 'CIRUJANO DENTISTA', '26118', '3'),
    (58, '29234739', 'MELLADO CALLE JOSE', 'CIRUJANO DENTISTA', '6423', '3'),
    (59, '45848999', 'BELLIDO SOSA YEMID ERIKA', 'CIRUJANO DENTISTA', '26963', '3'),
    (60, '47188180', 'URQUIZO RODRIGUEZ JULIO C', 'CIRUJANO DENTISTA', '60923', '3'),
    (61, '72189715', 'CUELLAR APAZA KATHERIN JAZMIN', 'PSICOLOGO', '60159', '8'),
    (62, '46900604', 'NINA CHAVEZ CRISTHIAN GREGORY', 'PSICOLOGO', '32537', '8'),)

#: ``atencion_codigo`` (área) -> código de especialidad principal.
AREA_SPECIALTY = {
    '1': 'Especialidades:003',
    '10': 'Especialidades:005',
    '3': 'Especialidades2:006',
    '4': 'Especialidades:002',
    '5': 'Especialidades:008',
    '6': 'Especialidades2:001',
    '8': 'Especialidades:006',}

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
