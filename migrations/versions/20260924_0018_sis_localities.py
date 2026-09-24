"""SIS territory and affiliation codes as managed catalog data.

The legacy SIS export keys every encounter by a territory tuple
(``Disa``/``Red``/``MicroRed``/``Establecimiento`` and
``Provincia``/``Distrito``/``Localidad``) plus an affiliation. The province and
district codes are already derivable from the six-digit UBIGEO, but the
locality was free text, so a district could not own its sectors nor carry their
code. This revision:

* creates ``localidades`` (SIS code plus owning UBIGEO district);
* links ``pacientes.localidad_id`` to that catalog;
* annotates ``seguros`` with the source ``codigo_sis`` and ``regimen`` so a
  change of region or insurer is catalog data, not a hardcoded value.

The Arequipa rows are a seed example taken from the source ``Z_01..Z_29``
tables. Another region is added the same way: insert its UBIGEOs and its
localities with their SIS code. Nothing already stored is renamed or removed.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "20260924_0018_sis_localities"
down_revision = "20260923_0017_insurance_plans"
branch_labels = None
depends_on = None

#: ``codigo`` de ``seguros`` -> ``(codigo_sis, regimen)``. The SIS code is the
#: ``EESS_SIS`` legacy value (001..009) that the source system exported.
AFFILIATIONS: tuple[tuple[str, str | None, str], ...] = (
    ("SIN_SEGURO", "001", "NINGUNO"),
    ("SIS_GRATUITO", "002", "SIS"),
    ("SIS_AFILIACION_TEMPORAL", "003", "SIS"),
    ("SIS_SEMI_SUBSIDIADO", "004", "SIS"),
    ("SIS_NRUS", "005", "SIS"),
    ("SIS_PARA_TODOS", "006", "SIS"),
    ("ESSALUD", "007", "ESSALUD"),
    ("SANIDAD", "008", "SANIDAD"),
    ("PARTICULAR", "009", "PARTICULAR"),
    ("SIS", None, "SIS"),
    ("OTRO", None, "OTRO"),
)


def _columns(bind, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("localidades"):
        op.create_table(
            "localidades",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column("ubigeo_codigo", sa.CHAR(6), nullable=False),
            sa.Column("codigo_sis", sa.String(10), nullable=False),
            sa.Column("nombre", sa.String(150), nullable=False),
            sa.Column("nombre_norm", sa.String(150), nullable=False),
            sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.ForeignKeyConstraint(
                ["ubigeo_codigo"], ["ubigeos.codigo"],
                name="fk_localidades_ubigeo", ondelete="RESTRICT", onupdate="CASCADE",
            ),
            sa.UniqueConstraint(
                "ubigeo_codigo", "codigo_sis", name="uq_localidades_ubigeo_codigo"
            ),
            sa.UniqueConstraint(
                "ubigeo_codigo", "nombre_norm", name="uq_localidades_ubigeo_nombre"
            ),
            mysql_engine="InnoDB",
        )
        op.create_index("ix_localidades_nombre_norm", "localidades", ["nombre_norm"], unique=False)

    if "localidad_id" not in _columns(bind, "pacientes"):
        op.add_column(
            "pacientes",
            sa.Column("localidad_id", mysql.BIGINT(unsigned=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_pacientes_localidad", "pacientes", "localidades",
            ["localidad_id"], ["id"], ondelete="RESTRICT", onupdate="CASCADE",
        )

    insurance_columns = _columns(bind, "seguros")
    if "codigo_sis" not in insurance_columns:
        op.add_column("seguros", sa.Column("codigo_sis", sa.String(10), nullable=True))
    if "regimen" not in insurance_columns:
        op.add_column("seguros", sa.Column("regimen", sa.String(20), nullable=True))

    _seed_ubigeos(bind)
    _seed_localities(bind)
    _annotate_insurances(bind)
    _link_patients(bind)


def _seed_ubigeos(bind) -> None:
    """Insert the Arequipa UBIGEOs that the locality catalog hangs from."""

    table = sa.table(
        "ubigeos",
        sa.column("codigo", sa.String),
        sa.column("departamento", sa.String),
        sa.column("provincia", sa.String),
        sa.column("distrito", sa.String),
        sa.column("localidad", sa.String),
        sa.column("altitud_msnm", mysql.DECIMAL(8, 2)),
        sa.column("quintil", sa.String),
    )
    existing = set(bind.execute(sa.select(table.c.codigo)).scalars())
    rows = [
        {
            "codigo": codigo,
            "departamento": "Arequipa",
            "provincia": "Arequipa",
            "distrito": nombre,
            "localidad": None,
            "altitud_msnm": altitud,
            "quintil": str(quintil),
        }
        for codigo, nombre, altitud, quintil in AREQUIPA_DISTRICTS
        if codigo not in existing
    ]
    if rows:
        op.bulk_insert(table, rows)


def _seed_localities(bind) -> None:
    """Insert each district's localities, numbered by their SIS code."""

    table = sa.table(
        "localidades",
        sa.column("ubigeo_codigo", sa.String),
        sa.column("codigo_sis", sa.String),
        sa.column("nombre", sa.String),
        sa.column("nombre_norm", sa.String),
    )
    existing = {
        (row[0], row[1])
        for row in bind.execute(
            sa.select(table.c.ubigeo_codigo, table.c.codigo_sis)
        ).all()
    }
    rows = []
    for ubigeo, block in AREQUIPA_LOCALITIES.items():
        for index, nombre in enumerate(block.strip().splitlines(), start=1):
            nombre = nombre.strip()
            codigo = f"{index:04d}"
            if not nombre or (ubigeo, codigo) in existing:
                continue
            rows.append(
                {
                    "ubigeo_codigo": ubigeo,
                    "codigo_sis": codigo,
                    "nombre": nombre,
                    "nombre_norm": nombre.casefold(),
                }
            )
    if rows:
        op.bulk_insert(table, rows)


def _annotate_insurances(bind) -> None:
    """Attach the source SIS code and regime to the catalog rows."""

    table = sa.table(
        "seguros",
        sa.column("codigo", sa.String),
        sa.column("codigo_sis", sa.String),
        sa.column("regimen", sa.String),
    )
    for codigo, codigo_sis, regimen in AFFILIATIONS:
        bind.execute(
            sa.update(table)
            .where(table.c.codigo == codigo)
            .values(codigo_sis=codigo_sis, regimen=regimen)
        )


def _link_patients(bind) -> None:
    """Promote a stored locality name to the catalog row of its district."""

    bind.execute(
        sa.text(
            """
            UPDATE pacientes p
            JOIN localidades l
              ON l.ubigeo_codigo = p.ubigeo_residencia_codigo
             AND l.nombre_norm = LOWER(TRIM(p.localidad))
            SET p.localidad_id = l.id
            WHERE p.localidad_id IS NULL
              AND p.localidad IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    """Drop the new catalog and columns; never delete stored catalog rows."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "localidad_id" in _columns(bind, "pacientes"):
        op.drop_constraint("fk_pacientes_localidad", "pacientes", type_="foreignkey")
        op.drop_column("pacientes", "localidad_id")
    insurance_columns = _columns(bind, "seguros")
    for column in ("codigo_sis", "regimen"):
        if column in insurance_columns:
            op.drop_column("seguros", column)
    if inspector.has_table("localidades"):
        op.drop_index("ix_localidades_nombre_norm", table_name="localidades")
        op.drop_table("localidades")


# Seed data. ``AREQUIPA_DISTRICTS`` is (UBIGEO, distrito, altitud, quintil) taken
# from the source ``Provincia`` table; ``AREQUIPA_LOCALITIES`` maps each UBIGEO to
# the district's ``Z_*`` localities in SIS-code order (line order = code 0001..).
AREQUIPA_DISTRICTS: tuple[tuple[str, str, int, int], ...] = (
    ("040102", "ALTO SELVA ALEGRE", 2520, 5),
    ("040103", "CAYMA", 2403, 5),
    ("040101", "CERCADO", 2335, 5),
    ("040104", "CERRO COLORADO", 2406, 5),
    ("040105", "CHARACATO", 2480, 5),
    ("040106", "CHIGUATA", 2960, 3),
    ("040107", "JACOBO HUNTER", 2250, 5),
    ("040129", "JOSÉ LUIS BUSTAMANTE Y RIVERO", 2310, 5),
    ("040108", "LA JOYA", 1270, 3),
    ("040109", "MARIANO MELGAR", 2335, 5),
    ("040110", "MIRAFLORES", 2430, 5),
    ("040111", "MOLLEBAYA", 2483, 4),
    ("040112", "PAUCARPATA", 2405, 5),
    ("040113", "POCSI", 3047, 3),
    ("040114", "POLOBAYA", 3091, 3),
    ("040115", "QUEQUEÑA", 2550, 5),
    ("040116", "SABANDÍA", 2390, 4),
    ("040117", "SACHACA", 2240, 5),
    ("040118", "SAN JUAN DE SIGUAS", 1152, 3),
    ("040119", "SAN JUAN DE TARUCANI", 4210, 3),
    ("040120", "SANTA ISABEL DE SIGUAS", 1360, 3),
    ("040121", "SANTA RITA DE SIGUAS", 1268, 3),
    ("040122", "SOCABAYA", 2300, 5),
    ("040123", "TIABAYA", 2178, 4),
    ("040124", "UCHUMAYO", 1950, 5),
    ("040125", "VÍTOR", 1620, 3),
    ("040126", "YANAHUARA", 2390, 5),
    ("040127", "YARABAMBA", 2460, 4),
    ("040128", "YURA", 2590, 3),
)

_SEED_PARTS: tuple[dict[str, str], ...] = (
    {
        "040102": """
            14 DE AGOSTO
            ALTO SELVA ALEGRE "A"
            ALTO SELVA ALEGRE "B"
            ALTO SELVA ALEGRE "C"
            AMPLIACION APURIMAC
            AMPLIACION VILLA ASUNCION
            AMPLIACION VILLA UNION
            ANDENES DE CHILINA
            ANDRES AVELINO CACERES
            ANGELES DEL MISTI
            ANTONIO JOSE DE SUCRE
            APURIMAC
            ARTESANAL APROMA
            ARTESANOS EL MISTI
            AUGUSTO SALAZAR BONDY
            AUIS RAFAEL HOYOS RUBIO
            BALCONES DE CHILINA
            BELLA ESPERANZA
            BELLO HORIZONTE
            COMPLEJO ARTESANAL ALTO SELVA ALEGRE
            CRUCE DE CHILINA - AUIS
            CRUCE DE CHILINA - COOP.
            EL GRAN CHAPARRAL
            EL HUARANGAL
            EL MIRADOR I ETAPA
            EL MIRADOR II ETAPA
            ENACE
            ENACE AMPLIACION
            ENATRU AREQUIPA
            EUCALIPTOS
            GARCILAZO DE LA VEGA
            GRAFICOS
            HEROES CHAVIN DE HUANTAR
            HUARANGAL AMPLIACION
            INDEPENDENCIA "A"
            INDEPENDENCIA "B"
            JAVIER HERAUD - AAHH
            JAVIER HERAUD - ASOC.
            JUAN VELASCO ALVARADO "A"
            JUAN VELASCO ALVARADO "B"
            LA ESTRELLA
            LAS CANTERAS
            LEALTAD DEMOCRATICA
            LEONES DEL MISTI
            LUIS GORVENIA SAMAN
            MORRO DE ARICA
            NESTOR CACERES VELÁSQUEZ I
            NESTOR CACERES VELÁSQUEZ II
            NUEVA VILLA ECOLOGICA
            PAMPA CHICA
            PORTALES DEL MIRADOR
            PRIMERO DE ENERO
            RAMIRO PRIALET
            ROCAS DEL MIRADOR A.S.A.
            SAN HILARION
            SAN ISIDRO EL LABRADOR
            SAN JOSE
            SAN LAZARO
            SAN LUIS
            SAN LUIS GONZAGA
            SEÑOR DE LAS PIEDADES
            SOLIDARIDAD
            TRES BALCONES DEL MISTI
            VILLA AREQUIPA
            VILLA ASUNCION
            VILLA CHACHAS
            VILLA CONFRATERNIDAD A
            VILLA CONFRATERNIDAD B
            VILLA CONFRATERNIDAD C
            VILLA ECOLOGICA A
            VILLA ECOLOGICA B
            VILLA ECOLOGICA C
            VILLA ECOLOGICA D
            VILLA ECOLOGICA E
            VILLA EL CONQUISTADOR 1
            VILLA EL CONQUISTADOR 2
            VILLA EL MIRADOR
            VILLA EL SALVADOR
            VILLA EL SOL
            VILLA FLORIDA
            VILLA INDEPENDIENTE
            VILLA MAGISTERIAL
            VILLA PARAISITO
            VILLA SAN PABLO
            VILLA UNION
            VILLA VITARTE
            VIRGEN DE CHAPI
            VISTA ALEGRE
        """,
        "040103": """
            11 DE MAYO
            30 DE MARZO
            ACEQUIA ALTA
            AMPLIACION LA TOMILLA
            BUEN AMANECER
            BUENOS AIRES
            CARMEN ALTO
            CERRITO SAN JACINTO
            COOPERATIVA TRABAJADORES DEL COLCA
            EMBAJADA DE JAPON
            ENACE
            FRANCISCO BOLOGNESI
            FUNDO CABRERIAS
            JOSE ABELARDO QUIÑONES
            JOSE OLAYA ZONA A
            JOSE OLAYA ZONA B
            JUAN VELASCO ALVARADO
            LA TOMILLA
            LOS JAZMINES
            MICAELA BASTIDAS
            MUJERES CON ESPERANZA
            PIONEROS
            PRIMERO DE JUNIO
            PUEBLO JOVEN CHARCANI
            PUEBLO TRADICIONAL CAYMA
            RAFEL BELAUNDE ZONA A
            RAFEL BELAUNDE ZONA B
            RAFEL BELAUNDE ZONA C
            RESIDENCIA DE CAYMA
            SAN MARTIN DE PORRES
            SANTA ROSA DE LIMA
            SANTUARIO CHARCANI CHAPI CHICO
            SEÑOR DE LA CAÑA
            SEÑOR DE LOS MILAGROS
            TRONCHADERO
            URBANIZACION LEON XIII
            VICTOR RAUL HAYA DE LA TORRE
            VILLA EL MIRADOR
            VIRGEN DE CHAPI
        """,
        "040101": """
            CERCADO
            COOP. UNIVERSITARIA
            LA NEGRITA
        """,
        "040104": """
            CERRO COLORADO
            CERRO VIEJO
            PACHACUTEC
        """,
        "040105": """
            CHARACATO
        """,
        "040106": """
            CHIGUATA
        """,
        "040107": """
            HUNTER
            PAMPAS DEL CUZCO
        """,
    },
    {
        "040129": """
            13 DE ENERO
            3 DE OCTUBRE
            AGRICULTURA
            ALAMEDA DEL SOL
            ALAMEDA DOLORES
            ALAS DEL SUR
            ALBORADA
            ALTO DE LA LUNA
            AMAUTA
            ASOCIACION HUERTAS
            BANCARIOS
            CALLEJON
            CALLEJON TASAHUAYO
            CAMINO REAL
            CASA BELLA
            CASA BLANCA
            CASAPIA
            COLON
            COOP. ALCIDES CARRION
            COOP. CORAZON DE MARIA
            COOP. MAGISTRAL SAN MANUEL
            COOP. MANUEL PRADO
            DUEÑOS DEL SUR
            EL MORAL
            FUNDO LOS HUERTOS
            JACINTOS
            JARDINES DE LA FLORIDA
            JUAN PABLO VIZCARDO Y GUZMAN
            KENNEDY
            LA BREÑA
            LA CAMPIÑA
            LA CANTUTA
            LA CASTRO
            LA ESPERANZA (ADEPA)
            LA ESTRELLA
            LA FLORIDA
            LA MELGAR
            LA MELGARIANA
            LA UNION
            LAMBRAMANI
            LAS BEGONIAS
            LAS ESMERALDAS
            LAS MORAS
            LOS CARDENALES
            LOS CISNES
            LOS CONQUISTADORES
            LOS HERALDOS
            LOS LAURELES
            LOS NARANJOS
            LOS OLMOS - CEDRO DE VILLA
            LOS SAUCES
            MALECON PAUCARPATA
            MI PERU
            MOLLARI
            MONTERREY
            MONTERRICO
            PARAISO
            PASAJE TASAHUAYO
            PEDRO DIEZ CANSECO
            PEDRO P. DIAZ
            PLAZA REAL - LA ENCALADA
            PRIMAVERA
            QUINTA LOS NARANJOS
            QUINTA LOURDES
            QUINTA SAN JOSE
            QUINTA SANTA MARIA
            QUINTA TRISTAN
            RESIDENCIAL LOS QUINTALES
            RESIDENCIAL MONTERRICO
            ROSARIO
            SAN EULALIO
            SANTA CATALINA
            SANTA ELSA
            SANTA LUCIA
            SANTA LUISA
            SANTA MARIA LAMBRAMANI
            SANTA MONICA
            SANTO DOMINGO
            SIMON BOLIVAR
            SOLAR DEL BOSQUE
            TASAHUAYO
            URISH NEISSER
            VILLA AMERICA
            VILLA DOLORES
            VILLA FAP
            VILLA JABIRU
            VILLA LOS FRANCOS
            VILLA RESIDENCIAL AURORA
            VINATEA REYNOSO
        """,
        "040108": """
            BARRIOS ALTOS
            BASE AEREA
            BENITO LAZO
            CRISTO REY
            CUESTA DE GALLINAZOS
            EL PARAISO
            EL TRIUNFO CRUCE LA JOYA
            EL TRIUNFO II
            FILTRACIONES
            HEROES ANONIMOS
            KILOMETRO 48
            LA CANO
            LA CURVA
            LA ESTRELLA
            LA FLORIDA
            LA GRANJA
            LA VICTORIA
            LA VICTORIA II
            LAS DUNAS
            LAS PALMERAS
            LATERAL 1
            LATERAL 2
            LATERAL 3
            LATERAL 4
            LATERAL 5
            LATERAL 6
            LATERAL 7
            LATERAL 8
            LECHE GLORIA
            LOS GIRASOLES
            LOS LAURELES
            LOS MEDANOS
            LOS MILAGROS
            LOS PATRIOTAS
            LOS ROSALES
            MARKO JARA
            MI BUEN JESUS
            MIRADOR EL TRIUNFO
            MIRADOR LA VICTORIA
            PALCA
            PRIMAVERA
            PUEBLO LIBRE
            PUEBLO TRADICIONAL LA JOYA
            SAN CAMILO
            SAN ISIDRO
            SAN JOSE
            SAN PEDRO
            SAN PEDRO Y SAN PABLO
            VILLA EL SALVADOR
            VILLA LA JOYA
            VILLA SAN JUAN
            VITOR
            YURAMAYO
        """,
    },
    {
        "040109": """
            9 DE OCTUBRE
            ALTO PERU
            ALTO SAN MARTIN
            ARTURO VILLEGAS
            ATALAYA
            BERLIN
            BUEN PASTOR
            BUENA VISTA
            CASUARINAS
            CERRITO BELEN
            CHACHANI
            CHAPARRAL
            COMANDANTE CANGA
            CRISTOBAL COLON
            FRANCISCO MOSTAJO
            GARCILAZO DE LA VEGA
            GOLGOTA
            HEROES DEL CENEPA
            HUASCAR
            ISLA MELGAR
            JERUSALEN
            JOSE CARLOS MARIATEGUI
            JOSE MARIA ARGUEDAS
            LA RINCONADA
            LAS AMERICAS
            LAS DALIAS
            LAS ROCAS
            LOS ANGELES
            LOS CEDROS
            LOS CLAVELES
            LOS GERANIOS
            LOS OLIVOS
            LOS PINOS
            LOS ROSALES
            MARIA NIEVES Y BUSTAMANTE
            MARIANO BUSTAMANTE
            MIRADOR
            MONTESORI
            NICOLAS DE PIEROLA
            NUEVO AMANECER
            NUEVO ISRAEL
            NUEVO MILENIO
            OLIMPICA
            PASAJE ATAHUALPA
            PASAJE BELEN
            PASEO AREQUIPA
            PUEBLO LIBRE
            REPUBLICA DE CHILE
            REVOLUCION PERUANA
            ROSASPATA
            SAN ANDRES
            SAN CRISTOBAL
            SAN FRANCISCO
            SAN JERONIMO
            SAN MIGUEL
            SAN VALENTIN
            SANTO DOMINGO
            SEÑOR DE HUANCA
            SEÑOR DE LOS MILAGROS
            SUDAMERICA
            VILLA MARIA DEL TRIUNFO
            VILLA SAN FELIPE
            VILLAMAR
            VIRGEN DE CHAPI
            VIRGEN DEL ROSARIO
        """,
        "040110": """
            ALTO MISTI
            LAS PALMERAS
            MIRAFLORES
        """,
        "040111": """
            MOLLEBAYA
        """,
        "040112": """
            15 DE AGOSTO
            ALAMEDA CHORRILLOS
            ALEJANDRO VON HUMBOLT
            ALTO JESUS
            ALTO PAUCARPATA
            AMPLIACION ALTO JESUS
            AMPLIACION PAUCARPATA
            APIMA
            BALNEARIO DE JESUS
            CALIFORNIA
            CAMPO DE MARTE
            CAYRO
            CIUDAD BLANCA
            CRISTO REY
            EL PEDREGAL
            GUARDIA CIVIL
            HÉROES DE ANGAMOS
            HIJOS DE GRAU
            ISRAEL
            JESÚS MARIA
            JESUS NAZARENO
            JORGE CHÁVEZ
            JOSÉ CARLOS MARIÁTEGUI
            JUVENTUD FRANCISCO MOSTAJO
            LA COLONIAL
            LEONCIO PRADO
            LUZ Y ALEGRIA
            MANCO CAPAC
            MANUEL PRADO
            MIGUEL GRAU
            MORRO DE ARICA
            NUEVA ALBORADA
            NUEVO PERU
            PAUCARPATA
            PEDRO P. DIAZ
            PEDRO VILCAPAZA
            PORONGOCHE VILLA HERMOZA
            PROGRESISTA
            PUEBLO TRADICIONAL DE PAUCARPATA
            QUINCE DE ENERO
            SAN JUAN FRANCISCO MOSTAJO
            SAN MIGUEL GRAU
            SAN SALVADOR
            SANTA MARIA
            SEÑOR DE LOS MILAGROS
            SOR ANA DE LOS ANGELES
            ULRICH NEISSER
            VILLA ARTESANAL AREQUIPA
            VILLA EL SOL
            VILLA GRAU
            VILLA LOS PINOS
            VILLA MARÍA DEL TRIUNFO
            VILLA MIGUEL GRAU
            VILLA PORONGOCHE
            VIÑA DEL MAR
        """,
    },
    {
        "040113": """
            POCSI
        """,
        "040114": """
            POLOBAYA
        """,
        "040115": """
            QUEQUEÑA
        """,
        "040116": """
            SABANDÍA
        """,
        "040117": """
            SACHACA
        """,
        "040118": """
            SAN JUAN DE SIGUAS
        """,
        "040119": """
            SAN JUAN DE TARUCANI
        """,
        "040120": """
            SANTA ISABEL DE SIGUAS
        """,
        "040121": """
            SANTA RITA DE SIGUAS
        """,
        "040122": """
            SOCABAYA
        """,
        "040123": """
            8 DE DICIEMBRE
            ALTO PATASAGUA
            ALTO SAN JOSÉ
            JUAN PABLO II
            MICAELA BASTIDAS
            PAMPAS NUEVAS
            SAN JOSÉ
            SAN PEDRO
            SANTA RITA
            SANTA TERESA
            TIABAYA
            VIRGEN DE LAS PEÑAS
        """,
        "040124": """
            UCHUMAYO
        """,
        "040125": """
            VITOR
        """,
        "040126": """
            YANAHUARA
        """,
        "040127": """
            YARABAMBA
        """,
    },
    {
        "040128": """
            ALTIPLANO
            APIAAR
            APIPA
            CALERA
            CAMINEROS EMPLEADOS
            CAMINEROS OBREROS
            CASAO
            CHASQUIPAMPA
            CHUCA
            CIUDAD DE DIOS
            COLCA
            EL TRIUNFO
            ESTACION
            HATUMPATA
            HIJOS CIUDAD DE DIOS
            HUANCA
            IMATA
            JOSE ABELARDO QUIÑONES
            LLUTA
            MALATA
            MILAGROS
            MISANAYO
            MOKKA
            MURCO
            NUEVA JUVENTUD
            PAMPA BLANCA
            PAMPA CAÑAHUAS
            PASCANA
            PASMA
            PICHINCA
            PILLONE
            PILLONES
            PORVENIR
            PROFAM
            PUCCRO
            QUISCOS
            SAN BASILIO
            SUMBAY
            TANCAYA
            TAYA
            TOCROYO
            TOROY
            UYUPAMPA
            VILLA CRISTO
            VINCOCAYA
            YURA VIEJO
        """,
    },
)

AREQUIPA_LOCALITIES: dict[str, str] = {}
for _part in _SEED_PARTS:
    AREQUIPA_LOCALITIES.update(_part)
