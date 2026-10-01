"""Real HTTP + MySQL regression cases; synthetic patients in a dedicated DB only."""

from datetime import datetime
import json
import sys
from pathlib import Path

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from audit_admission import configure, TEST_USER, TEST_PASSWORD

_, target = configure(sys.argv[1])
from app.models.patient import Patient
from app.models.clinical import Attention
from app.models.organization import Establishment, Office
from app.models.security import Professional

engine = create_engine(target)
with Session(engine) as session:
    site = session.scalar(
        select(Establishment.id).where(Establishment.nombre == "PRUEBA E2E NO REAL")
    )
    office = session.scalar(select(Office.id).where(Office.codigo == "TEST-E2E"))
    professional = session.scalar(
        select(Professional.id).where(Professional.colegiatura == "TEST-E2E")
    )
assert site and office and professional
client = httpx.Client(base_url="http://127.0.0.1:8001/api/v1", timeout=30)
login = client.post("/auth/login", json={"nombre_usuario": TEST_USER, "password": TEST_PASSWORD})
login.raise_for_status()
client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
insurers = client.get("/catalogos/seguros").json()
sis = next(i["id"] for i in insurers if i["codigo"] == "SIS")
no_sis = next(i["id"] for i in insurers if i["codigo"] == "SIN_SEGURO")
results = []
serial = 0
stamp = datetime.now().strftime("%H%M%S")


def check(name, ok):
    results.append({"case": name, "pass": bool(ok)})
    assert ok, name


def request(name, method, path, expected, **payload):
    response = client.request(method, path, json=payload if payload else None)
    check(f"{name}: HTTP {expected}", response.status_code == expected)
    return response.json()


def patient(**overrides):
    global serial
    serial += 1
    return {
        "tipo_documento_codigo": "DNI",
        "numero_documento": f"{85000000 + serial}",
        "fecha_nacimiento": "1994-02-10",
        "primer_nombre": "FICTICIO",
        "apellido_paterno": "PRUEBA",
        "apellido_materno": "E2E",
        "sexo_codigo": "F",
        "establecimiento_registro_id": site,
        "historia_clinica": f"FIX-{stamp}-{serial}",
        **overrides,
    }


def attention(pid, **overrides):
    return (
        dict(
            paciente_id=pid,
            establecimiento_id=site,
            profesional_id=professional,
            consultorio_id=office,
            fecha_atencion=datetime.now().replace(microsecond=0).isoformat(),
            modalidad_atencion_codigo="AMBULATORIA",
            grupo_atencion_codigo="NINOS_ADOLESCENTES_ADULTOS_MAYORES",
            **overrides,
        )
        if not overrides
        else {
            **attention(pid),
            **overrides,
        }
    )


sis_fields = ("sis_diresa", "sis_tipo", "sis_numero", "sis_secuencia")
affiliation = dict(sis_diresa="040", sis_tipo="2", sis_numero="00112233", sis_secuencia="01")
for bad in ["PASUI000033", "1234567", "123456789", "１２３４５６７８", "1234-678"]:
    request("DNI inválido", "POST", "/patients", 422, **patient(numero_documento=bad))

created = []
for index, kind in enumerate(["DNI", "CE", "PAS", "DE", "OTRO"]):
    birth = ["2020-03-10", "1950-06-15", "1994-02-10"][index % 3]
    payload = patient(
        tipo_documento_codigo=kind,
        numero_documento="00123456" if kind == "DNI" else f"X{stamp}{index}",
        fecha_nacimiento=birth,
        seguro_id=sis,
    )
    payload.update(affiliation)
    if birth.startswith("2020"):
        payload["responsables"] = [
            {"parentesco": "MADRE", "nombre_completo": "MADRE FICTICIA", "es_principal": True}
        ]
    p = request(f"Alta {kind} / {birth}", "POST", "/patients", 201, **payload)
    created.append(p)
    fetched = request(f"Recuperar {kind}", "GET", f"/patients/{p['id']}", 200)
    check(
        f"Persistencia documento {kind}", fetched["numero_documento"] == payload["numero_documento"]
    )
    with Session(engine) as session:
        check(
            f"MySQL documento {kind}",
            session.get(Patient, p["id"]).numero_documento == payload["numero_documento"],
        )

p = created[2]
request(
    "PATCH solo tipo PAS a DNI inválido",
    "PATCH",
    f"/patients/{p['id']}",
    422,
    tipo_documento_codigo="DNI",
)
request(
    "PATCH conjunto válido",
    "PATCH",
    f"/patients/{p['id']}",
    200,
    tipo_documento_codigo="DNI",
    numero_documento="00998877",
)
request(
    "PATCH solo número inválido",
    "PATCH",
    f"/patients/{p['id']}",
    422,
    numero_documento="PASUI000033",
)

old = request("FUA con SIS", "POST", "/atenciones", 201, **attention(p["id"]))
check("SIS presente en FUA inicial", old["fua_impresion"]["sis_numero"] == "00112233")
changed = request("SIS a sin seguro", "PATCH", f"/patients/{p['id']}", 200, seguro_id=no_sis)
check("Afiliación limpia en respuesta", all(changed[k] is None for k in sis_fields))
with Session(engine) as session:
    check(
        "Afiliación limpia en MySQL",
        all(getattr(session.get(Patient, p["id"]), k) is None for k in sis_fields),
    )
fresh = request(
    "Nueva FUA sin seguro",
    "POST",
    "/atenciones",
    201,
    **attention(p["id"], modalidad_atencion_codigo="EMERGENCIA"),
)
check(
    "Nueva FUA sin afiliación residual", all(fresh["fua_impresion"][k] is None for k in sis_fields)
)
historical = request("Releer FUA histórica", "GET", f"/atenciones/{old['id']}", 200)
check("Historia inmutable", historical["fua_impresion"] == old["fua_impresion"])
request("No añadir SIS con sin seguro", "PATCH", f"/patients/{p['id']}", 422, **affiliation)
request("Alta incompatible", "POST", "/patients", 422, **patient(seguro_id=no_sis, **affiliation))

for insurer in insurers:
    changed = request(
        f"Cambiar seguro {insurer['codigo']}",
        "PATCH",
        f"/patients/{p['id']}",
        200,
        seguro_id=insurer["id"],
    )
    check("No resucita afiliación", changed["sis_numero"] is None)
    if insurer.get("regimen") == "SIS" or insurer["codigo"] == "SIS":
        request("Añadir afiliación a plan SIS", "PATCH", f"/patients/{p['id']}", 200, **affiliation)
        request(
            "Limpiar afiliación antes del siguiente plan",
            "PATCH",
            f"/patients/{p['id']}",
            200,
            **dict.fromkeys(sis_fields),
        )

for mode in ["AMBULATORIA", "EMERGENCIA"]:
    for group in ["NINOS_ADOLESCENTES_ADULTOS_MAYORES", "GESTANTES", "PUERPERAS"]:
        for field, value in [
            ("tipo_embarazo_codigo", "UNICO"),
            ("peso_antes_embarazo_kg", 55),
            ("fecha_probable_parto", "2027-03-01"),
        ]:
            if group != "GESTANTES":
                request(
                    f"Rechazar {field} en {mode}/{group}",
                    "POST",
                    "/atenciones",
                    422,
                    **attention(
                        p["id"],
                        modalidad_atencion_codigo=mode,
                        grupo_atencion_codigo=group,
                        **{field: value},
                    ),
                )
        pregnancy = (
            dict(
                tipo_embarazo_codigo="MULTIPLE",
                peso_antes_embarazo_kg=55,
                fecha_probable_parto="2027-03-01",
            )
            if group == "GESTANTES"
            else {}
        )
        saved = request(
            f"Atención válida {mode}/{group}",
            "POST",
            "/atenciones",
            201,
            **attention(
                p["id"], modalidad_atencion_codigo=mode, grupo_atencion_codigo=group, **pregnancy
            ),
        )
        fetched = request("Recuperar atención", "GET", f"/atenciones/{saved['id']}", 200)
        check(
            "Modo/grupo recuperados",
            fetched["modalidad_atencion_codigo"] == mode
            and fetched["grupo_atencion_codigo"] == group,
        )
        with Session(engine) as session:
            row = session.get(Attention, saved["id"])
            check(
                "MySQL modo/grupo",
                row.modalidad_atencion_codigo == mode and row.grupo_atencion_codigo == group,
            )

for p in created:
    saved = request("FUA documento y edad", "POST", "/atenciones", 201, **attention(p["id"]))
    snapshot = saved["fua_impresion"]
    check("Identidad conservada en snapshot", bool(snapshot["numero_documento"]))
    check(
        "TDI no inventado",
        snapshot["tdi"] == {"DNI": "2", "CE": "3"}.get(snapshot["tipo_documento"]),
    )

output = Path(__file__).with_name(f"{target.database}_regression.json")
output.write_text(
    json.dumps({"database": target.database, "cases": results}, indent=2), encoding="utf-8"
)
print(json.dumps({"passed": len(results), "failed": 0, "database": target.database}))
client.close()
engine.dispose()
