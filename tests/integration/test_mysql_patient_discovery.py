"""Patient discovery contract, matching what the SPA sends from its search box."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.patient import Patient

pytestmark = pytest.mark.integration


def _token() -> str:
    return uuid4().hex[:8].upper()


def test_exact_clinical_history_and_document_filters(
    clinic_scene, create_patient, api_prefix
) -> None:
    token = _token()
    patient = create_patient(
        clinic_scene.professional_client,
        historia_clinica=f"HC-{token}",
        numero_documento=str(uuid4().int)[:8],
    )
    create_patient(clinic_scene.professional_client)

    exact = clinic_scene.professional_client.get(
        f"{api_prefix}/patients", params={"historia_clinica": f"HC-{token}"}
    )
    assert exact.status_code == 200
    assert [item["id"] for item in exact.json()["items"]] == [patient["id"]]
    assert exact.json()["total"] == 1

    by_document = clinic_scene.professional_client.get(
        f"{api_prefix}/patients", params={"numero_documento": patient["numero_documento"]}
    )
    assert by_document.status_code == 200
    assert [item["id"] for item in by_document.json()["items"]] == [patient["id"]]

    by_type = clinic_scene.professional_client.get(
        f"{api_prefix}/patients",
        params={"tipo_documento_codigo": "DNI", "numero_documento": patient["numero_documento"]},
    )
    assert by_type.status_code == 200
    assert by_type.json()["total"] == 1

    # An exact history that does not exist returns an empty page, not an error.
    missing = clinic_scene.professional_client.get(
        f"{api_prefix}/patients", params={"historia_clinica": "HC-NO-EXISTE"}
    )
    assert missing.status_code == 200
    assert missing.json()["items"] == []


def test_partial_terms_match_history_document_and_names(
    clinic_scene, create_patient, api_prefix
) -> None:
    token = _token()
    patient = create_patient(
        clinic_scene.professional_client,
        historia_clinica=f"HC-{token}",
        apellido_paterno=f"Zamora{token}",
        primer_nombre=f"Ana{token}",
    )

    for term in (f"HC-{token}", patient["numero_documento"], f"Zamora{token}", f"ana{token}"):
        response = clinic_scene.professional_client.get(
            f"{api_prefix}/patients", params={"q": term}
        )
        assert response.status_code == 200, term
        assert patient["id"] in [item["id"] for item in response.json()["items"]], term


def test_partial_search_requires_two_characters_and_escapes_wildcards(
    clinic_scene, create_patient, api_prefix
) -> None:
    patient = create_patient(clinic_scene.professional_client, apellido_paterno="Ochare")

    too_short = clinic_scene.professional_client.get(
        f"{api_prefix}/patients", params={"q": "O"}
    )
    assert too_short.status_code == 422
    assert too_short.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"

    # ``%`` and ``_`` are literal characters for a clinician, never wildcards.
    for wildcard in ("%%", "__", "%_"):
        response = clinic_scene.professional_client.get(
            f"{api_prefix}/patients", params={"q": wildcard}
        )
        assert response.status_code == 200, wildcard
        assert patient["id"] not in [item["id"] for item in response.json()["items"]], wildcard


def test_pagination_reports_a_stable_total_and_has_more(
    clinic_scene, create_patient, api_prefix
) -> None:
    token = _token()
    created = [
        create_patient(clinic_scene.professional_client, apellido_paterno=f"Paginado{token}")
        for _ in range(3)
    ]

    first_page = clinic_scene.professional_client.get(
        f"{api_prefix}/patients", params={"q": f"Paginado{token}", "limit": 2, "offset": 0}
    )
    assert first_page.status_code == 200
    body = first_page.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["has_more"] is True
    assert len(body["items"]) == 2

    second_page = clinic_scene.professional_client.get(
        f"{api_prefix}/patients", params={"q": f"Paginado{token}", "limit": 2, "offset": 2}
    )
    assert second_page.status_code == 200
    assert second_page.json()["has_more"] is False
    assert len(second_page.json()["items"]) == 1

    pages = [
        item["id"] for item in body["items"]
    ] + [item["id"] for item in second_page.json()["items"]]
    assert sorted(pages) == sorted(item["id"] for item in created)

    # The total respects the same filter as the page, even beyond the window.
    beyond = clinic_scene.professional_client.get(
        f"{api_prefix}/patients", params={"q": f"Paginado{token}", "offset": 10}
    )
    assert beyond.status_code == 200
    assert beyond.json()["items"] == []
    assert beyond.json()["total"] == 3


def test_invalid_pagination_and_filters_are_rejected(clinic_scene, api_prefix) -> None:
    client = clinic_scene.professional_client
    invalid = [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"establecimiento_id": 0},
        {"historia_clinica": ""},
    ]
    for params in invalid:
        response = client.get(f"{api_prefix}/patients", params=params)
        assert response.status_code == 422, params
        assert response.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


def test_establishment_filter_restricts_the_result_set(
    clinic_scene, create_patient, api_prefix
) -> None:
    patient = create_patient(
        clinic_scene.professional_client,
        establecimiento_registro_id=clinic_scene.establecimiento_id,
    )

    matching = clinic_scene.admin_client.get(
        f"{api_prefix}/patients",
        params={"establecimiento_id": clinic_scene.establecimiento_id, "limit": 100},
    )
    assert matching.status_code == 200
    assert patient["id"] in [item["id"] for item in matching.json()["items"]]

    other = clinic_scene.admin_client.get(
        f"{api_prefix}/patients", params={"establecimiento_id": 999999999}
    )
    assert other.status_code == 200
    assert other.json()["items"] == []


def test_deactivated_patients_respect_the_role_scope(
    clinic_scene, create_patient, db_session: Session, api_prefix
) -> None:
    patient = create_patient(clinic_scene.professional_client)
    clinic_scene.admin_client.delete(f"{api_prefix}/patients/{patient['id']}")

    # ADMIN, explicit request: the logical low is visible for administration.
    admin_including = clinic_scene.admin_client.get(
        f"{api_prefix}/patients",
        params={"incluir_inactivos": True, "historia_clinica": patient["historia_clinica"]},
    )
    assert admin_including.status_code == 200
    assert [item["id"] for item in admin_including.json()["items"]] == [patient["id"]]
    assert admin_including.json()["items"][0]["estado"] is False

    # ADMIN, default filter: only active records.
    admin_default = clinic_scene.admin_client.get(
        f"{api_prefix}/patients", params={"historia_clinica": patient["historia_clinica"]}
    )
    assert admin_default.status_code == 200
    assert admin_default.json()["items"] == []

    # A clinician never receives deactivated records, even when asking for them.
    professional_including = clinic_scene.professional_client.get(
        f"{api_prefix}/patients",
        params={"incluir_inactivos": True, "historia_clinica": patient["historia_clinica"]},
    )
    assert professional_including.status_code == 200
    assert professional_including.json()["items"] == []

    assert db_session.get(Patient, patient["id"]).estado is False


def test_listing_without_filters_returns_the_active_base(clinic_scene, create_patient, api_prefix) -> None:
    patient = create_patient(clinic_scene.professional_client)

    response = clinic_scene.admin_client.get(f"{api_prefix}/patients", params={"limit": 100})

    assert response.status_code == 200
    body = response.json()
    assert patient["id"] in [item["id"] for item in body["items"]]
    assert body["total"] >= len(body["items"])
    assert body["limit"] == 100
    assert body["offset"] == 0
