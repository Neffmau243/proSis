-- =====================================================================
--  esquema destino MySQL 8  (base limpia, normalizada)
--  Origen: Data_base.mdb  (Microsoft Access / Jet 4)
--  Orden de ejecucion: 00_schema.sql -> 20_catalogos -> 30_pacientes
--                      -> 40_atenciones -> 50_formatos -> 60_config -> 90_calidad
--  El ETL (etl_mysql.py) genera los stg_* y todos los INSERT.
-- =====================================================================

DROP DATABASE IF EXISTS sishosp_clean;
CREATE DATABASE sishosp_clean
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE sishosp_clean;

SET NAMES utf8mb4;
SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION';
SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================================
-- 1. CATALOGOS  (dimensiones; se pueblan desde los catalogos Access)
-- =====================================================================

CREATE TABLE cat_distrito (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  codigo_legacy  INT          NULL,
  distrito       VARCHAR(120) NOT NULL,
  nombre_norm    VARCHAR(120) NOT NULL,
  ubigeo         VARCHAR(10)  NULL,
  id_dpto        VARCHAR(4)   NULL,
  id_provincia   VARCHAR(4)   NULL,
  id_distrito    VARCHAR(4)   NULL,
  altitud_msnm   SMALLINT UNSIGNED NULL,
  quintil        TINYINT UNSIGNED  NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_distrito_norm (nombre_norm),
  KEY ix_distrito_ubigeo (ubigeo)
) ENGINE=InnoDB COMMENT='Provincia (Access): distritos con ubigeo y altitud';

CREATE TABLE cat_microred (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  codigo_legacy INT          NULL,
  descripcion   VARCHAR(120) NOT NULL,
  nombre_norm   VARCHAR(120) NOT NULL,
  id_disa       VARCHAR(4)   NULL,
  id_red        VARCHAR(4)   NULL,
  id_microred   VARCHAR(4)   NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_microred_norm (nombre_norm)
) ENGINE=InnoDB;

CREATE TABLE cat_establecimiento (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  codigo_legacy  INT          NULL,
  nombre         VARCHAR(160) NOT NULL,
  nombre_norm    VARCHAR(160) NOT NULL,
  renaes         VARCHAR(10)  NULL,
  clave          VARCHAR(6)   NULL,
  sien           VARCHAR(6)   NULL,
  origen         ENUM('EESS','EESS_PS','texto_libre') NOT NULL,
  microred_id    INT UNSIGNED NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_eess_norm (nombre_norm),
  KEY ix_eess_microred (microred_id),
  CONSTRAINT fk_eess_microred FOREIGN KEY (microred_id)
    REFERENCES cat_microred (id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='EESS + EESS_PS + nombres libres vistos en los datos';

CREATE TABLE cat_eess_sesma (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  codigo_legacy  INT          NULL,
  nombre         VARCHAR(160) NOT NULL,
  nombre_norm    VARCHAR(160) NOT NULL,
  renaes         VARCHAR(10)  NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_sesma_norm (nombre_norm)
) ENGINE=InnoDB COMMENT='Padron nacional EESS_PS_SESMA (257) para resolver nombres';

CREATE TABLE cat_especialidad (
  id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  codigo       VARCHAR(10)  NULL,
  nombre       VARCHAR(120) NOT NULL,
  nombre_norm  VARCHAR(120) NOT NULL,
  origen       VARCHAR(24)  NOT NULL COMMENT 'Especialidades|Especialidades2|Especialidades3|Certificado|Esp_*',
  PRIMARY KEY (id),
  UNIQUE KEY uq_especialidad_norm (nombre_norm)
) ENGINE=InnoDB;

CREATE TABLE cat_profesional (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  codigo_legacy   INT          NULL,
  nombre          VARCHAR(160) NOT NULL,
  nombre_norm     VARCHAR(160) NOT NULL,
  dni             CHAR(8)      NULL,
  profesion       VARCHAR(60)  NULL,
  especialidad    VARCHAR(80)  NULL,
  colegiatura     VARCHAR(20)  NULL,
  atencion_codigo VARCHAR(20)  NULL,
  origen          VARCHAR(24)  NOT NULL COMMENT 'Profesionales|Prof_*',
  PRIMARY KEY (id),
  UNIQUE KEY uq_profesional_dni (dni),
  KEY ix_profesional_norm (nombre_norm)
) ENGINE=InnoDB COMMENT='Profesionales + Prof_<servicio>';

CREATE TABLE cat_consultorio (
  id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre       VARCHAR(60) NOT NULL,
  nombre_norm  VARCHAR(60) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_consultorio_norm (nombre_norm)
) ENGINE=InnoDB COMMENT='Consultorio / servicio de atencion';

CREATE TABLE cat_seguro (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  codigo_legacy VARCHAR(10)  NULL,
  nombre        VARCHAR(80) NOT NULL,
  nombre_norm   VARCHAR(80) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_seguro_norm (nombre_norm)
) ENGINE=InnoDB COMMENT='EESS_SIS (mal nombrada) + valores de Pacientes.Seguro';

CREATE TABLE cat_condicion (
  id                 INT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre             VARCHAR(40) NOT NULL,
  nombre_norm        VARCHAR(40) NOT NULL,
  etapa_vida         ENUM('NINO','ADOLESCENTE','JOVEN','ADULTO','ADULTO_MAYOR') NULL,
  estado_gestacional ENUM('GESTANTE','PUERPERA','NO_GESTANTE','LACTANTE')      NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_condicion_norm (nombre_norm)
) ENGINE=InnoDB COMMENT='Condicion del paciente; se desdobla en etapa_vida + estado_gestacional';

CREATE TABLE cat_lugar (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  tabla_origen   VARCHAR(16)  NOT NULL COMMENT 'Z_01..Z_29 o texto_libre',
  anio           SMALLINT UNSIGNED NULL,
  codigo_legacy  INT          NULL,
  nombre         VARCHAR(160) NOT NULL,
  nombre_norm    VARCHAR(160) NOT NULL,
  clave_texto    VARCHAR(20)  NULL COMMENT 'valor crudo de Clave (28 de 29 tablas lo tienen roto)',
  ubigeo         VARCHAR(10)  NULL COMMENT 'solo si la clave era un ubigeo real',
  PRIMARY KEY (id),
  UNIQUE KEY uq_lugar_origenn (tabla_origen, nombre_norm),
  KEY ix_lugar_norm (nombre_norm),
  KEY ix_lugar_ubigeo (ubigeo)
) ENGINE=InnoDB COMMENT='Union de los 29 catalogos Z_* (lugar / localidad)';

CREATE TABLE cat_tipo_certificado (
  id     INT UNSIGNED NOT NULL AUTO_INCREMENT,
  codigo VARCHAR(10)  NULL,
  nombre VARCHAR(80)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tipo_cert (nombre)
) ENGINE=InnoDB COMMENT='Certificado (Access): tipos de certificado';

CREATE TABLE cat_prestacion (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  codigo           VARCHAR(60) NOT NULL COMMENT 'valor tal cual: MEDICINA39, CONSULTA12...',
  servicio_prefijo VARCHAR(40) NULL,
  item_numero      VARCHAR(20) NULL,
  en_catalogo      TINYINT(1)  NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY uq_prestacion_codigo (codigo)
) ENGINE=InnoDB COMMENT='Valores reutilizables detectados en Atencion.Codigo_N';

CREATE TABLE cat_institucion (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  codigo_legacy INT          NULL,
  nombre        VARCHAR(120) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_institucion (nombre)
) ENGINE=InnoDB;

-- =====================================================================
-- 2. NUCLEO
-- =====================================================================

CREATE TABLE paciente (
  id                        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  legacy_codclie            INT          NOT NULL COMMENT 'Pacientes.Codclie original',
  origen_tabla              ENUM('Pacientes','Pacientes_ref','Atencion') NOT NULL DEFAULT 'Pacientes',
  historia_clinica          VARCHAR(24)  NULL,
  historia_familiar         VARCHAR(24)  NULL,
  historia_familiar_placeholder TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1 si el origen traia "-"',
  tipo_documento            ENUM('DNI','LIBRETA','SIN_DOCUMENTO') NOT NULL DEFAULT 'SIN_DOCUMENTO',
  numero_documento          VARCHAR(12)  NULL,
  apellido_paterno          VARCHAR(80)  NULL,
  apellido_materno          VARCHAR(80)  NULL,
  primer_nombre             VARCHAR(80)  NULL,
  otros_nombres             VARCHAR(120) NULL,
  nombre_completo           VARCHAR(300) GENERATED ALWAYS AS
      (TRIM(CONCAT_WS(' ', apellido_paterno, apellido_materno, primer_nombre, otros_nombres))) STORED,
  sexo                      CHAR(1)      NULL COMMENT 'M / F; NULL si el origen estaba corrupto o vacio',
  fecha_nacimiento          DATE         NULL,
  fecha_nacimiento_texto    VARCHAR(25)  NULL COMMENT 'valor crudo: (Empty Date)|(Invalid Date)|...',
  fecha_inscripcion         DATE         NULL,
  fecha_inscripcion_placeholder TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1 si es el 2016-01-01 de la carga masiva (62%)',
  distrito_id               INT UNSIGNED NULL,
  lugar_id                  INT UNSIGNED NULL,
  establecimiento_id        INT UNSIGNED NULL,
  seguro_id                 INT UNSIGNED NULL,
  condicion_id              INT UNSIGNED NULL,
  etapa_vida                ENUM('NINO','ADOLESCENTE','JOVEN','ADULTO','ADULTO_MAYOR') NULL,
  estado_gestacional        ENUM('GESTANTE','PUERPERA','NO_GESTANTE','LACTANTE')      NULL,
  direccion                 VARCHAR(255) NULL,
  distrito_texto            VARCHAR(120) NULL COMMENT 'texto crudo, para trazabilidad',
  localidad_texto           VARCHAR(160) NULL,
  establecimiento_texto     VARCHAR(160) NULL,
  seguro_texto              VARCHAR(80)  NULL,
  tiene_celda_corrupta      TINYINT(1)   NOT NULL DEFAULT 0,
  es_duplicado_sospechoso   TINYINT(1)   NOT NULL DEFAULT 0,
  created_at                TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_paciente_legacy (legacy_codclie, origen_tabla),
  KEY ix_paciente_hc (historia_clinica),
  KEY ix_paciente_doc (numero_documento),
  KEY ix_paciente_nombre (nombre_completo(60)),
  KEY ix_paciente_distrito (distrito_id),
  KEY ix_paciente_lugar (lugar_id),
  KEY ix_paciente_eess (establecimiento_id),
  KEY ix_paciente_seguro (seguro_id),
  CONSTRAINT fk_pac_distrito FOREIGN KEY (distrito_id) REFERENCES cat_distrito (id) ON DELETE SET NULL,
  CONSTRAINT fk_pac_lugar    FOREIGN KEY (lugar_id)    REFERENCES cat_lugar (id)    ON DELETE SET NULL,
  CONSTRAINT fk_pac_eess     FOREIGN KEY (establecimiento_id) REFERENCES cat_establecimiento (id) ON DELETE SET NULL,
  CONSTRAINT fk_pac_seguro   FOREIGN KEY (seguro_id)   REFERENCES cat_seguro (id)   ON DELETE SET NULL,
  CONSTRAINT fk_pac_cond     FOREIGN KEY (condicion_id) REFERENCES cat_condicion (id) ON DELETE SET NULL,
  CONSTRAINT ck_pac_sexo     CHECK (sexo IS NULL OR sexo IN ('M','F'))
) ENGINE=InnoDB COMMENT='Un registro por persona (padron)';

-- Campos "anchos" y de significado no confirmado: Anexo1..25, Peso_PG, Arequipa_*,
-- Semana, Parto, etc. Se conservan en EAV para poder decidir despues sin perder dato.
CREATE TABLE paciente_anexo (
  paciente_id  BIGINT UNSIGNED NOT NULL,
  campo        VARCHAR(40) NOT NULL,
  valor        TEXT        NULL,
  origen_tabla VARCHAR(24) NOT NULL COMMENT 'Pacientes | Pacientes_ref',
  cargado_at   TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (paciente_id, campo, origen_tabla),
  CONSTRAINT fk_anexo_pac FOREIGN KEY (paciente_id) REFERENCES paciente (id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Anexo1..25 + campos heredados duplicados (pendiente confirmar significado)';

CREATE TABLE atencion (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  legacy_id           INT          NOT NULL COMMENT 'Atencion.Id original',
  paciente_id         BIGINT UNSIGNED NULL COMMENT 'NULL = atencion huerfana (60 casos), ver dq_rechazo',
  establecimiento_id  INT UNSIGNED NULL,
  consultorio_id      INT UNSIGNED NULL,
  profesional_id      INT UNSIGNED NULL,
  fecha_atencion      DATETIME     NULL COMMENT 'Fecha_atencion (date) + Hora1 (time)',
  fecha_atendido_texto VARCHAR(20) NULL COMMENT 'Fecha_atendido crudo dd/mm/yyyy (redundante)',
  hora_rango          TINYINT UNSIGNED NULL COMMENT 'Hora2 (7..19, solo la hora)',
  historia_clinica    VARCHAR(24)  NULL,
  edad_texto          VARCHAR(60)  NULL COMMENT '"75 años, 8 meses y 24 días"',
  edad_anios          SMALLINT UNSIGNED NULL,
  edad_meses          TINYINT UNSIGNED  NULL,
  edad_dias           SMALLINT UNSIGNED NULL,
  peso_kg             DECIMAL(5,2) NULL,
  talla_cm            DECIMAL(5,1) NULL,
  peso_pg_kg          DECIMAL(5,2) NULL,
  talla_pg_cm         DECIMAL(5,1) NULL,
  sistolica           SMALLINT UNSIGNED NULL,
  diastolica          SMALLINT UNSIGNED NULL,
  peso_edad_valor     DECIMAL(6,2) NULL COMMENT 'PE numerico (z-score)',
  peso_edad_etiqueta  VARCHAR(60)  NULL COMMENT 'PE cuando venia como "Normal"/"Desnutricion global"',
  talla_edad_valor    DECIMAL(6,2) NULL,
  talla_edad_etiqueta VARCHAR(60)  NULL,
  peso_talla_valor    DECIMAL(6,2) NULL,
  peso_talla_etiqueta VARCHAR(60)  NULL,
  tiene_celda_corrupta TINYINT(1)  NOT NULL DEFAULT 0,
  created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_atencion_legacy (legacy_id),
  KEY ix_ate_paciente (paciente_id),
  KEY ix_ate_fecha (fecha_atencion),
  KEY ix_ate_eess (establecimiento_id),
  KEY ix_ate_consultorio (consultorio_id),
  KEY ix_ate_profesional (profesional_id),
  KEY ix_ate_hc (historia_clinica),
  CONSTRAINT fk_ate_paciente FOREIGN KEY (paciente_id) REFERENCES paciente (id) ON DELETE SET NULL,
  CONSTRAINT fk_ate_eess     FOREIGN KEY (establecimiento_id) REFERENCES cat_establecimiento (id) ON DELETE SET NULL,
  CONSTRAINT fk_ate_consult  FOREIGN KEY (consultorio_id) REFERENCES cat_consultorio (id) ON DELETE SET NULL,
  CONSTRAINT fk_ate_prof     FOREIGN KEY (profesional_id) REFERENCES cat_profesional (id) ON DELETE SET NULL,
  CONSTRAINT ck_ate_peso     CHECK (peso_kg IS NULL OR peso_kg BETWEEN 0.2 AND 300),
  CONSTRAINT ck_ate_talla    CHECK (talla_cm IS NULL OR talla_cm BETWEEN 20 AND 250),
  CONSTRAINT ck_ate_pa       CHECK (sistolica IS NULL OR sistolica BETWEEN 30 AND 300)
) ENGINE=InnoDB COMMENT='Una fila por atencion (Atencion: 59.213)';

-- Explosion de Atencion.Codigo_1..15: 1 fila por codigo no vacio
CREATE TABLE atencion_codigo (
  atencion_id      BIGINT UNSIGNED NOT NULL,
  posicion         TINYINT UNSIGNED NOT NULL COMMENT '1..15 = Codigo_N de origen',
  valor            VARCHAR(120) NULL,
  prestacion_id    INT UNSIGNED NULL,
  servicio_prefijo VARCHAR(40)  NULL COMMENT 'texto alfabetico inicial del valor',
  es_texto_libre   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1 si la columna tenia alta cardinalidad (diagnostico/observacion)',
  PRIMARY KEY (atencion_id, posicion),
  KEY ix_atecod_prestacion (prestacion_id),
  KEY ix_atecod_valor (valor),
  CONSTRAINT fk_atecod_atencion FOREIGN KEY (atencion_id) REFERENCES atencion (id) ON DELETE CASCADE,
  CONSTRAINT fk_atecod_prest    FOREIGN KEY (prestacion_id) REFERENCES cat_prestacion (id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Prestaciones por atencion (antes Codigo_1..15)';

CREATE TABLE referencia (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  legacy_codclie     INT          NOT NULL,
  paciente_id        BIGINT UNSIGNED NULL,
  fecha_atencion     DATE         NULL,
  historia_clinica   VARCHAR(24)  NULL,
  numero_documento   VARCHAR(12)  NULL,
  apellidos_nombres  VARCHAR(200) NULL,
  sexo               CHAR(1)      NULL,
  edad_texto         VARCHAR(60)  NULL,
  distrito_texto     VARCHAR(120) NULL,
  localidad_texto    VARCHAR(160) NULL,
  direccion          VARCHAR(255) NULL,
  establecimiento_id INT UNSIGNED NULL,
  seguro_texto       VARCHAR(80)  NULL,
  grupo              VARCHAR(40)  NULL,
  referencia         TEXT         NULL,
  contrareferencia   TEXT         NULL,
  consultorio_id     INT UNSIGNED NULL,
  profesional_id     INT UNSIGNED NULL,
  admision           VARCHAR(40)  NULL,
  hora               VARCHAR(20)  NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_ref_legacy (legacy_codclie),
  KEY ix_ref_paciente (paciente_id),
  CONSTRAINT fk_ref_paciente FOREIGN KEY (paciente_id) REFERENCES paciente (id) ON DELETE SET NULL,
  CONSTRAINT fk_ref_eess     FOREIGN KEY (establecimiento_id) REFERENCES cat_establecimiento (id) ON DELETE SET NULL,
  CONSTRAINT fk_ref_consult  FOREIGN KEY (consultorio_id) REFERENCES cat_consultorio (id) ON DELETE SET NULL,
  CONSTRAINT fk_ref_prof     FOREIGN KEY (profesional_id) REFERENCES cat_profesional (id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Pacientes_ref: referencia / contrareferencia';

CREATE TABLE referencia_codigo (
  referencia_id BIGINT UNSIGNED NOT NULL,
  posicion      TINYINT UNSIGNED NOT NULL,
  valor         VARCHAR(120) NULL,
  PRIMARY KEY (referencia_id, posicion),
  CONSTRAINT fk_refcod_ref FOREIGN KEY (referencia_id) REFERENCES referencia (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Formatos con estructura propia (hoy casi vacios en Access, se dejan listos)
CREATE TABLE atencion_fua (
  id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  legacy_codclie    INT          NULL,
  historia_clinica  VARCHAR(24)  NULL,
  fecha_atencion    DATE         NULL,
  numero_documento  VARCHAR(12)  NULL,
  apellidos         VARCHAR(200) NULL,
  sexo              CHAR(1)      NULL,
  grupo             VARCHAR(40)  NULL,
  consultorio_id    INT UNSIGNED NULL,
  profesional       VARCHAR(160) NULL,
  admision          VARCHAR(40)  NULL,
  fua               VARCHAR(60)  NULL,
  referencia        TEXT         NULL,
  contrareferencia  TEXT         NULL,
  PRIMARY KEY (id),
  KEY ix_fua_legacy (legacy_codclie)
) ENGINE=InnoDB COMMENT='Atencion_fua (0 filas hoy)';

CREATE TABLE atencion_certificado (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  legacy_id        INT          NULL,
  legacy_codclie   VARCHAR(20)  NULL,
  nro_certificado  VARCHAR(40)  NULL,
  fecha_atencion   DATE         NULL,
  numero_documento VARCHAR(12)  NULL,
  apellidos_nombres VARCHAR(200) NULL,
  tipo_certificado_id INT UNSIGNED NULL,
  consultorio_id   INT UNSIGNED NULL,
  profesional      VARCHAR(160) NULL,
  admision         VARCHAR(40)  NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_cert_legacy (legacy_id),
  KEY ix_cert_tipo (tipo_certificado_id),
  CONSTRAINT fk_cert_tipo FOREIGN KEY (tipo_certificado_id)
    REFERENCES cat_tipo_certificado (id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Atencion_certificado (0 filas hoy)';

CREATE TABLE atencion_certificado_codigo (
  certificado_id BIGINT UNSIGNED NOT NULL,
  posicion       TINYINT UNSIGNED NOT NULL,
  valor          VARCHAR(120) NULL,
  PRIMARY KEY (certificado_id, posicion),
  CONSTRAINT fk_certcod_cert FOREIGN KEY (certificado_id)
    REFERENCES atencion_certificado (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE certificado_correlativo (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  legacy_codclie INT          NULL,
  numero         VARCHAR(40)  NULL,
  codigo         VARCHAR(40)  NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB COMMENT='Certificado_Nro (correlativo de certificados)';

-- =====================================================================
-- 3. CONFIGURACION HEREDADA (NO son datos de negocio: van a JSON)
-- =====================================================================

CREATE TABLE config_legado (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  tabla_origen  VARCHAR(32)  NOT NULL,
  fila_legacy   INT          NOT NULL,
  descripcion   VARCHAR(160) NULL,
  payload_json  JSON         NOT NULL,
  cargado_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_config_origen (tabla_origen, fila_legacy)
) ENGINE=InnoDB COMMENT='fua/fua2/fua3, Impresion, Impresora, Paginas_web, Instituciones, Responsable, EESS_HF, EESS_Padron, Calibrar';

CREATE TABLE plantilla_impresion (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre        VARCHAR(60)  NOT NULL,
  codigo_legacy INT          NULL,
  payload_json  JSON         NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_plantilla (nombre, codigo_legacy)
) ENGINE=InnoDB COMMENT='Calibrar / Calibrar_2 / Calibrar_3: coordenadas de impresion (NO son datos clinicos)';

CREATE TABLE formato_exportacion (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre        VARCHAR(60)  NOT NULL,
  fila_legacy   INT          NOT NULL,
  payload_json  JSON         NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_formato_export (nombre, fila_legacy)
) ENGINE=InnoDB COMMENT='Detalle_Adultos / Detalle_Mujeres_Gestantes / Detalle_Ninos (plantillas de exportacion SIS)';

-- =====================================================================
-- 4. CALIDAD / GOBIERNO DEL ETL
-- =====================================================================

CREATE TABLE dq_rechazo (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  origen_tabla  VARCHAR(32)  NOT NULL,
  origen_fila   INT          NULL,
  clave_negocio VARCHAR(64)  NULL COMMENT 'Codclie / Id / HC para poder rastrear la fila',
  regla         VARCHAR(40)  NOT NULL COMMENT 'R1_CELDA_CORRUPTA, R2_DNI_CENTINELA, ...',
  detalle       VARCHAR(255) NULL,
  valor_raw     TEXT         NULL,
  created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_dq_regla (regla),
  KEY ix_dq_origen (origen_tabla, origen_fila),
  KEY ix_dq_clave (clave_negocio)
) ENGINE=InnoDB COMMENT='Todo lo dudoso queda aqui: nada se descarta en silencio';

CREATE TABLE paciente_duplicado (
  id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  grupo             VARCHAR(80)  NOT NULL COMMENT 'hash del criterio de duplicidad',
  criterio          ENUM('HISTORIA_CLINICA','DNI','NOMBRE_FECHA_NAC','CODCLIE') NOT NULL,
  paciente_id       BIGINT UNSIGNED NULL,
  legacy_codclie    INT          NULL,
  historia_clinica  VARCHAR(24)  NULL,
  numero_documento  VARCHAR(12)  NULL,
  nombre_completo   VARCHAR(300) NULL,
  fecha_nacimiento  DATE         NULL,
  es_maestro        TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1 = fila que se conserva',
  decision          ENUM('PENDIENTE','MANTENER','FUSIONAR','DESCARTAR') NOT NULL DEFAULT 'PENDIENTE',
  created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_dup_grupo (grupo),
  KEY ix_dup_paciente (paciente_id),
  CONSTRAINT fk_dup_paciente FOREIGN KEY (paciente_id) REFERENCES paciente (id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Candidatos a fusion manual (el ETL nunca fusiona solo)';

CREATE TABLE etl_run (
  id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  iniciado_at  DATETIME     NOT NULL,
  terminado_at DATETIME     NULL,
  origen       VARCHAR(120) NOT NULL,
  version_etl  VARCHAR(20)  NOT NULL,
  resumen_json JSON         NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

-- =====================================================================
-- 5. STAGING: el ETL crea un stg_<tabla> por cada tabla de Access
--    (todas las columnas TEXT) + _src_row, para auditoria 1:1.
--    Ejemplo de la forma que genera:
-- CREATE TABLE stg_pacientes (
--   _src_row INT NOT NULL PRIMARY KEY, `Codclie` TEXT, `Historia_Clinica` TEXT,
--   ... , cargado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- ) ENGINE=InnoDB;
-- =====================================================================
