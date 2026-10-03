"""Regression tests for clinical-attention persistence details."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.exceptions import AuthorizationError
from app.schemas.attention import AttentionCreate, CareGroupCode, PregnancyTypeCode
from app.services.attention import AttentionService
from app.domain.age import CalendarAge
from app.domain.nutrition import calculate_nutritional_indicators


@pytest.mark.parametrize("manual", [None, {"diagnostico_peso_edad": "TEXTO INCORRECTO"}])
def test_nutritional_snapshot_is_calculated_without_trusting_preview(manual):
    session = _RecordingSession()
    service = AttentionService(session)
    service._attentions = SimpleNamespace(add_nutritional_evaluation=session.add)
    measured = datetime(2025, 1, 15)
    command = AttentionCreate(
        paciente_id=1, establecimiento_id=1, profesional_id=1, consultorio_id=1,
        modalidad_atencion_codigo="AMBULATORIA", fecha_atencion=measured,
        peso_kg=Decimal("9.5"), talla_cm=Decimal("75.2"), valoracion_nutricional=manual,
    )
    indicators = calculate_nutritional_indicators(
        birth_date=date(2024, 1, 15), sex_code="M", measured_on=measured.date(),
        weight_kg=command.peso_kg, height_cm=command.talla_cm,
    )
    entity = SimpleNamespace(id=42, paciente_id=1, establecimiento_id=1,
        fecha_atencion=measured, peso_kg=command.peso_kg, talla_cm=command.talla_cm,
        perimetro_abdominal_cm=None)
    service._add_nutritional_snapshot(entity, command, CalendarAge(1, 0, 0), indicators)
    assert len(session.added) == 1
    saved = session.added[0]
    assert saved.diagnostico_peso_edad == "Normal"
    assert saved.diagnostico_talla_edad == "Normal"
    assert saved.diagnostico_peso_talla == "Normal"
    assert saved.waz == Decimal("-0.147")


class _RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, entity: object) -> None:
        self.added.append(entity)


class _ActiveDetailCatalog:
    def __init__(self) -> None:
        self.persisted_details: dict[str, object] | None = None

    @staticmethod
    def get_active_service_offering(_: str) -> object:
        return object()

    @staticmethod
    def get_active_cie10(_: str) -> object:
        return object()

    def add_details(self, **values: object) -> None:
        self.persisted_details = values


def test_add_details_delegates_orm_persistence_to_repository() -> None:
    """The use case validates inputs; the repository builds/stages ORM rows."""

    session = _RecordingSession()
    service = AttentionService(session)  # type: ignore[arg-type]
    repository = _ActiveDetailCatalog()
    service._attentions = repository  # type: ignore[assignment]
    command = AttentionCreate(
        paciente_id=1,
        establecimiento_id=1,
        profesional_id=1,
        consultorio_id=1,
        modalidad_atencion_codigo="AMBULATORIA",
        fecha_atencion=datetime(2026, 9, 9, 9, 0),
        prestaciones=[{"prestacion_codigo": "CONSULTA_MED", "cantidad": 2}],
        diagnosticos=[{"cie10_codigo": "Z00.0", "tipo_diagnostico": "PRESUNTIVO"}],
    )

    service._add_details(SimpleNamespace(id=42), command)

    assert repository.persisted_details == {
        "attention_id": 42,
        "service_details": [(1, "CONSULTA_MED", 2)],
        "diagnosis_details": [(1, "Z00.0", "PRESUNTIVO", None)],
    }


def test_linked_professional_can_register_an_attention_for_another_professional() -> None:
    service = AttentionService(_RecordingSession())  # type: ignore[arg-type]
    service._attentions = SimpleNamespace(  # type: ignore[assignment]
        get_active_professional_id_for_user=lambda _: 7,
    )

    assert service._ensure_actor_is_linked_professional(
        actor_id=12,
        actor_roles={"PROFESIONAL"},
    ) == 7


def test_linked_professional_cannot_cancel_another_professionals_attention() -> None:
    service = AttentionService(_RecordingSession())  # type: ignore[arg-type]
    service._attentions = SimpleNamespace(  # type: ignore[assignment]
        get_active_professional_id_for_user=lambda _: 7,
    )

    with pytest.raises(AuthorizationError) as exc_info:
        service._ensure_actor_can_cancel_attention(
            actor_id=12,
            actor_roles={"PROFESIONAL"},
            professional_id=8,
        )

    assert exc_info.value.code == "PROFESIONAL_DISTINTO_AL_USUARIO"


def test_care_group_defaults_to_general_population() -> None:
    """Clients that never declared a population stay on the general group."""

    command = AttentionCreate(
        paciente_id=1,
        establecimiento_id=1,
        profesional_id=1,
        consultorio_id=1,
        modalidad_atencion_codigo="AMBULATORIA",
        fecha_atencion=datetime(2026, 9, 9, 9, 0),
    )

    assert command.grupo_atencion_codigo is CareGroupCode.GENERAL


def test_care_group_rejects_unknown_populations() -> None:
    with pytest.raises(ValueError):
        AttentionCreate(
            paciente_id=1,
            establecimiento_id=1,
            profesional_id=1,
            consultorio_id=1,
            modalidad_atencion_codigo="AMBULATORIA",
            grupo_atencion_codigo="GESTANTE",  # typo: the code is plural
            fecha_atencion=datetime(2026, 9, 9, 9, 0),
        )


def test_pregnancy_values_are_optional_and_validated() -> None:
    """Only the two gestation pluralities are accepted, and neither is required."""

    base = {
        "paciente_id": 1,
        "establecimiento_id": 1,
        "profesional_id": 1,
        "consultorio_id": 1,
        "modalidad_atencion_codigo": "AMBULATORIA",
        "grupo_atencion_codigo": "GESTANTES",
        "fecha_atencion": datetime(2026, 9, 9, 9, 0),
    }

    empty = AttentionCreate(**base)  # type: ignore[arg-type]
    assert empty.peso_antes_embarazo_kg is None
    assert empty.tipo_embarazo_codigo is None
    assert empty.fecha_probable_parto is None

    filled = AttentionCreate(
        **base,  # type: ignore[arg-type]
        tipo_embarazo_codigo="MULTIPLE",
        peso_antes_embarazo_kg="58.40",
        fecha_probable_parto="2027-03-15",
    )
    assert filled.tipo_embarazo_codigo is PregnancyTypeCode.MULTIPLE
    assert filled.fecha_probable_parto == date(2027, 3, 15)

    with pytest.raises(ValueError):
        AttentionCreate(**base, tipo_embarazo_codigo="TRIPLE")  # type: ignore[arg-type]


def test_snapshot_records_the_declared_care_group() -> None:
    """The audit trail must show the population the encounter was filed under."""

    entity = SimpleNamespace(
        id=1,
        paciente_id=10,
        establecimiento_id=2,
        profesional_id=3,
        consultorio_id=4,
        modalidad_atencion_codigo="AMBULATORIA",
        grupo_etario_codigo="ADULTO",
        grupo_atencion_codigo="PUERPERAS",
        fecha_atencion=datetime(2026, 9, 10, 9, 30),
        historia_clinica_snapshot="HC-001",
        imc=None,
        pe=None,
        te=None,
        pt=None,
        referencia_nutricional=None,
        estado="ATENDIDO",
        observaciones=None,
    )

    snapshot = AttentionService._snapshot(entity)  # type: ignore[arg-type]

    assert snapshot["grupo_atencion_codigo"] == "PUERPERAS"


def test_admin_cannot_operate_clinical_encounters() -> None:
    service = AttentionService(_RecordingSession())  # type: ignore[arg-type]
    service._attentions = SimpleNamespace(  # type: ignore[assignment]
        get_active_professional_id_for_user=lambda _: (_ for _ in ()).throw(AssertionError()),
    )

    with pytest.raises(AuthorizationError) as exc_info:
        service._ensure_actor_is_linked_professional(
            actor_id=1,
            actor_roles={"ADMIN"},
        )

    assert exc_info.value.code == "ROL_CLINICO_REQUERIDO"
