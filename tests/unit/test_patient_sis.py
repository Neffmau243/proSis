import importlib.util
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models import Patient
from app.schemas.patient import PatientCreate, PatientUpdate
from app.schemas.patient_sis import PatientSisFields, affiliation_problem
from app.mappers.patient import patient_update_to_entity_kwargs


@pytest.mark.parametrize("value", [
    {"sis_diresa": "01"}, {"sis_tipo": "ABC"}, {"sis_numero": "1234567"},
    {"sis_numero": "1234567890"}, {"sis_numero": "AB123456"}, {"sis_numero": 12345678},
    {"sis_secuencia": "RN"}, {"sis_secuencia": "123"}, {"etnia_codigo": "mestizo"},
])
def test_invalid_master_lengths_or_number_types_are_rejected(value):
    with pytest.raises(ValidationError):
        PatientSisFields(**value)


def test_master_data_preserves_zeroes_normalizes_codes_and_patch_semantics():
    values = dict(sis_diresa=" 001 ", sis_tipo=" e1 ", sis_numero="000000001", sis_secuencia="01", etnia_codigo="02")
    command = PatientCreate(tipo_documento_codigo="DNI", numero_documento="00000001", fecha_nacimiento="1990-01-01", **values)
    assert command.sis_numero == "000000001"
    assert command.sis_tipo == "E1"
    assert command.etnia_codigo == "2"
    assert affiliation_problem(command.model_dump()) is None
    assert affiliation_problem({"sis_diresa": "001"})
    assert affiliation_problem({"sis_tipo": "2", "sis_numero": "00000001"}) is None
    assert patient_update_to_entity_kwargs(PatientUpdate(sis_secuencia=None)) == {"sis_secuencia": None}
    assert PatientSisFields().model_dump() == dict.fromkeys(values)


def test_ethnicity_foreign_key_and_versioned_seed_preserve_official_identifiers():
    fk = next(iter(Patient.__table__.c.etnia_codigo.foreign_keys))
    assert fk.target_fullname == "etnias.codigo"
    path = Path("migrations/versions/20260919_0015_patient_sis.py")
    spec = importlib.util.spec_from_file_location("patient_sis_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(module.ETHNICITIES) == 59
    assert "41" not in module.ETHNICITIES
    assert module.ETHNICITIES["58"] == "Mestizo"
    assert module.ETHNICITIES["49"] == "Uro"
