from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

from app.mappers.patient import (
    patient_to_response,
    patient_update_to_entity_kwargs,
    risk_to_response,
)
from app.schemas.patient import PatientUpdate


def test_patch_mapper_distinguishes_omitted_and_explicit_null() -> None:
    assert patient_update_to_entity_kwargs(PatientUpdate()) == {}
    assert patient_update_to_entity_kwargs(PatientUpdate(historia_clinica=None)) == {
        "historia_clinica": None
    }


def test_patient_mapper_never_returns_orm_entities() -> None:
    risk = SimpleNamespace(
        grupo_riesgo_id=3,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=None,
        observacion=None,
        grupo_riesgo=SimpleNamespace(codigo="GESTANTE", nombre="Gestante"),
    )
    patient = SimpleNamespace(
        id=9,
        codclie_legacy=None,
        historia_clinica="HC-9",
        historia_familiar=None,
        tipo_documento_codigo="DNI",
        numero_documento="11111111",
        fecha_inscripcion=None,
        fecha_nacimiento=date(1990, 1, 1),
        apellido_paterno="Pérez",
        apellido_materno=None,
        primer_nombre="Ana",
        otros_nombres=None,
        sexo_codigo="F",
        ubigeo_residencia_codigo=None,
        localidad=None,
        direccion=None,
        establecimiento_registro_id=None,
        seguro_id=None,
        telefono_principal=None,
        condicion=None,
        estado=True,
        created_at=datetime(2026, 1, 1, 8, 0),
        updated_at=datetime(2026, 1, 1, 8, 0),
        responsables=[],
        riesgos=[risk],
    )

    response = patient_to_response(patient)

    assert response.id == 9
    assert response.riesgos[0].grupo_riesgo_codigo == "GESTANTE"
    assert risk_to_response(risk).model_dump()["grupo_riesgo_nombre"] == "Gestante"
