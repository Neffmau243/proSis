"""Pure, repeatable import decisions. No writes and no automatic identity merges."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
import re

from app.domain.age import calendar_age

from .normalization import clean_text, dni, normalized_name, positive_int, source_date, text_problems

VERSION = "2.0.0"
# Province 0401 cross-checked against the official territorial table:
# https://www.sunat.gob.pe/legislacion/superin/2000/048_01.htm
# Full name of 040129 also checked against INEI's district table.
DISTRICTS = dict(zip((f"0401{i:02d}" for i in range(1, 30)), (
    "AREQUIPA", "ALTO SELVA ALEGRE", "CAYMA", "CERRO COLORADO", "CHARACATO",
    "CHIGUATA", "JACOBO HUNTER", "LA JOYA", "MARIANO MELGAR", "MIRAFLORES",
    "MOLLEBAYA", "PAUCARPATA", "POCSI", "POLOBAYA", "QUEQUEÑA", "SABANDÍA",
    "SACHACA", "SAN JUAN DE SIGUAS", "SAN JUAN DE TARUCANI", "SANTA ISABEL DE SIGUAS",
    "SANTA RITA DE SIGUAS", "SOCABAYA", "TIABAYA", "UCHUMAYO", "VÍTOR", "YANAHUARA",
    "YARABAMBA", "YURA", "JOSÉ LUIS BUSTAMANTE Y RIVERO",
), strict=True))


@dataclass
class Decision:
    issues: list[dict] = field(default_factory=list)
    patient: dict | None = None
    history: dict | None = None
    source_patient: int | None = None  # Original 1-based row in Pacientes, not Codclie.
    state: str = "ARCHIVADO"


@dataclass
class Plan:
    decisions: dict[tuple[str, int], Decision]
    establishments: list[dict]
    insurances: list[dict]
    geography: list[dict]
    summary: dict
    selected: set[tuple[str, int]]


def plan(tables: dict[str, list[dict]], manifest: dict, *, as_of: date, pilot=False) -> Plan:
    decisions = {(t, i): Decision() for t, rows in tables.items() for i in range(1, len(rows)+1)}
    # Audit every cell, including fields that will remain only in the source archive.
    for table, rows in tables.items():
        for i, row in enumerate(rows, 1):
            for key, value in row.items():
                if isinstance(value, str):
                    decisions[table, i].issues.extend({"codigo": c, "campo": key} for c in text_problems(value))

    geography, districts = [], {}
    for row in tables["Provincia"]:
        parts = [row.get(k) for k in ("IdDpto", "IdProvincia", "IdDistrito")]
        if not all(isinstance(v, str) and re.fullmatch(r"[0-9]{2}", v) for v in parts):
            continue
        code = "".join(parts)
        if code not in DISTRICTS or str(row.get("Ubigeo", "")).zfill(6) != code:
            continue
        expected = DISTRICTS[code]
        if normalized_name(row.get("Distrito")) not in {normalized_name(expected), "cercado" if code == "040101" else ""}:
            continue
        districts[normalized_name(row["Distrito"])] = code
        geography.append({"codigo": code, "departamento": "Arequipa", "provincia": "Arequipa", "distrito": expected})

    establishments, sites = [], defaultdict(list)
    renaes = Counter(r.get("Renaes") for r in tables["EESS"])
    site_codes = Counter(r.get("Codigo") for r in tables["EESS"])
    for i, row in enumerate(tables["EESS"], 1):
        decision = decisions["EESS", i]
        name = clean_text(row.get("EESS"), "EESS", decision.issues, 200)
        code = clean_text(row.get("Renaes"), "Renaes", decision.issues, 30)
        if name and code and code.isascii() and code.isdigit() and renaes[row["Renaes"]] == 1 and site_codes[row["Codigo"]] == 1 and positive_int(row["Codigo"]):
            establishments.append({"id": i, "codigo_legacy": row["Codigo"], "codigo_renaes": code, "nombre": name})
            sites[normalized_name(name)].append(i)
            decision.state = "CATALOGO"
        else:
            decision.issues.append({"codigo": "establishment_unresolved", "campo": "Renaes"})

    insurances = []
    insurance_map = {}
    for label in sorted({r.get("Seguro") or "" for r in tables["Pacientes"]}):
        key = normalized_name(label)
        if key in {"sin seguro", "essalud"}:
            insurance_map[key] = "SIN_SEGURO" if key == "sin seguro" else "ESSALUD"
        elif label and not text_problems(label) and len(label.strip()) <= 100 and not label.isdigit():
            code = f"LEGACY_PLAN_{len(insurances)+1:02d}"
            insurances.append({"codigo": code, "nombre": label.strip()})
            insurance_map[key] = code

    patients = tables["Pacientes"]
    docs = Counter(dni(r.get("N°_DNI")) for r in patients)
    codes = Counter(r.get("Codclie") for r in patients)
    # Same name/date with different documents is flagged; no merge is attempted.
    identities = Counter(tuple(normalized_name(r.get(k)) for k in ("Apellido_Paterno", "Apellido_Materno", "Primer_Nombre", "Otros_Nombres", "Fecha_nacimiento")) for r in patients)
    source_ids = defaultdict(list)
    history_numbers = Counter(r.get("Historia_Clinica", "").strip() if isinstance(r.get("Historia_Clinica"), str) else None for r in patients)
    for i, row in enumerate(patients, 1):
        d = decisions["Pacientes", i]
        issues = d.issues
        code = positive_int(row.get("Codclie"))
        if code:
            source_ids[code].append(i)
        document = dni(row.get("N°_DNI"))
        birth = source_date(row.get("Fecha_nacimiento"), "Fecha_nacimiento", issues, as_of=as_of, required=True)
        blocked = False
        for condition, reason in (
            (document is None, "invalid_or_missing_dni"),
            (document is not None and docs[document] > 1, "duplicate_dni"),
            (code is None or codes[code] > 1, "invalid_or_duplicate_codclie"),
            (birth is None, "invalid_or_missing_birth_date"),
            (identities[tuple(normalized_name(row.get(k)) for k in ("Apellido_Paterno", "Apellido_Materno", "Primer_Nombre", "Otros_Nombres", "Fecha_nacimiento"))] > 1, "duplicate_name_birth"),
        ):
            if condition:
                issues.append({"codigo": reason, "campo": "identidad"})
                blocked = True
        values = {"id": i, "codclie_legacy": code, "tipo_documento_codigo": "DNI", "numero_documento": document, "fecha_nacimiento": birth.date() if birth else None}
        mapping = {
            "Historia_Clinica": ("historia_clinica", 255), "Historia_Familiar": ("historia_familiar", 65535),
            "Apellido_Paterno": ("apellido_paterno", 100), "Apellido_Materno": ("apellido_materno", 100),
            "Primer_Nombre": ("primer_nombre", 100), "Otros_Nombres": ("otros_nombres", 150),
            "Localidad": ("localidad", 150), "Dirección": ("direccion", 300), "Condicion": ("condicion", 100),
        }
        for source, (target, limit) in mapping.items():
            values[target] = clean_text(row.get(source), source, issues, limit)
            if row.get(source) and values[target] is None:
                blocked = True  # Do not promote a partial, damaged identity/address.
        if not any(values[k] for k in ("apellido_paterno", "apellido_materno", "primer_nombre", "otros_nombres")):
            issues.append({"codigo": "missing_names", "campo": "identidad"})
            blocked = True
        registered = source_date(row.get("Fecha_inscripcion"), "Fecha_inscripcion", issues, as_of=as_of)
        values["fecha_inscripcion"] = registered.date() if registered else None
        if registered and birth and registered < birth:
            issues.append({"codigo": "registration_before_birth", "campo": "Fecha_inscripcion"})
            values["fecha_inscripcion"] = None
        if values["fecha_inscripcion"] == date(2016, 1, 1):
            issues.append({"codigo": "possible_default_registration_date", "campo": "Fecha_inscripcion"})
        values["sexo_codigo"] = {"femenino": "F", "masculino": "M"}.get(normalized_name(row.get("Sexo")))
        if row.get("Sexo") and values["sexo_codigo"] is None:
            issues.append({"codigo": "sex_unresolved", "campo": "Sexo"})
        values["ubigeo_residencia_codigo"] = districts.get(normalized_name(row.get("Distrito")))
        if values["ubigeo_residencia_codigo"] is None:
            issues.append({"codigo": "district_unresolved", "campo": "Distrito"})
        # Locality/address stay literal text; no unsupported district/locality FK.
        matches = sites.get(normalized_name(row.get("Establecimiento")), [])
        values["establecimiento_registro_id"] = matches[0] if len(matches) == 1 else None
        if values["establecimiento_registro_id"] is None:
            issues.append({"codigo": "registration_site_unresolved", "campo": "Establecimiento"})
        values["seguro_codigo"] = insurance_map.get(normalized_name(row.get("Seguro")))
        if values["seguro_codigo"] is None:
            issues.append({"codigo": "insurance_unresolved", "campo": "Seguro"})
        # A source plan label is not proof of current SIS accreditation.
        diresa, kind, number = (row.get(k) for k in ("Arequipa_040", "Arequipa_2", "Arequipa_SIS"))
        sis_values = [v.strip().upper() if isinstance(v, str) else "" for v in (diresa, kind, number)]
        if any(sis_values):
            valid = bool(normalized_name(row.get("Seguro")).startswith("s.i.s.") and re.fullmatch(r"[A-Z0-9]{3}", sis_values[0]) and re.fullmatch(r"[A-Z0-9]{1,2}", sis_values[1]) and re.fullmatch(r"[0-9]{8,9}", sis_values[2]))
            if valid:
                values.update(zip(("sis_diresa", "sis_tipo", "sis_numero"), sis_values, strict=True))
            else:
                issues.append({"codigo": "sis_incomplete_or_inconsistent", "campo": "Arequipa_SIS"})
        if values["historia_clinica"] and history_numbers[values["historia_clinica"]] > 1:
            issues.append({"codigo": "shared_history_number", "campo": "Historia_Clinica"})
        d.patient = None if blocked else values
        d.state = "PENDIENTE" if blocked else "ACEPTADO"

    for i, row in enumerate(tables["Atencion"], 1):
        d = decisions["Atencion", i]
        candidates = source_ids.get(positive_int(row.get("Idcliente")), [])
        history = clean_text(row.get("Historia_Clinica"), "Historia_Clinica", d.issues, 255)
        if len(candidates) == 1:
            d.source_patient = candidates[0]
            other = patients[d.source_patient - 1]
            patient_hc = other.get("Historia_Clinica")
            patient_hc = patient_hc.strip() if isinstance(patient_hc, str) else None
            matched = bool(history and history == patient_hc)
            if not matched:
                d.issues.append({"codigo": "attention_history_mismatch", "campo": "Historia_Clinica"})
        else:
            matched = False
            d.issues.append({"codigo": "attention_patient_unresolved", "campo": "Idcliente"})
        accepted = decisions["Pacientes", d.source_patient].patient if d.source_patient else None
        linked = bool(matched and accepted)
        attended = source_date(row.get("Fecha_atencion"), "Fecha_atencion", d.issues, as_of=as_of, required=True)
        professional = clean_text(row.get("Profesional"), "Profesional", d.issues, 200)
        if not professional:
            d.issues.append({"codigo": "historical_without_professional", "campo": "Profesional"})
        clinical = {k: v for k, v in row.items() if k in {"Edad", "Peso", "Talla", "Peso_PG", "Talla_PG", "Distolica", "Sistolica", "PE", "TE", "PT", "Hora1", "Hora2", "Fecha_atendido"} or k.startswith("Codigo_")}
        # Native JSON cannot represent isolated surrogates. The complete original
        # remains in ASCII-escaped LONGTEXT; a corrupt clinical field is flagged.
        clinical = {k: v for k, v in clinical.items() if not isinstance(v, str) or not text_problems(v)}
        if linked and attended:
            if attended.date() >= accepted["fecha_nacimiento"]:
                age = calendar_age(accepted["fecha_nacimiento"], attended)
                clinical["edad_calculada"] = {"anios": age.years, "meses": age.months, "dias": age.days}
                # Group classification is deliberately not inferred from Condicion.
            else:
                d.issues.append({"codigo": "attention_before_birth", "campo": "Fecha_atencion"})
                linked = False
        d.state = "HISTORICO_VINCULADO" if linked else "HISTORICO_PENDIENTE"
        d.history = {"paciente_id": accepted["id"] if linked else None, "profesional_id": None, "fecha_atencion": attended, "historia_clinica": history, "consultorio_texto": clean_text(row.get("Consultorio"), "Consultorio", d.issues, 150), "profesional_texto": professional, "datos_clinicos": clinical, "vinculo_estado": d.state}

    # References use an independent identity namespace. Codclie is not a patient FK.
    for i, _row in enumerate(tables["Pacientes_ref"], 1):
        decisions["Pacientes_ref", i].state = "PENDIENTE"
        decisions["Pacientes_ref", i].issues.append({"codigo": "reference_identity_requires_review", "campo": "Codclie"})

    selected = set(decisions)
    if pilot:
        selected = {(table, i) for table, rows in tables.items() if table not in {"Pacientes", "Atencion", "Pacientes_ref"} for i in range(1, len(rows)+1)}
        for table in ("Pacientes", "Atencion", "Pacientes_ref"):
            selected.update((table, i) for i in range(1, min(len(tables[table]), 100)+1))
            seen = Counter()
            for key, decision in decisions.items():
                if key[0] != table:
                    continue
                categories = {x["codigo"] for x in decision.issues} | {decision.state}
                if any(seen[c] < 3 for c in categories):
                    selected.add(key)
                    seen.update(categories)
        # Keep source patient dependencies, using decisions from the FULL input
        # so a duplicate outside the pilot can never slip into its accepted set.
        selected.update(("Pacientes", decisions[k].source_patient) for k in list(selected) if decisions[k].source_patient)
    states = Counter(decisions[k].state for k in selected)
    issues = Counter(issue["codigo"] for k in selected for issue in decisions[k].issues)
    summary = {"version": VERSION, "as_of": as_of.isoformat(), "mode": "pilot" if pilot else "full", "source_rows": sum(map(len, tables.values())), "archive_rows": len(selected), "patients_accepted": sum(decisions[k].patient is not None for k in selected), "historical_attentions": sum(decisions[k].history is not None for k in selected), "states": dict(sorted(states.items())), "issues": dict(sorted(issues.items())), "source_count_discrepancies": [{"table": t["name"], "reported": t["reported_count"], "enumerated": t["rows"]} for t in manifest["tables"] if t.get("count_mismatch")]}
    return Plan(decisions, establishments, insurances, geography, summary, selected)
