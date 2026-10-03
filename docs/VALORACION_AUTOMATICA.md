# Valoración nutricional automática

La admisión consulta el cálculo del servidor al cambiar paciente, fecha, peso,
talla o los datos de nacimiento/sexo del paciente guardado. La espera de 300 ms
evita consultas por cada pulsación. Los resultados anteriores se limpian al
cambiar las entradas y las respuestas atrasadas se descartan.

P/E, T/E y P/T muestran una clasificación antropométrica y su puntaje Z, en
campos de solo lectura. Presión arterial, temperatura y perímetro abdominal no
intervienen en estos indicadores.

Se conservan exactamente tres campos en el bloque original, con etiquetas fijas
P/E, T/E y P/T. Los valores no aplicables muestran «No aplica»; el IMC y la
referencia guardados no sustituyen estos campos.

| Contexto | Tres campos |
| --- | --- |
| Infantil | P/E, T/E, P/T |
| Escolar hasta 120 meses | P/E, T/E, P/T: No aplica |
| Escolar mayor de 120 meses | P/E: No aplica, T/E, P/T: No aplica |
| Adulto o adulto mayor | P/E, T/E y P/T: No aplica |
| Gestante o puérpera | P/E, T/E y P/T: No aplica |

OMS 2007 se calcula con tablas LMS oficiales almacenadas localmente, interpolando
coeficientes por edad en días/30,4375 y aplicando colas lineales más allá de ±3 Z
para peso e IMC. Rango: 61–228 meses; P/E termina en 120 meses. La librería
infantil instalada termina en 1826 días: en el intervalo hasta 61 meses solo
se ofrece IMC y un aviso de referencia no disponible, sin extrapolar puntajes.
Después de 228 meses se usa IMC adulto; desde los 60 años, umbrales MINSA de
adulto mayor (≤23 delgadez; >23 y <28 normal; ≥28 y <32 sobrepeso; ≥32 obesidad).
Gestantes usan peso previo para el IMC pregestacional (clasificación general
solo desde los 20 años); la ganancia no se clasifica sin evaluación por semana.
Puérperas muestran IMC sin clasificación automática, porque no se registra aquí
el tiempo desde el parto. Los grupos maternos tienen prioridad sobre la edad.
Los campos sin medidas suficientes y los errores de cálculo tienen estados
explícitos. La clasificación antropométrica no sustituye la evaluación clínica.

Fuente de los umbrales: tabla «Growth problems (0–5 years)», página impresa 24
de [WHO Child Growth Monitoring: A Technical Guide](https://www.emro.who.int/images/stories/nutrition/Child-growth-monitoring-a-technical-guide-for-healtcare-professionals.pdf).
Los puntos exactamente en una línea no se consideran por encima o por debajo.
P/E alto indica evaluar IMC/edad: no se etiqueta obesidad a partir de P/E.

Al crear una atención el servidor recalcula las clasificaciones con sus propias
medidas y las guarda en evaluaciones_nutricionales junto con WAZ/HAZ/WHZ y la
edad detallada. Genera esa evaluación automáticamente cuando hay indicadores,
aunque el cliente no envíe valoracion_nutricional. Los tres textos diagnósticos
enviados por un cliente no sustituyen el cálculo. Las evaluaciones históricas
existentes no se modifican. La migración 0024 añade un JSON nullable a atenciones
con la valoración calculada completa y su referencia. POST, GET y listado
devuelven ese resultado histórico; no se recalcula al cambiar la ficha.
La migración se aplicó a la base local y a la base aislada de pruebas.

Fuentes adicionales:

- [OMS 2007: indicadores y tablas](https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators).
- [Algoritmo LMS y ejemplos oficiales](https://cdn.who.int/media/docs/default-source/child-growth/growth-reference-5-19-years/computation.pdf).
- [Manual AnthroPlus: edad e interpolación](https://www.who.int/docs/default-source/child-growth/growth-reference-5-19-years/who-anthroplus-manual.pdf).
- [OMS: IMC adulto](https://www.who.int/data/nutrition/nlis/info/malnutrition-in-women).
- [MINSA: umbrales del adulto mayor](https://bvs.minsa.gob.pe/local/MINSA/7691.pdf).
- [INS: valoración de gestantes](https://alimentacionsaludable.ins.gob.pe/gestantes-y-puerperas/valoracion-nutricional).

Las seis tablas descargadas conservan URLs y SHA-256 en app/data/who2007_lms.json.
El script de importación no se ejecuta al iniciar la aplicación.

Verificación: 65 pruebas backend (incluidos ejemplos oficiales y medianas de las
792 filas LMS), 14 casos API/MySQL con siete perfiles en ambas modalidades,
10 pruebas de vista/presentación y 11 del composable. TypeScript y ESLint
verificados. Datos sintéticos exclusivamente en la base aislada para los casos
de guardado. La revisión visual del navegador quedó bloqueada por el límite de
uso del revisor automático; no se realizó una validación clínica de campo.
