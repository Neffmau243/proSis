# Análisis de migraciones y preparación de despliegue

Fecha de revisión: 26 de septiembre de 2026.

## Resumen ejecutivo

El proyecto usa **Alembic**, **SQLAlchemy 2** y **MySQL 8** para controlar la evolución del esquema. La cadena de migraciones es lineal, tiene un único head y la base configurada se encuentra actualizada en ese head.

~~~
20260926_0022_specialty_codes (head)
~~~

La comprobación <code>alembic check</code> no detectó diferencias entre los modelos ORM y la base configurada. Además, el 26/09/2026 se ejecutó <code>alembic upgrade head</code> correctamente. Como la base ya estaba en el head, no tuvo cambios pendientes que aplicar.

La parte técnica de Alembic es buena. El punto que debe corregirse es separar la estructura de la base de los datos reales de personas y pacientes.

| Clase de dato | Lugar correcto | Ejemplos |
| --- | --- | --- |
| Estructura | Migraciones Alembic | tablas, índices, FK, columnas, restricciones |
| Catálogos oficiales estables | Migración o bootstrap de referencia | tipos de documento, etnias, modalidades |
| Datos de demostración | Semillas solo de desarrollo | pacientes ficticios y cuentas demo |
| Datos reales y clínicos | Importador seguro o administración | pacientes, personal, cuentas, atenciones |

Los datos reales no deben estar incluidos en código versionado ni replicarse automáticamente en cada entorno.

## Estado actual de Alembic

Las revisiones están encadenadas de forma lineal, sin ramas ni heads múltiples:

~~~
0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008 → 0009 → 0010
     → 0011 → 0012 → 0013 → 0014 → 0015 → 0016 → 0017 → 0018 → 0019
     → 0020 → 0021 → 0022 (head)
~~~

| Verificación | Resultado observado |
| --- | --- |
| <code>alembic heads</code> | Un solo head: <code>20260926_0022_specialty_codes</code> |
| <code>alembic current</code> | La base configurada está en el head |
| <code>alembic check</code> | No detectó operaciones de upgrade pendientes entre ORM y BD |
| <code>alembic upgrade head</code> | Ejecutado correctamente el 26/09/2026; no había revisiones pendientes |
| Pruebas unitarias | 174 pasaron con <code>--no-cov</code> |

La prueba de integración completa no se ejecutó en esta estación porque no está definida <code>TEST_DATABASE_URL</code>. La CI sí define una MySQL 8 desechable y ejecuta migraciones contra ella.

## Qué contiene cada bloque de revisiones

| Revisiones | Propósito principal |
| --- | --- |
| 0001–0002 | Esquema inicial IPRESS, catálogos básicos y series de documentos |
| 0003–0006 | Rangos etarios, roles, seguridad e integridad clínica |
| 0007–0014 | Nutrición, profesional, localidad, grupo de atención, embarazo y FUA |
| 0015 | Datos SIS de pacientes, etnias y campos de impresión |
| 0016 | Archivo de registros históricos del sistema legado |
| 0017–0019 | Planes de seguro, localidades SIS y establecimientos oficiales |
| 0020–0021 | Catálogos operativos, especialidades, oficinas, profesiones y profesionales |
| 0022 | Normalización a mayúsculas de códigos de especialidad |

Varias revisiones inspeccionan MySQL antes de crear columnas, índices o claves foráneas. Es adecuado porque MySQL no hace DDL transaccional: una interrupción puede dejar una revisión aplicada parcialmente. Las guardas ayudan a reintentar sin recrear objetos ya existentes.

La revisión 0015, por ejemplo, contempla una columna de etnia con una collation incompatible tras una interrupción. Es una buena práctica específica para MySQL.

## Qué hace <code>alembic upgrade head</code>

El comando ejecuta únicamente las revisiones faltantes entre la versión almacenada en <code>alembic_version</code> y el head del código.

### En la base actual

La base ya estaba en 0022. Volver a ejecutar el comando fue seguro e idempotente: Alembic verificó la versión y no aplicó DDL ni inserciones nuevas.

### En una base vacía

El comando crea el esquema completo y carga los datos presentes en las migraciones, incluidos catálogos, localidades, establecimientos, especialidades, consultorios, profesiones y profesionales.

No crea automáticamente:

- El primer administrador.
- Cuentas clínicas demo.
- Pacientes ficticios.
- Pacientes reales manejados por scripts de desarrollo.

Esas operaciones viven en <code>app/scripts/</code>, no en Alembic.

### En una base antigua

El upgrade puede transformar datos además del esquema. Existen cambios de roles, normalización de códigos de especialidad y ajustes de estados históricos. Por eso no se debe ejecutar por primera vez sobre producción sin backup, staging y una ventana de despliegue.

Antes de actualizar una base antigua:

~~~powershell
alembic current
alembic heads
alembic check
~~~

Después de validar staging:

~~~powershell
alembic upgrade head
alembic current
~~~

## Política de rollback

No todas las revisiones eliminan sus datos durante <code>downgrade()</code>. Algunas expresan la decisión de no borrar establecimientos, profesionales o catálogos que podrían estar referenciados por registros clínicos.

Esto es aceptable como una política **forward-only**: se corrige un error publicando una revisión nueva hacia delante en vez de borrar datos válidos. Debe formalizarse como una política del equipo.

Consecuencias:

- No prometer que cualquier <code>alembic downgrade</code> restaure exactamente todos los datos históricos.
- Tomar backup antes de cambios de alto impacto.
- Probar todo upgrade en staging o una copia de producción.
- Corregir mediante una nueva migración; nunca editar una revisión ya aplicada.

## Datos reales y datos demo

Este es el hallazgo de mayor prioridad.

El repositorio contiene información real del origen dentro de scripts de desarrollo y algunas migraciones incorporan información de personal real. Que el archivo Access original esté ignorado por Git no es suficiente: los datos copiados a archivos Python rastreados siguen presentes en el árbol e historial Git.

Riesgos:

- Una instalación nueva recibe información real sin que el operador lo decida.
- CI, staging y estaciones de desarrollo pueden replicar información personal innecesariamente.
- Eliminar los datos con una revisión futura no los elimina del historial Git.
- Los datos clínicos y de identidad requieren retención, autorización y controles de acceso institucionales.

Acciones recomendadas:

1. No agregar más pacientes, DNI, cuentas, atenciones o profesionales reales a código ni migraciones.
2. Mover los datos reales a una fuente segura con acceso limitado.
3. Crear un importador operativo con huella de origen, validaciones y conciliación.
4. Planificar con seguridad y datos la limpieza del historial Git. No reescribir historia compartida sin coordinación.
5. Mantener los datos demo como registros completamente ficticios y protegidos por <code>ENVIRONMENT=development</code>.

## Decisión sobre <code>etlSis/</code>

El directorio <code>etlSis/</code> no es dependencia de ejecución de la API ni de las migraciones Alembic actuales. El backend usa el esquema creado por <code>migrations/</code>.

Además, <code>etlSis/schema.sql</code> crea otra base llamada <code>sishosp_clean</code>, con tablas y nombres distintos. Incluye <code>DROP DATABASE IF EXISTS</code>; nunca debe ser parte de un despliegue de la API actual.

Por tanto, retirar <code>etlSis/</code> no debería afectar:

~~~powershell
alembic upgrade head
~~~

Antes de retirarlo:

- Actualizar README y documentos que lo mencionen.
- Conservar fuera del repositorio y con acceso restringido cualquier evidencia que la institución deba retener.
- Decidir si alguna regla de limpieza debe reimplementarse en el futuro importador oficial.

No se debe usar ese dump como ruta alternativa para poblar la base de la API.

## ¿Conviene una supermigración?

No para bases que ya existen o han sido compartidas. La historia tiene 22 revisiones: el costo de ejecutarlas sobre una base vacía es pequeño frente al riesgo de perder trazabilidad.

| Situación | Recomendación |
| --- | --- |
| Base existente en cualquier revisión | Mantener historia y agregar migraciones incrementales |
| Base productiva | Migraciones pequeñas, forward-only, backup y staging |
| Proyecto totalmente preproducción y bases descartables | Se puede crear un baseline nuevo y reconstruir entornos |
| Migración Access a la web | Importador ETL separado; no Alembic |

Un baseline único solo tendría sentido si se confirma que ninguna base debe conservar la historia 0001–0022. En ese caso se reconstruyen los entornos coordinadamente. No se deben borrar o editar revisiones ya aplicadas de forma aislada.

## Diseño objetivo para importar datos reales

La importación de datos debe ser un caso de uso separado del despliegue:

~~~
Archivo autorizado
       ↓
Validación y huella del origen
       ↓
Staging / archivo de registros originales
       ↓
Transformación por lotes y reglas explícitas
       ↓
Cuadratura: conteos, FK, duplicados y errores
       ↓
Revisión humana de cuarentena
       ↓
Confirmación y auditoría de importación
~~~

Requisitos mínimos:

- Modo simulación antes de escribir.
- Huella del archivo origen para impedir importaciones duplicadas.
- Operaciones idempotentes y por lotes.
- Cuarentena de registros ambiguos; nunca inventar valores clínicos.
- Logs sin secretos ni datos sensibles innecesarios.
- Reporte de filas leídas, aceptadas, actualizadas, rechazadas y pendientes.
- Pruebas contra MySQL desechable.
- Autorización explícita antes de importar a producción.

## Entrega a DevOps

El proyecto puede desplegarse técnicamente, pero el handoff debe incluir un runbook y no solo el repositorio.

### Infraestructura requerida

- MySQL 8 con <code>utf8mb4</code> y backups.
- Usuario de aplicación con privilegios mínimos.
- Job de migración separado con permisos DDL; no ejecutar Alembic desde cada réplica de API.
- Secretos inyectados por el gestor de secretos de la plataforma.
- TLS, red privada hacia MySQL y CORS limitado a dominios autorizados.
- Reverse proxy o ingress, logs centralizados y monitoreo de <code>/api/v1/health</code>.

### Variables fuera de Git

~~~text
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=...
SECRET_KEY=<secreto único de al menos 32 caracteres>
JWT_ISSUER=...
JWT_AUDIENCE=...
CORS_ORIGINS=["https://dominio-autorizado"]
~~~

No reutilizar claves, usuarios ni contraseñas demo fuera de un entorno local descartable.

### Secuencia sugerida

1. Crear backup y confirmar el destino.
2. Ejecutar una sola vez <code>alembic upgrade head</code>.
3. Confirmar <code>alembic current</code>.
4. Desplegar la API.
5. Verificar <code>/api/v1/health</code> y OpenAPI.
6. Crear el administrador inicial mediante un canal seguro.
7. No ejecutar <code>reset_demo_database</code> ni <code>seed_demo_data</code> en producción.

## Deuda técnica relacionada

| Prioridad | Hallazgo | Acción |
| --- | --- | --- |
| Crítica | Datos personales reales en código y migraciones | Retirar del repositorio y crear importación segura |
| Alta | ETL antiguo no coincide con esquema web | Retirarlo o archivarlo; no usarlo para desplegar |
| Alta | Documentación menciona head 0010 aunque el real es 0022 | Actualizar README y guía de rutas |
| Media | Ruff completo informa 392 hallazgos; CI solo valida F | Alinear CI o corregir gradualmente |
| Media | CI no ejecuta explícitamente <code>alembic check</code> | Agregarlo al job de calidad |
| Media | Dependencias Python sin lockfile | Fijar dependencias o imagen reproducible |
| Media | Servicios grandes, especialmente pacientes | Dividir por casos de uso |
| Media | Historial de atenciones por paciente no paginado | Aplicar paginación |
| Media | Roles ADMIN + PROFESIONAL tienen conflicto de alcance | Corregir precedencia y añadir pruebas |

## Comandos de operación seguros

Desde la raíz y usando el entorno virtual del proyecto:

~~~powershell
# Versión de la base elegida por .env
.\.venv\Scripts\alembic.exe current

# Verificar que solo existe un head
.\.venv\Scripts\alembic.exe heads

# Comparar ORM y base sin aplicar DDL
.\.venv\Scripts\alembic.exe check

# Aplicar solamente revisiones pendientes
.\.venv\Scripts\alembic.exe upgrade head
~~~

Para ejecutar las pruebas unitarias cuando no existe una MySQL de pruebas:

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests/unit --no-cov
~~~

La suite completa exige <code>TEST_DATABASE_URL</code> apuntando a una MySQL desechable cuyo nombre contenga <code>test</code>. Nunca debe apuntar a una base de desarrollo o producción.

## Decisiones pendientes del equipo

1. Confirmar qué catálogos son oficiales, estables y aptos para versionarse.
2. Confirmar que profesionales, cuentas y pacientes reales saldrán del código.
3. Definir quién aprueba una importación y cómo se conserva la fuente.
4. Decidir si el proyecto sigue en preproducción o si la historia Alembic ya es contrato de despliegue.
5. Preparar artefactos de despliegue y runbook para DevOps.

## Conclusión

Alembic está funcional y el <code>upgrade head</code> actual es seguro para la base configurada. No hace falta una supermigración para llevar el proyecto a web: la API ya tiene su propio esquema y sus revisiones.

El siguiente paso correcto es separar esquema y datos reales, retirar el ETL incompatible y completar seguridad, CI y despliegue para DevOps.

