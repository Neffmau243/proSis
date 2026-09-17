from datetime import date

import pytest
from pydantic import ValidationError

from app.mappers.patient import patient_update_to_entity_kwargs
from app.schemas.patient import PatientUpdate


@pytest.mark.parametrize("field", ["tipo_documento_codigo", "numero_documento", "fecha_nacimiento"])
def test_patch_can_omit_but_cannot_clear_required_columns(field: str) -> None:
    assert patient_update_to_entity_kwargs(PatientUpdate()) == {}
    with pytest.raises(ValidationError):
        PatientUpdate.model_validate({field: None})


@pytest.mark.parametrize("field", ["responsables", "riesgos", "edad_anios", "grupo_etario_codigo", "estado"])
def test_patch_rejects_child_derived_and_protected_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        PatientUpdate.model_validate({"primer_nombre": "Ana", field: None})


def test_patch_can_update_identity_residence_and_clear_optional_fields_together() -> None:
    command = PatientUpdate.model_validate({
        "primer_nombre": " Ana ",
        "fecha_nacimiento": "1990-05-10",
        "ubigeo_residencia_codigo": "040101",
        "localidad": "Centro",
        "telefono_principal": None,
    })
    assert patient_update_to_entity_kwargs(command) == {
        "primer_nombre": "Ana",
        "fecha_nacimiento": date(1990, 5, 10),
        "ubigeo_residencia_codigo": "040101",
        "localidad": "Centro",
        "telefono_principal": None,
    }
