# -*- coding: utf-8 -*-
"""Genera esquema_pos_mysql.md embebiendo schema.sql y etl_mysql.py tal cual."""

from datetime import date

schema = open("schema.sql", encoding="utf-8").read().rstrip()
etl = open("etl_mysql.py", encoding="utf-8").read().rstrip()
resumen = open("dump/resumen_etl.txt", encoding="utf-8").read().rstrip()

DOC = """# De `Data_base.mdb` (Access) a MySQL limpio y normalizado

Documento único con **todo el script**: el DDL de la base destino y el ETL que la
puebla con los datos, más el diagnóstico que justifica cada decisión.

- Origen: `Data_base.mdb` — Microsoft Access, contenedor **Jet 4** (Access 2000-2003), 56,6 MiB, páginas de 4096 bytes.
- Destino: **MySQL 8** (`utf8mb4`), 26 tablas + staging, con PK/FK reales.
- Resultado de la corrida real: **1.398.187 filas** cargadas y **6.057 filas en cuarentena** (auditables, nada se borra en silencio).
- Fecha: __FECHA__

---

## 1. Diagnóstico: por qué no se puede migrar 1:1

### 1.1 Tipo de archivo

| Dato | Valor |
|---|---|
| Firma (offset 4) | `Standard Jet DB` |
| Versión JET (byte `0x14`) | `0x01` → Jet 4 (Access 2000-2003) |
| Tamaño de página | 4096 bytes → 14.497 páginas |
| Formato | binario paginado (header + páginas TDEF/DATA), no es texto ni SQL |
| Contenido | 82 tablas de usuario + 13 `MSys*` + 11 consultas + formularios/informes/módulos |

### 1.2 Problemas estructurales

| Problema | Evidencia |
|---|---|
| Sin PK/FK reales | 0 constraints en el origen; `Atencion` ni siquiera declara PK |
| Integridad rota | 91 atenciones (60 clientes) con `Idcliente` inexistente en `Pacientes` |
| Encabezado ancho ("wide table") | `Atencion.Codigo_1..15`, `Pacientes.Anexo1..25`, `Hora_1..20`, `Aspa_1..6` |
| Columnas 100% vacías | `Codigo_13/15` (Atencion), `Semana`, `Anexo8/9/19-22/24/25` (Pacientes) |
| Redundancia dentro de la fila | `Fecha_atendido` (texto dd/mm/yyyy) duplica `Fecha_atencion`; `Hora1` (HH:MM:SS) duplica `Hora2` (hora entera) |
| Catálogos fragmentados | 5 tablas de establecimientos (`EESS`, `EESS_HF`, `EESS_PS`, `EESS_PS_SESMA`, `EESS_SIS`), 3 de especialidades, 8 `Esp_*`, 8 de profesionales |
| Catálogos duplicados por versión | `Z_01`, `Z_01_2018`, `Z_01_2019` … 29 tablas de "lugar" que son el mismo catálogo en distintas vigencias |
| Configuración metida como datos | `Calibrar_2/3` (66 columnas de coordenadas de impresión), `fua/fua2/fua3`, `Impresion`, `Impresora`, `Paginas_web` |
| Tablas muertas | `Atencion_certificado`, `Atencion_fua`, `Detalle_Mujeres_Gestantes`, `Prof_Tecnico` con 0 filas |

### 1.3 Problemas de datos (lo que sospechabas: hay datos dañados y repetidos)

**a) Celdas con bytes rotos (corrupción real, no error de tipeo)**
136 celdas en `Pacientes` con texto desalineado (byte-swap), por ejemplo:

| Campo | Valores corruptos |
|---|---|
| `Sexo` | `'`䅚䕌s勾卉'`, `'blasyþab'`, `'luisyþma'`, `'o䏾䡁䕕\\ufeff'` |
| `Apellido_Materno` | `'㔶㌷㘹㌀　㠀'`, `'䅉\\ufeff䅍䥘'` |
| `Dirección` | 1.253 celdas con caracteres CJK / BOM embebido |
| `Apellidos_Nombres` | 376 celdas |

`Atencion` y `Pacientes_ref` están limpias: la corrupción se concentra en `Pacientes`.

**b) Valores centinela (placeholder) usados como dato**

| Hallazgo | Filas |
|---|---|
| `Pacientes.Fecha_inscripcion = 2016-01-01` (carga masiva, no es fecha real) | 45.891 de 73.209 (**62 %**) |
| `Pacientes.N°_DNI` vacío o nulo | 18.224 |
| DNI basura: `NN`, `nnnnnnnn`, `XXX`, `xxxxxxxx`… | 583 |
| DNI con formato != 8 dígitos (6-7 dígitos suelen ser libretas antiguas; 9+ son errores) | 967 con formato inválido + 1.872 de 6-7 dígitos |
| `Pacientes.Historia_Familiar = '-'` | 22.632 |
| `EESS.Renaes`/`Sien = '-'`, `Profesionales.Colegiatura = '-'`, `Especialidad = '.'` | 25/31, 26/37, 35/37 |
| `Anexo18 = '-'` | 5.416 |
| `Pacientes_ErroresDeExportación` (errores ya conocidos por el sistema origen) | 3 |

**c) Duplicados de identidad**

| Criterio | Grupos duplicados |
|---|---|
| `Codclie` (llave lógica) repetido | 1 caso |
| `Historia_Clinica` repetida | 42 (hasta 3 veces) |
| DNI válido (8 dígitos) repetido | 1.576 grupos |
| Mismos apellidos + nombres + fecha de nacimiento | 263 grupos |

**d) Medidas y textos mezclados**
`Edad` es texto libre (`"75 años, 8 meses y 24 días"`, 22.093 valores distintos), `PE`/`TE`/`PT` mezclan percentil, z-score y diagnóstico (`"Normal"`, `"Riesgo desnutrición global"`, `215,018.86`, `-28.2`, `539.0`), `Peso` llega a `4805` y `Talla_PG` a `1.57`, `Sistolica`/`Distolica` son texto.

**e) Catálogos que no cuadran con los datos**
`Pacientes.Localidad` tiene 209 valores distintos y **74 de ellos (66.830 filas) no existen en ningún `Z_*`**; además el 86 % de las filas usa `Distrito = 'ALTO SELVA ALEGRE'` mientras el catálogo es más granular. En 28 de los 29 `Z_*` la columna `Clave` (ubigeo) está rota o es constante (`'00000001'`, `'-'`, `'0001'`); solo `Z_01_2018`, `Z_10` y `Z_29` traen ubigeo real.

---

## 2. Decisiones acordadas

| Tema | Decisión aplicada |
|---|---|
| Identidad del paciente | **PK surrogate** (`BIGINT` autoincremento) + `legacy_codclie` conservado con `UNIQUE` |
| Datos dudosos | **Cuarentena**: se carga lo limpio y todo lo dudoso queda en `dq_rechazo` / `paciente_duplicado`. El ETL **nunca** fusiona ni borra por su cuenta |
| `Codigo_1..15` | **Explosión** a `atencion_codigo` (1 fila por prestación, con FK a `cat_prestacion` cuando el valor es catalogable) |
| `Anexo1..25` y campos anchos | Significado sin confirmar → **EAV** en `paciente_anexo` (nada se pierde y se puede borrar después) |
| Instalación de MySQL | La versión concreta queda pendiente; el DDL apunta a MySQL 8 (ver §9) |

### Reglas de limpieza implementadas

| Regla | Qué hace |
|---|---|
| `R1_CELDA_CORRUPTA` | Detecta CJK/PUA/BOM → `NULL` + registro en cuarentena |
| `R2_DNI_CENTINELA` | `NN`, `XXX`, `nnnnnnnn`… → sin documento + registro |
| `R3_DOCUMENTO_FORMATO` | No tiene 6-8 dígitos → sin documento + registro |
| `R4_HISTORIA_CLINICA_DUPLICADO` / `R5_CODCLIE_DUPLICADO` / `R6_DNI_DUPLICADO` | Genera grupos en `paciente_duplicado` (decisión manual) |
| `R8_FECHA_INVALIDA` | `(Empty Date)`, `(Invalid Date)`, futuras → `NULL` + registro |
| `R9_MEDIDA_FUERA_RANGO` | peso 0,2-300 kg, talla 20-250 cm, presión 30-300 / 20-200 → `NULL` + registro |
| `R10_SEXO_NO_MAPEABLE` | Solo `M`/`F`; lo demás `NULL` + registro |
| `R11_ETAPA_DESCONOCIDA` | `Condicion` sin clasificar |
| `R12_FECHA_INSCRIPCION_PLACEHOLDER` | Marca los 45.891 `2016-01-01` (1 fila resumen, no 45.891) |
| `R13_ATENCION_HUERFANA` | Atención sin paciente → se carga con `paciente_id NULL` (no se pierde dato clínico) |
| `R13_PACIENTE_SOLO_EN_REF` | Paciente que solo existe en `Pacientes_ref` → se crea |
| `R14_CATALOGO_NO_RESUELTO` | Nombre que no matchea catálogo → se guarda el texto crudo + registro |
| `R15_LEGADO_ERROR_EXPORTACION` | Errores que ya venían en `Pacientes_ErroresDeExportación` |
| `R16_EDAD_NO_PARSEABLE` | `Edad` que no sigue el patrón "X años, Y meses y Z días" |

---

## 3. Mapa de normalización (Access → MySQL)

| Origen Access | Destino MySQL | Nota |
|---|---|---|
| `Pacientes` | `paciente` + `paciente_anexo` | documento, fechas y sexo normalizados; 25 `Anexo*` + 11 campos anchos al EAV |
| `Atencion` | `atencion` + `atencion_codigo` | `Codigo_1..15` → 452.270 filas de prestaciones |
| `Pacientes_ref` | `referencia` + `referencia_codigo` + pacientes que solo existían ahí | |
| `EESS` + `EESS_PS` + nombres libres de los datos | `cat_establecimiento` | `origen` indica de dónde vino |
| `EESS_PS_SESMA` | `cat_eess_sesma` | padrón nacional (257) para resolver nombres |
| `Microred` | `cat_microred` | |
| `Provincia` | `cat_distrito` | ubigeo, altitud y quintil conservados |
| `Z_01`…`Z_29` + `Localidad` de los datos | `cat_lugar` | catálogo unificado con `tabla_origen`, `anio` y `clave_texto` (se conserva el ubigeo solo cuando es real) |
| `Especialidades`/`2`/`3` + `Certificado` + `Esp_*` | `cat_especialidad` | `origen` por tabla |
| `Profesionales` + `Prof_*` | `cat_profesional` | deduplicado por DNI o nombre normalizado |
| `EESS_SIS` | `cat_seguro` | está mal nombrada: es el catálogo de seguros |
| `Condicion` (14 valores) | `cat_condicion` + `etapa_vida`/`estado_gestacional` | se desdobla el concepto mezclado |
| `Certificado` | `cat_tipo_certificado` | |
| `Instituciones` | `cat_institucion` | |
| Columnas `Codigo_N` de baja cardinalidad | `cat_prestacion` (305) | columnas con ≤200 valores distintos; las de alta cardinalidad van como texto libre |
| `Calibrar`/`Calibrar_2`/`Calibrar_3` | `plantilla_impresion` (JSON) | coordenadas de impresión, **no** datos clínicos |
| `fua`/`fua2`/`fua3`/`Impresion`/`Impresora`/`Paginas_web`/`EESS_HF`/`EESS_Padron`/`Responsable` | `config_legado` (JSON) | configuración de la aplicación |
| `Detalle_Adultos`/`Mujeres_Gestantes`/`Niños` | `formato_exportacion` (JSON) | plantillas de exportación al SIS |
| `Atencion_fua`, `Atencion_certificado`, `Certificado_Nro` | `atencion_fua`, `atencion_certificado`(+`_codigo`), `certificado_correlativo` | hoy casi vacíos, quedan listos |
| las 88 tablas | `stg_*` | copia 1:1 en texto para auditoría (`--staging all`) |

---

## 4. Orden de ejecución: sí, primero las tablas y luego los datos

Respuesta corta: **sí, DDL primero** — pero el DDL solo se puede cerrar bien *después* de auditar los datos (por eso este documento arranca con el diagnóstico). El pipeline queda en este orden:

```
Fase 0  recon        leer Access, medir cardinalidades, detectar corrupción y duplicados
Fase 1  staging      copia 1:1 (auditoría: nada se pierde)
Fase 2  catálogos    dimensiones normalizadas -> ids
Fase 3  pacientes    documento/fechas/sexo normalizados + EAV de anexos + grupos de duplicados
Fase 4  atenciones   1 fila por atención + explosión de Codigo_1..15
Fase 5  formatos     referencia / fua / certificado
Fase 6  configuración plantillas y config heredada en JSON
Fase 7  calidad      dq_rechazo, paciente_duplicado, etl_run
```

Cada fase escribe su propio `.sql` y el ETL asigna **ids explícitos**, así que las FK se resuelven en Python y el orden de carga queda garantizado por el nombre del archivo.

---

## 5. `schema.sql` — DDL completo

```sql
__SCHEMA__
```

---

## 6. `etl_mysql.py` — ETL completo

Requiere solo `pip install access_parser` (no necesita driver de MySQL: genera un dump SQL ejecutable).

```python
__ETL__
```

---

## 7. Cómo ejecutarlo

```bash
# 0) dependencia (solo lee el .mdb)
pip install access_parser

# 1) generar el dump (crea ./dump, ~148 MB, tarda 2-3 min)
python etl_mysql.py --mdb Data_base.mdb --out dump

#    opciones:
#      --staging core   copia 1:1 de Pacientes, Atencion y Pacientes_ref (por defecto)
#      --staging all    copia 1:1 de las 88 tablas (auditoría total, +60 MB)
#      --staging none   sin staging (dump más liviano)
#      --limit 2000     prueba rápida con pocas filas
#
# (el dump de esta corrida se generó con --staging core: 148 MB)

# 2) validar el dump antes de cargar (aridad de cada INSERT, totales por tabla)
python validate_dump.py

# 3) cargar en MySQL 8 (el orden de archivos ya respeta las FK)
cat dump/*.sql | mysql -u root -p

# o, en Windows/Git Bash, archivo por archivo:
for f in dump/*.sql; do mysql -u root -p < "$f"; done
```

> `dump/00_schema.sql` es una copia de `schema.sql` y hace `DROP DATABASE IF EXISTS sishosp_clean`:
> **si ya tienes la base creada, borra ese archivo del dump** antes de cargar.

---

## 8. Resultado de la corrida real

Verificado con `validate_dump.py`: **3.585 sentencias INSERT** con aridad consistente,
29 tablas destino (26 del modelo + 3 de staging) y **1.398.187 filas** en total.

```
__RESUMEN__
```

### Consultas de control (deben dar estos números)

```sql
USE sishosp_clean;

SELECT COUNT(*) FROM paciente;            -- 75569  (73209 de Pacientes + 2360 solo en Pacientes_ref)
SELECT COUNT(*) FROM paciente_anexo;      -- 571714
SELECT COUNT(*) FROM atencion;            -- 59213
SELECT COUNT(*) FROM atencion WHERE paciente_id IS NULL;  -- 91 atenciones huérfanas
SELECT COUNT(*) FROM atencion_codigo;     -- 452270
SELECT COUNT(*) FROM referencia;          -- 8561
SELECT COUNT(*) FROM dq_rechazo;          -- 6057
SELECT COUNT(*) FROM paciente_duplicado;  -- 3946

-- integridad referencial: ninguna FK debe quedar colgada
SELECT COUNT(*) FROM atencion a LEFT JOIN paciente p ON p.id = a.paciente_id
 WHERE a.paciente_id IS NOT NULL AND p.id IS NULL;                 -- 0
SELECT COUNT(*) FROM atencion_codigo c LEFT JOIN atencion a ON a.id = c.atencion_id
 WHERE a.id IS NULL;                                               -- 0

-- calidad: lo que quedó pendiente de revisión humana
SELECT regla, COUNT(*) n FROM dq_rechazo GROUP BY regla ORDER BY n DESC;
SELECT criterio, COUNT(*) grupos, SUM(es_maestro) maestros FROM paciente_duplicado GROUP BY criterio;
SELECT COUNT(*) FROM paciente WHERE sexo IS NULL;            -- 9 + vacíos
SELECT COUNT(*) FROM paciente WHERE tipo_documento = 'SIN_DOCUMENTO';
SELECT COUNT(*) FROM paciente WHERE fecha_inscripcion_placeholder = 1;  -- 45891

-- negocio
SELECT MIN(fecha_atencion), MAX(fecha_atencion) FROM atencion;   -- 2025-01-02 .. 2026-09-08
SELECT c.nombre, COUNT(*) n FROM atencion a JOIN cat_consultorio c ON c.id = a.consultorio_id
 GROUP BY 1 ORDER BY n DESC;
SELECT p.codigo, COUNT(*) n FROM atencion_codigo ac JOIN cat_prestacion p ON p.id = ac.prestacion_id
 GROUP BY 1 ORDER BY n DESC LIMIT 10;
```

---

## 9. Pendientes y decisiones abiertas

1. **Significado de `Anexo1..25`** — quedó en `paciente_anexo` (EAV) a propósito. Cuando el usuario funcional confirme qué son, se convierten en columnas propias y la tabla EAV se puede tirar sin perder información.
2. **`Calibrar_2`/`Calibrar_3`** — hoy en `plantilla_impresion`; si son solo coordinadas de impresión, lo sano es sacarlas de MySQL y guardarlas como archivos de plantilla.
3. **Semántica de `PE`/`TE`/`PT`** — se guardan como `*_valor` + `*_etiqueta` sin rango porque mezclan percentil (5,56-95,32), z-score (-28,2) y diagnóstico textual. Falta definir cuál es la unidad correcta por grupo etario.
4. **`Atencion` no trae establecimiento** — `atencion.establecimiento_id` queda `NULL`. Se puede derivar de `paciente.establecimiento_id` cuando negocio lo confirme (lo dejé explícito para no inventar dato).
5. **Versión de MySQL** — el DDL asume MySQL 8 (`utf8mb4_0900_ai_ci`, `CHECK` aplicados, columna generada `STORED`, tipo `JSON`). Para MySQL 5.7 o MariaDB: cambiar la collation a `utf8mb4_unicode_ci`, y en 5.7 los `CHECK` se ignoran silenciosamente (conviene replicarlos como triggers o validaciones del ETL).
6. **Duplicados** — 3.946 filas en `paciente_duplicado` están en `decision = 'PENDIENTE'`. Ninguna se fusionó automáticamente.
7. **`Operarios`** — tiene claves en texto plano; no se versionó como tabla de usuarios. Si se va a reactivar el login, hay que hash (bcrypt/argon2) y rotar credenciales.

---

## 10. Archivos de este trabajo

| Archivo | Contenido |
|---|---|
| `esquema_pos_mysql.md` | este documento (DDL + ETL + diagnóstico) |
| `schema.sql` | DDL ejecutable (idéntico al del §5) |
| `etl_mysql.py` | ETL ejecutable (idéntico al del §6) |
| `dump/` | dump SQL generado en la corrida real (148 MB) + `resumen_etl.txt` |
| `validate_dump.py` | valida el dump (aridad de INSERT y totales por tabla) |
| `analyze_mdb.py` | inspección general del `.mdb` (tipo, esquema, relaciones) |
| `audit_data.py` / `audit_corrupt.py` | auditoría de calidad y de corrupción que respalda §1 |
| `audit_out.txt` / `audit_corrupt.txt` / `esquema_completo.txt` | salidas de esas auditorías |
| `build_doc.py` | regenera este documento embebiendo `schema.sql` y `etl_mysql.py` |

Para regenerar desde cero:

```bash
python audit_data.py && python audit_corrupt.py     # evidencia de calidad
python analyze_mdb.py                               # esquema del origen
python etl_mysql.py --out dump                      # DDL + datos limpios
python validate_dump.py                             # control de aridad y conteos
cat dump/*.sql | mysql -u root -p                   # cargar
python build_doc.py                                 # regenerar este .md
```
"""

doc = (DOC
       .replace("__FECHA__", date(2026, 9, 21).isoformat())
       .replace("__SCHEMA__", schema)
       .replace("__ETL__", etl)
       .replace("__RESUMEN__", resumen))

with open("esquema_pos_mysql.md", "w", encoding="utf-8", newline="\n") as f:
    f.write(doc)

print(f"esquema_pos_mysql.md generado: {len(doc)} caracteres, {doc.count(chr(10))} lineas")
