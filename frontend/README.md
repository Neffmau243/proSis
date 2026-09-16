# IPRESS Frontend

Interfaz web del **Sistema de Salud IPRESS**, construida con **Vue 3 + TypeScript (Composition API, `<script setup>`) + Vite + Pinia + Vue Router 5 + Element Plus** (locale español).

El backend (FastAPI) vive en la raíz del repo. La integración de rutas, permisos, sobre de errores, paginación y vacíos actuales está documentada en [`../GUIA_FRONTEND_RUTAS.md`](../GUIA_FRONTEND_RUTAS.md).

---

## 1. Credenciales demo (solo BD local desechable)

Creadas por `python -m app.scripts.seed_demo_data` (o `reset_demo_database --demo-credentials`). **Nunca usar fuera de desarrollo.**

| Usuario | Contraseña | Rol | Notas |
| --- | --- | --- | --- |
| `admin` | `IpressDev!Admin2026` | **ADMIN** | Gestión administrativa completa |
| `medico.demo` | `IpressDev!Medico2026` | **PROFESIONAL** | Dra. Andrea Prueba — flujo clínico |

La semilla también carga un cohorte para probar el sistema con volumen: **14 pacientes** con nombres, DNI e historias clínicas distintos (`HC-DEMO-0001`…`HC-DEMO-0012` más los dos originales), repartidos entre IPRESS Demo Central (11) e IPRESS Demo Destino (3), con niños, adolescentes, adultos y adultos mayores, responsables para cada menor, antecedentes de riesgo, seguros variados (SIS, EsSalud, Particular, Sin seguro) y tres distritos.

| Dato | Valor |
| --- | --- |
| Paciente original adulto | DNI `99900001` (Ana Prueba Demo), `HC-DEMO-ADULTO` |
| Paciente original menor | DNI `99900002` (Luis), `HC-DEMO-MENOR` |
| Consultorio / especialidad | `MED-GEN` / `MED_GEN` |
| Prestación / CIE-10 | `CONSULTA_MED` / `Z00.0` |
| Riesgos | `RIESGO_DEMO`, `RIESGO_CARDIO`, `RIESGO_METABOLICO` |
| Atenciones demo | 5 en total (ids 10–14) con signos vitales e indicadores del servidor |
| Documentos demo | 1 FUA, 1 certificado y 1 referencia a la sede Destino |

Los 3 pacientes de IPRESS Demo Destino están a propósito sin asignación ni atención de `medico.demo`: sirven para comprobar que el ámbito asistencial los filtra (no aparecen ni buscándolos por DNI).

---

## 2. Roles: qué hace cada uno

El backend define un mapa de permisos (`app/domain/authorization.py`) y lo entrega en el login (`permisos`). El frontend **solo** usa ese arreglo para mostrar menú y botones; el backend sigue siendo la autoridad final.

| Permiso | ADMIN | PROFESIONAL |
| --- | :---: | :---: |
| Pacientes: leer | ✅ | ✅ (ámbito clínico) |
| Pacientes: crear/editar (+ responsables/riesgos) | ✅ | ✅ (solo su ámbito: sede asignada, atención propia o registro/traslado propio) |
| Pacientes: dar de baja | ✅ | ❌ |
| Atenciones: crear / leer / anular | ❌ | ✅ (solo las propias) |
| FUA / certificados / referencias | ❌ | ✅ (solo de sus atenciones) |
| Grupos etarios (configurar) | ✅ | ❌ |
| Profesionales (gestionar) | ✅ | ❌ |
| Consultorios + asignaciones | ✅ | ❌ |
| Usuarios (crear, roles, contraseñas, baja) | ✅ | ❌ |
| Auditoría (permiso existe, sin endpoint aún) | ✅ | ❌ |

### ADMIN — rol administrativo

1. **Usuarios**: alta de cuentas, roles `ADMIN`/`PROFESIONAL`, restablecer contraseñas, baja. No puede quitarse/desactivar al último ADMIN activo.
2. **Profesionales**: alta, edición, especialidades, baja lógica.
3. **Consultorios**: alta/edición y asignación de profesionales con fechas (requisito para atender).
4. **Grupos etarios**: rangos sin solapes, cobertura continua opcional.
5. **Pacientes**: admisión, edición, responsables, riesgos y baja lógica.
6. **No puede** operar atenciones ni emitir documentos clínicos (ni aunque lo intente: los servicios lo rechazan con 403).

### PROFESIONAL — rol asistencial

1. **Pacientes** de su ámbito: sedes con asignación vigente, pacientes con atención propia no anulada y pacientes que él registró o trasladó de sede.
2. **Atenciones**: registra, consulta y anula **solo las suyas** (el `profesional_id` sale de la sesión, nunca del formulario).
3. **Documentos**: FUA (único por atención), certificados y referencias de sus atenciones.
4. **No puede**: dar de baja pacientes ni administrar usuarios/configuración.

---

## 3. Barra lateral (flujo del sistema antiguo, rediseñada)

Un solo layout (`src/layouts/AppLayout.vue`) que filtra por permisos. La navegación va **por secciones** y el paciente activo vive en una **tarjeta contextual**, en lugar de ítems de menú deshabilitados (eso era lo que se veía "soso" y redundante).

```text
🏥 IPRESS · Sistema de Salud

[ Admisión ]            (botón principal)
[ Nuevo paciente ]      (botón secundario)

┌ Paciente seleccionado ─────────────┐
│ Ana Pérez                          │
│ DNI 99900001 · HC 99900001         │
│ [Modificar] [Borrar] [Quitar]      │
└────────────────────────────────────┘

Principal
├─ Base de datos        → /            (tabla)
└─ Ref. Laboratorio     → /laboratorio

Clínico                  (solo PROFESIONAL)
├─ Historial de atenciones → /atenciones
└─ Nueva atención          → /atenciones/nueva

Administración            (solo ADMIN)
├─ Usuarios              → /configuracion/usuarios
└─ Auditoría             → /configuracion/auditoria

Configuración             (solo ADMIN)
├─ Grupos etarios        → /configuracion/grupos-etarios
├─ Profesionales         → /configuracion/profesionales
└─ Consultorios          → /configuracion/consultorios

👤 <usuario> · <rol>
[ Salir ]
```

- Seleccionar una fila en la tabla llena la tarjeta **Paciente seleccionado** con sus acciones (Modificar / Borrar / Quitar). Se eliminaron los ítems de menú duplicados ("Ver paciente" apuntaba a la misma página y Modificar/Borrar repetían las acciones de la tabla).
- El pie muestra el usuario y su rol, con **Salir**; el header conserva **Cambiar contraseña**.
- Si un usuario tuviera ambos roles, vería las tres secciones (los ítems se filtran por permisos reales, no por rol escrito).

---

## 4. Módulos implementados (conectados al API real)

### Pacientes — tabla "Base de datos" (dashboard)

| Vista | Ruta | Endpoints usados |
| --- | --- | --- |
| **Base de datos**: tabla con las columnas del sistema antiguo (N° Historia, H. Familiar, N° DNI, apellidos, nombres, Sexo, Disi) y 5 modos de búsqueda | `/` | `GET /patients` |
| Admisión (contexto del paciente editable + atención) | `/admision?patientId=` | `GET /patients/{id}`, `PATCH /patients/{id}`, `POST /atenciones` |
| Nuevo paciente (con historia familiar, responsables y riesgos) | `/pacientes/nuevo` | `POST /patients` |
| Ficha con pestañas Datos/Responsables/Riesgos/Atenciones | `/pacientes/:id` | `GET /patients/{id}`, `GET /atenciones?paciente_id=`, POST/PATCH responsables y riesgos |
| Modificar datos | `/pacientes/:id/editar` | `PATCH /patients/{id}` |
| Borrar (baja lógica, solo ADMIN) | desde la tabla o la ficha | `DELETE /patients/{id}` |

**Búsqueda dinámica** (selector segmentado; el **DNI** es la modalidad por defecto porque es la más usada):

| Modalidad | Parámetro |
| --- | --- |
| **DNI** | `q` (coincidencia parcial mientras se escribe) |
| H. Clínica exacta | `historia_clinica` (exacto) |
| H. Clínica similar | `q` (parcial) |
| Apellidos y nombres | `q` (parcial) |
| H. Familiar | — *(pendiente: el backend aún no filtra por `historia_familiar`; opción deshabilitada)* |

- La tabla **filtra mientras se escribe** (debounce 280 ms) y **lista toda la base** cuando el campo está vacío, como el sistema antiguo. Ya no hay botón "Buscar": el refresco manual es el botón ↻.
- Con menos de 2 caracteres el backend no filtra por `q`, así que se sigue mostrando toda la base.
- Si el filtro deja **un único paciente**, se selecciona automáticamente y queda listo para Modificar/Borrar.
- Las modalidades parciales usan `q` porque el backend solo expone `numero_documento` **exacto** (la coincidencia parcial existe únicamente en `q`, que abarca DNI, historia clínica y nombres).

La columna **Disi** reproduce el indicador de estado del sistema antiguo: `ALT` = activo, `BAJA` = inactivo (la baja es lógica). El checkbox **Incluir bajas** (solo ADMIN) los muestra en la tabla.

### Atenciones
| Vista | Ruta | Endpoints usados |
| --- | --- | --- |
| Historial con filtros y paginación | `/atenciones` | `GET /atenciones/busqueda` |
| Nueva atención / Admisión (contexto + antropometría + presión/temperatura + PE/TE/PT calculados + valoración nutricional + prestaciones + CIE-10 + historial del paciente) | `/atenciones/nueva`, `/admision?patientId=` | `POST /atenciones`, `POST /atenciones/indicadores-nutricionales/vista-previa`, `GET /atenciones?paciente_id=` |
| Detalle con anulación y documentos | `/atenciones/:id` | `GET /atenciones/{id}`, `POST .../anulacion`, `POST /documentos/fua`, `POST /documentos/certificados`, `POST /documentos/referencias` |

Reglas respetadas por la UI: no se envía `grupo_etario_codigo`, edad, estado, `imc`, `pe`, `te` ni `pt` (el backend los calcula); la anulación exige justificación ≥ 5 caracteres; una referencia nueva siempre inicia `PENDIENTE`; los consultorios se cargan según el establecimiento elegido. La **valoración nutricional** es opcional y solo se envía si el profesional registra al menos un dato (su `tipo` es opcional en el backend). El formulario muestra los indicadores que devuelve `POST /atenciones/indicadores-nutricionales/vista-previa` (IMC y, para menores de 60 meses, P/E, T/E y P/T con referencia OMS 2006) sin persistir nada. Admisión muestra el resultado como "Guardar atención" y el botón de escape como "Salir", igual que el sistema antiguo.

La **tarjeta lateral “Datos del paciente”** de `/admision` permite corregir en línea `sexo_codigo`, `localidad`, `direccion`, `establecimiento_registro_id` y `seguro_id`. Cada cambio manda un `PATCH` de un solo campo (`exclude_unset` en el backend) y deshabilita los editores mientras guarda; la misma tarjeta muestra `HC-DEMO-ADULTO` y la edad calculada por `utils/calendarAge.ts`.

### Configuración (ADMIN)
| Vista | Ruta | Endpoints usados |
| --- | --- | --- |
| Grupos etarios | `/configuracion/grupos-etarios` | `GET` y `PUT /configuracion/grupos-etarios` (reemplaza configuración completa) |
| Usuarios (alta) | `/configuracion/usuarios` | `POST /usuarios` |

### Pendientes
- **Profesionales** y **Consultorios**: vistas placeholder (listas para implementar con los endpoints de la GUIA).
- **Auditoría**: el permiso `AUDITORIA_LEER` existe y la base registra todo, pero el backend no expone endpoint de consulta.
- **Gestión de usuarios completa**: no existe `GET /usuarios`, así que no hay listado; roles/contraseñas/baja requieren conocer el ID por otro medio.

---

## 5. Puesta en marcha

Requisitos: Node >= 22.18 y el backend corriendo (`uvicorn app.main:app --reload`).

```bash
cd frontend
npm install
npm run dev
```

- App en `http://localhost:5173` (si el puerto está ocupado, Vite usa 5174, 5175…).
- Vite reenvía `/api` al backend (`http://127.0.0.1:8000`) por proxy (`vite.config.ts`): **no hace falta configurar CORS** en desarrollo.
- Para otro host: crear `.env.local` con `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`.

> En Windows, si algo luce viejo tras cambios, hacer **Ctrl+F5** (caché del navegador).

### Scripts

| Comando | Qué hace |
| --- | --- |
| `npm run dev` | Servidor de desarrollo con recarga en caliente |
| `npm run type-check` | `vue-tsc --build` |
| `npm run build` | Type-check + build de producción |
| `npm run lint` | Oxlint + ESLint con autocorrección |
| `npm run format` | Prettier sobre `src/` |

---

## 6. Estructura

```text
src/
├── main.ts                  # bootstrap: Pinia, Router, Element Plus (es) e iconos
├── App.vue                  # <el-config-provider> es + hidratación de sesión al arrancar
├── router/index.ts          # rutas + guards de auth/permisos (lee localStorage)
├── stores/auth.ts           # sesión reactiva (token, roles, permisos, hasPermission)
├── services/
│   ├── http.ts              # axios: Bearer automático, 401 → /login, sobre de error → ApiError
│   ├── session-storage.ts   # persistencia de sesión (fuente de verdad para guards)
│   ├── auth.ts              # POST /auth/login, PUT /auth/me/password
│   ├── catalogos.ts         # los 14 catálogos tipados
│   ├── pacientes.ts         # pacientes + responsables + riesgos
│   ├── atenciones.ts        # atenciones + FUA/certificados/referencias
│   ├── configuracion.ts     # grupos etarios
│   └── usuarios.ts          # alta de usuarios
├── types/api.ts             # sobre de error, PageResponse, LoginResponse
├── utils/calendarAge.ts     # edad calendario para la ficha del paciente
├── composables/
│   ├── usePagination.ts             # limit/offset/total/has_more
│   ├── usePacienteSeleccionado.ts   # fila activa compartida tabla ↔ sidebar
│   ├── useAdmissionPatientDetails.ts # catálogos y filas de la tarjeta de admisión
│   └── useNutritionalIndicatorsPreview.ts # vista previa OMS 2006 con debounce
├── components/
│   ├── PagePlaceholder.vue          # estado vacío para vistas pendientes
│   ├── admission/                   # AdmissionPatientSummary, AdmissionHistory, AdmissionFinalActions
│   ├── patient/                     # DniSearchMatch, ResponsibleDialog, RiskDialog
│   └── patients/                    # PatientRegistrationFamilySections
├── layouts/AppLayout.vue    # sidebar por rol + header
└── views/                   # una vista por ruta
```

---

## 7. Convenciones

- **Composition API** con `<script setup lang="ts">` en todo.
- La sesión vive en `localStorage` (`ipress:session`); el guard de rutas y el cliente HTTP la leen de ahí para evitar ciclos de importación. `App.vue` hidrata el store al arrancar (cubre refresco y entrada directa por URL).
- Menú, rutas y botones se controlan por **permisos** (`auth.hasPermission`), nunca por rol escrito.
- Los errores llegan como `ApiError` con el `message` del sobre del backend: mostrar `error.message` y conservar `error.requestId` para soporte.
- Toda tabla paginada usa `limit`/`offset`/`has_more`; nunca asumir que una página incompleta es la última.
- Los catálogos paginados exigen `q` con mínimo 2 caracteres; el servicio omite `q` vacío (el backend valida `min_length=2`).
- No llamar endpoints que el rol no puede usar (ej. el ADMIN no carga atenciones en la ficha de paciente: el backend respondería 403).

---

## 8. Bugs corregidos durante el desarrollo

1. **Página en blanco en `/pacientes/:id`**: la tabla de atenciones usaba `:data="atenciones"` (el objeto de servicio) en vez de `:data="atencionesList"` → `TypeError: rows is not iterable` que tiraba todo el render. Detectado con Chrome headless + consola.
2. **Menú/botones invisibles al refrescar o entrar directo a una URL**: el store de Pinia no se hidrataba desde localStorage → se agregó `hydrateFromStorage()` en `App.vue`.
3. **403 silencioso en la ficha**: el ADMIN no debe cargar el tab de atenciones (no tiene `ATENCION_LEER`); ahora la carga se condiciona al permiso.
4. **`eslint-plugin-oxlint` desalineado con `oxlint`** en el template de create-vue → ambos fijados en `~1.82.0`.
5. **Panel “Datos del paciente” con controles de distinto ancho y filas superpuestas** en `/admision?patientId=1`: la regla de la grilla (`.patient-context__details div`) alcanzaba también al `div` raíz de `el-input`/`el-select`, que terminaba dentro de una columna de 94px, y los editores iban con `position:absolute` dentro de una fila de 26px aunque medían 32px (`el-input`) y 26px (`el-select`). Ahora la grilla se limita a `> div`, ambos wrappers comparten `--patient-context-control-height: 26px` y el editor ya no flota. En Chrome headless las 18 filas quedan en `142×26` con paso uniforme de 29px.
6. **403 al cambiar de establecimiento en admisión**: intervenía la regla RB-02 (asignación vigente en la sede destino). El backend la retiró: registrar o trasladar solo exige una sede activa y el profesional que lo hace conserva el acceso al paciente. El detalle está en [`../GUIA_FRONTEND_RUTAS.md`](../GUIA_FRONTEND_RUTAS.md#8-cambios-recientes-del-contrato).

## 9. Verificación

Última corrida sobre esta rama:

| Chequeo | Resultado |
| --- | --- |
| `npm run type-check` | ✅ sin errores |
| `npm run lint` | ✅ 0 errores (oxlint + eslint) |
| `npm run build` | ✅ |
| Render real ADMIN en `/pacientes/4` (Chrome headless + token) | ✅ 0 errores, sidebar administrativa, Editar/Dar de baja |
| Render real PROFESIONAL en `/pacientes/4` | ✅ 0 errores, sidebar clínica, sin Dar de baja |
| Render real PROFESIONAL en `/admision?patientId=1` (Chrome headless + token) | ✅ 18 filas del panel medidas en `142×26`, sin solapes |
| `GET /patients/4` contra backend | ✅ 200 con datos |
| Backend | `pytest tests/unit` 54 passed, `ruff` limpio, `alembic check` sin pendientes |

> Nota de alcance: las búsquedas de la tabla se resuelven con los parámetros que `GET /patients` expone (`historia_clinica`, `numero_documento`, `q`, `tipo_documento_codigo`, `incluir_inactivos`); la modalidad **H. Familiar** sigue deshabilitada porque el backend todavía no filtra por `historia_familiar`.