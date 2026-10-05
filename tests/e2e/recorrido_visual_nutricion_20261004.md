# Recorrido visual de admisión y valoración nutricional

Prueba realizada en la interfaz local el 3 de octubre de 2026 y retomada el 4 de octubre, con frontend Vite y API FastAPI. Cuenta de prueba: `medico.demo`. No se usaron llamadas directas a API ni escrituras SQL para crear los casos de este recorrido.

## Resultado

Registro → admisión → cálculo → guardar → historial → apertura de FUA: comprobado en pantalla con dos pacientes ficticios. La impresión final no está validada; véanse los límites abajo.

| Caso | Paciente | Documento | Modalidad | Grupo de atención | Medidas | Resultado guardado |
|---|---|---|---|---|---|---|
| Adulto, 32 años | 15, PRUEBA FICTICIA ADULTO | Pasaporte UI261003A | Ambulatoria | Niños, adolescentes, adultos y adultos mayores | 80 kg, 180 cm; PA 120/60; PAB 90 cm | IMC 24.691, Normal; P/E, T/E y P/T No aplica, con explicación |
| Infantil, 1 año | 16, PRUEBA FICTICIA INFANTIL | DNI ficticio 99001003 | Emergencia | Niños, adolescentes, adultos y adultos mayores | 9.5 kg, 75.2 cm | IMC 16.799; P/E −0.140, T/E −0.227, P/T −0.056; los tres diagnósticos Normal |

Los dos pacientes y sus atenciones permanecen en la base local, identificados como PRUEBA FICTICIA. No se modificaron pacientes reales.

## Comprobaciones visuales

- Registro adulto, selección de sede, consultorio y profesional, edad calculada desde nacimiento y fecha de atención.
- Registro infantil rechazado sin responsable; completado correctamente con una madre ficticia.
- Ingreso de peso y talla por teclado: cálculo automático y valores visibles después de abandonar el campo.
- Borrado de talla infantil: desaparecen los puntajes anteriores y se solicita completar las medidas; al reingresar talla se recupera el cálculo.
- Guardado: aparece confirmación, se deshabilita el botón de guardar y se habilita Imprimir S.I.S.
- Historial de admisión: valores iguales a la vista previa, incluidos los tres puntajes infantiles; botón Refrescar conserva los resultados.
- Después de reiniciar frontend/API e iniciar sesión otra vez: el historial conserva la atención infantil del 03/10/2026 y sus tres puntajes.
- Historial general: filtro por paciente 16 devuelve una atención, ID 9; se abre su detalle y su FUA histórica.
- FUA adulta: identificación PAS de uso local, modalidad Ambulatoria y medidas conservadas.
- FUA infantil recuperada del historial: DNI/TDI 2, modalidad Emergencia, peso 9.5, talla 75.2 e IMC 16.8 (formato de impresión a dos decimales).

## Ajustes realizados

- Se mantienen los tres campos y columnas P/E, T/E y P/T.
- La valoración explica los límites de la referencia según edad o grupo, y presenta el IMC disponible antes de la explicación.
- El historial distingue «No aplica» de «—» y ofrece el detalle de la valoración en el IMC.
- No se modificaron fórmulas ni se extrapolaron puntajes fuera de sus referencias.

## Límites de impresión observados

- La FUA requiere confirmar una calibración física antes de habilitar «Imprimir solo datos». No se marcó esa confirmación porque no se ha realizado una prueba física.
- Se pulsó «Imprimir prueba sin datos». La pestaña del navegador integrado quedó sin responder; no se expuso un diálogo nativo de impresión accesible y no se obtuvo un PDF ni papel impreso. Se cerró esa pestaña y se continuó en otra, sin perder la atención guardada.
- La historia adulta `PRUEBA-UI-20261003` excede el ancho de la casilla FUA de ejemplo; la interfaz lo detecta y solicita ajustar ancho, paso o fuente. La historia infantil `UI26003` no presenta ese aviso.
- Los campos opcionales omitidos intencionalmente se enumeran en la FUA. No se confirmó que se completarían a mano.
- La impresión final requiere verificar salida y alineación con el navegador/impresora del usuario. No se afirma que el recorrido completo hasta papel esté aprobado.

## Observaciones de interfaz y automatización

- El método automatizado `fill` en InputNumber actualiza el cálculo pero puede dejar vacío el valor al perder foco. Se repitió la prueba con `pressSequentially` y Tab, reproduciendo escritura real: las medidas se ven y persisten correctamente. No se cambió la implementación de los campos por este artefacto de automatización.
- El historial compacto necesita desplazamiento horizontal para ver todas las columnas a 1280 px; algunos números se parten en más de una línea. No se rediseñó esa tabla.
- Estos dos recorridos no sustituyen una matriz visual exhaustiva de todos los documentos y grupos. La matriz previa de API es una comprobación distinta.

## Verificación de código

- `npm run test -- tests/nutritionalDisplay.test.ts tests/views/AdmisionView.test.ts`: 21 pruebas aprobadas.
- `npm run type-check`: aprobado.
- `npm run lint:check`: aprobado.
- `git diff --check`: sin errores de espacios.
- Detector de Impeccable sobre los tres archivos modificados: sin hallazgos.

## Evidencias

- [Adulto guardado](evidence_20261003/adulto-guardado.png)
- [FUA adulta](evidence_20261003/fua-datos-adulto.png)
- [Aviso de calibración y ancho](evidence_20261003/fua-calibracion.png)
- [Infantil guardado, ventana estrecha](evidence_20261003/infantil-guardado.png)
- [Historial infantil tras reinicio](evidence_20261003/infantil-historial-reinicio.png)
- [FUA infantil desde historial](evidence_20261003/fua-infantil-desde-historial.png)
