/*
  Prueba funcional reversible para schema_mysql_salud.sql.
  Requiere MySQL 8.0+ y que schema_mysql_salud.sql ya haya sido ejecutado.

  Crea un escenario de prueba, consulta las vistas, realiza actualizaciones y
  una baja lógica. Finaliza con ROLLBACK, por lo que no deja datos de prueba.
*/

USE sistema_salud_ipress;

START TRANSACTION;

/*
  Solo para esta prueba. Los rangos definitivos deben ser confirmados y
  configurados por la IPRESS antes de usar el sistema en producción.
*/
UPDATE grupos_etarios
   SET edad_minima_meses = CASE codigo
       WHEN 'NINO' THEN 0
       WHEN 'ADOLESCENTE' THEN 144
       WHEN 'ADULTO' THEN 216
       WHEN 'ADULTO_MAYOR' THEN 720
     END,
       edad_maxima_meses = CASE codigo
       WHEN 'NINO' THEN 143
       WHEN 'ADOLESCENTE' THEN 215
       WHEN 'ADULTO' THEN 719
       WHEN 'ADULTO_MAYOR' THEN NULL
     END
 WHERE codigo IN ('NINO', 'ADOLESCENTE', 'ADULTO', 'ADULTO_MAYOR');

/* Catálogos geográficos y establecimiento de prueba. */
INSERT INTO disa (codigo, nombre) VALUES ('TEST-DISA', 'DISA de prueba');
SET @disa_id = LAST_INSERT_ID();

INSERT INTO redes (id_disa, codigo, nombre)
VALUES (@disa_id, 'TEST-RED', 'Red de prueba');
SET @red_id = LAST_INSERT_ID();

INSERT INTO microredes (id_red, codigo, nombre)
VALUES (@red_id, 'TEST-MICRO', 'Microred de prueba');
SET @microred_id = LAST_INSERT_ID();

INSERT INTO ubigeos (codigo, departamento, provincia, distrito, localidad)
VALUES ('999999', 'Departamento de prueba', 'Provincia de prueba',
        'Distrito de prueba', 'Localidad de prueba');

INSERT INTO establecimientos
  (codigo_legacy, id_microred, codigo_renaes, codigo_ideess, nombre, ubigeo_codigo)
VALUES
  (999999, @microred_id, 'REN-TEST-001', 'IDEESS-TEST-001',
   'Centro de Salud de Prueba', '999999');
SET @establecimiento_id = LAST_INSERT_ID();

/* Profesional y estructura Medicina -> Medicina General. */
INSERT INTO profesiones (nombre) VALUES ('Medico de prueba');
SET @profesion_id = LAST_INSERT_ID();

INSERT INTO especialidades (codigo, nombre, grupo)
VALUES ('MEDGEN_TEST', 'Medicina General de prueba', 'Medicina');

INSERT INTO profesionales
  (codigo_legacy, numero_documento, nombre_completo, profesion_id, colegiatura)
VALUES
  (999999, '99999999', 'DRA. PROFESIONAL DE PRUEBA', @profesion_id, 'CMP-TEST');
SET @profesional_id = LAST_INSERT_ID();

INSERT INTO consultorios
  (establecimiento_id, codigo, nombre)
VALUES
  (@establecimiento_id, 'MEDICINA', 'Medicina');
SET @consultorio_medicina_id = LAST_INSERT_ID();

INSERT INTO consultorios
  (establecimiento_id, consultorio_padre_id, codigo, nombre, especialidad_codigo)
VALUES
  (@establecimiento_id, @consultorio_medicina_id, 'MEDGEN',
   'Medicina General', 'MEDGEN_TEST');
SET @consultorio_medgen_id = LAST_INSERT_ID();

INSERT INTO consultorio_profesionales
  (consultorio_id, profesional_id, fecha_inicio, es_responsable)
VALUES
  (@consultorio_medgen_id, @profesional_id, '2020-01-01', TRUE);

/* Catálogos clínicos mínimos para la atención de prueba. */
INSERT INTO prestaciones (codigo, descripcion, grupo)
VALUES ('CONS-TEST', 'Consulta de prueba', 'Consulta');

INSERT INTO cie10 (codigo, descripcion, categoria)
VALUES ('Z00-TEST', 'Examen general de prueba', 'Pruebas');

SELECT id INTO @seguro_sin_seguro
  FROM seguros
 WHERE codigo = 'SIN_SEGURO';

/* CREATE: paciente adulto, su atención, valoración, FUA y certificado. */
INSERT INTO pacientes
  (codclie_legacy, historia_clinica, historia_familiar,
   tipo_documento_codigo, numero_documento, fecha_inscripcion,
   fecha_nacimiento, apellido_paterno, apellido_materno,
   primer_nombre, otros_nombres, sexo_codigo, ubigeo_residencia_codigo,
   localidad, direccion, establecimiento_registro_id, seguro_id,
   telefono_principal)
VALUES
  (999000001, 'HC-PRUEBA-001', 'Sin antecedentes registrados',
   'DNI', '99900001', '2026-09-09', '2000-01-01', 'PACIENTE', 'PRUEBA',
   'ANA', 'MARIA', 'F', '999999', 'Localidad de prueba',
   'Direccion de prueba 123', @establecimiento_id, @seguro_sin_seguro,
   '999-999-999');
SET @paciente_id = LAST_INSERT_ID();

INSERT INTO grupos_riesgo (codigo, nombre)
VALUES ('RIESGO-TEST', 'Riesgo de prueba');
SET @grupo_riesgo_id = LAST_INSERT_ID();

INSERT INTO paciente_grupos_riesgo
  (paciente_id, grupo_riesgo_id, fecha_inicio, observacion)
VALUES
  (@paciente_id, @grupo_riesgo_id, '2026-09-09', 'Registro de prueba');

INSERT INTO atenciones
  (paciente_id, establecimiento_id, profesional_id, especialidad_codigo,
   consultorio_id, modalidad_atencion_codigo, grupo_etario_codigo,
   fecha_atencion, historia_clinica_snapshot, peso_kg, talla_cm,
   perimetro_abdominal_cm, presion_sistolica, presion_diastolica,
   temperatura_c, observaciones)
VALUES
  (@paciente_id, @establecimiento_id, @profesional_id, 'MEDGEN_TEST',
   @consultorio_medgen_id, 'AMBULATORIA', 'ADULTO',
   '2026-09-09 10:30:00', 'HC-PRUEBA-001', 60.50, 165.00,
   75.00, 120, 80, 36.5, 'Atencion de prueba');
SET @atencion_id = LAST_INSERT_ID();

INSERT INTO atencion_prestaciones
  (atencion_id, numero_orden, prestacion_codigo)
VALUES (@atencion_id, 1, 'CONS-TEST');

INSERT INTO atencion_diagnosticos
  (atencion_id, numero_orden, cie10_codigo, tipo_diagnostico)
VALUES (@atencion_id, 1, 'Z00-TEST', 'PRESUNTIVO');

INSERT INTO evaluaciones_nutricionales
  (paciente_id, atencion_id, establecimiento_id, tipo, fecha,
   peso_kg, talla_cm, perimetro_abdominal_cm, edad_anios, edad_meses,
   edad_dias, diagnostico_peso_edad, diagnostico_talla_edad,
   diagnostico_peso_talla)
VALUES
  (@paciente_id, @atencion_id, @establecimiento_id, 'ADULTO',
   '2026-09-09 10:30:00', 60.50, 165.00, 75.00, 26, 8, 8,
   NULL, NULL, NULL);

INSERT INTO fua
  (atencion_id, numero_fua, codigo_ciudad, codigo_anio, codigo_eess,
   edad_declarada, estado)
VALUES
  (@atencion_id, 'FUA-TEST-0001', '999', '2026', 'IDEESS-TEST-001',
   '26 anios, 8 meses, 8 dias', 'EMITIDO');

INSERT INTO certificados
  (atencion_id, establecimiento_id, profesional_id, numero_certificado,
   tipo, consultorio, estado)
VALUES
  (@atencion_id, @establecimiento_id, @profesional_id,
   'CERT-TEST-0001', 'Certificado de atencion', 'Medicina General', 'EMITIDO');
SET @certificado_id = LAST_INSERT_ID();

INSERT INTO certificado_prestaciones
  (certificado_id, numero_orden, prestacion_codigo)
VALUES (@certificado_id, 1, 'CONS-TEST');

/* READ: consultas de referencia. En producción estas uniones las hace el backend. */
SELECT
  p.id, p.codclie_legacy, p.historia_clinica, p.numero_documento,
  p.apellido_paterno, p.apellido_materno, p.primer_nombre, p.otros_nombres,
  e.nombre AS establecimiento, s.nombre AS seguro
FROM pacientes p
JOIN establecimientos e ON e.id = p.establecimiento_registro_id
LEFT JOIN seguros s ON s.id = p.seguro_id
WHERE p.id = @paciente_id;

SELECT
  a.id AS atencion_id, a.fecha_atencion, f.numero_fua,
  p.codclie_legacy, p.numero_documento, c.nombre AS consultorio,
  pr.nombre_completo AS profesional
FROM atenciones a
JOIN pacientes p ON p.id = a.paciente_id
JOIN fua f ON f.atencion_id = a.id
JOIN consultorios c ON c.id = a.consultorio_id
JOIN profesionales pr ON pr.id = a.profesional_id
WHERE a.id = @atencion_id;

SELECT
  cert.id AS certificado_id, cert.numero_certificado, cert.tipo,
  cert.fecha_emision, a.id AS atencion_id, p.codclie_legacy
FROM certificados cert
JOIN atenciones a ON a.id = cert.atencion_id
JOIN pacientes p ON p.id = a.paciente_id
WHERE cert.id = @certificado_id;

/* UPDATE: corrección de datos sin duplicar la historia clínica. */
UPDATE pacientes
   SET telefono_principal = '999-999-998'
 WHERE id = @paciente_id;

UPDATE atenciones
   SET observaciones = 'Atencion de prueba actualizada'
 WHERE id = @atencion_id;

/* DELETE lógico: los datos clínicos no se eliminan físicamente. */
UPDATE pacientes
   SET estado = FALSE
 WHERE id = @paciente_id;

SELECT id, estado, telefono_principal
  FROM pacientes
 WHERE id = @paciente_id;

/* Las reglas de rechazo se prueban en el backend; ver README.md. */

ROLLBACK;
