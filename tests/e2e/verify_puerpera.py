"""Synthetic puerperal workflow through FastAPI routes and real isolated MySQL.

Run against the dedicated audit database only. Does not change application code.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from audit_admission import TEST_PASSWORD, TEST_USER, configure

_, target = configure(sys.argv[1])

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.main import app
from app.models.clinical import Attention
from app.models.organization import Establishment, Office
from app.models.security import Professional
from app.models.audit import AuditLog
from app.models.patient import Patient
from app.repositories.attention import AttentionRepository

engine = create_engine(target)
with Session(engine) as session:
    site = session.scalar(select(Establishment.id).where(Establishment.nombre == "PRUEBA E2E NO REAL"))
    office = session.scalar(select(Office.id).where(Office.codigo == "TEST-E2E"))
    professional = session.scalar(select(Professional.id).where(Professional.colegiatura == "TEST-E2E"))
assert site and office and professional
results = []


def check(name, success):
    results.append({"case": name, "pass": bool(success)})
    assert success, name


with TestClient(app, base_url="http://localhost") as client:
    login = client.post("/api/v1/auth/login", json={"nombre_usuario": TEST_USER, "password": TEST_PASSWORD})
    assert login.status_code == 200
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]

    def request(name, method, route, status, payload=None):
        response = client.request(method, "/api/v1" + route, json=payload)
        check(name + " HTTP " + str(status), response.status_code == status)
        return response.json()

    stamp = datetime.now().strftime("%H%M%S")
    patient = request("Alta adulta ficticia", "POST", "/patients", 201, {
        "tipo_documento_codigo": "DNI", "numero_documento": "99" + stamp,
        "primer_nombre": "PUERPERIO", "apellido_paterno": "PRUEBA", "apellido_materno": "FICTICIA",
        "fecha_nacimiento": "1994-02-10", "sexo_codigo": "F", "condicion": "NO GESTANTE",
        "establecimiento_registro_id": site, "historia_clinica": "PUERPERIO-" + stamp,
    })
    pid = patient["id"]
    base = dict(paciente_id=pid, establecimiento_id=site, consultorio_id=office,
                profesional_id=professional, modalidad_atencion_codigo="AMBULATORIA",
                fecha_atencion="2026-10-01T09:00:00", grupo_atencion_codigo="PUERPERAS",
                peso_kg=60, talla_cm=160, presion_sistolica=110, presion_diastolica=70)
    pregnant = request("Atención gestante previa", "POST", "/atenciones", 201, {
        **base, "fecha_atencion": "2026-09-01T09:00:00", "grupo_atencion_codigo": "GESTANTES",
        "tipo_embarazo_codigo": "UNICO", "peso_antes_embarazo_kg": 55,
        "fecha_probable_parto": "2026-09-20",
    })
    current = request("Condición tras gestante", "GET", f"/patients/{pid}", 200)
    check("Sincroniza GESTANTE", current["condicion"] == "GESTANTE")
    ids = []
    for mode in ("AMBULATORIA", "EMERGENCIA"):
        saved = request("Puérpera " + mode, "POST", "/atenciones", 201,
                        {**base, "modalidad_atencion_codigo": mode})
        ids.append(saved["id"])
        fetched = request("Recuperar " + mode, "GET", f"/atenciones/{saved['id']}", 200)
        check("Grupo y modalidad recuperados " + mode,
              fetched["grupo_atencion_codigo"] == "PUERPERAS" and fetched["modalidad_atencion_codigo"] == mode)
        check("Sin arrastre obstétrico " + mode, all(fetched[key] is None for key in (
            "tipo_embarazo_codigo", "peso_antes_embarazo_kg", "fecha_probable_parto")))
        check("FUA puerperal sin FPP " + mode, fetched["fua_impresion"]["grupo_atencion_codigo"] == "PUERPERAS"
              and fetched["fua_impresion"]["fecha_probable_parto"] is None)
        with Session(engine) as session:
            row = session.get(Attention, saved["id"])
            check("Persistencia MySQL " + mode, row.grupo_atencion_codigo == "PUERPERAS"
                  and row.modalidad_atencion_codigo == mode and row.fua_impresion == fetched["fua_impresion"])
        for key, value in (("tipo_embarazo_codigo", "UNICO"), ("peso_antes_embarazo_kg", 55),
                           ("fecha_probable_parto", "2026-12-01"),
                           ("valoracion_nutricional", {"edad_gestacional_semanas": 30})):
            request("Rechazo " + mode + " / " + key, "POST", "/atenciones", 422,
                    {**base, "modalidad_atencion_codigo": mode, key: value})
    with Session(engine) as session:
        check("Intentos rechazados no crean atenciones", session.scalar(
            select(func.count()).select_from(Attention).where(Attention.paciente_id == pid)) == 3)
    original = request("Recuperar gestación histórica", "GET", f"/atenciones/{pregnant['id']}", 200)
    check("Gestación histórica intacta", original["fua_impresion"] == pregnant["fua_impresion"]
          and original["grupo_atencion_codigo"] == "GESTANTES")
    current = request("Revisar condición de ficha", "GET", f"/patients/{pid}", 200)
    check("Sincroniza PUERPERA sin PATCH adicional", current["condicion"] == "PUERPERA")
    general = request("Grupo general no sobrescribe condición", "POST", "/atenciones", 201,
                      {**base, "grupo_atencion_codigo": "NINOS_ADOLESCENTES_ADULTOS_MAYORES"})
    ids.append(general["id"])
    current = request("Recuperar condición actualizada", "GET", f"/patients/{pid}", 200)
    check("General conserva PUERPERA", current["condicion"] == "PUERPERA")
    with Session(engine) as session:
        logs = session.scalars(select(AuditLog).where(
            AuditLog.tabla_nombre == "pacientes", AuditLog.registro_id == pid,
            AuditLog.accion == "UPDATE").order_by(AuditLog.id)).all()
        check("Solo se auditan cambios efectivos", len(logs) == 2)
        check("Auditoría de transición gestante", logs[0].datos_anteriores["condicion"] == "NO GESTANTE"
              and logs[0].datos_nuevos == {"condicion": "GESTANTE", "atencion_id": pregnant["id"]})
        check("Auditoría de transición puérpera", logs[1].datos_anteriores["condicion"] == "GESTANTE"
              and logs[1].datos_nuevos == {"condicion": "PUERPERA", "atencion_id": ids[0]})
    # Fail after the patient update has been staged: neither write may survive.
    with patch.object(AttentionRepository, "add_audit", side_effect=RuntimeError("TEST_ROLLBACK")):
        try:
            client.post("/api/v1/atenciones", json={**base, "grupo_atencion_codigo": "GESTANTES"})
        except RuntimeError as error:
            check("Fallo posterior al cambio de condición", str(error) == "TEST_ROLLBACK")
        else:
            raise AssertionError("Expected transaction failure")
    with Session(engine) as session:
        check("Rollback de condición", session.get(Patient, pid).condicion == "PUERPERA")
        check("Rollback de atención", session.scalar(select(func.count()).select_from(Attention)
              .where(Attention.paciente_id == pid)) == 4)
        check("Rollback de auditoría", session.scalar(select(func.count()).select_from(AuditLog)
              .where(AuditLog.tabla_nombre == "pacientes", AuditLog.registro_id == pid,
                     AuditLog.accion == "UPDATE")) == 2)

report = {"database": target.database, "patient_id": pid, "attention_ids": [pregnant["id"], *ids], "cases": results}
Path(__file__).with_name("puerpera_sync_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"passed": len(results), "failed": 0, "patient_id": pid, "attention_ids": report["attention_ids"]}))
engine.dispose()
