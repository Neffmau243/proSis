"""Patient SIS master data and documented ethnicity catalog; site paper defaults.

No patient is assigned an affiliation or an ethnicity by this migration.
Source: MINSA 2022 manual, https://bvs.minsa.gob.pe/local/MINSA/5702.pdf pp.8-9.
The published table skips code 41; preserve its identifiers, do not renumber.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "20260919_0015_patient_sis"
down_revision = "20260919_0014_fua_print"
branch_labels = None
depends_on = None

# MySQL requires matching character sets AND collations on both sides of a
# textual foreign key. Existing installations may default to 0900_ai_ci.
ETHNICITY_COLLATION = "utf8mb4_unicode_ci"


def _ensure_patient_ethnicity_column(bind) -> None:
    columns = {column["name"]: column for column in sa.inspect(bind).get_columns("pacientes")}
    code_type = mysql.VARCHAR(2, charset="utf8mb4", collation=ETHNICITY_COLLATION)
    existing = columns.get("etnia_codigo")
    if existing is None:
        op.add_column("pacientes", sa.Column("etnia_codigo", code_type, nullable=True))
    elif getattr(existing["type"], "collation", None) != ETHNICITY_COLLATION:
        # Resume the original interrupted upgrade: MySQL commits preceding DDL
        # even when a later FK fails. Modify only this new two-character code;
        # do not rebuild tables, remove records, or stamp a partial revision.
        op.alter_column(
            "pacientes", "etnia_codigo", existing_type=existing["type"],
            type_=code_type, existing_nullable=existing["nullable"],
        )

ETHNICITIES = {
    "1": "Achuar", "2": "Aimara", "3": "Amahuaca", "4": "Arabela",
    "5": "Ashaninka", "6": "Asheninka", "7": "Awajún", "8": "Bora",
    "9": "Capanahua", "10": "Cashinahua", "11": "Chamicuro", "12": "Chapra",
    "13": "Chitonahua", "14": "Ese Eja", "15": "Harakbut", "16": "Ikiyu",
    "17": "Iñapari", "18": "Isconahua", "19": "Jaqaru", "20": "Jíbaro",
    "21": "Kakataibo", "22": "Kakinte", "23": "Kandozi", "24": "Kichwa",
    "25": "Kukama Kukamiria", "26": "Madija", "27": "Maijuna", "28": "Marinahua",
    "29": "Mashco Piro", "30": "Mastanahua", "31": "Matsés", "32": "Matsigenka",
    "33": "Muniche", "34": "Murui Muinani", "35": "Nahua", "36": "Nanti",
    "37": "Nomatsigenga", "38": "Ocaina", "39": "Omagua", "40": "Quechuas",
    "42": "Resígaro", "43": "Sharanahua", "44": "Shawi", "45": "Shipibo-Konibo",
    "46": "Shiwilu", "47": "Tikuna", "48": "Urarina", "49": "Uro",
    "50": "Vacacocha", "51": "Wampis", "52": "Yagua", "53": "Yaminahua",
    "54": "Yanesha", "55": "Yine", "56": "Afroperuano", "57": "Blanco",
    "58": "Mestizo", "59": "Asiático descendiente", "60": "Otro",
}


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("etnias"):
        op.create_table(
            "etnias", sa.Column("codigo", sa.String(2), primary_key=True),
            sa.Column("nombre", sa.String(100), nullable=False),
            sa.Column("fuente", sa.String(100), nullable=False),
            sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
        )
    table = sa.table("etnias", sa.column("codigo"), sa.column("nombre"), sa.column("fuente"))
    existing = set(bind.execute(sa.select(table.c.codigo)).scalars())
    rows = [{"codigo": code, "nombre": name, "fuente": "MINSA HIS 2022 · RM 975-2017 · pp. 8-9"}
            for code, name in ETHNICITIES.items() if code not in existing]
    if rows:
        op.bulk_insert(table, rows)
    columns = {c["name"] for c in sa.inspect(bind).get_columns("pacientes")}
    for name, length in (("sis_diresa", 3), ("sis_tipo", 2), ("sis_numero", 9), ("sis_secuencia", 2)):
        if name not in columns:
            op.add_column("pacientes", sa.Column(name, sa.String(length), nullable=True))
    _ensure_patient_ethnicity_column(bind)
    fks = {fk["name"] for fk in sa.inspect(bind).get_foreign_keys("pacientes")}
    if "fk_pacientes_etnia" not in fks:
        op.create_foreign_key("fk_pacientes_etnia", "pacientes", "etnias", ["etnia_codigo"], ["codigo"], ondelete="RESTRICT", onupdate="CASCADE")
    columns = {c["name"] for c in sa.inspect(bind).get_columns("establecimientos")}
    for column in (
        sa.Column("fua_personal_atiende", sa.String(20), nullable=False, server_default="IPRESS"),
        sa.Column("fua_lugar_atencion", sa.String(20), nullable=False, server_default="INTRAMURAL"),
        sa.Column("fua_codigo_aisped", sa.String(20), nullable=True),
        sa.Column("fua_renipress_preimpreso", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
    ):
        if column.name not in columns:
            op.add_column("establecimientos", column)


def downgrade() -> None:
    # Only an explicit Alembic downgrade removes these new data columns.
    for name in ("fua_personal_atiende", "fua_lugar_atencion", "fua_codigo_aisped", "fua_renipress_preimpreso"):
        op.drop_column("establecimientos", name)
    op.drop_constraint("fk_pacientes_etnia", "pacientes", type_="foreignkey")
    for name in ("sis_diresa", "sis_tipo", "sis_numero", "sis_secuencia", "etnia_codigo"):
        op.drop_column("pacientes", name)
    op.drop_table("etnias")
