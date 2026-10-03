# Verificación de admisión — 3 de octubre de 2026

Resultado: **212/212 escenarios de API y MySQL**, sin fallos en la ejecución final.
Además: **105/105 pruebas unitarias** de nutrición, validación y atención.

## Combinaciones

| Tipo de documento | Ambulatoria | Emergencia | Total con medidas completas |
| --- | ---: | ---: | ---: |
| CE | 14 | 14 | 28 |
| DE | 14 | 14 | 28 |
| DNI | 14 | 14 | 28 |
| OTRO | 14 | 14 | 28 |
| PAS | 14 | 14 | 28 |
| Total | 70 | 70 | 140 |

Cada documento y modalidad se cruzó con:

- Grupo general: pacientes de 1, 8, 14, 32 y 76 años; sexo femenino y masculino.
- Gestantes: pacientes femeninas de 16 y 32 años, con peso pregestacional.
- Puérperas: pacientes femeninas de 16 y 32 años.

Para cada atención se compararon vista previa, creación, consulta individual,
historial, persistencia MySQL y copia de datos para imprimir el FUA. El IMC se
contrastó con el cálculo independiente peso/(talla en metros)². Se comprobó que
el documento y la modalidad no alteran el resultado nutricional, y que el FUA
conserva documento, modalidad, grupo e IMC. El FUA convierte su texto a mayúsculas.

Adicionalmente se verificaron 60 combinaciones con peso o talla faltante y 12
rechazos de entradas inválidas: medidas cero, fuera del protocolo configurado,
peso pregestacional en grupo general y grupo inexistente.

## Correcciones encontradas durante las pruebas

- La vista previa ahora utiliza el mismo protocolo de validación de peso y talla
  que el guardado. Antes aceptaba 501 kg o 301 cm, aunque el guardado los rechazaba.
- La vista previa rechaza peso pregestacional fuera del grupo Gestantes, igual
  que el guardado de la atención.

## Alcance y pendiente

Se usó la base separada `ipress_test_admission_20261003_matrix` con pacientes
ficticios; se conservaron los datos de prueba. No se modificaron pacientes de la
base de trabajo del usuario. No se ejecutó una comprobación visual en navegador.

Estas pruebas verifican las referencias nutricionales implementadas. **No se
habilitó la extrapolación de P/E, T/E y P/T a todas las edades**: falta definir una
fórmula o tabla alternativa. Los resultados no aplicables continúan como tales.

Evidencia detallada: [JSON de resultados](ipress_test_admission_20261003_matrix_matrix.json).
Script reproducible: [verify_admission_matrix.py](verify_admission_matrix.py).

```powershell
.venv/Scripts/python.exe tests/e2e/verify_admission_matrix.py ipress_test_admission_20261003_matrix
.venv/Scripts/python.exe -m pytest tests/unit/test_nutrition_preview_validation.py tests/unit/test_attention_service.py tests/unit/test_admission_validation_regression.py tests/unit/domain/test_nutrition.py tests/unit/domain/test_growth_reference.py -q --no-cov -p no:cacheprovider
```

La repetición agrega un nuevo conjunto ficticio, sin reiniciar ni borrar la base.
La ejecución unitaria es dirigida y no mide cobertura global.
