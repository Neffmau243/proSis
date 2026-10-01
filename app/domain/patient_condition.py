"""Las nueve etiquetas de Condicion encontradas en el catálogo ETLSIS.

Son etiquetas del registro, no diagnósticos ni el grupo clínico de una atención.
La restricción se aplica a nuevas escrituras; no modifica el texto histórico.
"""

from typing import Annotated, Any, Literal, get_args
from unicodedata import normalize

from pydantic import BeforeValidator


PatientConditionLabel = Literal[
    "ADULTO",
    "ADOLESCENTE",
    "NIÑO",
    "JOVEN",
    "PUERPERA",
    "RECIEN NACIDO",
    "ADULTO MAYOR",
    "GESTANTE",
    "NO GESTANTE",
]
PATIENT_CONDITIONS = get_args(PatientConditionLabel)


def _comparison_key(value: str) -> str:
    return "".join(
        char for char in normalize("NFD", " ".join(value.upper().split()))
        if not 0x0300 <= ord(char) <= 0x036F
    )


def normalize_patient_condition(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    if not value.strip():
        return None
    for condition in PATIENT_CONDITIONS:
        if _comparison_key(value) == _comparison_key(condition):
            return condition
    raise ValueError("Seleccione una condición del catálogo ETLSIS.")


PatientCondition = Annotated[PatientConditionLabel | None, BeforeValidator(normalize_patient_condition)]
