"""Manual HTTP/MySQL audit, exclusively in a fresh local test database.

Setup never reuses or drops a database. No production code or live patients are
modified. Start the real API with `serve`; use `matrix` and the real Vue UI.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import get_settings

TEST_USER = "auditoria_e2e"
TEST_PASSWORD = "12345678"  # Disposable local-only account, like integration fixtures.


def configure(database: str):
    settings = get_settings()
    original = make_url(settings.sqlalchemy_database_url)
    if (
        settings.environment != "development"
        or original.host not in {"localhost", "127.0.0.1"}
        or not re.fullmatch(r"ipress_test_admission_[a-z0-9_]+", database)
        or original.database == database
    ):
        raise RuntimeError("Requires development, local MySQL and a distinct audit database.")
    target = original.set(database=database)
    os.environ["DATABASE_URL"] = target.render_as_string(hide_password=False)
    os.environ["CORS_ORIGINS"] = '["http://localhost:5174","http://127.0.0.1:5174"]'
    get_settings.cache_clear()
    return original, target


def setup(original, target):
    from alembic import command
    from alembic.config import Config
    from app.core.security import hash_password
    from app.models.organization import Establishment, Office, OfficeProfessional, Ubigeo
    from app.models.security import Professional, Role, User, UserRole

    # CREATE (not IF NOT EXISTS): an existing database is never reused or reset.
    server = create_engine(original.set(database=None))
    with server.connect() as connection:
        connection.execute(text(f"CREATE DATABASE `{target.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    server.dispose()
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    engine = create_engine(target)
    with Session(engine) as session:
        ubigeo = Ubigeo(codigo="999999", departamento="PRUEBA", provincia="PRUEBA", distrito="E2E FICTICIO")
        session.add(ubigeo)
        session.flush()
        site = Establishment(nombre="PRUEBA E2E NO REAL", ubigeo_codigo=ubigeo.codigo, activo=True)
        professional = Professional(nombre_completo="PRUEBA E2E PROFESIONAL", colegiatura="TEST-E2E", activo=True)
        session.add_all([site, professional])
        session.flush()
        office = Office(establecimiento_id=site.id, codigo="TEST-E2E", nombre="PRUEBA E2E CONSULTORIO", activo=True)
        session.add(office)
        session.flush()
        session.add(OfficeProfessional(consultorio_id=office.id, profesional_id=professional.id, fecha_inicio=date(2020, 1, 1), es_responsable=True))
        user = User(nombre_usuario=TEST_USER, password_hash=hash_password(TEST_PASSWORD), profesional_id=professional.id)
        session.add(user)
        session.flush()
        role = session.scalar(select(Role).where(Role.codigo == "PROFESIONAL"))
        session.add(UserRole(usuario_id=user.id, rol_id=role.id))
        session.commit()
        print(json.dumps({"database": target.database, "site": site.id, "office": office.id, "professional": professional.id, "test_user": TEST_USER}))
    engine.dispose()


def matrix(target):
    import httpx
    from app.models.organization import Establishment, Office
    from app.models.security import Professional
    from app.models.patient import Patient
    from app.models.clinical import Attention

    engine = create_engine(target)
    with Session(engine) as session:
        site = session.scalar(select(Establishment.id).where(Establishment.nombre == "PRUEBA E2E NO REAL"))
        office = session.scalar(select(Office.id).where(Office.codigo == "TEST-E2E"))
        professional = session.scalar(select(Professional.id).where(Professional.colegiatura == "TEST-E2E"))
    assert site and office and professional
    client = httpx.Client(base_url="http://127.0.0.1:8001/api/v1", timeout=30)
    login = client.post("/auth/login", json={"nombre_usuario": TEST_USER, "password": TEST_PASSWORD})
    assert login.status_code == 200, login.text
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    results = []
    stamp = datetime.now().strftime("%H%M%S")
    serial = 0

    def record(case, response, expected, checks=None):
        passed = response.status_code == expected and (checks is None or checks(response.json()))
        item = {"case": case, "status": response.status_code, "expected": expected, "pass": passed}
        if response.status_code >= 400 or not passed:
            item["detail"] = response.json()
        elif isinstance(response.json(), dict) and "id" in response.json():
            item["id"] = response.json()["id"]
        results.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
        return response

    def payload(**overrides):
        nonlocal serial
        serial += 1
        return {"tipo_documento_codigo": "DNI", "numero_documento": f"{81000000 + serial}", "fecha_nacimiento": "1990-01-10", "apellido_paterno": "PRUEBA", "apellido_materno": "E2E", "primer_nombre": f"FICTICIO{serial}", "sexo_codigo": "F", "establecimiento_registro_id": site, "historia_clinica": f"TEST-{stamp}-{serial}", **overrides}

    def persisted_patient(response, sent):
        if response.status_code != 201:
            return
        patient_id = response.json()["id"]
        keys = ("tipo_documento_codigo", "numero_documento", "seguro_id", "fecha_nacimiento", "sis_tipo", "sis_numero")
        keys = [k for k in keys if k in sent]
        fetched = client.get(f"/patients/{patient_id}")
        record(f"GET paciente {patient_id}", fetched, 200, lambda b: all(b[k] == sent[k] for k in keys))
        with Session(engine) as session:
            row = session.get(Patient, patient_id)
            ok = all(str(getattr(row, k)) == str(sent[k]) for k in keys)
            results.append({"case": f"MySQL paciente {patient_id}", "pass": ok})

    docs = client.get("/catalogos/tipos-documento").json()
    insurances = client.get("/catalogos/seguros").json()
    print(json.dumps({"document_types": docs, "insurances": insurances}, ensure_ascii=False))
    patients = []
    by_insurance = {}
    for index, insurance in enumerate(insurances):
        doc = docs[index % len(docs)]["codigo"]
        birth = ["2020-03-10", "1950-06-15", "1994-02-10"][index % 3]
        number = f"{82000000 + index}" if doc == "DNI" else f"E2E{stamp}{index:03}"
        values = payload(tipo_documento_codigo=doc, numero_documento=number, fecha_nacimiento=birth, seguro_id=insurance["id"])
        if birth.startswith("2020"):
            values["responsables"] = [{"parentesco": "TUTOR", "nombre_completo": "TUTOR FICTICIO E2E", "es_principal": True}]
        if insurance["codigo"].startswith("SIS"):
            values.update(sis_diresa="040", sis_tipo="2", sis_numero=f"00{index:06}", sis_secuencia="01")
        response = record(f"Alta {doc}, {insurance['codigo']}, nacimiento {birth}", client.post("/patients", json=values), 201)
        persisted_patient(response, values)
        if response.status_code == 201:
            patients.append(response.json())
            by_insurance[insurance["codigo"]] = response.json()

    groups = ["NINOS_ADOLESCENTES_ADULTOS_MAYORES", "GESTANTES", "PUERPERAS"]
    attention_patient = next(p for p in patients if p["fecha_nacimiento"] == "1994-02-10")

    def attention(**overrides):
        return {"paciente_id": attention_patient["id"], "establecimiento_id": site, "consultorio_id": office, "profesional_id": professional, "fecha_atencion": datetime.now().replace(microsecond=0).isoformat(), "modalidad_atencion_codigo": "AMBULATORIA", "grupo_atencion_codigo": groups[0], **overrides}

    for mode in ["AMBULATORIA", "EMERGENCIA"]:
        for group in groups:
            values = attention(modalidad_atencion_codigo=mode, grupo_atencion_codigo=group)
            if group == "GESTANTES":
                values.update(tipo_embarazo_codigo="UNICO", peso_antes_embarazo_kg="55.00", fecha_probable_parto=(date.today() + timedelta(days=150)).isoformat())
            response = record(f"Atencion {mode}/{group}", client.post("/atenciones", json=values), 201)
            if response.status_code == 201:
                ident = response.json()["id"]
                record(f"GET atencion {ident}", client.get(f"/atenciones/{ident}"), 200, lambda b: b["modalidad_atencion_codigo"] == mode and b["grupo_atencion_codigo"] == group and b["fua_impresion"]["tipo_atencion"] == mode and b["fua_impresion"]["grupo_atencion_codigo"] == group)
                with Session(engine) as session:
                    row = session.get(Attention, ident)
                    results.append({"case": f"MySQL atencion {ident}", "pass": row.modalidad_atencion_codigo == mode and row.grupo_atencion_codigo == group})
    for birth in ["2020-03-10", "1950-06-15"]:
        p = next(p for p in patients if p["fecha_nacimiento"] == birth)
        record(f"Atencion edad {birth}", client.post("/atenciones", json=attention(paciente_id=p["id"])), 201)

    changing = patients[0]
    for index, doc in enumerate(docs):
        values = {"tipo_documento_codigo": doc["codigo"], "numero_documento": f"{83000000 + index}" if doc["codigo"] == "DNI" else f"PATCH{stamp}{index}"}
        record(f"PATCH documento {doc['codigo']}", client.patch(f"/patients/{changing['id']}", json=values), 200, lambda b: all(b[k] == v for k, v in values.items()))
        record(f"Relectura documento {doc['codigo']}", client.get(f"/patients/{changing['id']}"), 200, lambda b: all(b[k] == v for k, v in values.items()))
    for insurance in insurances:
        record(f"PATCH seguro {insurance['codigo']}", client.patch(f"/patients/{changing['id']}", json={"seguro_id": insurance["id"]}), 200, lambda b: b["seguro_id"] == insurance["id"])
    record("PATCH seguro sin declarar", client.patch(f"/patients/{changing['id']}", json={"seguro_id": None}), 200, lambda b: b["seguro_id"] is None)

    duplicate = patients[-1]
    record("Documento duplicado", client.post("/patients", json=payload(tipo_documento_codigo=duplicate["tipo_documento_codigo"], numero_documento=duplicate["numero_documento"])), 409)
    record("Menor sin responsable", client.post("/patients", json=payload(fecha_nacimiento="2020-01-01")), 422)
    record("Documento tipo inexistente", client.post("/patients", json=payload(tipo_documento_codigo="INVALID")), 422)
    record("Seguro inexistente", client.post("/patients", json=payload(seguro_id=99999999)), 422)
    record("Documento 31 caracteres", client.post("/patients", json=payload(numero_documento="X" * 31)), 422)
    record("Documento 30 caracteres", client.post("/patients", json=payload(numero_documento="X" * 30)), 201)
    record("Modalidad invalida", client.post("/atenciones", json=attention(modalidad_atencion_codigo="INVALID")), 422)
    record("Grupo invalido", client.post("/atenciones", json=attention(grupo_atencion_codigo="INVALID")), 422)
    record("SIS incompleto", client.post("/patients", json=payload(sis_tipo="2")), 422)

    # Characterize gaps without falsely presenting today's behavior as desired.
    observations = []
    def observe(case, response, keys):
        body = response.json()
        item = {"case": case, "status": response.status_code, "stored": {k: body.get(k) for k in keys} if response.status_code < 300 else body}
        observations.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)

    observe("DNI no numerico de un caracter", client.post("/patients", json=payload(numero_documento="A")), ["id", "tipo_documento_codigo", "numero_documento"])
    probe = client.post("/patients", json=payload(tipo_documento_codigo="PAS", numero_documento=f"PAS{stamp}"))
    if probe.status_code == 201:
        observe("Cambiar solo PAS a DNI conserva numero incompatible", client.patch(f"/patients/{probe.json()['id']}", json={"tipo_documento_codigo": "DNI"}), ["id", "tipo_documento_codigo", "numero_documento"])
    sis = next((v for k, v in by_insurance.items() if k.startswith("SIS")), None)
    no_insurance = next((i for i in insurances if i["codigo"] == "SIN_SEGURO"), None)
    if sis and no_insurance:
        observe("Cambiar SIS a SIN_SEGURO conserva afiliacion", client.patch(f"/patients/{sis['id']}", json={"seguro_id": no_insurance["id"]}), ["id", "seguro_id", "sis_diresa", "sis_tipo", "sis_numero"])
    observe("GENERAL permite datos de embarazo por API", client.post("/atenciones", json=attention(tipo_embarazo_codigo="UNICO", peso_antes_embarazo_kg="55.00")), ["id", "grupo_atencion_codigo", "tipo_embarazo_codigo", "peso_antes_embarazo_kg"])
    observe("Grupo GESTANTES sin datos obstetricos", client.post("/atenciones", json=attention(grupo_atencion_codigo="GESTANTES")), ["id", "grupo_atencion_codigo"])
    client.close()
    engine.dispose()
    result = {"database": target.database, "cases": results, "observations": observations, "patients": [{k: p[k] for k in ["id", "tipo_documento_codigo", "numero_documento", "fecha_nacimiento", "seguro_id"]} for p in patients]}
    output = ROOT / "tests" / "e2e" / f"{target.database}_results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(output), "checks": len(results), "passed": sum(r["pass"] for r in results)}))


def inspect(target):
    engine = create_engine(target)
    with engine.connect() as connection:
        for table, columns in [
            ("pacientes", "id, primer_nombre, tipo_documento_codigo, numero_documento, fecha_nacimiento, seguro_id, sis_tipo, sis_numero, condicion"),
            ("atenciones", "id, paciente_id, modalidad_atencion_codigo, grupo_atencion_codigo, grupo_etario_codigo, tipo_embarazo_codigo"),
        ]:
            print(json.dumps({table: [dict(row) for row in connection.execute(text(f"SELECT {columns} FROM {table} ORDER BY id")).mappings()]}, default=str, ensure_ascii=False))
    engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["setup", "serve", "matrix", "inspect"])
    parser.add_argument("database")
    args = parser.parse_args()
    original, target = configure(args.database)
    if args.action == "setup":
        setup(original, target)
    elif args.action == "serve":
        import uvicorn
        uvicorn.run("app.main:app", host="127.0.0.1", port=8001)
    elif args.action == "matrix":
        matrix(target)
    else:
        inspect(target)
