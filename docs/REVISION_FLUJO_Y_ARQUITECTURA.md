# Revisión de flujo y arquitectura — 17/09/2026

## Alcance y conclusión

Se contrastaron las rutas SPA, servicios HTTP, permisos, controladores, schemas,
servicios de negocio, repositorios, migraciones y CI; se ejecutaron las pruebas
disponibles y se inspeccionó Admisión en el navegador. La revisión sigue el
flujo transversal de cada módulo; no equivale a una auditoría exhaustiva de
cada rama del código, una prueba de carga ni una certificación de producción.

La base de arquitectura es adecuada: Vue con componentes/composables y
contratos tipados; backend por capas, reglas de dominio, transacciones,
auditoría y migraciones. No se puede afirmar que todo el proyecto ya esté
terminado o validado para escalar. Hay diferencias entre capacidades de API,
funciones visibles y documentación anterior, además de deuda concreta.

## Flujo real contrastado

| Etapa | Frontend | Backend / resultado |
| --- | --- | --- |
| Acceso | Selector público de usuarios activos y clave de 8 dígitos | Login, bcrypt, JWT, limitador persistente, bloqueo y auditoría. |
| Sesión | Pinia, almacenamiento local, guards y cliente Axios | Revalida usuario, roles y versión de credenciales en peticiones protegidas. |
| Buscar paciente | Dashboard con debounce, páginas y carga adicional | GET paginado y filtrado por ámbito profesional; ADMIN puede ver bajas. |
| Registrar paciente | Formulario dividido en datos base y familiares | POST atómico; valida documento, catálogos, fechas y responsable si es menor. |
| Actualizar paciente | Panel en Admisión con borrador y Guardar cambios | PATCH parcial, bloqueo de fila, reglas de negocio, auditoría y commit. |
| Madre/responsables/riesgos | Diálogos reutilizados en ficha y Admisión | POST/PATCH propios; no se reemplazan colecciones con el PATCH maestro. |
| Registrar atención | Contexto, signos y valoración escrita | POST crea un nuevo acto y calcula indicadores/grupo etario; valida autor y asignación. |
| Historial | Lista general paginada y resumen por paciente | Consultas de ámbito clínico; el resumen por paciente aún carga una lista completa. |
| Documentos | Formularios desde detalle | FUA, certificado y referencia; numeración y auditoría transaccionales. |
| Administración | Alta de usuario y configuración de edades | Profesionales/consultorios tienen API, pero sus pantallas siguen pendientes. |

Las 56 operaciones se contaron desde `app.openapi()`. El head de Alembic del
código es `20260916_0010_locality`; esto no verifica el estado de una base
desplegada. Los IDs de datos demo no son constantes del contrato.

## Cambios aplicados en esta revisión

- El panel antes autoguardaba solo sexo, localidad, dirección, establecimiento
  y seguro. Ahora admite todas las columnas de `PatientUpdate` y guarda sus
  diferencias en un único PATCH al pulsar **Guardar cambios**.
- Se agregó descarte, validación local, conservación del borrador ante error,
  estado de guardado y control de doble envío. La atención queda bloqueada
  mientras se resuelven cambios pendientes del paciente.
- Edad y grupo etario se mantienen calculados. Madre y riesgos se gestionan
  desde el panel con sus formularios y endpoints existentes.
- Se separaron lista de campos/diferencias (`patientDraft.ts`), ciclo de edición
  (`useAdmissionPatientEditor.ts`), catálogos (`useAdmissionPatientDetails.ts`,
  `useRemoteCatalog.ts`) e interfaz de relaciones (`AdmissionPatientRelations.vue`).
  El editor recibe la operación de actualización como dependencia para probarla.
- Se actualizan el contexto de paciente y la selección compartida tras guardar;
  un cambio de `patientId` en Admisión monta el contexto correcto. Navegar con un
  borrador exige guardarlo o descartarlo; una sesión vencida puede salir al login.
- El PATCH rechaza `null` en documento/nacimiento y campos no admitidos, en vez
  de permitir que lleguen a una comparación de fechas o columna obligatoria.
- Al actualizar el ubigeo, el repositorio invalida la relación anterior antes de
  producir la respuesta y la auditoría. La búsqueda de pacientes precarga esa
  relación para evitar una consulta adicional por distrito al serializar listas.
- Las búsquedas de catálogos normalizan `q`; el editor usa debounce y descarta
  respuestas antiguas. Los errores de catálogos permiten reintentar.
- Un fallo del historial de Admisión ya no se presenta como “Sin atenciones”;
  muestra el error y permite refrescar. Se eliminó la carga inicial duplicada.
- Se agregaron pruebas del editor, regresiones del contrato PATCH y un job de
  frontend en CI con lint sin autocorrección, pruebas y compilación.
- Se corrigieron los dos README y la guía de rutas: sin atribuir a la UI
  controles de CIE-10/prestaciones o vista previa nutricional que hoy no conecta.

El PATCH y el POST son transacciones independientes. Un PATCH confirmado
permanece guardado aunque falle el POST de atención. Los cambios de identidad
no reescriben los snapshots de atenciones históricas.

## Hallazgos pendientes priorizados

| Prioridad | Evidencia | Efecto y siguiente trabajo |
| --- | --- | --- |
| Alta — flujo por permisos | `frontend/src/router/index.ts`, `app/domain/authorization.py` | ADMIN tiene `PACIENTE_EDITAR` pero Admisión exige `ATENCION_CREAR`. Al retirar el editor anterior se quedó sin acceso SPA a datos maestros. Si debe corregirlos, habilitar un modo de paciente en la misma pantalla, manteniendo el POST clínico restringido. |
| Alta — roles combinados | `app/services/discovery.py::_professional_scope` frente a `app/services/attention.py` | La búsqueda clínica rechaza cualquier principal con ADMIN antes de comprobar PROFESIONAL; otros servicios sí admiten PROFESIONAL vinculado. Alinear la precedencia y añadir pruebas de usuario con ambos roles. |
| Alta — módulos incompletos | `ProfesionalesView.vue`, `ConsultoriosView.vue`, `AuditoriaView.vue`, `LaboratorioView.vue` | Son pantallas pendientes. Preparar profesionales/asignaciones aún requiere API/Postman. Auditoría/laboratorio carecen de API de consulta operativa. |
| Media — pantalla móvil | `frontend/src/layouts/AppLayout.vue` | La barra lateral mantiene 264 px. En 390 px el documento alcanzó 495 px de ancho y el formulario quedó estrecho. Adaptar la navegación global a un menú plegable; no basta con las media queries del panel. |
| Media — historia sin límite | `atenciones.listByPatient`, `AttentionRepository.list_by_patient` | Carga todas las atenciones con relaciones. Usar búsqueda paginada también en los resúmenes, medir consultas y tamaño de respuesta con historia extensa. |
| Media — concurrencia de edición | PATCH de pacientes | El bloqueo SQL serializa escrituras, pero dos borradores del mismo campo pueden sobrescribirse. Añadir versión/ETag y respuesta de conflicto si habrá edición simultánea. Enviar diferencias ya evita sobrescribir campos ajenos no editados. |
| Media — tamaño y responsabilidades | `AtencionNuevaView.vue`, `main.ts` | La vista aún concentra contexto, medidas y nutrición; separar por responsabilidad. Se importa Element Plus y todos sus iconos globalmente. Build advierte de un chunk de aproximadamente 844 kB (266 kB gzip); medir y adoptar imports selectivos. |
| Media — interfaz/API clínica | `useNutritionalIndicatorsPreview.ts`, `AtencionNuevaView.vue` | Vista previa no conectada; alta sin controles de prestaciones/CIE-10. “Imprimir S.I.S.”, “Otra consulta” y “FUA adicional” solo muestran avisos. Implementar o seguir identificándolos como pendientes. |
| Media — formularios y errores restantes | `AtencionNuevaView.vue`, `PacienteDetalleView.vue`, cliente HTTP | Aún hay búsquedas sin captura local de errores y lógica de formularios en vistas grandes. Extraer estado/cargas con cancelación o descarte de respuestas antiguas y estados de error explícitos por sección. |
| Media — sesión y límites aceptados | `services/session-storage.ts`, `services/http.ts`, `auth` backend | Token en localStorage y lectura duplicada de sesión; evaluar almacenamiento según despliegue y unificar acceso. El directorio público y las claves de ocho dígitos son decisiones expresas del equipo, no endurecimiento de seguridad. Conservar limitador/bloqueo y evaluar el perímetro de uso. |
| Media — cobertura de operación | `.github/workflows/ci.yml`, `tests/integration` | CI no provisiona MySQL, por lo que la integración queda omitida sin configuración. Faltan E2E del POST/PATCH contra base desechable, pruebas de carga y comprobaciones de migración en CI. |
| Baja — reproducibilidad | `requirements.txt`, Ruff | Python usa rangos amplios sin lock; CI comprueba solo `F`. Fijar dependencias resueltas y ampliar controles de estilo en un cambio separado. |

También faltan lectura/lista administrativa de usuarios, consulta/descarga y
transiciones de documentos clínicos, así como perfil autenticado con vínculo
profesional. No crear interfaces que supongan esos contratos disponibles.

## Verificación y límites

- Backend: **70 pruebas pasaron**, **1 integración omitida** por no existir
  `TEST_DATABASE_URL`; Ruff `--select F` sin errores.
- Editor frontend: **6 pruebas pasaron**, incluyendo petición única,
  ausencia de autoguardado, fallo/reintento, validación, descarte y relaciones.
- Frontend: TypeScript, lint sin autocorrección y build de producción correctos;
  persiste la advertencia de tamaño de chunk descrita arriba.
- Navegador en `http://localhost:5173/admision?patientId=8`: campos presentes,
  guardar habilitado al editar, POST bloqueado con borrador, navegación bloqueada,
  descarte y nacimiento vacío validados. Prueba de escritorio y móvil; la
  limitación del layout móvil está documentada, no se declara corregida.
- En esta base, el ID 8 corresponde a un paciente demo distinto del ejemplo
  pegado por el usuario. No se cambió identidad ni se grabaron datos ficticios
  en ese paciente para verificar el formulario.
- No se creó una atención clínica ni se ejecutó la colección Postman, semillas,
  reset de base o migraciones sobre la base de trabajo. El guardado se comprobó
  con persistencia simulada y pruebas de contrato; falta una corrida E2E de
  escrituras contra MySQL desechable.

## Repetir las comprobaciones

Desde la raíz:

```powershell
python -m pytest        # unitarias + integración + cobertura (umbral en pyproject.toml)
python -m ruff check app tests migrations --select F
alembic heads
```

Desde `frontend/`:

```powershell
npm run test:coverage
npm run lint:check
npm run type-check
npm run build
```

Para integración, usar solamente una MySQL de pruebas: su fixture aplica
migraciones y las revierte al terminar. No apuntar `TEST_DATABASE_URL` a la
base de trabajo ni interpretar pruebas unitarias como una prueba de capacidad.

Estado al 20/09/2026: 231 pruebas backend (~92% con ramas) y 134 pruebas de
frontend. La integración dejó de omitirse: `TEST_DATABASE_URL` apunta a una base
desechable y CI levanta MySQL 8, por lo que el SQL y los `downgrade` de las
migraciones sí se ejecutan en cada corrida. Siguen sin cubrirse las pantallas de
configuración (usuarios, profesionales, consultorios, auditoría, laboratorio) y
las secciones grandes de `AtencionNuevaView.vue`.
