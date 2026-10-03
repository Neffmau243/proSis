"""Real API + MySQL nutrition audit in an existing isolated synthetic database."""
import sys
import json
from pathlib import Path
from uuid import uuid4

from audit_admission import configure, TEST_USER, TEST_PASSWORD

_, target = configure(sys.argv[1])
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.main import app
from app.models.clinical import Attention
from app.models.organization import Establishment, Office
from app.models.security import Professional

command.upgrade(Config("alembic.ini"), "head")
engine = create_engine(target)
with Session(engine) as db:
    site = db.scalar(select(Establishment.id).where(Establishment.nombre == "PRUEBA E2E NO REAL"))
    office = db.scalar(select(Office.id).where(Office.codigo == "TEST-E2E"))
    professional = db.scalar(select(Professional.id).where(Professional.colegiatura == "TEST-E2E"))
assert site and office and professional
run = uuid4().hex[:10]
general = "NINOS_ADOLESCENTES_ADULTOS_MAYORES"
cases = [
    ("INFANTIL", "2023-01-01", 14, 95, general),
    ("ESCOLAR", "2018-01-01", 25, 125, general),
    ("ESCOLAR", "2012-01-01", 50, 160, general),
    ("ADULTO", "1994-01-01", 60, 160, general),
    ("ADULTO_MAYOR", "1950-01-01", 60, 160, general),
    ("GESTANTE", "1994-01-01", 70, 160, "GESTANTES"),
    ("PUERPERA", "1994-01-01", 70, 160, "PUERPERAS"),
]
report = {"database": target.database, "cases": []}
with TestClient(app, base_url="http://localhost") as client:
    def request(method, route, data=None, status=200):
        response = client.request(method, "/api/v1" + route, json=data)
        assert response.status_code == status, response.text[:700]
        return response.json()
    token = request("POST", "/auth/login", {"nombre_usuario": TEST_USER, "password": TEST_PASSWORD})
    client.headers["Authorization"] = "Bearer " + token["access_token"]
    for index, (group, birth, weight, height, care) in enumerate(cases):
        patient = dict(tipo_documento_codigo="PAS", numero_documento=f"NUT{run}{index}",
            primer_nombre="PRUEBA", apellido_paterno="NUTRICION", apellido_materno="FICTICIA",
            sexo_codigo="F", fecha_nacimiento=birth, establecimiento_registro_id=site,
            historia_clinica=f"NUT-{run}-{index}", condicion="NO GESTANTE")
        if group in {"INFANTIL", "ESCOLAR"}:
            patient["responsables"] = [{"parentesco": "MADRE", "nombre_completo": "RESPONSABLE FICTICIA", "es_principal": True}]
        patient = request("POST", "/patients", patient, 201)
        for mode in ["AMBULATORIA", "EMERGENCIA"]:
            preview_payload = dict(paciente_id=patient["id"], fecha_atencion="2026-10-01T09:00:00", peso_kg=weight, talla_cm=height, grupo_atencion_codigo=care)
            if care == "GESTANTES":
                preview_payload["peso_antes_embarazo_kg"] = 60
            preview = request("POST", "/atenciones/indicadores-nutricionales/vista-previa", preview_payload)
            assert preview["grupo_referencia"] == group
            payload = dict(**preview_payload, establecimiento_id=site, consultorio_id=office, profesional_id=professional, modalidad_atencion_codigo=mode)
            saved = request("POST", "/atenciones", payload, 201)
            fetched = request("GET", f'/atenciones/{saved["id"]}')
            assert saved["valoracion_calculada"] == fetched["valoracion_calculada"] == preview
            with Session(engine) as db:
                row = db.get(Attention, saved["id"])
                assert row.valoracion_calculada == preview
            report["cases"].append({"group": group, "mode": mode, "attention_id": saved["id"], "result": preview})
        # Changing demographics later must not rewrite the encounter's nutrition.
        request("PATCH", f'/patients/{patient["id"]}', {"fecha_nacimiento": "1990-01-01"})
        assert request("GET", f'/atenciones/{saved["id"]}')["valoracion_calculada"] == preview
report["passed"] = len(report["cases"])
Path(__file__).with_name("nutrition_age_results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"database": target.database, "passed": report["passed"]}))
