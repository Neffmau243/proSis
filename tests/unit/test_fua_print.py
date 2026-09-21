from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.fua_print import FuaPrintInput, FuaPrintSnapshot
from app.services.fua_print import build_fua_snapshot


def fixtures():
    attention = SimpleNamespace(
        modalidad_atencion_codigo="AMBULATORIA", fecha_atencion=datetime(2026, 9, 19, 9, 30),
        historia_clinica_snapshot="HC-005", peso_kg=Decimal("60"), talla_cm=Decimal("160"),
        presion_sistolica=120, presion_diastolica=80, imc=Decimal("23.438"),
        perimetro_abdominal_cm=Decimal("80"), grupo_atencion_codigo="GESTANTES",
        fecha_probable_parto=date(2027, 1, 1),
    )
    patient = SimpleNamespace(
        tipo_documento_codigo="DNI", numero_documento="01234567", apellido_paterno="Pérez",
        apellido_materno=None, primer_nombre="Ana", otros_nombres="María",
        sexo_codigo="F", fecha_nacimiento=date(1990, 2, 3),
    )
    site = SimpleNamespace(codigo_renaes="00001234", nombre="IPRESS de prueba")
    professional = SimpleNamespace(nombre_completo="Profesional de prueba",
                                   numero_documento="76543210", colegiatura="00123")
    return attention, patient, site, professional


def test_snapshot_maps_official_document_code_and_keeps_server_owned_values():
    a, p, s, professional = fixtures()
    p.sis_diresa, p.sis_tipo, p.sis_numero = "001", "2", "01234567"
    p.etnia_codigo = "58"
    result = build_fua_snapshot(a, p, s, professional, FuaPrintInput(
        personal_atiende="IPRESS", lugar_atencion="INTRAMURAL",
        sis_diresa="001", sis_tipo="2", sis_numero="01234567", etnia_codigo="58",
    ))
    assert result["tdi"] == "2"
    assert result["sis_diresa"] == "001"
    assert result["codigo_renipress"] == "00001234"
    assert result["hora_atencion"] == "09:30:00"
    assert result["imc"] == "23.438"
    assert result["historia_clinica"] == "HC-005"
    assert result["apellido_materno"] is None
    p.primer_nombre = "Cambio posterior"
    assert result["primer_nombre"] == "ANA"
    assert FuaPrintSnapshot.model_validate(result).version == 2


def test_missing_values_are_not_invented_and_internal_ids_are_not_renipress():
    a, p, s, professional = fixtures()
    s.codigo_renaes = "1234"
    p.tipo_documento_codigo = "PAS"
    result = build_fua_snapshot(a, p, s, professional, None)
    assert result["codigo_renipress"] is None
    assert result["tdi"] is None
    assert result["sis_numero"] is None
    assert result["etnia_codigo"] is None
    assert result["personal_atiende"] == "IPRESS"
    assert result["lugar_atencion"] == "INTRAMURAL"
    assert result["renipress_preimpreso"] is True
    assert "numero_fua" not in result


@pytest.mark.parametrize("value", [
    {"sis_diresa": "001"}, {"sis_componente": "RN1"},
    {"personal_atiende": "AISPED"}, {"codigo_aisped": "A001"},
    {"tipo_atencion": "REFERENCIA"}, {"referencia_hoja": "0023"},
    {"codigo_renipress": "123"}, {"etnia_codigo": "MESTIZO"},
    {"imc": 99}, {"tdi": "2"}, {"numero_documento": "12345678"},
])
def test_invalid_or_client_owned_clinical_data_is_rejected(value):
    with pytest.raises(ValidationError):
        FuaPrintInput.model_validate(value)


def test_valid_reference_and_normalization():
    result = FuaPrintInput(
        personal_atiende="aisped", codigo_aisped=" a001 ", tipo_atencion="REFERENCIA",
        referencia_renipress="00000001", referencia_nombre="Origen", referencia_hoja="0002",
        sis_diresa="001", sis_tipo="e", sis_numero="00042", etnia_codigo="  ",
    )
    assert result.codigo_aisped == "A001"
    assert result.sis_tipo == "E"
    assert result.etnia_codigo is None


def test_patient_site_and_modality_override_old_client_supplements():
    a, p, s, professional = fixtures()
    a.modalidad_atencion_codigo = "EMERGENCIA"
    p.sis_diresa, p.sis_tipo, p.sis_numero = "001", "E1", "000000001"
    p.sis_secuencia, p.etnia_codigo = "01", "2"
    s.fua_personal_atiende, s.fua_lugar_atencion = "ITINERANTE", "EXTRAMURAL"
    result = build_fua_snapshot(a, p, s, professional, FuaPrintInput(
        personal_atiende="IPRESS", lugar_atencion="INTRAMURAL", tipo_atencion="AMBULATORIA",
        sis_diresa="999", sis_tipo="9", sis_numero="99999999", etnia_codigo="58",
    ))
    assert result["tipo_atencion"] == "EMERGENCIA"
    assert result["personal_atiende"] == "ITINERANTE"
    assert result["lugar_atencion"] == "EXTRAMURAL"
    assert result["sis_numero"] == "000000001"
    assert result["sis_secuencia"] == "01"
    assert result["sis_componente"] is None
    assert result["etnia_codigo"] == "2"
    p.sis_numero = "11111111"
    assert result["sis_numero"] == "000000001"
