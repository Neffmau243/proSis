# Matriz de guardado — 2026-10-01

Resultado: **550/550 combinaciones aprobadas**, 165 pacientes ficticios en la ejecución completa.
Base aislada: `ipress_test_admission_20261001_fixes`. No se modificaron pacientes reales.

## Cobertura

| Perfil | Documentos | Seguros | Modalidades | Grupos | Atenciones |
| --- | --- | --- | --- | --- | --- |
| Adulta | 5 | 11 | 2 | General, gestantes, puérperas | 330 |
| Niño | 5 | 11 | 2 | General | 110 |
| Adulto mayor | 5 | 11 | 2 | General | 110 |

Documentos: DNI, CE, PAS, DE, OTRO. Modalidades: ambulatoria y emergencia.
Los 11 seguros se obtienen del catálogo real de la base de pruebas; sus valores
y cada combinación están en `full_matrix_results.json`.

Cada paciente se crea y recupera por API, contrastando documento, seguro, fecha
de nacimiento y afiliación con MySQL. Cada atención se crea y recupera por API,
contrastando grupo, modalidad, condición del paciente y snapshot FUA con MySQL.
Se verifican los campos obstétricos de la respuesta, la identificación y afiliación
del snapshot, y la inmutabilidad de todas las FUA creadas para cada paciente.
La secuencia de la adulta incluye volver a general después de puérpera: conserva
la condición, conforme al comportamiento acordado.

Se ejecutaron además **237 pruebas unitarias de backend** y **39 comprobaciones
de puerperio**, incluyendo rechazo de datos gestacionales incompatibles y rollback
ante fallo intencional. Todas aprobadas. El log TEST_ROLLBACK es esperado.

## Alcance y pendientes

- Son pruebas de integración con las rutas FastAPI mediante TestClient y MySQL
  real. No equivalen a recorrer las 550 combinaciones con clics en el navegador.
- Se verifica el guardado, no la validez administrativa de cualquier combinación
  documento/seguro ni una consulta de afiliación a servicios externos.
- PAS, DE y OTRO conservan su identificación en el snapshot, pero siguen sin TDI
  verificado: la impresión continúa bloqueada. Esto no impide guardar la atención.
- CE mantiene la validación genérica de 1–30 caracteres alfanuméricos. La prueba
  utiliza CE numérico de 9 dígitos; no certifica una validación estricta del CE.
- La matriz cruza las opciones enumeradas, no todos los valores posibles de cada
  campo, edades, sexo, cambios entre todos los seguros/documentos ni errores de red.
- Un primer intento se detuvo tras 132 casos aprobados porque el test comparaba
  literalmente las letras del documento en FUA. La FUA normaliza a mayúsculas;
  corregida esa expectativa, la ejecución completa aprobó 550 casos. Los datos
  parciales permanecen exclusivamente en la base de pruebas, sin borrados.

## Repetición

```powershell
.venv/Scripts/python.exe tests/e2e/verify_full_matrix.py ipress_test_admission_20261001_fixes
.venv/Scripts/python.exe tests/e2e/verify_puerpera.py ipress_test_admission_20261001_fixes
.venv/Scripts/python.exe -m pytest tests/unit -o addopts='' -q -p no:cacheprovider
```

La matriz genera identificadores nuevos y no borra registros anteriores.
No se modificó código de producción durante esta revisión.
