# Revisión funcional de pacientes y admisión

Pruebas realizadas el 30 de septiembre y el 1 de octubre de 2026.

## Resultado

El recorrido de guardado funciona para modalidad, grupo de atención, tipo/número
de documento y seguro. No se observó pérdida de los valores seleccionados en los
casos ejecutados. Hay defectos de validación, de registro de responsables y de
coherencia entre seguro y afiliación que conviene resolver antes de dar el flujo
por cerrado.

Esta revisión no modificó código de producción. Los archivos nuevos son utilidades
de prueba, evidencias y este informe. Se conservaron las modificaciones previas
del proyecto y las de otros trabajos.

## Entorno y alcance real

- Base exclusiva: `ipress_test_admission_20260930_a1`, creada vacía y migrada hasta
  `20260929_0023_nutrition_risks`. No se copiaron ni modificaron pacientes reales.
- API real en `127.0.0.1:8001`; Vue real en `127.0.0.1:5174`, con proxy hacia esa API.
  No se usaron respuestas simuladas para los recorridos de navegador ni HTTP.
- Cuenta PROFESIONAL y establecimiento/consultorio ficticios. Inicio de sesión normal.
- 16 pacientes ficticios persistidos, incluyendo casos deliberadamente inválidos
  aceptados por el sistema; 14 atenciones de prueba. Permanecen en la base aislada.
- Los servidores temporales se detuvieron al terminar; la aplicación habitual
  de los puertos 5173/8000 no se modificó ni se reinició.
- Cobertura combinada: navegador → API → MySQL, pruebas HTTP de catálogo completo,
  consultas posteriores independientes y revisión del código. No todos los cruces
  documento × seguro × edad se repitieron en navegador.
- No se enviaron datos a SIS/RENIEC/aseguradoras ni se verificó elegibilidad real,
  validez oficial de documentos o impresión física. FUA aquí es la copia local.

## Lo comprobado

| Área | Prueba | Resultado |
|---|---|---|
| Modalidad | AMBULATORIA y EMERGENCIA × los 3 grupos, HTTP + GET + SQL | Se conservan los 6 cruces |
| Grupos | General, GESTANTES y PUERPERAS | Se guarda un único grupo por atención; son radios, no 3 casillas independientes |
| Niño | Alta en navegador, CE, SIS Gratuito, madre responsable; atención ambulatoria | Paciente 15 y atención 11; grupo etario calculado NINO |
| Adulto mayor | Alta en navegador, PAS, EsSalud; emergencia | Paciente 16 y atención 12; ADULTO_MAYOR |
| Gestantes | Paciente ficticia adulta, admisión en navegador | Atención 13: AMBULATORIA/GESTANTES, UNICO, peso previo 55.00, FPP 2027-03-01 |
| Puérperas | Cambiar desde Gestantes con campos llenos y guardar por navegador | Atención 14: EMERGENCIA/PUERPERAS; tipo, peso previo y FPP quedan nulos |
| Documentos | Altas y cambios CE, DE, DNI, OTRO y PAS por API | Tipo/número guardados y recuperados; 30 caracteres aceptados, 31 rechazados |
| Cambio desde admisión | DNI → PAS → DNI → DE por navegador | PATCH persiste; pendiente validación del número según tipo |
| Seguros | Altas y actualizaciones de las 11 opciones | Cada actualización verificada mediante GET y MySQL independiente |
| Edición pendiente | Cambiar documento sin guardar paciente | Impide guardar atención; se habilita tras guardar cambios |
| Integridad | Documento duplicado, catálogo inexistente, menor sin responsable, SIS incompleto, modalidad/grupo inválidos | API rechaza correctamente |
| FUA histórica | Cambiar documento del paciente después de atención 1 | La copia de atención 1 conserva DNI/82000002; no se reescribe con DE/DEUI000033 |

Los seguros probados: ESSALUD, OTRO, PARTICULAR, SIS_AFILIACION_TEMPORAL,
SIS_GRATUITO, SIS_NRUS, SIS_SEMI_SUBSIDIADO, SIS_PARA_TODOS, SANIDAD, SIN_SEGURO y SIS.

## Ajustes pendientes, por prioridad

### 1. Alta con Tutor sin formulario utilizable — alta

En `/pacientes/nuevo` se puede seleccionar Tutor, pero solamente hay campos para
padre y madre. Seleccionarlo crea un responsable con nombre vacío, sin una entrada
visible donde completarlo. Guardar muestra el mensaje genérico de datos inválidos.
Se reprodujo antes del alta del paciente 15; al cambiar a Madre y completar nombre
y documento, el alta funcionó.

Además, los documentos de padre/madre se envían siempre como DNI. No puede
identificarse correctamente a un responsable con CE/PAS/DE desde este formulario.
La API sí soporta tipo de documento para responsables.

Ajuste: formulario para Tutor y selector de documento para cada responsable,
con validación visible por campo. Revisar también el cambio de parentesco para
no trasladar inadvertidamente el nombre de una persona a otra.

Fuente: `frontend/src/components/patients/PatientRegistrationFamilySections.vue`,
líneas 27–48, 64–84 y 145–196.

### 2. No hay reglas de número por tipo de documento — alta

El contrato actual es texto de 1 a 30 caracteres para todos los tipos.
Se registró `DNI / A` mediante API. Por navegador se guardó un pasaporte y luego
se cambió solamente el tipo a DNI: quedó `DNI / PASUI000033`, sin advertencia.
No es un fallo de persistencia: falta la validación específica.

El alta tampoco aplica el límite de 30 en el input ni en sus reglas; el rechazo
de 31 caracteres llega desde el backend como error general. Admisión sí limita
el campo a 30, pero tampoco cambia sus reglas al seleccionar otro tipo.

Ajuste: acordar las reglas permitidas por cada tipo y compartirlas entre alta,
edición y API. Revalidar tipo y número como pareja; no truncar ni borrar datos
históricos automáticamente. Este informe no establece longitudes oficiales
para documentos extranjeros.

Fuentes: `app/schemas/patient.py:21`, `frontend/src/utils/patientDraft.ts:9`,
`frontend/src/views/PacienteNuevoView.vue:85`,
`frontend/src/components/patients/PatientRegistrationBaseSection.vue:87`.

### 3. Seguro y afiliación SIS pueden quedar inconsistentes — alta

Se guardó SIS Gratuito con afiliación y después se seleccionó SIN SEGURO, tanto
por API como por navegador. El seguro cambió correctamente, pero DIRESA/tipo/número
de SIS permanecieron. La nueva atención 13 copió esa afiliación a su FUA aunque el
paciente ya tenía `seguro_id=1` (SIN SEGURO).

Ajuste: definir si se conserva como antecedente o se desactiva, y distinguir la
afiliación vigente de la histórica antes de usarla en una nueva FUA. No conviene
borrar antecedentes silenciosamente. Mostrar claramente qué datos se usarán.

El seguro es hoy un dato del paciente: se guarda mediante PATCH del paciente,
no como un campo del POST de atención. La FUA conserva afiliación, pero no una
copia del código/nombre del plan de seguro. Si se necesita conocer el plan vigente
en cada atención pasada, falta guardar esa copia histórica.

Fuentes: `app/services/patient.py:727`, `app/schemas/patient_sis.py:29`,
`app/services/fua_print.py:21`, `app/models/clinical.py:38`.

### 4. El backend no exige coherencia grupo/datos obstétricos — media

La interfaz limpia correctamente los campos al salir de Gestantes. Sin embargo,
la API aceptó y guardó la atención 9 con grupo GENERAL, tipo UNICO y peso previo
55.00. Otro cliente puede enviar esa combinación y saltarse la limpieza de la UI.

Ajuste: validar en el backend las mismas relaciones entre campos que aplica el
frontend. La obligatoriedad de datos obstétricos y las reglas de compatibilidad
clínica deben acordarse; no se infieren solamente de esta prueba.

Condición del paciente, grupo de atención y grupo etario calculado son conceptos
separados. Elegir Gestantes no actualiza automáticamente Condición. Si se desea
advertir contradicciones, debe definirse explícitamente la regla.

Fuentes: `app/schemas/attention.py:81`, `app/services/attention.py:151`,
`frontend/src/views/AtencionNuevaView.vue:779`.

### 5. Impresión FUA no resuelve todos los documentos — media

CE y DNI tienen equivalencia TDI. PAS, DE y OTRO se guardan en el paciente y en la
copia de atención, pero el formato impreso deja la identificación en blanco y
avisa que no hay equivalencia. Se comprobó el aviso del pasaporte en la FUA de
la emergencia 12. No es pérdida del dato en MySQL, sino una limitación del mapeo.

Ajuste: validar las equivalencias con el formato aplicable antes de ampliarlas;
mantener la advertencia o bloquear el flujo que no esté soportado. No inventar TDI.

Fuentes: `app/services/fua_print.py:46`, `frontend/src/utils/fuaPrint.ts:56,188`.

### 6. Recuperación ante catálogos fallidos — media/baja

Durante la preparación, una petición de catálogo falló y el alta quedó con todos
los selectores vacíos, sin aviso visible ni reintento. La recarga recuperó el
formulario. El origen del fallo de conexión no quedó aislado y no se atribuye al
backend. Sí está confirmado que `onMounted` usa `Promise.all` sin captura y solo
asigna los resultados si todos responden correctamente.

Ajuste: estado de carga/error visible, reintento y evitar que un catálogo opcional
impida cargar documento/sexo/seguro. Fuente: `PacienteNuevoView.vue:218`.

## Evidencias y repetición

- `audit_admission.py`: crea una base NUEVA con prefijo seguro; nunca reinicia ni
  elimina una existente. Ejecuta la API real y la matriz HTTP inicial.
- `ipress_test_admission_20260930_a1_results.json`: 84 comprobaciones iniciales.
  82 pasaron; 2 tenían una expectativa incorrecta del script (404 en vez de 422
  para catálogos inexistentes). Ambos rechazos de aplicación eran correctos.
  Se corrigió la expectativa, no la aplicación; el seguimiento los repitió.
- `verify_admission_audit.py` y `ipress_test_admission_20260930_a1_followup.json`:
  24/24 comprobaciones posteriores correctas, incluyendo esos dos rechazos,
  los 11 seguros, las cuatro atenciones de navegador y la FUA histórica.
- Frontend: 22/22 pruebas de AdmisionView, PacienteNuevoView,
  AdmissionPatientSummary y AdmissionPatientRelations; repetidas el 1 de octubre.
- `npm run type-check`: correcto. Scripts Python: compilación correcta.
- Las observaciones sobre datos inconsistentes se registran aparte: no debe
  interpretarse que las pruebas positivas implican ausencia de esos defectos.

Para volver a abrir el entorno conservado, desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe tests/e2e/audit_admission.py serve ipress_test_admission_20260930_a1
```

En otra terminal, dentro de `frontend`:

```powershell
$env:VITE_API_BASE_URL = '/api/v1'
npm run dev -- --config tests/vite.audit.config.ts
```

Cuenta ficticia local: `auditoria_e2e`, contraseña de fixture `12345678`.
No usar estas credenciales ni esta base en producción. La matriz inicial debe
ejecutarse sobre una nueva base para evitar colisiones con sus datos anteriores.
El verificador de seguimiento está ligado deliberadamente a los IDs de esta
ejecución; no constituye una suite genérica para cualquier base.
