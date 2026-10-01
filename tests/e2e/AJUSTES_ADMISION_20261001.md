# Validaciones de admisión — 01/10/2026

## Resultado

- Documento: se valida la pareja tipo/número al crear y al modificar cualquiera de sus partes. Un PATCH solo de tipo usa el número almacenado, no evade la validación. Los ceros iniciales se conservan.
- DNI: exactamente 8 dígitos ASCII. CE/PAS: entre 1 y 30 letras ASCII o dígitos, sin espacios. DE/OTRO: hasta 30 caracteres, letras/dígitos y separadores `. / -`, empezando por letra o dígito. Los documentos extranjeros mantienen el límite existente; estas reglas de captura no verifican identidad ni afirman un formato universal por país.
- Un documento legado inválido no se reescribe ni bloquea correcciones de campos ajenos a la identidad. Se revalida al editar tipo o número.
- Seguro: al cambiar fuera del régimen SIS o quitar el seguro se limpian DIRESA, tipo, número y secuencia. La etnia no se borra. La limpieza queda en la auditoría de la misma transacción. Volver a SIS no resucita afiliaciones antiguas.
- Un alta no SIS con afiliación o un PATCH que intenta añadir afiliación sin SIS se rechazan. Un PATCH explícito de seguro a no SIS limpia la afiliación incluso si un cliente antiguo la reenvía.
- Nueva FUA: solo copia afiliación de un seguro SIS, incluso ante datos residuales legados. Las FUA históricas permanecen inmutables.
- Embarazo: el servidor rechaza tipo de embarazo, peso pregestacional, FPP y edad gestacional de la valoración nutricional si el grupo no es GESTANTES. No añade requisitos clínicos de edad o sexo ni obliga a completar todos los datos de una gestante.

## TDI / ETLSIS: pendiente de equivalencia, no migrado

Se revisaron el esquema del MDB y el manifiesto de las 82 tablas de `etlSis/private/ace-source`. Se recorrieron únicamente categorías documentales/anexos con salida agregada y redactada; no se exportaron identidades.

- No se encontró una tabla explícita de equivalencias PAS/DE/OTRO → TDI SIS.
- `Detalle_Adultos.TipoDocumento`: dos filas DNI. `Detalle_Niños.TipoDocumento`: cuatro filas DNI. `Detalle_Mujeres_Gestantes`: sin filas.
- `Atencion_fua`: sin filas; no proporciona una correspondencia documental.
- `Pacientes.Anexo4` contiene códigos 1–4 sin etiquetas suficientes para atribuirles un significado TDI. No se migraron como equivalencias por suposición.
- No se pudieron recuperar definiciones de consultas de Access: la conexión de metadatos ACE no respondió y el lector alternativo no expone MSysQueries. Por tanto, no se descarta una regla alojada fuera de las tablas exportadas, en consultas o en el programa original.

La impresión ahora muestra un error y bloquea PAS/DE/OTRO o una pareja tipo/TDI incoherente. Registro del paciente y atención siguen disponibles, con identificación conservada en el JSON y visible en el resumen. Esto es una contención, **no la habilitación de impresión de esos documentos**. Para completarla se necesita una equivalencia oficial verificable; no se generó una migración vacía ni con códigos inventados.

Referencias: [DNI de ocho dígitos](https://www.gob.pe/13432-encontrar-d-gito-verificador-en-el-dni); referencia FUA del proyecto en [FUA_IMPRESION.md](../../docs/FUA_IMPRESION.md). No se equipararon códigos SUNAT con códigos SIS.

## Verificación

Entorno independiente `ipress_test_admission_20261001_fixes`, API 8001 y Vite 5174. La base habitual no se utilizó para escrituras. Se conservan cinco pacientes ficticios y trece atenciones del ejercicio HTTP, además del cambio de seguro probado desde la interfaz.

- **237 pruebas unitarias de backend** correctas.
- **206 pruebas frontend** correctas, incluidos formularios montados con Element Plus, cambio de tipo de documento y borrado de los cuatro campos SIS.
- **124 comprobaciones HTTP/MySQL** correctas: altas de niños con responsable, adultos y mayores; cinco tipos de documento; once seguros; dos modalidades y tres grupos; rechazos 422; PATCH parcial y conjunto; persistencia recuperada; FUA histórica inmutable. Las semanas de gestación anidadas se cubrieron posteriormente con pruebas unitarias, no con esta corrida HTTP.
- Type-check, build y ESLint de los archivos funcionales modificados correctos. Ruff de los módulos de documento/seguro, servicios modificados y nuevas pruebas unitarias correcto. Persisten avisos generales de dependencias y tamaño del bundle; no se cambiaron para este alcance.
- Navegador contra API real: rechazo visible de DNI/PASUI000033; SIS → SIN SEGURO, campos vacíos/deshabilitados y guardado confirmado tras recargar; detalle de atención OTRO con identidad visible y botón de impresión bloqueado.
- No se realizó impresión física, validación con RENIEC/Migraciones ni envío/acreditación SIS.

## Reproducción

1. `python tests/e2e/audit_admission.py setup ipress_test_admission_<sufijo_nuevo>`: exige una base nueva local; nunca reutiliza ni borra una existente.
2. `python tests/e2e/audit_admission.py serve ipress_test_admission_<sufijo_nuevo>`.
3. `python tests/e2e/verify_admission_fixes.py ipress_test_admission_<sufijo_nuevo>`: usar una vez sobre ese entorno nuevo. Guarda el resultado JSON junto al script.
4. Para navegador, ejecutar Vite con `tests/vite.audit.config.ts` y `VITE_API_BASE_URL=/api/v1`.

Los servidores auxiliares se detienen al cerrar la revisión; los datos ficticios se retienen para inspección. Los cambios de código no requieren migración de esquema ni reescritura masiva de pacientes.
