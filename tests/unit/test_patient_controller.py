from __future__ import annotations

from datetime import date, datetime
from unittest.mock import Mock

from app.controllers.patient import create_patient, update_patient
from app.core.dependencies import AuthenticatedPrincipal
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate


def _response() -> PatientResponse:
    return PatientResponse(
        id=1,
        codclie_legacy=None,
        historia_clinica=None,
        historia_familiar=None,
        tipo_documento_codigo="DNI",
        numero_documento="12345678",
        fecha_inscripcion=None,
        fecha_nacimiento=date(1990, 1, 1),
        apellido_paterno=None,
        apellido_materno=None,
        primer_nombre="Ana",
        otros_nombres=None,
        sexo_codigo=None,
        ubigeo_residencia_codigo=None,
        localidad=None,
        direccion=None,
        establecimiento_registro_id=None,
        seguro_id=None,
        telefono_principal=None,
        condicion=None,
        estado=True,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def test_create_controller_only_delegates_payload_and_actor() -> None:
    service = Mock()
    expected = _response()
    service.create.return_value = expected
    principal = AuthenticatedPrincipal(1, "registro", frozenset(), frozenset())
    payload = PatientCreate(
        tipo_documento_codigo="DNI",
        numero_documento="12345678",
        fecha_nacimiento=date(1990, 1, 1),
    )

    assert create_patient(payload, service, principal) is expected
    service.create.assert_called_once_with(payload, actor_id=1, actor_roles=frozenset())


def test_update_controller_only_delegates_payload_and_actor() -> None:
    service = Mock()
    expected = _response()
    service.update.return_value = expected
    principal = AuthenticatedPrincipal(8, "registro", frozenset(), frozenset())
    payload = PatientUpdate(primer_nombre="Ana María")

    assert update_patient(1, payload, service, principal) is expected
    service.update.assert_called_once_with(1, payload, actor_id=8, actor_roles=frozenset())
