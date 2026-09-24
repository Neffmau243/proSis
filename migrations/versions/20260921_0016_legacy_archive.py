"""Preserve every source record and incomplete historical encounter.

No clinical table is relaxed and no existing data is rewritten.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "20260921_0016_legacy_archive"
down_revision = "20260919_0015_patient_sis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    options = dict(mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci")
    if "importaciones_legado" not in tables:
        op.create_table("importaciones_legado",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column("huella_fuente", sa.String(64), nullable=False, unique=True),
            sa.Column("version_etl", sa.String(30), nullable=False),
            sa.Column("manifiesto", mysql.JSON, nullable=False),
            sa.Column("resumen", mysql.JSON, nullable=True),
            sa.Column("estado", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            **options)
    if "registros_legado" not in tables:
        op.create_table("registros_legado",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column("importacion_id", mysql.BIGINT(unsigned=True), sa.ForeignKey("importaciones_legado.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("tabla_origen", sa.String(64), nullable=False),
            sa.Column("fila_origen", mysql.INTEGER(unsigned=True), nullable=False),
            sa.Column("huella_fila", sa.String(64), nullable=False),
            sa.Column("payload_json", mysql.LONGTEXT, nullable=False),
            sa.Column("incidencias", mysql.JSON, nullable=False),
            sa.Column("estado", sa.String(30), nullable=False),
            sa.Column("destino_tabla", sa.String(64), nullable=True),
            sa.Column("destino_id", sa.String(100), nullable=True),
            sa.UniqueConstraint("importacion_id", "tabla_origen", "fila_origen", name="uq_legado_fila"),
            **options)
    if "atenciones_legado" not in tables:
        op.create_table("atenciones_legado",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column("registro_id", mysql.BIGINT(unsigned=True), sa.ForeignKey("registros_legado.id", ondelete="RESTRICT"), nullable=False, unique=True),
            sa.Column("paciente_id", mysql.BIGINT(unsigned=True), sa.ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("paciente_registro_id", mysql.BIGINT(unsigned=True), sa.ForeignKey("registros_legado.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("profesional_id", mysql.BIGINT(unsigned=True), sa.ForeignKey("profesionales.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("fecha_atencion", sa.DateTime, nullable=True),
            sa.Column("historia_clinica", sa.String(255), nullable=True),
            sa.Column("consultorio_texto", sa.String(150), nullable=True),
            sa.Column("profesional_texto", sa.String(200), nullable=True),
            sa.Column("datos_clinicos", mysql.JSON, nullable=False),
            sa.Column("vinculo_estado", sa.String(30), nullable=False),
            **options)
    for table, name, columns in (
        ("registros_legado", "ix_legado_estado", ["importacion_id", "estado"]),
        ("atenciones_legado", "ix_atenciones_legado_paciente_fecha", ["paciente_id", "fecha_atencion", "id"]),
    ):
        if name not in {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}:
            op.create_index(name, table, columns)


def downgrade() -> None:
    for table in ("atenciones_legado", "registros_legado", "importaciones_legado"):
        op.drop_table(table)
