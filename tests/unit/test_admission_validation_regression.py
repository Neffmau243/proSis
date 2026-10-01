# Imported pytest fixtures are intentionally injected by name.
# ruff: noqa: F811
from datetime import datetime

import pytest
from pydantic import ValidationError
from test_fua_print import fixtures
from test_patient_service import adult_command, environment  # noqa: F401

from app.domain.patient_document import document_problem
from app.domain.patient_insurance import SIS_FIELDS
from app.exceptions import ValidationDomainError
from app.schemas.attention import AttentionCreate
from app.schemas.patient import PatientUpdate
from app.services.fua_print import build_fua_snapshot


@pytest.mark.parametrize(
    "kind,number,valid",
    [
        ("DNI", "00000001", True),
        ("DNI", "PASUI000033", False),
        ("DNI", "1234567", False),
        ("DNI", "123456789", False),
        ("DNI", "１２３４５６７８", False),
        ("DNI", "1234 678", False),
        ("CE", "000123456", True),
        ("CE", "N12345678", True),
        ("PAS", "PASUI000033", True),
        ("PAS", "A 123", False),
        ("DE", "AB-123/45", True),
        ("OTRO", "TMP.001", True),
        ("OTRO", "<script>", False),
        ("PAS", "A" * 31, False),
    ],
)
def test_document_rules(kind, number, valid):
    assert (document_problem(kind, number) is None) == valid


def test_invalid_create_and_partial_patch_are_rejected(environment):
    service, repo, session, audit = environment
    with pytest.raises(ValidationDomainError):
        service.create(adult_command(numero_documento="PASUI000033"), actor_id=41)
    assert repo.created_patient_count == 0
    patient = service.create(
        adult_command(tipo_documento_codigo="PAS", numero_documento="PASUI000033"), actor_id=41
    )
    with pytest.raises(ValidationDomainError):
        service.update(patient.id, PatientUpdate(tipo_documento_codigo="DNI"), actor_id=41)
    assert repo.patients[patient.id].tipo_documento_codigo == "PAS"
    fixed = service.update(
        patient.id,
        PatientUpdate(tipo_documento_codigo="DNI", numero_documento="00123456"),
        actor_id=41,
    )
    assert fixed.numero_documento == "00123456"
    with pytest.raises(ValidationDomainError):
        service.update(patient.id, PatientUpdate(numero_documento="A"), actor_id=41)


@pytest.mark.parametrize("target", [None, 1, 3, 4])
def test_insurance_switch_clears_affiliation_and_audits_without_clearing_ethnicity(
    environment, target
):
    service, repo, session, audit = environment
    patient = service.create(
        adult_command(
            seguro_id=2,
            sis_diresa="040",
            sis_tipo="2",
            sis_numero="00000001",
            sis_secuencia="01",
            etnia_codigo="58",
        ),
        actor_id=41,
    )
    changed = service.update(patient.id, PatientUpdate(seguro_id=target), actor_id=41)
    assert all(getattr(changed, field) is None for field in SIS_FIELDS)
    assert changed.etnia_codigo == "58"
    assert audit.events[-1]["before"]["sis_numero"] == "00000001"
    assert audit.events[-1]["after"]["sis_numero"] is None
    with pytest.raises(ValidationDomainError):
        service.update(patient.id, PatientUpdate(sis_tipo="2", sis_numero="00000001"), actor_id=41)
    returned = service.update(patient.id, PatientUpdate(seguro_id=2), actor_id=41)
    assert returned.sis_numero is None


def test_non_sis_creation_rejects_affiliation(environment):
    service, repo, session, audit = environment
    with pytest.raises(ValidationDomainError):
        service.create(adult_command(seguro_id=1, sis_tipo="2", sis_numero="00000001"), actor_id=41)
    assert repo.created_patient_count == 0


def test_legacy_stale_affiliation_never_leaks_to_new_fua():
    a, p, site, professional = fixtures()
    p.sis_diresa, p.sis_tipo, p.sis_numero, p.sis_secuencia = "040", "2", "00000001", "01"
    old = build_fua_snapshot(a, p, site, professional, None)
    p.insurance = None
    fresh = build_fua_snapshot(a, p, site, professional, None)
    assert all(fresh[field] is None for field in SIS_FIELDS)
    assert old["sis_numero"] == "00000001"


@pytest.mark.parametrize("group", ["NINOS_ADOLESCENTES_ADULTOS_MAYORES", "PUERPERAS", "GESTANTES"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("tipo_embarazo_codigo", "UNICO"),
        ("peso_antes_embarazo_kg", 55),
        ("fecha_probable_parto", "2027-03-01"),
        ("valoracion_nutricional", {"edad_gestacional_semanas": 12}),
    ],
)
def test_pregnancy_fields_require_pregnant_group(group, field, value):
    payload = dict(
        paciente_id=1,
        establecimiento_id=1,
        profesional_id=1,
        consultorio_id=1,
        modalidad_atencion_codigo="EMERGENCIA",
        fecha_atencion=datetime(2026, 10, 1),
        grupo_atencion_codigo=group,
        **{field: value},
    )
    if group == "GESTANTES":
        assert getattr(AttentionCreate(**payload), field) is not None
    else:
        with pytest.raises(ValidationError, match="GESTANTES"):
            AttentionCreate(**payload)
