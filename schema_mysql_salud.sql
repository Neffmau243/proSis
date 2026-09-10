/*
  Sistema de Salud IPRESS - esquema base
  Motor objetivo: MySQL 8.0+

  Referencia estática del esquema al finalizar la revisión Alembic
  20260910_0006_clinical_integrity. La fuente operativa es Alembic:
  use `python -m app.scripts.bootstrap_database`, no este archivo, para
  desplegar o evolucionar una base existente.

  No borra una base existente ni importa datos desde Data_base.mdb.

  No contiene triggers, procedimientos, vistas, columnas generadas ni reglas de
  negocio: dichas reglas deben implementarse en el backend. Ver
  README.md.

  Decisiones de diseño:
  - "id" es la clave técnica interna.
  - codclie_legacy conserva el Codclie de Access y es único.
  - Los signos vitales pertenecen a una atención, no a la ficha permanente del paciente.
  - Los Anexo1...Anexo25 se guardan temporalmente en una tabla compatible,
    preservando la diferencia entre NULL y una cadena vacía.
*/

CREATE DATABASE IF NOT EXISTS sistema_salud_ipress
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE sistema_salud_ipress;

/* ============================================================
   1. CATÁLOGOS BÁSICOS
   ============================================================ */

CREATE TABLE IF NOT EXISTS tipos_documento (
  codigo VARCHAR(10) PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sexos (
  codigo CHAR(1) PRIMARY KEY,
  nombre VARCHAR(30) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS seguros (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(30) NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_seguros_codigo UNIQUE (codigo),
  CONSTRAINT uq_seguros_nombre UNIQUE (nombre)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS profesiones (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_profesiones_nombre UNIQUE (nombre)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS especialidades (
  codigo VARCHAR(20) PRIMARY KEY,
  nombre VARCHAR(150) NOT NULL,
  grupo VARCHAR(100) NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS prestaciones (
  codigo VARCHAR(30) PRIMARY KEY,
  descripcion VARCHAR(300) NOT NULL,
  grupo VARCHAR(100) NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cie10 (
  codigo VARCHAR(20) PRIMARY KEY,
  descripcion VARCHAR(500) NOT NULL,
  categoria VARCHAR(200) NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

/* Una atención es ambulatoria O de emergencia, no ambas a la vez. */
CREATE TABLE IF NOT EXISTS modalidades_atencion (
  codigo VARCHAR(20) PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

/*
  El grupo se calcula desde la fecha de nacimiento al registrar la atención
  y se guarda como foto histórica. Los rangos son configurables por la IPRESS.
*/
CREATE TABLE IF NOT EXISTS grupos_etarios (
  codigo VARCHAR(20) PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  edad_minima_meses SMALLINT UNSIGNED NULL,
  edad_maxima_meses SMALLINT UNSIGNED NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

/* ============================================================
   2. UBICACIÓN E IPRESS
   ============================================================ */

CREATE TABLE IF NOT EXISTS disa (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(20) NOT NULL,
  nombre VARCHAR(200) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_disa_codigo UNIQUE (codigo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS redes (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_disa BIGINT UNSIGNED NOT NULL,
  codigo VARCHAR(20) NOT NULL,
  nombre VARCHAR(200) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_redes_disa_codigo UNIQUE (id_disa, codigo),
  CONSTRAINT fk_redes_disa
    FOREIGN KEY (id_disa) REFERENCES disa(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS microredes (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_red BIGINT UNSIGNED NOT NULL,
  codigo VARCHAR(20) NOT NULL,
  nombre VARCHAR(200) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_microredes_red_codigo UNIQUE (id_red, codigo),
  CONSTRAINT fk_microredes_red
    FOREIGN KEY (id_red) REFERENCES redes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ubigeos (
  codigo CHAR(6) PRIMARY KEY,
  departamento VARCHAR(100) NOT NULL,
  provincia VARCHAR(100) NOT NULL,
  distrito VARCHAR(100) NOT NULL,
  localidad VARCHAR(150) NULL,
  altitud_msnm DECIMAL(8,2) NULL,
  quintil VARCHAR(50) NULL,
  INDEX idx_ubigeos_distrito (distrito)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS establecimientos (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo_legacy BIGINT UNSIGNED NULL,
  id_microred BIGINT UNSIGNED NULL,
  codigo_renaes VARCHAR(30) NULL,
  codigo_ideess VARCHAR(30) NULL,
  nombre VARCHAR(200) NOT NULL,
  abreviatura VARCHAR(50) NULL,
  ubigeo_codigo CHAR(6) NULL,
  area_urbana VARCHAR(50) NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_establecimientos_legacy UNIQUE (codigo_legacy),
  CONSTRAINT uq_establecimientos_renaes UNIQUE (codigo_renaes),
  CONSTRAINT uq_establecimientos_ideess UNIQUE (codigo_ideess),
  CONSTRAINT fk_establecimientos_microred
    FOREIGN KEY (id_microred) REFERENCES microredes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_establecimientos_ubigeo
    FOREIGN KEY (ubigeo_codigo) REFERENCES ubigeos(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_establecimientos_nombre (nombre)
) ENGINE=InnoDB;

-- Serie bloqueada por sede/año para emitir documentos sin colisiones.
CREATE TABLE IF NOT EXISTS documento_series (
  tipo VARCHAR(30) NOT NULL,
  establecimiento_id BIGINT UNSIGNED NOT NULL,
  periodo VARCHAR(20) NOT NULL,
  siguiente_numero BIGINT UNSIGNED NOT NULL DEFAULT 1,
  PRIMARY KEY (tipo, establecimiento_id, periodo),
  CONSTRAINT fk_documento_series_establecimiento
    FOREIGN KEY (establecimiento_id) REFERENCES establecimientos(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

/* ============================================================
   3. PACIENTES
   ============================================================ */

CREATE TABLE IF NOT EXISTS pacientes (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codclie_legacy BIGINT UNSIGNED NULL,
  historia_clinica VARCHAR(255) NULL,
  historia_familiar TEXT NULL,
  tipo_documento_codigo VARCHAR(10) NOT NULL,
  numero_documento VARCHAR(30) NOT NULL,
  fecha_inscripcion DATE NULL,
  fecha_nacimiento DATE NOT NULL,
  apellido_paterno VARCHAR(100) NULL,
  apellido_materno VARCHAR(100) NULL,
  primer_nombre VARCHAR(100) NULL,
  otros_nombres VARCHAR(150) NULL,
  sexo_codigo CHAR(1) NULL,
  ubigeo_residencia_codigo CHAR(6) NULL,
  localidad VARCHAR(150) NULL,
  direccion VARCHAR(300) NULL,
  establecimiento_registro_id BIGINT UNSIGNED NULL,
  seguro_id BIGINT UNSIGNED NULL,
  telefono_principal VARCHAR(30) NULL,
  condicion VARCHAR(100) NULL,
  estado BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_pacientes_codclie_legacy UNIQUE (codclie_legacy),
  CONSTRAINT uq_pacientes_documento UNIQUE (tipo_documento_codigo, numero_documento),
  CONSTRAINT fk_pacientes_tipo_documento
    FOREIGN KEY (tipo_documento_codigo) REFERENCES tipos_documento(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pacientes_sexo
    FOREIGN KEY (sexo_codigo) REFERENCES sexos(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pacientes_ubigeo
    FOREIGN KEY (ubigeo_residencia_codigo) REFERENCES ubigeos(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pacientes_establecimiento
    FOREIGN KEY (establecimiento_registro_id) REFERENCES establecimientos(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pacientes_seguro
    FOREIGN KEY (seguro_id) REFERENCES seguros(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_pacientes_historia (historia_clinica),
  INDEX idx_pacientes_nombres (apellido_paterno, apellido_materno, primer_nombre)
) ENGINE=InnoDB;

/* Un paciente puede tener más de un riesgo activo durante su vida clínica. */
CREATE TABLE IF NOT EXISTS grupos_riesgo (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(30) NOT NULL,
  nombre VARCHAR(150) NOT NULL,
  descripcion VARCHAR(500) NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_grupos_riesgo_codigo UNIQUE (codigo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS paciente_grupos_riesgo (
  paciente_id BIGINT UNSIGNED NOT NULL,
  grupo_riesgo_id BIGINT UNSIGNED NOT NULL,
  fecha_inicio DATE NOT NULL,
  fecha_fin DATE NULL,
  observacion VARCHAR(500) NULL,
  PRIMARY KEY (paciente_id, grupo_riesgo_id, fecha_inicio),
  CONSTRAINT fk_paciente_grupo_riesgo_paciente
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_paciente_grupo_riesgo_grupo
    FOREIGN KEY (grupo_riesgo_id) REFERENCES grupos_riesgo(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_paciente_grupos_riesgo_activos (paciente_id, fecha_fin)
) ENGINE=InnoDB;

/* Madre, padre, tutor u otro responsable, especialmente importante en menores. */
CREATE TABLE IF NOT EXISTS paciente_responsables (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  paciente_id BIGINT UNSIGNED NOT NULL,
  parentesco VARCHAR(30) NOT NULL,
  nombre_completo VARCHAR(200) NOT NULL,
  tipo_documento_codigo VARCHAR(10) NULL,
  numero_documento VARCHAR(30) NULL,
  telefono VARCHAR(30) NULL,
  es_principal BOOLEAN NOT NULL DEFAULT FALSE,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT fk_paciente_responsables_paciente
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_paciente_responsables_tipo_documento
    FOREIGN KEY (tipo_documento_codigo) REFERENCES tipos_documento(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_paciente_responsables_paciente (paciente_id, activo)
) ENGINE=InnoDB;

/* Códigos externos de Access: AREQUIPA_040, AREQUIPA_2, AREQUIPA_SIS, etc. */
CREATE TABLE IF NOT EXISTS paciente_codigos_externos (
  paciente_id BIGINT UNSIGNED NOT NULL,
  sistema VARCHAR(40) NOT NULL,
  valor VARCHAR(255) NOT NULL,
  PRIMARY KEY (paciente_id, sistema),
  CONSTRAINT fk_paciente_codigos_paciente
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

/*
  Tabla de compatibilidad durante la migración. valor_texto permite diferenciar
  NULL de ''. Anexo7 del origen se importa como tipo_origen = 'BOOLEANO'.
*/
CREATE TABLE IF NOT EXISTS paciente_anexos_legacy (
  paciente_id BIGINT UNSIGNED NOT NULL,
  numero_anexo TINYINT UNSIGNED NOT NULL,
  tipo_origen VARCHAR(20) NOT NULL DEFAULT 'TEXTO',
  valor_texto VARCHAR(255) NULL,
  valor_booleano BOOLEAN NULL,
  PRIMARY KEY (paciente_id, numero_anexo),
  CONSTRAINT fk_anexos_legacy_paciente
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

/* ============================================================
   4. PROFESIONALES, USUARIOS Y AUDITORÍA
   ============================================================ */

CREATE TABLE IF NOT EXISTS profesionales (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo_legacy BIGINT UNSIGNED NULL,
  numero_documento VARCHAR(30) NULL,
  nombre_completo VARCHAR(200) NOT NULL,
  profesion_id BIGINT UNSIGNED NULL,
  colegiatura VARCHAR(50) NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_profesionales_legacy UNIQUE (codigo_legacy),
  CONSTRAINT uq_profesionales_documento UNIQUE (numero_documento),
  CONSTRAINT fk_profesionales_profesion
    FOREIGN KEY (profesion_id) REFERENCES profesiones(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS profesional_especialidades (
  profesional_id BIGINT UNSIGNED NOT NULL,
  especialidad_codigo VARCHAR(20) NOT NULL,
  es_principal BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (profesional_id, especialidad_codigo),
  CONSTRAINT fk_profesional_especialidades_profesional
    FOREIGN KEY (profesional_id) REFERENCES profesionales(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_profesional_especialidades_especialidad
    FOREIGN KEY (especialidad_codigo) REFERENCES especialidades(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

/*
  Un consultorio puede tener subconsultorios. Ejemplo:
  MEDICINA -> MEDICINA GENERAL.
*/
CREATE TABLE IF NOT EXISTS consultorios (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  establecimiento_id BIGINT UNSIGNED NOT NULL,
  consultorio_padre_id BIGINT UNSIGNED NULL,
  codigo VARCHAR(30) NOT NULL,
  nombre VARCHAR(150) NOT NULL,
  especialidad_codigo VARCHAR(20) NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_consultorios_establecimiento_codigo UNIQUE (establecimiento_id, codigo),
  CONSTRAINT fk_consultorios_establecimiento
    FOREIGN KEY (establecimiento_id) REFERENCES establecimientos(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_consultorios_padre
    FOREIGN KEY (consultorio_padre_id) REFERENCES consultorios(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_consultorios_especialidad
    FOREIGN KEY (especialidad_codigo) REFERENCES especialidades(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_consultorios_padre (consultorio_padre_id)
) ENGINE=InnoDB;

/* Historial de responsables y profesionales asignados a cada (sub)consultorio. */
CREATE TABLE IF NOT EXISTS consultorio_profesionales (
  consultorio_id BIGINT UNSIGNED NOT NULL,
  profesional_id BIGINT UNSIGNED NOT NULL,
  fecha_inicio DATE NOT NULL,
  fecha_fin DATE NULL,
  es_responsable BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (consultorio_id, profesional_id, fecha_inicio),
  CONSTRAINT fk_consultorio_profesionales_consultorio
    FOREIGN KEY (consultorio_id) REFERENCES consultorios(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_consultorio_profesionales_profesional
    FOREIGN KEY (profesional_id) REFERENCES profesionales(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_consultorio_profesionales_vigencia (consultorio_id, fecha_inicio, fecha_fin)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS roles (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(50) NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  CONSTRAINT uq_roles_codigo UNIQUE (codigo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS usuarios (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  profesional_id BIGINT UNSIGNED NULL,
  nombre_usuario VARCHAR(100) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  ultimo_acceso_at DATETIME NULL,
  intentos_fallidos_inicio_sesion SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  bloqueado_inicio_sesion_hasta DATETIME NULL,
  ultimo_intento_fallido_inicio_sesion_at DATETIME NULL,
  version_credenciales INT UNSIGNED NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_usuarios_nombre_usuario UNIQUE (nombre_usuario),
  CONSTRAINT uq_usuarios_profesional UNIQUE (profesional_id),
  CONSTRAINT fk_usuarios_profesional
    FOREIGN KEY (profesional_id) REFERENCES profesionales(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Limitación persistente por huella HMAC de usuario/origen; no guarda IP ni contraseña.
CREATE TABLE IF NOT EXISTS limites_inicio_sesion (
  clave_hash VARCHAR(64) PRIMARY KEY,
  ventana_inicio_at DATETIME NOT NULL,
  intentos SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  bloqueado_hasta DATETIME NULL,
  INDEX idx_limites_inicio_sesion_bloqueado_hasta (bloqueado_hasta)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS usuario_roles (
  usuario_id BIGINT UNSIGNED NOT NULL,
  rol_id BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (usuario_id, rol_id),
  CONSTRAINT fk_usuario_roles_usuario
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_usuario_roles_rol
    FOREIGN KEY (rol_id) REFERENCES roles(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

/* ============================================================
   5. ATENCIONES CLÍNICAS
   ============================================================ */

CREATE TABLE IF NOT EXISTS atenciones (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo_legacy BIGINT UNSIGNED NULL,
  paciente_id BIGINT UNSIGNED NOT NULL,
  establecimiento_id BIGINT UNSIGNED NOT NULL,
  profesional_id BIGINT UNSIGNED NOT NULL,
  especialidad_codigo VARCHAR(20) NULL,
  consultorio_id BIGINT UNSIGNED NOT NULL,
  modalidad_atencion_codigo VARCHAR(20) NOT NULL,
  grupo_etario_codigo VARCHAR(20) NOT NULL,
  fecha_atencion DATETIME NOT NULL,
  fecha_atendido DATETIME NULL,
  historia_clinica_snapshot VARCHAR(255) NULL,
  edad_anios SMALLINT UNSIGNED NULL,
  peso_kg DECIMAL(6,2) NULL,
  talla_cm DECIMAL(6,2) NULL,
  perimetro_abdominal_cm DECIMAL(6,2) NULL,
  presion_sistolica SMALLINT UNSIGNED NULL,
  presion_diastolica SMALLINT UNSIGNED NULL,
  temperatura_c DECIMAL(4,1) NULL,
  pe VARCHAR(50) NULL,
  te VARCHAR(50) NULL,
  pt VARCHAR(50) NULL,
  hora_inicio TIME NULL,
  hora_fin TIME NULL,
  admision VARCHAR(100) NULL,
  observaciones TEXT NULL,
  estado VARCHAR(30) NOT NULL DEFAULT 'ATENDIDO',
  created_by_usuario_id BIGINT UNSIGNED NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_atenciones_codigo_legacy UNIQUE (codigo_legacy),
  CONSTRAINT uq_atenciones_id_profesional UNIQUE (id, profesional_id),
  CONSTRAINT ck_atenciones_estado_valido CHECK (estado IN ('ATENDIDO', 'ANULADO')),
  CONSTRAINT fk_atenciones_paciente
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_atenciones_establecimiento
    FOREIGN KEY (establecimiento_id) REFERENCES establecimientos(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_atenciones_profesional
    FOREIGN KEY (profesional_id) REFERENCES profesionales(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_atenciones_especialidad
    FOREIGN KEY (especialidad_codigo) REFERENCES especialidades(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_atenciones_consultorio
    FOREIGN KEY (consultorio_id) REFERENCES consultorios(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_atenciones_modalidad
    FOREIGN KEY (modalidad_atencion_codigo) REFERENCES modalidades_atencion(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_atenciones_grupo_etario
    FOREIGN KEY (grupo_etario_codigo) REFERENCES grupos_etarios(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_atenciones_creado_por
    FOREIGN KEY (created_by_usuario_id) REFERENCES usuarios(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_atenciones_paciente_fecha (paciente_id, fecha_atencion),
  INDEX idx_atenciones_establecimiento_fecha (establecimiento_id, fecha_atencion),
  INDEX idx_atenciones_profesional_fecha (profesional_id, fecha_atencion)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS atencion_prestaciones (
  atencion_id BIGINT UNSIGNED NOT NULL,
  numero_orden SMALLINT UNSIGNED NOT NULL,
  prestacion_codigo VARCHAR(30) NOT NULL,
  cantidad DECIMAL(8,2) NOT NULL DEFAULT 1,
  PRIMARY KEY (atencion_id, numero_orden),
  CONSTRAINT fk_atencion_prestaciones_atencion
    FOREIGN KEY (atencion_id) REFERENCES atenciones(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_atencion_prestaciones_prestacion
    FOREIGN KEY (prestacion_codigo) REFERENCES prestaciones(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_atencion_prestaciones_codigo (prestacion_codigo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS atencion_diagnosticos (
  atencion_id BIGINT UNSIGNED NOT NULL,
  numero_orden SMALLINT UNSIGNED NOT NULL,
  cie10_codigo VARCHAR(20) NOT NULL,
  tipo_diagnostico VARCHAR(50) NULL,
  observacion VARCHAR(500) NULL,
  PRIMARY KEY (atencion_id, numero_orden),
  CONSTRAINT fk_atencion_diagnosticos_atencion
    FOREIGN KEY (atencion_id) REFERENCES atenciones(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_atencion_diagnosticos_cie10
    FOREIGN KEY (cie10_codigo) REFERENCES cie10(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_atencion_diagnosticos_cie10 (cie10_codigo)
) ENGINE=InnoDB;

/* ============================================================
   6. DOCUMENTOS CLÍNICOS: FUA, CERTIFICADOS Y REFERENCIAS
   ============================================================ */

CREATE TABLE IF NOT EXISTS referencias (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  atencion_id BIGINT UNSIGNED NOT NULL,
  numero_referencia VARCHAR(100) NULL,
  tipo VARCHAR(30) NOT NULL,
  establecimiento_origen_id BIGINT UNSIGNED NOT NULL,
  establecimiento_destino_id BIGINT UNSIGNED NOT NULL,
  fecha_emision DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  motivo TEXT NULL,
  observaciones TEXT NULL,
  estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
  CONSTRAINT uq_referencias_numero UNIQUE (numero_referencia),
  CONSTRAINT fk_referencias_atencion
    FOREIGN KEY (atencion_id) REFERENCES atenciones(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_referencias_origen
    FOREIGN KEY (establecimiento_origen_id) REFERENCES establecimientos(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_referencias_destino
    FOREIGN KEY (establecimiento_destino_id) REFERENCES establecimientos(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT ck_referencias_estado_valido CHECK (
    estado IN ('PENDIENTE', 'ACEPTADA', 'ATENDIDA', 'CONTRARREFERIDA', 'CERRADA', 'ANULADA')
  ),
  INDEX idx_referencias_atencion (atencion_id),
  INDEX idx_referencias_destino_estado (establecimiento_destino_id, estado)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS fua (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  atencion_id BIGINT UNSIGNED NOT NULL,
  numero_fua VARCHAR(100) NULL,
  codigo_ciudad VARCHAR(50) NULL,
  codigo_anio VARCHAR(20) NULL,
  codigo_eess VARCHAR(50) NULL,
  edad_declarada VARCHAR(20) NULL,
  fecha_emision DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  estado VARCHAR(30) NOT NULL DEFAULT 'EMITIDO',
  observaciones TEXT NULL,
  CONSTRAINT uq_fua_atencion UNIQUE (atencion_id),
  CONSTRAINT uq_fua_numero UNIQUE (numero_fua),
  CONSTRAINT fk_fua_atencion
    FOREIGN KEY (atencion_id) REFERENCES atenciones(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT ck_fua_estado_valido CHECK (estado IN ('EMITIDO', 'ANULADO')),
  INDEX idx_fua_fecha_emision (fecha_emision)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS certificados (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  atencion_id BIGINT UNSIGNED NOT NULL,
  establecimiento_id BIGINT UNSIGNED NOT NULL,
  profesional_id BIGINT UNSIGNED NOT NULL,
  numero_certificado VARCHAR(100) NOT NULL,
  tipo VARCHAR(100) NOT NULL,
  fecha_emision DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  consultorio VARCHAR(100) NULL,
  admision VARCHAR(100) NULL,
  estado VARCHAR(30) NOT NULL DEFAULT 'EMITIDO',
  CONSTRAINT uq_certificados_eess_numero UNIQUE (establecimiento_id, numero_certificado),
  CONSTRAINT fk_certificados_atencion_profesional
    FOREIGN KEY (atencion_id, profesional_id)
    REFERENCES atenciones(id, profesional_id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_certificados_establecimiento
    FOREIGN KEY (establecimiento_id) REFERENCES establecimientos(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_certificados_profesional
    FOREIGN KEY (profesional_id) REFERENCES profesionales(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT ck_certificados_estado_valido CHECK (estado IN ('EMITIDO', 'ANULADO')),
  INDEX idx_certificados_atencion (atencion_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS certificado_prestaciones (
  certificado_id BIGINT UNSIGNED NOT NULL,
  numero_orden SMALLINT UNSIGNED NOT NULL,
  prestacion_codigo VARCHAR(30) NOT NULL,
  PRIMARY KEY (certificado_id, numero_orden),
  CONSTRAINT fk_certificado_prestaciones_certificado
    FOREIGN KEY (certificado_id) REFERENCES certificados(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_certificado_prestaciones_prestacion
    FOREIGN KEY (prestacion_codigo) REFERENCES prestaciones(codigo)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

/* ============================================================
   7. MÓDULOS DE VIGILANCIA Y NUTRICIÓN
   ============================================================ */

CREATE TABLE IF NOT EXISTS vigilancia_sien (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  paciente_id BIGINT UNSIGNED NOT NULL,
  atencion_id BIGINT UNSIGNED NULL,
  establecimiento_id BIGINT UNSIGNED NOT NULL,
  fecha DATETIME NOT NULL,
  peso_kg DECIMAL(6,2) NULL,
  talla_cm DECIMAL(6,2) NULL,
  hemoglobina DECIMAL(5,2) NULL,
  fecha_hemoglobina DATE NULL,
  enviado BOOLEAN NOT NULL DEFAULT FALSE,
  estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
  CONSTRAINT fk_sien_paciente
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_sien_atencion
    FOREIGN KEY (atencion_id) REFERENCES atenciones(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_sien_establecimiento
    FOREIGN KEY (establecimiento_id) REFERENCES establecimientos(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_sien_paciente_fecha (paciente_id, fecha)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS evaluaciones_nutricionales (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  paciente_id BIGINT UNSIGNED NOT NULL,
  atencion_id BIGINT UNSIGNED NULL,
  establecimiento_id BIGINT UNSIGNED NOT NULL,
  tipo VARCHAR(20) NOT NULL,
  fecha DATETIME NOT NULL,
  peso_kg DECIMAL(6,2) NULL,
  talla_cm DECIMAL(6,2) NULL,
  hemoglobina DECIMAL(5,2) NULL,
  fecha_hemoglobina DATE NULL,
  edad_anios SMALLINT UNSIGNED NULL,
  edad_meses TINYINT UNSIGNED NULL,
  edad_dias TINYINT UNSIGNED NULL,
  edad_gestacional_semanas SMALLINT UNSIGNED NULL,
  perimetro_abdominal_cm DECIMAL(6,2) NULL,
  imc DECIMAL(6,3) NULL,
  whz DECIMAL(6,3) NULL,
  haz DECIMAL(6,3) NULL,
  waz DECIMAL(6,3) NULL,
  diagnostico_peso_edad VARCHAR(100) NULL,
  diagnostico_talla_edad VARCHAR(100) NULL,
  diagnostico_peso_talla VARCHAR(100) NULL,
  diagnostico VARCHAR(500) NULL,
  enviado BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_nutricion_paciente
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_nutricion_atencion
    FOREIGN KEY (atencion_id) REFERENCES atenciones(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_nutricion_establecimiento
    FOREIGN KEY (establecimiento_id) REFERENCES establecimientos(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_nutricion_paciente_fecha (paciente_id, fecha),
  INDEX idx_nutricion_tipo_fecha (tipo, fecha)
) ENGINE=InnoDB;

/* ============================================================
   8. AUDITORÍA
   ============================================================ */

CREATE TABLE IF NOT EXISTS auditoria (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id BIGINT UNSIGNED NULL,
  tabla_nombre VARCHAR(100) NOT NULL,
  registro_id BIGINT UNSIGNED NULL,
  accion VARCHAR(20) NOT NULL,
  fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  datos_anteriores JSON NULL,
  datos_nuevos JSON NULL,
  CONSTRAINT fk_auditoria_usuario
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_auditoria_tabla_registro (tabla_nombre, registro_id),
  INDEX idx_auditoria_fecha (fecha)
) ENGINE=InnoDB;

/* ============================================================
   9. CATÁLOGOS INICIALES
   ============================================================ */

INSERT IGNORE INTO tipos_documento (codigo, nombre) VALUES
  ('DNI', 'Documento Nacional de Identidad'),
  ('CE', 'Carné de Extranjería'),
  ('PAS', 'Pasaporte'),
  ('DE', 'Documento de Extranjero'),
  ('OTRO', 'Otro documento');

INSERT IGNORE INTO sexos (codigo, nombre) VALUES
  ('F', 'FEMENINO'),
  ('M', 'MASCULINO'),
  ('I', 'INTERSEXUAL');

INSERT IGNORE INTO seguros (codigo, nombre) VALUES
  ('SIN_SEGURO', 'SIN SEGURO'),
  ('SIS', 'SIS'),
  ('ESSALUD', 'EsSalud'),
  ('PARTICULAR', 'Particular'),
  ('OTRO', 'Otro');

INSERT IGNORE INTO modalidades_atencion (codigo, nombre) VALUES
  ('AMBULATORIA', 'Ambulatoria'),
  ('EMERGENCIA', 'Emergencia');

/* Rangos base en meses completos; ADMIN puede reemplazarlos bajo validación. */
INSERT IGNORE INTO grupos_etarios
  (codigo, nombre, edad_minima_meses, edad_maxima_meses)
VALUES
  ('NINO', 'Niño', 0, 143),
  ('ADOLESCENTE', 'Adolescente', 144, 215),
  ('ADULTO', 'Adulto', 216, 719),
  ('ADULTO_MAYOR', 'Adulto mayor', 720, NULL);

INSERT IGNORE INTO roles (codigo, nombre) VALUES
  ('ADMIN', 'Administrador'),
  ('PROFESIONAL', 'Profesional de salud');

/*
  Antes de importar Data_base.mdb:
  1. Inserta los catálogos geográficos y establecimientos.
  2. Carga pacientes respetando codclie_legacy.
  3. Para el paciente Codclie = 2, inserta Anexo1='00', Anexo4='1',
     Anexo7=false, Anexo10='' y Anexo17...25=NULL en paciente_anexos_legacy.
  4. Valida conteos, documentos duplicados, fechas y relaciones huérfanas
     antes de cargar atenciones, FUA y certificados.
*/
