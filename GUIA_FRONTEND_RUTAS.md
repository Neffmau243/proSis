# Guía de frontend — rutas, páginas y consumo del API IPRESS

> Documento de integración para el equipo frontend, actualizado contra los
> routers, esquemas y permisos reales del backend. La base de datos es la
> MySQL local `sistema_salud_ipress`; el frontend no usa ni debe criar otra
> base ni otro entorno para este flujo.
>
> La SPA ya vive en [`frontend/`](frontend/README.md). Este documento sigue
> siendo el contrato HTTP por pantalla; para la implementación concreta (módulos
> terminados, componentes y verificación) use ese README.

## 1. Alcance y convención de rutas

El backend expone su API bajo `http://127.0.0.1:8000/api/v1`. Todas las rutas
que comienzan con `/api/v1` en este documento son **rutas reales de FastAPI**.
Las rutas sin ese prefijo son las páginas de la SPA, declaradas en
`frontend/src/router/index.ts`; cada una exige los permisos indicados y el
backend sigue siendo la autoridad final.

```text
Navegador → ruta de la SPA → cliente HTTP → /api/v1 → FastAPI → MySQL
```

### Rutas implementadas en la SPA

| Ruta | Vista | Permiso exigido en el guard |
| --- | --- | --- |
| `/login` | Acceso | Pública |
| `/` | Base de datos (tabla de pacientes) | Sesión |
| `/laboratorio` | Referencia de laboratorio | Sesión |
| `/cuenta/cambiar-contrasena` | Cambio de clave propia | Sesión |
| `/admision?patientId=:id` | Admisión: contexto del paciente + atención | `ATENCION_CREAR` |
| `/pacientes/nuevo` | Registro de paciente | `PACIENTE_EDITAR` |
| `/pacientes/:id` | Ficha del paciente | `PACIENTE_LEER` |
| `/pacientes/:id/editar` | Edición de datos base | `PACIENTE_EDITAR` |
| `/pacientes` | Redirección a `/` | Sesión |
| `/atenciones` | Historial de atenciones | `ATENCION_LEER` |
| `/atenciones/nueva` | Nueva atención fuera de admisión | `ATENCION_CREAR` |
| `/atenciones/:id` | Detalle de atención | `ATENCION_LEER` |
| `/configuracion/usuarios` | Alta de usuarios | `USUARIO_GESTIONAR` |
| `/configuracion/auditoria` | Auditoría (placeholder) | `AUDITORIA_LEER` |
| `/configuracion/grupos-etarios` | Grupos etarios | `GRUPO_ETARIO_CONFIGURAR` |
| `/configuracion/profesionales` | Profesionales (placeholder) | `PROFESIONAL_GESTIONAR` |
| `/configuracion/consultorios` | Consultorios (placeholder) | `CONSULTORIO_GESTIONAR` |

Si falta un permiso, el guard redirige a `/`; si no hay sesión, a `/login` con
`redirect`.

Use una única variable de configuración en el frontend:

```text
API_BASE_URL=http://127.0.0.1:8000/api/v1
```

No agregar `/api/v1` dos veces. En desarrollo, si frontend y backend se sirven
desde orígenes distintos, el backend debe tener el origen del frontend en
`CORS_ORIGINS`; por defecto CORS no queda abierto.

## 2. Sesión, autorización y manejo transversal

### Inicio y cierre de sesión

| Página propuesta | Acción | API | Resultado que debe conservar el cliente |
| --- | --- | --- | --- |
| `/login` | Iniciar sesión | `POST /auth/login` | `access_token`, `expires_in`, `usuario_id`, `roles` y `permisos` |
| `/cuenta/cambiar-contrasena` | Cambiar la clave del usuario actual | `PUT /auth/me/password` | Responde `204 No Content`; cerrar la sesión local y pedir nuevo inicio |

El login recibe `{ "nombre_usuario", "password" }`. Cada petición protegida
debe enviar `Authorization: Bearer <access_token>`. No existe endpoint de
refresh ni `/auth/me`; el estado inicial del usuario proviene de la respuesta
del login. Por ello el cliente debe vencer la sesión con `expires_in` y volver
a `/login` ante un `401`.

No mostrar los menús solo por el rol escrito en la interfaz: usar el arreglo
`permisos` que entrega el login y mantener el backend como autoridad final.
Un usuario puede tener ambos roles; en ese caso puede ver los módulos que sus
permisos habiliten, pero las reglas de ámbito clínico siguen validándose en el
servidor.

### Respuestas comunes

Las listas paginadas siempre tienen esta forma:

```json
{ "items": [], "total": 0, "limit": 25, "offset": 0, "has_more": false }
```

El límite es de 1 a 100. El paginador debe usar `has_more` o `total`, nunca
suponer que una página incompleta es la última. Los errores tienen el sobre
`{ "error": { "code", "message", "details", "request_id" } }`; mostrar
`message` al usuario y conservar `request_id` para soporte. En toda respuesta
el backend devuelve además `X-Request-ID`.

| Estado | Comportamiento de la UI |
| --- | --- |
| `201` | Mostrar confirmación y navegar/refrescar con el recurso retornado. |
| `204` | No intentar leer JSON; mostrar éxito. |
| `401` | Limpiar sesión y enviar a `/login`. |
| `403` | Ocultar la acción y, si llega igual, informar falta de permiso. |
| `404` | Volver a la lista con aviso de recurso inexistente. |
| `409` | Mantener formulario y mostrar conflicto/regla de negocio. |
| `422` | Asociar los errores de validación a los campos enviados. |
| `429` | Informar que el login está temporalmente limitado y no reintentar en bucle. |

## 3. Menú por permisos reales

| Área | ADMIN | PROFESIONAL | Observación |
| --- | :---: | :---: | --- |
| Pacientes: consultar, crear, editar, responsables y riesgos | Sí | Sí, con ámbito clínico | El profesional solo ve pacientes de sus establecimientos asignados, con atención propia o que él registró/trasladó. |
| Pacientes: dar de baja | Sí | No | Es baja lógica mediante `DELETE`; no se borra físicamente. |
| Atenciones e historial | No | Sí | Un ADMIN sin rol PROFESIONAL recibirá `403`. |
| FUA, certificados y referencias | No | Sí | Se emiten desde una atención accesible al profesional. |
| Configurar grupos etarios | Sí | No | Afecta el cálculo clínico futuro. |
| Gestionar profesionales y consultorios | Sí | No | Incluye activar/desactivar y asignaciones. |
| Gestionar usuarios | Sí | No | Falta un GET de usuarios; ver limitaciones. |
| Catálogos | Sí | Sí | Todos requieren token válido. |

Menú mínimo sugerido:

```text
ADMIN
├─ Pacientes
├─ Configuración
│  ├─ Grupos etarios
│  ├─ Profesionales
│  └─ Consultorios
├─ Usuarios (gestión parcial; sin listado API)
└─ Mi cuenta

PROFESIONAL
├─ Pacientes
├─ Nueva atención
├─ Historial de atenciones
└─ Mi cuenta
```

## 4. Mapa de páginas y ventanas

### Páginas compartidas

| Ruta de la SPA | Vista / ventana | Lecturas | Escrituras | Roles |
| --- | --- | --- | --- | --- |
| `/login` | Formulario de acceso | — | `POST /auth/login` | Pública |
| `/cuenta/cambiar-contrasena` | Formulario con clave actual, nueva y confirmación | — | `PUT /auth/me/password` | Autenticado |
| `/` | Tabla/buscador de pacientes (“Base de datos”) | `GET /patients` | — | ADMIN, PROFESIONAL |
| `/pacientes/nuevo` | Registro de paciente | Catálogos de identidad, seguro, ubigeo, riesgos y establecimientos | `POST /patients` | ADMIN, PROFESIONAL |
| `/pacientes/:id` | Ficha del paciente con pestañas Datos, Responsables, Riesgos y Atenciones | `GET /patients/{id}`; `GET /atenciones?paciente_id={id}` | Según pestaña | ADMIN, PROFESIONAL |
| `/pacientes/:id/editar` | Edición de datos base | `GET /patients/{id}` y catálogos | `PATCH /patients/{id}` | ADMIN, PROFESIONAL |
| `/admision?patientId=:id` | Admisión: tarjeta lateral del paciente con edición en línea + formulario de atención | `GET /patients/{id}`, catálogos, `GET /atenciones?paciente_id={id}` | `PATCH /patients/{id}`, `POST /atenciones` | PROFESIONAL |

En `/admision` la tarjeta “Datos del paciente” guarda al vuelo los campos que el
mostrador necesita corregir durante la atención: `sexo_codigo`, `localidad`,
`direccion`, `establecimiento_registro_id` y `seguro_id`. Cada cambio envía un
`PATCH` de **un solo campo** (el backend aplica `exclude_unset`) y el panel se
deshabilita mientras guarda; no hay botón de guardar para esa tarjeta.

En la ficha de paciente abrir ventanas laterales o modales, no páginas nuevas,
para estos cambios puntuales:

| Componente | API | Nota |
| --- | --- | --- |
| Modal “Agregar responsable” | `POST /patients/{patientId}/responsibles` | Para menor de edad debe existir al menos un responsable activo antes de crear una atención. |
| Modal “Editar responsable” | `PATCH /patients/{patientId}/responsibles/{responsibleId}` | Mantiene el historial de responsables. |
| Modal “Agregar riesgo” | `POST /patients/{patientId}/risk-groups` | Elegir el grupo desde catálogo y fecha de inicio. |
| Modal “Editar/cerrar riesgo” | `PATCH /patients/{patientId}/risk-groups/{riskGroupId}/{startDate}` | `startDate` forma parte de la identidad de la relación; enviar fecha ISO `YYYY-MM-DD`. |
| Diálogo “Dar de baja” | `DELETE /patients/{patientId}` | Solo ADMIN; pedir confirmación y luego retirar de las búsquedas activas. |

Filtros de `/pacientes`: `tipo_documento_codigo`, `numero_documento`,
`historia_clinica`, `q` (mínimo 2 caracteres), `establecimiento_id`,
`incluir_inactivos`, `limit` y `offset`. Para PROFESIONAL, `incluir_inactivos`
no amplía su visibilidad aunque lo envíe el cliente.

### Módulo clínico (solo PROFESIONAL)

| Ruta de la SPA | Vista / ventana | Lecturas | Escrituras |
| --- | --- | --- | --- |
| `/atenciones/nueva`, `/admision?patientId=:id` | Formulario clínico por pasos | Paciente, catálogos y consultorios/profesionales del establecimiento | `POST /atenciones` |
| `/atenciones/:attentionId` | Detalle de atención | `GET /atenciones/{attentionId}` | Anulación o emisión documental |
| `/atenciones` | Historial con filtros y paginación | `GET /atenciones/busqueda` | — |
| `/pacientes/:patientId` → pestaña Atenciones | Historial reducido del paciente | `GET /atenciones?paciente_id={patientId}` | Abrir detalle/nueva atención |

El formulario de nueva atención necesita `paciente_id`, `establecimiento_id`,
`profesional_id`, `consultorio_id`, `modalidad_atencion_codigo` (`AMBULATORIA`
o `EMERGENCIA`) y `fecha_atencion`. Puede añadir signos vitales, horas,
observaciones, prestaciones, diagnósticos y valoración nutricional. No enviar
`grupo_etario_codigo`, edad, estado, `imc`, `pe`, `te` ni `pt`: el backend los
calcula. Mientras el usuario escribe peso y talla, pedir
`POST /atenciones/indicadores-nutricionales/vista-previa` para mostrar la vista
previa, sin persistir nada.

La búsqueda paginada acepta `paciente_id`, `establecimiento_id`,
`profesional_id`, `desde`, `hasta`, `estado` (`ATENDIDO` o `ANULADO`), `limit`
y `offset`. Aunque la página tenga filtros de profesional/establecimiento, el
backend impone la identidad y consultorios activos del profesional conectado.

| Modal desde el detalle de atención | API | Regla visible para la UI |
| --- | --- | --- |
| “Anular atención” | `POST /atenciones/{attentionId}/anulacion` | Requiere `observaciones` de 5 a 10 000 caracteres. No ofrecerla si ya está anulada. |
| “Emitir FUA” | `POST /documentos/fua` | Una atención no puede tener dos FUA emitidos. |
| “Emitir certificado” | `POST /documentos/certificados` | Solicita tipo y puede recibir profesional y prestaciones. |
| “Crear referencia” | `POST /documentos/referencias` | Inicia necesariamente en `PENDIENTE`; no permitir otro estado en el formulario. |

Una atención con documentos vigentes no puede anularse. No hay endpoints para
listar, descargar, anular o cambiar el estado de FUA, certificados o
referencias: después de emitir, mostrar únicamente la respuesta devuelta en el
modal o en la ficha actual; no prometer un repositorio documental todavía.

### Configuración administrativa (solo ADMIN)

| Ruta web propuesta | Vista | Lecturas | Escrituras |
| --- | --- | --- | --- |
| `/configuracion/grupos-etarios` | Tabla editable completa de rangos | `GET /configuracion/grupos-etarios` | `PUT /configuracion/grupos-etarios` |
| `/configuracion/profesionales` | Lista de profesionales | `GET /configuracion/profesionales?incluir_inactivos=` | `POST /configuracion/profesionales` |
| `/configuracion/profesionales/nuevo` | Formulario de profesional | `GET /catalogos/profesiones`; `GET /catalogos/especialidades` | `POST /configuracion/profesionales` |
| `/configuracion/profesionales/:professionalId` | Ficha y edición | `GET /configuracion/profesionales/{professionalId}` | `PATCH`, `PUT .../especialidades`, `DELETE` del mismo recurso |
| `/configuracion/consultorios` | Lista filtrable por establecimiento | `GET /configuracion/consultorios` | `POST /configuracion/consultorios` |
| `/configuracion/consultorios/nuevo` | Formulario de consultorio | Catálogos de establecimientos, especialidades y consultorios padre | `POST /configuracion/consultorios` |
| `/configuracion/consultorios/:officeId` | Ficha, edición y asignaciones | `GET /configuracion/consultorios/{officeId}`; `GET .../{officeId}/profesionales` | `PATCH`, `DELETE`, asignar/cerrar profesional |

Para grupos etarios el `PUT` reemplaza la configuración completa: antes de
guardar, cargar el `GET`, editar su copia y reenviar todos los grupos en
`{ "grupos": [...], "exigir_cobertura_continua": boolean }`. Cada límite se
puede enviar como meses o como `{ "anios", "meses" }`; no enviar dos valores
que se contradigan.

En la ficha de consultorio, la tabla de asignaciones debe mostrarse aun cuando
venga `[]`: significa que no existe ninguna asignación histórica todavía, no
un error. Ese fue justamente el comportamiento correcto observado antes de
crear una asignación. Después de `POST
/configuracion/consultorios/{officeId}/profesionales`, recargar el mismo GET.

| Ventana de consultorio | API | Datos clave |
| --- | --- | --- |
| “Asignar profesional” | `POST /configuracion/consultorios/{officeId}/profesionales` | `profesional_id`, `fecha_inicio`, `fecha_fin` opcional, `es_responsable`. |
| “Cerrar asignación” | `PATCH /configuracion/consultorios/{officeId}/profesionales/{professionalId}/{startDate}/cierre` | Enviar `{ "fecha_fin": "YYYY-MM-DD" }`; `startDate` es la fecha inicial de esa asignación. |

Los `DELETE` de profesionales y consultorios son bajas lógicas. Incluir un
filtro “incluir inactivos” y no implementar un borrado irreversible en la UI.

### Usuarios (ADMIN, soporte parcial)

| Ruta web propuesta | Acciones que sí tienen API | Bloqueo actual |
| --- | --- | --- |
| `/usuarios/nuevo` | `POST /usuarios` | Puede crear usuario con `profesional_id` opcional, clave de mínimo 12 caracteres y roles `ADMIN`/`PROFESIONAL`. |
| `/usuarios/:userId/seguridad` | `PUT /usuarios/{userId}/roles`, `PUT /usuarios/{userId}/password`, `DELETE /usuarios/{userId}` | Funciona solo si ya se conoce el ID por otro contexto. |
| `/usuarios` | — | **No existe `GET /usuarios` ni `GET /usuarios/{userId}`.** No construir una tabla de usuarios funcional hasta que backend exponga lectura. |

## 5. Catálogos que cada pantalla debe consumir

Todos requieren autenticación. Conviene cargarlos al entrar al módulo que los
usa y cachearlos durante la sesión; los catálogos paginados deben consultarse
por texto (`q`, mínimo 2 caracteres) para autocompletes grandes.

| Recurso | Endpoint | Pantallas consumidoras |
| --- | --- | --- |
| Tipos de documento | `GET /catalogos/tipos-documento` | Paciente, responsable. |
| Sexos | `GET /catalogos/sexos` | Paciente. |
| Seguros | `GET /catalogos/seguros` | Paciente. |
| Ubigeos | `GET /catalogos/ubigeos?q=&limit=&offset=` | Paciente. |
| Grupos de riesgo | `GET /catalogos/grupos-riesgo` | Modal de riesgo. |
| Establecimientos | `GET /catalogos/establecimientos?q=&limit=&offset=` | Paciente, atención, consultorios, referencia. |
| Modalidades | `GET /catalogos/modalidades-atencion` | Atención. |
| Prestaciones | `GET /catalogos/prestaciones?q=&limit=&offset=` | Atención y certificado. |
| CIE-10 | `GET /catalogos/cie10?q=&limit=&offset=` | Diagnósticos de atención. |
| Consultorios | `GET /catalogos/consultorios?establecimiento_id=&q=&limit=&offset=` | Atención y consultorio padre. |
| Profesionales | `GET /catalogos/profesionales?q=&limit=&offset=` | Atención y asignación de consultorio. |
| Profesiones | `GET /catalogos/profesiones` | Profesional. |
| Especialidades | `GET /catalogos/especialidades` | Profesional y consultorio. |
| Grupos etarios de lectura | `GET /catalogos/grupos-etarios` | Etiquetas/consulta; la edición administrativa usa el endpoint de configuración. |

## 6. Flujos esperados entre pantallas

### Flujo administrativo de preparación

```text
Login ADMIN
  → Profesionales (crear + especialidades)
  → Consultorios (crear)
  → Detalle de consultorio / Asignar profesional
  → Pacientes (registrar o mantener)
```

La asignación no se crea al registrar un profesional ni al crear un
consultorio: es una acción explícita en la ficha del consultorio. Por eso el
primer `GET .../profesionales` puede devolver `[]` y debe renderizarse como
estado vacío “Aún no hay profesionales asignados”.

### Flujo asistencial

```text
Login PROFESIONAL
  → Buscar paciente
  → Ficha del paciente
  → (si es menor, verificar responsable activo)
  → Nueva atención
  → Detalle de atención
  → FUA / certificado / referencia, si corresponde
```

Antes de enviar una atención, el selector de **consultorio** y el
**profesional** deben reflejar una asignación vigente: el backend rechaza la
atención (`PROFESIONAL_NO_ASIGNADO`, `ESPECIALIDAD_INCOMPATIBLE`) si no existe
una fila vigente en `consultorio_profesionales` para la fecha. El
`establecimiento_registro_id` del paciente es otra cosa: desde el registro o el
traslado solo se exige que la sede exista y esté activa, y el profesional que
la registra o la cambia conserva el acceso al paciente (ver “Cambios recientes
del contrato”). No confiar solo en la UI: el backend valida el ámbito
asistencial en cada lectura y escritura de pacientes, atenciones y documentos.
Tras emitir un documento, actualizar la ficha local y desactivar la opción de
anulación mientras no existan endpoints de anulación/cierre de documentos.

## 7. Inventario completo de API por módulo

Esta lista complementa las páginas anteriores y permite al frontend comparar
su cliente HTTP con las **55 operaciones** disponibles (la colección Postman
cubre 54: todavía no incluye la vista previa de indicadores nutricionales).

| Módulo | Operaciones reales |
| --- | --- |
| Salud | `GET /health` (pública, no conecta a MySQL). |
| Autenticación | `POST /auth/login`; `PUT /auth/me/password`. |
| Pacientes | `GET`, `POST /patients`; `GET`, `PATCH`, `DELETE /patients/{patientId}`; `POST /patients/{patientId}/responsibles`; `PATCH /patients/{patientId}/responsibles/{responsibleId}`; `POST /patients/{patientId}/risk-groups`; `PATCH /patients/{patientId}/risk-groups/{riskGroupId}/{startDate}`. |
| Catálogos | Los 14 `GET /catalogos/...` de la sección anterior. |
| Grupos etarios | `GET`, `PUT /configuracion/grupos-etarios`. |
| Profesionales | `GET`, `POST /configuracion/profesionales`; `GET`, `PATCH`, `DELETE /configuracion/profesionales/{professionalId}`; `PUT /configuracion/profesionales/{professionalId}/especialidades`. |
| Consultorios | `GET`, `POST /configuracion/consultorios`; `GET`, `PATCH`, `DELETE /configuracion/consultorios/{officeId}`; `GET`, `POST /configuracion/consultorios/{officeId}/profesionales`; `PATCH /configuracion/consultorios/{officeId}/profesionales/{professionalId}/{startDate}/cierre`. |
| Atenciones | `GET`, `POST /atenciones`; `GET /atenciones/busqueda`; `GET /atenciones/{attentionId}`; `POST /atenciones/indicadores-nutricionales/vista-previa`; `POST /atenciones/{attentionId}/anulacion`. |
| Documentos | `POST /documentos/fua`; `POST /documentos/certificados`; `POST /documentos/referencias`. |
| Usuarios | `POST /usuarios`; `PUT /usuarios/{userId}/roles`; `PUT /usuarios/{userId}/password`; `DELETE /usuarios/{userId}`. |

## 8. Cambios recientes del contrato

Estos puntos cambiaron respecto de versiones anteriores de esta guía y ya están
implementados en el backend (`revisión 20260912_0009_patient_prof`):

- **Ámbito del paciente para un PROFESIONAL**: se compone de (1) pacientes
  registrados en una sede donde tiene asignación vigente, (2) pacientes con una
  atención no anulada suya y (3) pacientes cuyo `profesional_registro_id` es él.
  El tercer caso existe para que quien registra o traslada a un paciente no lo
  pierda de vista al moverlo de sede. La búsqueda filtra por ese ámbito, así que
  un paciente de otra sede no aparece ni con su DNI exacto.
- **Registro y traslado de sede**: `POST /patients` y `PATCH /patients/{id}` con
  `establecimiento_registro_id` ya **no** exigen asignación vigente en la sede
  destino; solo que la sede exista y esté activa (`CATALOGO_NO_DISPONIBLE`). El
  código `ESTABLECIMIENTO_FUERA_DE_AMBITO` dejó de emitirse y el backend guarda
  al profesional autenticado como autor del registro. El cliente no puede
  enviar ni limpiar `profesional_registro_id`: se deduce de la sesión.
- **Indicadores nutricionales en el servidor**: `POST /atenciones` calcula IMC y,
  para menores de 60 meses con sexo registrado, P/E, T/E y P/T con la referencia
  OMS 2006. El formulario puede pedir el mismo cálculo sin persistir con
  `POST /atenciones/indicadores-nutricionales/vista-previa` enviando solo
  `paciente_id`, `fecha_atencion`, `peso_kg` y `talla_cm`. **No enviar** `imc`,
  `pe`, `te` ni `pt`: son campos derivados del servidor.
- **Snapshot nutricional**: `valoracion_nutricional.tipo` es **opcional**; se
  acepta un snapshot solo diagnóstico y `tipo` puede ser nulo.

## 9. Vacíos actuales que frontend debe respetar

- No hay dashboard ni endpoint de métricas. No inventar contadores globales de
  atenciones para ADMIN: ese rol no puede leerlas. Puede mostrarse una portada
  de navegación sin métricas hasta que exista un contrato específico.
- No hay lectura/lista de usuarios; por tanto no hay gestión de usuarios
  completa desde una tabla.
- No hay lectura, listado, archivo/descarga, anulación ni transición de estado
  para documentos clínicos ya emitidos.
- No hay endpoint de auditoría aunque la base registra auditoría y existe el
  permiso correspondiente.
- No hay endpoint de perfil actual; el frontend debe usar solo los datos
  devueltos por login hasta que se agregue `/auth/me`.
- No hay endpoint público de catálogos: ejecutar el bootstrap de catálogos
  después del login, con token.

## 10. Lista de verificación antes de conectar el frontend

- [ ] Configurar `API_BASE_URL` como `http://127.0.0.1:8000/api/v1`.
- [ ] Iniciar el backend con `uvicorn app.main:app --reload` y comprobar
  `GET /api/v1/health`.
- [ ] Configurar `CORS_ORIGINS` con el origen real del frontend si no comparten
  host/puerto.
- [ ] Implementar interceptor Bearer, expiración de token, `401`, `403` y
  sobre de errores.
- [ ] Usar `permisos` del login para navegación y acciones; nunca sustituir la
  validación del servidor.
- [ ] Implementar paginación `limit`, `offset`, `has_more` en todas las tablas
  que usan respuesta paginada.
- [ ] Tratar `[]` de asignaciones de consultorio como estado vacío válido.
- [ ] No ofrecer el traslado de sede a establecimientos inactivos y recordar que
  el traslado no exige asignación vigente (ver “Cambios recientes del contrato”).
- [ ] No enviar campos derivados (`imc`, `pe`, `te`, `pt`, `grupo_etario_codigo`,
  `edad_*`) ni `profesional_registro_id` en ningún payload.
- [ ] No presentar como terminadas las pantallas marcadas como bloqueadas por
  endpoints de lectura ausentes.

Para el mapa interno del backend, modelo MySQL, migraciones, pruebas y
colección Postman, consultar [README.md](README.md).
