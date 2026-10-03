"""Ethnicity edits, historical FUA and invalid clinical requests, isolated DB only."""
import json
import sys
from pathlib import Path

from audit_admission import TEST_PASSWORD, TEST_USER, configure

_, target = configure(sys.argv[1])

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from app.main import app
from app.models.clinical import Attention
from app.models.patient import Patient

source = json.loads(Path(__file__).with_name("ethnicity_matrix_results.json").read_text(encoding="utf-8"))
assert source["complete"] and source["database"] == target.database
engine = create_engine(target)
checks = []
GENERAL = "NINOS_ADOLESCENTES_ADULTOS_MAYORES"


def check(name, ok):
    checks.append({"name": name, "passed": bool(ok)})
    assert ok, name


try:
    with TestClient(app, base_url="http://localhost") as client:
        def request(method, route, payload=None, status=200):
            response = client.request(method, "/api/v1" + route, json=payload)
            check(f"{method} {route}: HTTP {status}", response.status_code == status)
            return response.json()

        token = request("POST", "/auth/login", {"nombre_usuario": TEST_USER, "password": TEST_PASSWORD})
        client.headers["Authorization"] = "Bearer " + token["access_token"]
        for doc in ("DNI", "CE", "PAS", "DE", "OTRO"):
            anchor = next(case for case in source["cases"] if case["profile"] == "ADULTA" and case["document"] == doc and case["ethnicity"] == "40")
            pid, aid = anchor["patient_id"], anchor["attention_id"]
            historical = request("GET", f"/atenciones/{aid}")
            base = {key: historical[key] for key in ("paciente_id", "establecimiento_id", "consultorio_id", "profesional_id")}
            base.update(fecha_atencion="2026-10-02T09:00:00", peso_kg=60, talla_cm=160)
            for index, (ethnicity, group) in enumerate((("1", GENERAL), (None, "GESTANTES"), ("58", "PUERPERAS"), ("40", GENERAL))):
                changed = request("PATCH", f"/patients/{pid}", {"etnia_codigo": ethnicity})
                current = request("GET", f"/patients/{pid}")
                check(f"{doc}: ethnicity PATCH/GET", changed["etnia_codigo"] == current["etnia_codigo"] == ethnicity)
                with Session(engine) as session:
                    check(f"{doc}: ethnicity SQL", session.get(Patient, pid).etnia_codigo == ethnicity)
                payload = {**base, "grupo_atencion_codigo": group,
                           "modalidad_atencion_codigo": "AMBULATORIA" if index % 2 == 0 else "EMERGENCIA"}
                if group == "GESTANTES":
                    payload.update(tipo_embarazo_codigo="UNICO", fecha_probable_parto="2027-03-01", peso_antes_embarazo_kg=55)
                saved = request("POST", "/atenciones", payload, 201)
                fetched = request("GET", f"/atenciones/{saved['id']}")
                check(f"{doc}: new FUA uses edited ethnicity", fetched["fua_impresion"]["etnia_codigo"] == ethnicity)
                old = request("GET", f"/atenciones/{aid}")
                check(f"{doc}: old FUA remains immutable", old["fua_impresion"] == historical["fua_impresion"])
            with Session(engine) as session:
                count_before = session.scalar(select(func.count()).select_from(Attention).where(Attention.paciente_id == pid))
            for mode in ("AMBULATORIA", "EMERGENCIA"):
                for group in (GENERAL, "PUERPERAS"):
                    for key, value in (("tipo_embarazo_codigo", "UNICO"), ("peso_antes_embarazo_kg", 55),
                                       ("fecha_probable_parto", "2027-03-01"),
                                       ("valoracion_nutricional", {"edad_gestacional_semanas": 18})):
                        request("POST", "/atenciones", {**base, "grupo_atencion_codigo": group,
                                "modalidad_atencion_codigo": mode, key: value}, 422)
            request("PATCH", f"/patients/{pid}", {"etnia_codigo": "99"}, 422)
            with Session(engine) as session:
                check(f"{doc}: rejected requests create no attentions", session.scalar(
                    select(func.count()).select_from(Attention).where(Attention.paciente_id == pid)) == count_before)
                patient = session.get(Patient, pid)
                check(f"{doc}: rejected ethnicity leaves patient unchanged", patient.etnia_codigo == "40" and patient.condicion == "PUERPERA")
finally:
    report = {"database": target.database, "checks": checks,
              "passed": sum(c["passed"] for c in checks), "failed": sum(not c["passed"] for c in checks)}
    Path(__file__).with_name("ethnicity_transition_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("database", "passed", "failed")}))
    engine.dispose()
