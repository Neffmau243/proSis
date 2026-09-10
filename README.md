# Sistema de Salud IPRESS — Backend

Backend REST para el esquema `sistema_salud_ipress`, construido con **Python 3.12**, **FastAPI**, **SQLAlchemy 2** y **MySQL 8**. La estructura conserva la separación conceptual de Spring Boot, sin trasladar mecánicamente sus convenciones a Python.

La guía de navegación propuesta, pantallas, ventanas, permisos y endpoints
para el equipo frontend está en [GUIA_FRONTEND_RUTAS.md](GUIA_FRONTEND_RUTAS.md).

## Arquitectura

El flujo de una escritura es:

```text
Router / Controller  →  Service (caso de uso)  →  Repository  →  SQLAlchemy Model  →  MySQL
        │                       │                       │
        └── Pydantic schemas ───┴── Mappers ────────────┘
```

Los modelos nunca se devuelven desde HTTP. Los routers se limitan a autenticar, validar el contrato Pydantic y llamar a un servicio. Los servicios contienen reglas, límites transaccionales y orquestación; los repositorios únicamente ejecutan persistencia y consultas.

| Concepto Spring Boot | Equivalente aquí |
| --- | --- |
| `@Entity` | Modelo ORM SQLAlchemy (`app/models`) |
| `Repository` | Repositorio SQLAlchemy (`app/repositories`) |
| DTO | Schema Pydantic (`app/schemas`) |
| Mapper | Función/clase mapper explícita (`app/mappers`) |
| `@Service` | Servicio de caso de uso (`app/services`) |
| `@RestController` | `APIRouter` de FastAPI (`app/controllers`) |
| `@ConfigurationProperties` | `pydantic-settings` (`app/core/config.py`) |
| `@ControllerAdvice` | Handlers FastAPI (`app/exceptions`) |
| JUnit / Mockito | pytest / unittest.mock |

La organización es una arquitectura por capas pragmática: carpetas transversales para hacer visibles los límites de cada capa y módulos de dominio cohesionados dentro de ellas. Las políticas puras de edad y validación clínica viven en `app/domain`, para que no dependan ni de HTTP ni de SQLAlchemy.

## Estado verificado de MySQL

La API usa directamente la MySQL configurada en .env: localhost:3306, base
sistema_salud_ipress, en modo development. Para este flujo no existe una base
alterna ni se usa TEST_DATABASE_URL.

La base está en la revisión Alembic 20260910_0006_clinical_integrity, igual al
head local. Se verificó una correspondencia 1:1 entre las 39 tablas del ORM y
las 39 tablas funcionales en MySQL; alembic_version es la única tabla técnica
adicional. No faltan tablas, columnas, índices, claves foráneas ni
restricciones clínicas.

| Dominio | Tablas MySQL |
| --- | --- |
| Catálogos | tipos_documento, sexos, seguros, especialidades, prestaciones, cie10, modalidades_atencion, grupos_etarios, grupos_riesgo |
| Organización | disa, redes, microredes, ubigeos, establecimientos, consultorios, consultorio_profesionales |
| Seguridad | profesiones, profesionales, profesional_especialidades, roles, usuarios, usuario_roles, limites_inicio_sesion, auditoria |
| Pacientes | pacientes, paciente_anexos_legacy, paciente_codigos_externos, paciente_grupos_riesgo, paciente_responsables |
| Clínica | atenciones, atencion_diagnosticos, atencion_prestaciones, evaluaciones_nutricionales, vigilancia_sien |
| Documentos | fua, certificados, certificado_prestaciones, referencias, documento_series |

~~~text
disa → redes → microredes → establecimientos → consultorios
                                           └→ pacientes → atenciones → FUA / certificado / referencia
profesionales ↔ especialidades; profesionales ↔ consultorios
usuarios ↔ roles; pacientes ↔ grupos_riesgo
~~~

La FK compuesta de certificados obliga a que el profesional firmante sea el
mismo de la atención. documento_series controla la numeración por tipo,
establecimiento y período.

## Estructura

```text
app/
├── api/                 # ensamblaje de routers
├── controllers/         # borde HTTP/FastAPI
├── core/                # settings, DB, seguridad y dependencias
├── domain/              # políticas de negocio puras
├── exceptions/          # excepciones y handlers globales
├── mappers/             # ORM -> DTO, sin serializar entidades directamente
├── models/              # mapeo SQLAlchemy completo del esquema MySQL
├── repositories/        # acceso a datos, sin reglas de negocio
├── schemas/             # contratos Pydantic de entrada/salida
├── services/            # casos de uso y transacciones
└── main.py
tests/
├── unit/
└── integration/
```

## Operaciones HTTP (54)

| Dominio | Operaciones | Éxito |
| --- | --- | --- |
| Salud | GET /health | 200 |
| Autenticación | POST /auth/login; PUT /auth/me/password | 200, 204 |
| Usuarios | POST /usuarios; PUT /usuarios/{id}/roles; PUT /usuarios/{id}/password; DELETE /usuarios/{id} | 201, 200, 204 |
| Pacientes | GET y POST /patients; GET, PATCH y DELETE /patients/{id}; responsables y riesgos POST/PATCH | 200/201 |
| Catálogos | 14 GET bajo /catalogos para identidad, clínica, establecimientos, consultorios, profesionales y ubigeos | 200 |
| Grupos etarios | GET y PUT /configuracion/grupos-etarios | 200 |
| Profesionales | GET y POST /configuracion/profesionales; GET, PATCH y DELETE /{id}; PUT /{id}/especialidades | 200/201 |
| Consultorios | GET y POST /configuracion/consultorios; GET, PATCH y DELETE /{id}; asignaciones GET, POST y PATCH de cierre | 200/201 |
| Atenciones | GET de lista, búsqueda e individual; POST de registro y anulación | 200/201 |
| Documentos | POST /documentos/fua, /certificados y /referencias | 201 |

Los contratos de entrada y salida viven en app/schemas. Toda respuesta de error
usa el sobre definido por los handlers globales e incluye X-Request-ID.

## Puesta en marcha local

1. Cree un entorno virtual e instale dependencias:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Use el `.env` existente y complete sus variables `MYSQL_*` y secretos de JWT. El flujo normal usa esa misma MySQL; no requiere un environment ni una base de pruebas aparte.
3. Inicialice la base y aplique las migraciones:

   ```powershell
   python -m app.scripts.bootstrap_database
   ```

   El comando crea la base MySQL si falta, sin borrar una existente, y ejecuta
   `alembic upgrade head`. No ejecute `schema_mysql_salud.sql`: es solo una
   referencia del diseño.
4. Cree el primer administrador (el comando solicita la contraseña sin mostrarla):

   ```powershell
   python -m app.scripts.create_admin --username admin
   ```

5. Opcionalmente cargue datos ficticios para probar todos los flujos de la API.
   Este comando es idempotente: crea solo los registros de demostración que no
   existan y no elimina ni sustituye registros existentes. Úselo únicamente en
   desarrollo local:

   ```powershell
   python -m app.scripts.seed_demo_data
   ```

   Al terminar muestra los IDs creados o verificados. La colección Postman los
   descubre automáticamente, por lo que no hace falta copiarlos a un environment.

6. Ejecute la API:

   ```powershell
   uvicorn app.main:app --reload
   ```

La documentación interactiva queda disponible en `http://127.0.0.1:8000/docs` y la especificación OpenAPI en `/openapi.json`.

## Evolución del esquema

Alembic es la única fuente ejecutable del esquema. bootstrap_database crea la
base si falta y ejecuta la migración pendiente sin borrar ni vaciar datos.
schema_mysql_salud.sql es solo una referencia de diseño y no debe ejecutarse
para inicializar la instalación.

Para una migración futura, modifique el modelo, genere una propuesta, revísela
y aplíquela:

~~~powershell
alembic revision --autogenerate -m "descripcion_del_cambio"
alembic upgrade head
alembic check
~~~

No edite revisiones que ya hayan sido aplicadas. Los datos semilla y las reglas
de negocio requieren migraciones o servicios deliberados, no autogeneración.

### Reinicio local completo

Para una instalación local que puede descartarse, detenga primero Uvicorn y
ejecute este único comando. El script elimina **solo** la base definida en
`.env`, aplica todas las migraciones y carga las semillas ficticias con cuentas
listas para Postman:

```powershell
python -m app.scripts.reset_demo_database --demo-credentials --confirm-delete
```

Las credenciales son exclusivamente para esa BD desechable: `admin` /
`IpressDev!Admin2026` y `medico.demo` / `IpressDev!Medico2026`. El script no
puede ejecutarse en producción. Si prefiere una contraseña propia, omita
`--demo-credentials` y use el modo interactivo o `--generate-password`.

No se puede ejecutar si `ENVIRONMENT=production` o `prod`. No use este comando
en una base con información real.

Para una corrida completa sobre la MySQL ya configurada use solamente
[`postman/IPRESS_API_flujo_feliz.postman_collection.json`](postman/IPRESS_API_flujo_feliz.postman_collection.json).
Cubre las 54 operaciones publicadas, genera y captura los IDs/tokens propios y
fuerza sus variables de colección para que un Environment de Postman activo no
pueda reemplazar URL, credenciales ni IDs. Antes de correrla, edite
`adminUsername` y `adminPassword` dentro de la colección si su cuenta ADMIN
local no usa las credenciales demo. No ejecute el reinicio destructivo anterior
para usar esta colección.

Las altas responden `201` y los cambios de contraseña `204`, ambos estados de
éxito; la colección valida todo el rango `2xx` y detiene la corrida al primer
error. El `PUT` de grupos etarios reenvía el estado leído para no sustituir la
configuración clínica actual. Las bajas al final son lógicas: se conservan las
atenciones, documentos y auditorías de prueba por trazabilidad.

La asignación de un consultorio se prueba en este orden: el GET de
/configuracion/consultorios/{office_id}/profesionales devuelve [] al crear un
consultorio porque todavía no existe una fila en consultorio_profesionales;
luego el POST crea el vínculo y un segundo GET verifica que el profesional
aparece. La respuesta vacía inicial es correcta, no un error.

## Roles

El sistema opera con dos roles separados por responsabilidad:

- `ADMIN`: gestiona usuarios, profesionales, consultorios, asignaciones,
  configuración y admisión de pacientes. No puede registrar/anular atenciones
  ni emitir FUA, certificados o referencias clínicas.
- `PROFESIONAL` (rol del médico o profesional de salud): debe estar vinculado
  a un profesional activo. Puede buscar y trabajar pacientes dentro de sus
  establecimientos asignados o de su relación asistencial; registra, consulta
  y anula solo sus propias atenciones, y emite documentos únicamente para
  ellas. No puede dar de baja pacientes ni administrar usuarios/configuración.

Las asignaciones vigentes de consultorio se administran por `ADMIN` y son un
requisito para registrar una atención. Los cambios de roles, la baja lógica y
un cambio/restablecimiento de contraseña se aplican inmediatamente: las
sesiones JWT anteriores quedan invalidadas cuando cambia la contraseña.

## Flujo clínico longitudinal

`pacientes` guarda identidad y datos maestros; cada `POST /atenciones` inserta
una fila nueva vinculada al paciente, con fecha, profesional, sede,
consultorio, signos vitales, edad e historia clínica de ese acto. No existe un
endpoint que sobrescriba una atención: solo puede anularse de forma lógica y
con justificación. El historial se consulta con `GET /atenciones/busqueda` o
`GET /atenciones?paciente_id=...`, limitado al ámbito asistencial del
profesional.

Los indicadores nutricionales derivados todavía requieren un protocolo clínico
versionado y aprobado por la IPRESS. Aunque el modelo conserva el histórico de
peso, talla y perímetro por atención, no debe considerarse implementada una
clasificación automática de IMC, gestación o perímetro abdominal hasta retirar
los campos derivados ingresables y conectar las reglas oficiales aprobadas.

Los rangos etarios se conservan internamente en meses completos para la
precisión clínica, pero el API devuelve además `edad_minima`, `edad_maxima` y
`rango_edad_legible` en años y meses para que el frontend los muestre sin hacer
conversiones propias.

## Reglas que protege el backend

- Las credenciales se almacenan únicamente como hashes bcrypt y los roles se validan por acción.
- En producción se rechazan secretos JWT plantilla; las semillas ficticias se bloquean fuera de `ENVIRONMENT=development`.
- Los inicios de sesión quedan auditados sin almacenar contraseñas, usan límite persistente por huella HMAC y bloqueo progresivo de cuenta.
- Un usuario cambia su propia contraseña con la clave actual; `ADMIN` puede restablecer otra cuenta activa. Nunca se permite retirar el último `ADMIN` activo.
- Un menor requiere responsable activo; solo puede tener uno principal activo.
- El documento de identidad es único, se valida fecha de nacimiento y se comprueba que los catálogos estén activos.
- Los periodos de riesgo no se pueden solapar.
- Los grupos etarios se configuran sin solapes y se resuelven en el servidor; el cliente no puede imponerlos.
- Una atención valida paciente, ámbito, consultorio, sede, profesional, especialidad, vigencia y signos clínicos antes de grabarse; su anulación es lógica, auditada y se bloquea si conserva documentos vigentes.
- La emisión de FUA se pre-valida y se mantiene la garantía única de MySQL. Las operaciones relevantes incluyen su auditoría dentro de la misma transacción.

Los rangos clínicos y las políticas de numeración son configurables o puertos explícitos, no constantes de SQL. Las reglas detalladas se consolidan a continuación.

## Reglas funcionales detalladas

### RB-01: autenticación y autorización

- Las contraseñas se comparan con bcrypt; nunca se almacenan ni devuelven en
  texto plano.
- Solo ADMIN crea, desactiva o asigna roles. Un PROFESIONAL activo y vinculado
  opera exclusivamente su atención y documentos.
- Cada token se contrasta con usuario activo, roles y versión de credenciales.
  El cambio o restablecimiento de contraseña invalida sesiones anteriores.
- El login tiene límite persistente, bloqueo progresivo y auditoría sin
  contraseña ni IP en claro. No se puede desactivar ni quitar el rol al último
  ADMIN activo.

### RB-02: pacientes y responsables

- La combinación tipo de documento y número de documento es única; la fecha de
  nacimiento no puede ser futura y los catálogos deben existir y estar activos.
- Un menor requiere al menos un responsable activo y solo puede tener un
  responsable principal activo. Los parentescos admitidos son madre, padre y
  tutor.
- Un PROFESIONAL solo puede leer o editar pacientes de su ámbito asistencial o
  con relación clínica propia. Los períodos del mismo grupo de riesgo no pueden
  superponerse.

### RB-03: grupos etarios

- La unidad canónica es mes completo. Todo grupo activo necesita edad mínima,
  no puede haber solapes, solo uno puede quedar sin máximo y la cobertura
  continua se valida cuando la IPRESS la exige.
- Al crear una atención, el servidor calcula el grupo por fecha de nacimiento
  y fecha de atención. El cliente nunca impone el grupo etario.

### RB-04: consultorios y profesionales

- El consultorio y el profesional deben estar activos; el consultorio pertenece
  al mismo establecimiento de la atención.
- Debe existir una asignación vigente en consultorio_profesionales para la
  fecha de atención. Si el consultorio exige especialidad, el profesional debe
  tenerla.
- Solo puede existir un responsable vigente por consultorio. La asignación
  nueva no puede solaparse con otra del mismo profesional y consultorio.

### RB-05: atención clínica

- La atención valida paciente, sede, profesional, consultorio, modalidad,
  especialidad, grupo etario, asignación y signos vitales antes de confirmar.
- Peso, talla, perímetro y edad son una foto histórica de la atención; las
  clasificaciones nutricionales derivadas requieren un protocolo clínico
  versionado y aprobado.
- Las atenciones no se eliminan físicamente. La anulación exige justificación,
  auditoría y se bloquea si existen documentos vigentes.

### RB-06: documentos clínicos

- Solo el propietario profesional de una atención atendida puede emitir FUA,
  certificado o referencia.
- FUA es único por atención. Las series de FUA y certificados se reservan
  dentro de la misma transacción.
- Un certificado debe estar firmado por el profesional de su atención; una
  referencia debe tener origen, destino, tipo, motivo y estado válidos.

### RB-07: transacciones y auditoría

- Toda escritura relevante valida, persiste y audita antes de confirmar la
  transacción. Un fallo hace rollback.
- auditoria guarda actor, acción, fecha, registro y foto antes/después, sin
  password_hash ni secretos.
- Pacientes, usuarios, profesionales, consultorios y documentos usan bajas
  lógicas cuando aplica; no se hace DELETE físico sobre el historial clínico.

## Pruebas

```powershell
pytest
python -m ruff check app tests migrations --select F
```

> **Windows con Git Bash:** MSYS convierte valores que parecen rutas en las
> variables de entorno, por lo que `API_V1_PREFIX=/api/v1` llega a Python como
> `C:/Program Files/Git/api/v1` y la suite no recolecta. Use PowerShell, o desde
> Git Bash exporte `MSYS2_ENV_CONV_EXCL='API_V1_PREFIX'` antes de ejecutar
> `pytest`.

Las pruebas unitarias no requieren MySQL. Las pruebas de integración se habilitan al definir `TEST_DATABASE_URL` contra una base MySQL desechable; no se ejecutan contra la base productiva.
