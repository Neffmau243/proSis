"""Catálogos operativos reales de Arequipa, en lugar de las filas demo.

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
    ('01', 'RED AREQUIPA'),
    ('04', 'RED CARAVELÍ'),
    ('05', 'RED CASTILLA-CONDESUYOS-LA UNIÓN'),
    ('06', 'RED ISLAY'),)

#: ``(codigo_legacy, id_red, nombre)`` de ``cat_microred``.
MICROREDES = (
    (1, '01', '15 DE AGOSTO'),
    (2, '01', 'ALTO SELVA ALEGRE'),
    (3, '01', 'AMPLIACION PAUCARPATA'),
    (4, '01', 'CHIGUATA'),
    (5, '01', 'CIUDAD BLANCA'),
    (6, '01', 'EDIFICADORES MISTI'),
    (7, '01', 'GENERALISIMO SAN MARTIN'),
    (8, '01', 'MARIANO MELGAR'),
    (9, '01', 'CAYLLOMA'),
    (10, '01', 'CABANACONDE'),
    (11, '01', 'CALLALLI'),
    (12, '01', 'CHIVAY'),
    (13, '01', 'BUENOS AIRES DE CAYMA'),
    (14, '01', 'FRANCISCO BOLOGNESI'),
    (15, '01', 'MARISCAL CASTILLA'),
    (16, '01', 'MARITZA CAMPOS DIAZ'),
    (17, '01', 'YANAHUARA'),
    (18, '01', 'CIUDAD DE DIOS'),
    (19, '01', 'EL PEDREGAL'),
    (20, '01', 'CHARACATO'),
    (21, '01', 'HUNTER'),
    (22, '01', 'VICTOR RAUL HINOJOSA'),
    (23, '01', 'TIABAYA'),
    (24, '01', 'SAN MARTIN DE SOCABAYA'),
    (25, '01', 'LA JOYA'),
    (26, '01', 'SAN ISIDRO'),
    (27, '01', 'VITOR'),
    (28, '01', 'CERRO COLORADO'),
    (29, '04', 'ACARI'),
    (30, '04', 'CARAVELI'),
    (31, '04', 'CHALA'),
    (32, '04', 'IQUIPI'),
    (33, '04', 'LA PAMPA'),
    (34, '04', 'OCOÑA'),
    (35, '04', 'SAN GREGORIO'),
    (36, '04', 'SAN JOSE'),
    (37, '05', 'ALCA'),
    (38, '05', 'ANDAGUA'),
    (39, '05', 'CHUQUIBAMBA'),
    (40, '05', 'CORIRE'),
    (41, '05', 'COTAHUASI'),
    (42, '05', 'HUANCARQUI'),
    (43, '05', 'PAMPACOLCA'),
    (44, '05', 'VIRACO'),
    (45, '06', 'ALTO INCLAN'),
    (46, '06', 'COCACHACRA'),
    (47, '06', 'LA PUNTA'),)

#: ``(codigo, nombre, grupo)`` de ``cat_especialidad`` con ``origen:codigo``.
SPECIALTIES = (
    ('Especialidades:001', 'DENTAL', 'Especialidades'),
    ('Especialidades:002', 'LABORATORIO', 'Especialidades'),
    ('Especialidades:003', 'MEDICINA', 'Especialidades'),
    ('Especialidades:004', 'NIÑO SANO', 'Especialidades'),
    ('Especialidades:005', 'NUTRICION', 'Especialidades'),
    ('Especialidades:006', 'PSICOLOGIA', 'Especialidades'),
    ('Especialidades:007', 'PLANIFICACION FAMILIAR', 'Especialidades'),
    ('Especialidades:008', 'OBSTETRICIA', 'Especialidades'),
    ('Especialidades:009', 'TOPICO', 'Especialidades'),
    ('Especialidades2:001', 'ENFERMERIA', 'Especialidades2'),
    ('Especialidades2:006', 'ODONTOLOGIA', 'Especialidades2'),
    ('Especialidades3:002', 'ORIENTACION Y CONSEJERIA', 'Especialidades3'),
    ('Especialidades3:004', 'TERAPIA DEL LENGUAJE', 'Especialidades3'),
    ('Especialidades3:005', 'TERAPIA OCUPACIONAL', 'Especialidades3'),
    ('Certificado:001', 'CERTIFICADO MEDICO', 'Certificado'),
    ('Certificado:002', 'CERTIFICADO PSICOLOGICO', 'Certificado'),
    ('Esp_Enfermeria:003', 'ESTIMULACIÓN TEMPRANA', 'Esp_Enfermeria'),
    ('Esp_Enfermeria:004', 'VISITA DOMICILIARIA', 'Esp_Enfermeria'),
    ('Esp_Medicina:001', 'MEDICINA GENERAL', 'Esp_Medicina'),
    ('Esp_Medicina:002', 'DANT', 'Esp_Medicina'),
    ('Esp_Medicina:003', 'PEDIATRIA', 'Esp_Medicina'),
    ('Esp_Medicina:004', 'GINECOLOGIA', 'Esp_Medicina'),
    ('Esp_Nutricion:001', 'CONSULTA NUTRICIONAL', 'Esp_Nutricion'),
    ('Esp_Nutricion:002', 'CANASTA TBC', 'Esp_Nutricion'),
    ('Esp_Nutricion:003', 'SESION DEMOSTRATIVA', 'Esp_Nutricion'),
    ('Esp_Obstetricia:002', 'MATERNO', 'Esp_Obstetricia'),
    ('Esp_Obstetricia:003', 'MONITOREO FETAL', 'Esp_Obstetricia'),
    ('Esp_Obstetricia:004', 'PSICOPROFILAXIS', 'Esp_Obstetricia'),
    ('Esp_Obstetricia:005', 'CANCER', 'Esp_Obstetricia'),
    ('Esp_Odontologia:001', 'CONSULTA ODONTOLOGICA', 'Esp_Odontologia'),
    ('Esp_Psicologia:001', 'CONSULTA PSICOLOGICA', 'Esp_Psicologia'),
    ('Esp_Topico:001', 'CURACION', 'Esp_Topico'),
    ('Esp_Topico:002', 'INYECTABLE', 'Esp_Topico'),)

#: ``(codigo, nombre, especialidad_codigo)`` de ``cat_consultorio``.
OFFICE_AREAS = (
    ('MED', 'MEDICINA', 'Especialidades:003'),
    ('ENF', 'ENFERMERIA', 'Especialidades2:001'),
    ('ODO', 'ODONTOLOGIA', 'Especialidades2:006'),
    ('PSI', 'PSICOLOGIA', 'Especialidades:006'),
    ('OBS', 'OBSTETRICIA', 'Especialidades:008'),
    ('NUT', 'NUTRICION', 'Especialidades:005'),
    ('LAB', 'LABORATORIO', 'Especialidades:002'),)

#: Sólo las sedes reales; una oficina por área en cada una.
ESTABLISHMENT_RENAES = (
    '1291',
    '1300',
    '1301',
    '1302',
    '1303',
    '1304',)


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
