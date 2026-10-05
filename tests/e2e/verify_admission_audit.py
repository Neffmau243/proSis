"""Follow-up checks against the existing isolated admission audit database.

Preserves the original run's evidence. Updates insurance only on the synthetic
patient with HC TEST-112525-1. Other checks are reads or rejected input probes.
"""

import json
from pathlib import Path
import sys

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from audit_admission import TEST_PASSWORD, TEST_USER, configure
from app.models.patient import Patient
from app.models.clinical import Attention


def main(database):
    _, target = configure(database)
    engine = create_engine(target)
    with Session(engine) as session:
        patient = session.scalar(select(Patient).where(Patient.historia_clinica == "TEST-112525-1"))
        assert patient is not None and patient.primer_nombre == "FICTICIO1", "Wrong test scene"
        patient_id = patient.id
    checks = []
    with httpx.Client(base_url="http://127.0.0.1:8001/api/v1", timeout=20) as client:
        login = client.post("/auth/login", json={"nombre_usuario": TEST_USER, "password": TEST_PASSWORD})
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["access_token"]

        def check(name, ok, **evidence):
            item = {"case": name, "pass": bool(ok), **evidence}
            checks.append(item)
            print(json.dumps(item, ensure_ascii=False), flush=True)

        payload = {"tipo_documento_codigo": "DNI", "numero_documento": "REJECTED-E2E", "fecha_nacimiento": "1990-01-01", "primer_nombre": "PRUEBA RECHAZADA E2E"}
        for name, change in [
            ("Documento tipo inexistente", {"tipo_documento_codigo": "INVALID"}),
            ("Seguro inexistente", {"seguro_id": 99999999}),
        ]:
            response = client.post("/patients", json={**payload, **change})
            check(name, response.status_code == 422, status=response.status_code, detail=response.json())

        # Verify PATCH through a separate GET and a separate SQL session, not
        # just the returned object of the update request.
        for insurance in client.get("/catalogos/seguros").json():
            response = client.patch(f"/patients/{patient_id}", json={"seguro_id": insurance["id"]})
            fetched = client.get(f"/patients/{patient_id}")
            with Session(engine) as session:
                persisted = session.get(Patient, patient_id).seguro_id
            check(f"Seguro {insurance['codigo']} PATCH/GET/MySQL", response.status_code == 200 and fetched.status_code == 200 and fetched.json()["seguro_id"] == insurance["id"] == persisted)

        # Read all saved browser scenarios and compare API/SQL/FUA snapshot.
        expected = {
            11: (15, "AMBULATORIA", "NINOS_ADOLESCENTES_ADULTOS_MAYORES", "NINO"),
            12: (16, "EMERGENCIA", "NINOS_ADOLESCENTES_ADULTOS_MAYORES", "ADULTO_MAYOR"),
            13: (3, "AMBULATORIA", "GESTANTES", "ADULTO"),
            14: (3, "EMERGENCIA", "PUERPERAS", "ADULTO"),
        }
        for ident, wanted in expected.items():
            response = client.get(f"/atenciones/{ident}")
            body = response.json()
            with Session(engine) as session:
                row = session.get(Attention, ident)
                actual = (row.paciente_id, row.modalidad_atencion_codigo, row.grupo_atencion_codigo, row.grupo_etario_codigo) if row else None
            keys = ("paciente_id", "modalidad_atencion_codigo", "grupo_atencion_codigo", "grupo_etario_codigo")
            check(f"Atencion UI {ident} GET/MySQL", response.status_code == 200 and tuple(body.get(k) for k in keys) == actual == wanted, expected=wanted, actual=actual)
            if response.status_code == 200:
                snapshot = body["fua_impresion"]
                check(f"Atencion UI {ident} FUA modalidad/grupo", snapshot["tipo_atencion"] == wanted[1] and snapshot["grupo_atencion_codigo"] == wanted[2])
                if ident == 13:
                    check("Gestante conserva datos obstetricos", body["tipo_embarazo_codigo"] == "UNICO" and body["peso_antes_embarazo_kg"] == "55.00" and body["fecha_probable_parto"] == "2027-03-01")
                if ident == 14:
                    check("Cambio UI a puerpera limpia datos obstetricos", all(body[k] is None for k in ("tipo_embarazo_codigo", "peso_antes_embarazo_kg", "fecha_probable_parto")))

        original = client.get("/atenciones/1").json()["fua_impresion"]
        current = client.get("/patients/3").json()
        check("FUA historica mantiene documento original tras PATCH", original["tipo_documento"] == "DNI" and original["numero_documento"] == "82000002" and current["tipo_documento_codigo"] == "DE" and current["numero_documento"] == "DEUI000033")

    engine.dispose()
    output = Path(__file__).with_name(f"{database}_followup.json")
    output.write_text(json.dumps({"database": database, "checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checks": len(checks), "passed": sum(c["pass"] for c in checks), "report": str(output)}))
    return 0 if all(c["pass"] for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
