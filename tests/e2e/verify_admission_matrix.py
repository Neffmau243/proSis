"""API/MySQL combination audit in an explicitly isolated admission test database.

Run audit_admission.py setup <fresh database> first. This script never resets
or deletes data, and uses only the synthetic clinic and patients it creates.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from itertools import product
from pathlib import Path
import sys
import traceback
from uuid import uuid4

from audit_admission import TEST_PASSWORD, TEST_USER, configure

GENERAL = "NINOS_ADOLESCENTES_ADULTOS_MAYORES"
MEASURED = "2026-10-03T09:00:00"
MODES = ("AMBULATORIA", "EMERGENCIA")


def scenarios():
    for label, birth, weight, height, reference in [
        ("infantil", "2025-10-03", 9.5, 75.2, "INFANTIL"),
        ("escolar", "2018-10-03", 25, 125, "ESCOLAR"),
        ("adolescente", "2012-10-03", 50, 160, "ESCOLAR"),
        ("adulto", "1994-10-03", 80, 180, "ADULTO"),
        ("mayor", "1950-10-03", 60, 160, "ADULTO_MAYOR"),
    ]:
        for sex in ("M", "F"):
            yield dict(name=f"{label}_{sex}", birth=birth, sex=sex,
                       weight=weight, height=height, care=GENERAL, reference=reference)
    for label, birth in [("adulta", "1994-10-03"), ("adolescente", "2010-10-03")]:
        for care, reference in [("GESTANTES", "GESTANTE"), ("PUERPERAS", "PUERPERA")]:
            yield dict(name=f"{care}_{label}", birth=birth, sex="F",
                       weight=70, height=160, care=care, reference=reference)


def main(database: str) -> int:
    _, target = configure(database)
    # Import the app only after selecting the isolated database.
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.main import app
    from app.models.clinical import Attention
    from app.models.organization import Establishment, Office
    from app.models.security import Professional

    engine = create_engine(target)
    with Session(engine) as db:
        site = db.scalar(select(Establishment.id).where(Establishment.nombre == "PRUEBA E2E NO REAL"))
        office = db.scalar(select(Office.id).where(Office.codigo == "TEST-E2E"))
        professional = db.scalar(select(Professional.id).where(Professional.colegiatura == "TEST-E2E"))
    assert site and office and professional, "Run the isolated audit setup first"
    run = uuid4().hex[:10]
    serial = int(run[:6], 16) % 8_000_000
    report = {"database": database, "measured_on": MEASURED, "cases": [], "edge_cases": []}
    baseline = {}

    with TestClient(app, base_url="http://localhost") as client:
        def request(method, route, payload=None, expected=200):
            response = client.request(method, "/api/v1" + route, json=payload)
            assert response.status_code == expected, f"{method} {route}: {response.status_code}: {response.text[:600]}"
            return response.json()

        token = request("POST", "/auth/login", {"nombre_usuario": TEST_USER, "password": TEST_PASSWORD})
        client.headers["Authorization"] = "Bearer " + token["access_token"]
        docs = [item["codigo"] for item in request("GET", "/catalogos/tipos-documento") if item.get("activo", True)]
        assert docs
        report["document_types"] = docs
        adult_patients = {}

        for doc, scenario in product(docs, scenarios()):
            serial += 1
            patient_payload = dict(
                tipo_documento_codigo=doc, numero_documento=f"{serial:08}" if doc == "DNI" else f"MX{run}{serial}",
                fecha_nacimiento=scenario["birth"], sexo_codigo=scenario["sex"],
                primer_nombre="PRUEBA", apellido_paterno="MATRIZ", apellido_materno="FICTICIA",
                establecimiento_registro_id=site, historia_clinica=f"MX-{run}-{serial}",
            )
            if date.fromisoformat(scenario["birth"]).year > 2008:
                patient_payload["responsables"] = [dict(parentesco="TUTOR", nombre_completo="TUTOR FICTICIO", es_principal=True)]
            patient = request("POST", "/patients", patient_payload, 201)
            if scenario["name"] == "adulto_F":
                adult_patients[doc] = patient["id"]
            for mode in MODES:
                case = {"document": doc, "mode": mode, "scenario": scenario["name"], "care_group": scenario["care"]}
                try:
                    preview_payload = dict(paciente_id=patient["id"], fecha_atencion=MEASURED,
                        peso_kg=scenario["weight"], talla_cm=scenario["height"], grupo_atencion_codigo=scenario["care"])
                    if scenario["care"] == "GESTANTES":
                        preview_payload["peso_antes_embarazo_kg"] = 60
                    preview = request("POST", "/atenciones/indicadores-nutricionales/vista-previa", preview_payload)
                    assert preview["estado"] == "CALCULADO", preview
                    assert preview["grupo_referencia"] == scenario["reference"], preview
                    expected_bmi = (Decimal(str(scenario["weight"])) / (Decimal(str(scenario["height"])) / 100) ** 2).quantize(Decimal(".001"), ROUND_HALF_UP)
                    assert Decimal(preview["imc"]) == expected_bmi
                    if scenario["reference"] == "INFANTIL":
                        assert all(preview[key] is not None for key in ("pe", "te", "pt"))
                    if scenario["name"].startswith("escolar"):
                        assert all(preview[key] is not None for key in ("pe", "te", "imc_edad"))
                    if scenario["care"] == "GESTANTES":
                        assert preview["imc_pregestacional"] == "23.438"
                        assert Decimal(preview["ganancia_peso_kg"]) == 10
                    if scenario["reference"] in {"ADULTO", "ADULTO_MAYOR"}:
                        assert preview["diagnostico_imc"] == "Normal"
                    if scenario["reference"] == "PUERPERA":
                        assert preview["diagnostico_imc"] is None
                    # Identity document and encounter mode must never alter nutrition.
                    original = baseline.setdefault(scenario["name"], preview)
                    assert original == preview
                    payload = dict(**preview_payload, establecimiento_id=site, consultorio_id=office,
                        profesional_id=professional, modalidad_atencion_codigo=mode)
                    if scenario["care"] == "GESTANTES":
                        payload.update(tipo_embarazo_codigo="UNICO", fecha_probable_parto="2027-02-01")
                    saved = request("POST", "/atenciones", payload, 201)
                    fetched = request("GET", f'/atenciones/{saved["id"]}')
                    history = request("GET", f'/atenciones?paciente_id={patient["id"]}')
                    listed = next(item for item in history if item["id"] == saved["id"])
                    for response in (saved, fetched, listed):
                        assert response["valoracion_calculada"] == preview
                        assert response["modalidad_atencion_codigo"] == mode
                        assert response["grupo_atencion_codigo"] == scenario["care"]
                        assert Decimal(response["imc"]) == expected_bmi
                        for key in ("pe", "te", "pt"):
                            assert response[key] == preview[key]
                    fua = fetched["fua_impresion"]
                    assert fua["tipo_documento"] == doc
                    assert patient["numero_documento"] == patient_payload["numero_documento"]
                    # The paper FUA uppercases text; the patient record preserves it.
                    assert fua["numero_documento"] == patient["numero_documento"].upper()
                    assert fua["tipo_atencion"] == mode
                    assert fua["grupo_atencion_codigo"] == scenario["care"]
                    assert Decimal(fua["imc"]) == expected_bmi
                    with Session(engine) as db:
                        row = db.get(Attention, saved["id"])
                        assert row.valoracion_calculada == preview
                        assert row.modalidad_atencion_codigo == mode
                        assert row.grupo_atencion_codigo == scenario["care"]
                        assert row.imc == expected_bmi
                    case.update(passed=True, attention_id=saved["id"], result=preview)
                except AssertionError as exc:
                    case.update(passed=False, error=str(exc), assertion=traceback.extract_tb(exc.__traceback__)[-1].line)
                report["cases"].append(case)
            if scenario["name"] == "PUERPERAS_adolescente":
                print(json.dumps({"document": doc, "completed": len(report["cases"])}), flush=True)

        # Missing measurements must not retain a previous calculation.
        for doc, mode, care, missing in product(docs, MODES, (GENERAL, "GESTANTES", "PUERPERAS"), ("peso_kg", "talla_cm")):
            case = dict(document=doc, mode=mode, care_group=care, missing=missing)
            try:
                payload = dict(paciente_id=adult_patients[doc], fecha_atencion=MEASURED,
                    peso_kg=80, talla_cm=180, grupo_atencion_codigo=care)
                if care == "GESTANTES":
                    payload["peso_antes_embarazo_kg"] = 60
                payload[missing] = None
                preview = request("POST", "/atenciones/indicadores-nutricionales/vista-previa", payload)
                assert preview["imc"] is None
                assert all(preview[key] is None for key in ("pe", "te", "pt"))
                # Pregestational BMI remains available when only current weight is missing.
                expected = "CALCULADO" if care == "GESTANTES" and missing == "peso_kg" else "DATOS_INCOMPLETOS"
                assert preview["estado"] == expected
                saved = request("POST", "/atenciones", dict(**payload, modalidad_atencion_codigo=mode,
                    establecimiento_id=site, consultorio_id=office, profesional_id=professional), 201)
                assert saved["valoracion_calculada"] == preview
                case["passed"] = True
            except AssertionError as exc:
                case.update(passed=False, error=str(exc), assertion=traceback.extract_tb(exc.__traceback__)[-1].line)
            report["edge_cases"].append(case)

        # Reject invalid values in preview and save consistently.
        for changes in ({"peso_kg": 0}, {"talla_cm": 0}, {"peso_kg": 501}, {"talla_cm": 301},
                        {"peso_antes_embarazo_kg": 60}, {"grupo_atencion_codigo": "INVALID"}):
            for endpoint in ("/atenciones/indicadores-nutricionales/vista-previa", "/atenciones"):
                case = dict(invalid=changes, endpoint=endpoint)
                try:
                    payload = dict(paciente_id=next(iter(adult_patients.values())), fecha_atencion=MEASURED,
                        peso_kg=80, talla_cm=180, grupo_atencion_codigo=GENERAL)
                    payload.update(changes)
                    if endpoint == "/atenciones":
                        payload.update(modalidad_atencion_codigo="AMBULATORIA", establecimiento_id=site,
                                       consultorio_id=office, profesional_id=professional)
                    request("POST", endpoint, payload, 422)
                    case["passed"] = True
                except AssertionError as exc:
                    case.update(passed=False, error=str(exc), assertion=traceback.extract_tb(exc.__traceback__)[-1].line)
                report["edge_cases"].append(case)

    engine.dispose()
    all_cases = report["cases"] + report["edge_cases"]
    report["total"] = len(all_cases)
    report["passed"] = sum(case["passed"] for case in all_cases)
    output = Path(__file__).with_name(f"{database}_matrix.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(output), "total": report["total"], "passed": report["passed"],
                      "failures": [case for case in all_cases if not case["passed"]]}, ensure_ascii=True))
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
