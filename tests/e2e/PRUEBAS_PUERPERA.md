# Pruebas focalizadas: Puérperas

## Actualización: sincronización implementada

Al guardar una atención GESTANTES/PUERPERAS, el backend actualiza la ficha a GESTANTE/PUERPERA dentro de la misma transacción y bajo el bloqueo del paciente. Cada cambio efectivo se audita con condición anterior, nueva e ID de atención. El grupo general conserva la condición existente. No se reescriben atenciones anteriores ni se revierte la condición al anular una atención.

La interfaz refresca la ficha desde el servidor después de confirmar la atención. Un error del refresco muestra aviso, sin habilitar otro POST ni presentar como fallido el guardado ya confirmado. Los borradores de paciente pendientes se preservan.

Regresión: 237 pruebas unitarias de backend y 211 de frontend correctas. Las pruebas nuevas comprueban actualización visible, conservación del borrador, rechazo del POST sin cambio de condición y fallo del GET posterior sin duplicar la atención.

Verificación actual: **39 comprobaciones API/MySQL correctas**, incluida inyección de un fallo tras preparar la sincronización para verificar rollback conjunto de atención, condición y auditoría. Paciente ficticia ID 7; atenciones 17–20. Resultado en `puerpera_sync_results.json`. No requiere migración ni modifica pacientes de la base habitual. El informe de abajo corresponde al comportamiento previo y conserva el hallazgo que motivó este cambio.

## Revisión anterior (antes de implementar la sincronización)

Fecha: 01/10/2026. No se modificó código funcional ni pacientes de la base habitual.

## Ejecución

- `verify_puerpera.py ipress_test_admission_20261001_fixes`: **31 comprobaciones correctas**. FastAPI TestClient invoca las rutas reales con autenticación y MySQL aislado; no se simula el repositorio. No es una corrida de navegador.
- Vue/Vitest: `AdmisionView.test.ts` y `fuaPrint.test.ts`: **14 pruebas correctas**. Incluyen formulario montado con Element Plus y API simulada; el cambio Gestantes → Puérperas se envía en emergencia sin peso pregestacional ni FPP.
- Ejecución directa de `fuaValues`: **12 aserciones correctas**, en ambulatoria/emergencia. Marca Puérpera = X, Gestante vacía, fecha probable de parto vacía y modalidad correcta. No se imprimió físicamente.
- Contrato de embarazo: **12 pruebas parametrizadas correctas**, incluidos los cuatro campos obstétricos rechazados para Puérperas y grupo general, y admitidos para Gestantes.

## Caso persistido

Paciente ficticia ID 6, adulta, sexo F. Atención gestante histórica ID 14; nuevas atenciones de Puérperas ID 15 (ambulatoria) y 16 (emergencia). Los resultados están en `puerpera_results.json`.

Se comprobó POST → GET → MySQL y la copia FUA. Los ocho intentos con datos obstétricos incompatibles devolvieron 422 sin crear atenciones adicionales. La atención gestante anterior y su FUA quedaron intactas.

## Puntos pendientes de definición funcional

1. **Condición de ficha y grupo de atención son independientes.** Tras guardar Puérperas, una ficha con GESTANTE sigue diciendo GESTANTE. El PATCH explícito a PUERPERA sí funciona y se recupera correctamente. Si se desea sincronización o aviso de discrepancia, requiere definir e implementar esa regla; no se cambió durante esta revisión.
2. **No se calcula el puerperio desde la fecha real de parto.** El modelo revisado almacena FPP, pero no fecha real de parto ni días posparto. Puérperas es una selección manual del profesional, no una confirmación clínica automática. No se añadieron umbrales médicos ni reglas de elegibilidad.

Repetir el script crea otra paciente ficticia y tres atenciones dentro de la base aislada; nunca borra las anteriores. La numeración de documento de prueba incluye la hora: evitar ejecutarlo dos veces en el mismo segundo.
