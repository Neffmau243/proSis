"""Load repeatable development fixtures required by the API demonstration.

This command is deliberately separate from Alembic migrations: migrations
define the production schema and its minimum reference catalogs, whereas these
records are fictional data intended only for local development and Postman.
It is safe to run more than once; it never deletes or overwrites user data.
"""

from __future__ import annotations

from datetime import date
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.catalog import AgeGroup, Cie10, Profession, ServiceOffering, Specialty
from app.models.organization import (
    Disa,
    Establishment,
    MicroNetwork,
    Network,
    Office,
    OfficeProfessional,
    Ubigeo,
)
from app.models.patient import Patient, PatientResponsible, RiskGroup
from app.models.security import Professional, ProfessionalSpecialty, Role, User, UserRole

Entity = TypeVar("Entity")

# These credentials are deliberately limited to fictional development data.
# ``seed_demo_data`` refuses every environment other than ``development``.
# Never reuse them outside a disposable local database.
DEMO_ADMIN_USERNAME = "admin"
DEMO_ADMIN_PASSWORD = "IpressDev!Admin2026"
DEMO_PROFESSIONAL_USERNAME = "medico.demo"
DEMO_PROFESSIONAL_PASSWORD = "IpressDev!Medico2026"


def _get_or_create(
    session: Session,
    model: type[Entity],
    lookup: dict[str, Any],
    values: dict[str, Any] | None = None,
) -> Entity:
    """Return a natural-key record, creating it without changing existing data."""

    entity = session.scalar(select(model).filter_by(**lookup))
    if entity is not None:
        return entity
    entity = model(**lookup, **(values or {}))
    session.add(entity)
    session.flush()
    return entity


def _ensure_demo_professional_user(session: Session, professional: Professional) -> User:
    """Create the fixed local clinician account without changing existing credentials."""

    professional_role = session.scalar(select(Role).where(Role.codigo == "PROFESIONAL"))
    if professional_role is None:
        raise RuntimeError("No existe el rol PROFESIONAL. Ejecute las migraciones primero.")

    user = session.scalar(
        select(User).where(User.nombre_usuario == DEMO_PROFESSIONAL_USERNAME)
    )
    if user is None:
        linked_user = session.scalar(
            select(User).where(User.profesional_id == professional.id)
        )
        if linked_user is not None:
            raise RuntimeError(
                "El profesional demo ya está vinculado a otro usuario; "
                "no se puede crear medico.demo de forma segura."
            )
        user = User(
            profesional_id=professional.id,
            nombre_usuario=DEMO_PROFESSIONAL_USERNAME,
            password_hash=hash_password(DEMO_PROFESSIONAL_PASSWORD),
        )
        session.add(user)
        session.flush()
        session.add(UserRole(usuario_id=user.id, rol_id=professional_role.id))
        return user

    if user.profesional_id != professional.id:
        raise RuntimeError(
            "El usuario medico.demo ya está vinculado a otro profesional; "
            "no se puede reutilizar como cuenta demo."
        )
    return user


def seed_demo_data() -> dict[str, int]:
    """Create the development-only prerequisites for all exposed API workflows."""

    environment = get_settings().environment.strip().casefold()
    if environment != "development":
        raise RuntimeError(
            "Las semillas de demostración solo pueden ejecutarse con ENVIRONMENT=development."
        )

    session = SessionLocal()
    try:
        # The initial migration creates these codes but deliberately has no
        # clinical ranges.  Fill only entirely unset ranges, preserving any
        # configuration that an ADMIN has already established.
        for code, name, minimum, maximum in (
            ("NINO", "Niño", 0, 143),
            ("ADOLESCENTE", "Adolescente", 144, 215),
            ("ADULTO", "Adulto", 216, 719),
            ("ADULTO_MAYOR", "Adulto mayor", 720, None),
        ):
            group = session.get(AgeGroup, code)
            if group is None:
                group = AgeGroup(
                    codigo=code,
                    nombre=name,
                    edad_minima_meses=minimum,
                    edad_maxima_meses=maximum,
                )
                session.add(group)
            elif group.edad_minima_meses is None and group.edad_maxima_meses is None:
                group.edad_minima_meses = minimum
                group.edad_maxima_meses = maximum

        medicine = _get_or_create(session, Profession, {"nombre": "Medicina"})
        administration = _get_or_create(
            session, Profession, {"nombre": "Administración sanitaria"}
        )
        specialty = _get_or_create(
            session,
            Specialty,
            {"codigo": "MED_GEN"},
            {"nombre": "Medicina general", "grupo": "Clínica"},
        )
        _get_or_create(
            session,
            ServiceOffering,
            {"codigo": "CONSULTA_MED"},
            {"descripcion": "Consulta médica general", "grupo": "Consulta"},
        )
        _get_or_create(
            session,
            Cie10,
            {"codigo": "Z00.0"},
            {"descripcion": "Examen médico general", "categoria": "Factores que influyen en el estado de salud"},
        )
        risk = _get_or_create(
            session,
            RiskGroup,
            {"codigo": "RIESGO_DEMO"},
            {"nombre": "Riesgo de demostración", "descripcion": "Registro ficticio para pruebas locales."},
        )

        disa = _get_or_create(
            session, Disa, {"codigo": "DEMO_DISA"}, {"nombre": "DIRESA Demostración"}
        )
        network = _get_or_create(
            session,
            Network,
            {"id_disa": disa.id, "codigo": "DEMO_RED"},
            {"nombre": "Red Demostración"},
        )
        micro_network = _get_or_create(
            session,
            MicroNetwork,
            {"id_red": network.id, "codigo": "DEMO_MICRO"},
            {"nombre": "Microred Demostración"},
        )
        ubigeo = _get_or_create(
            session,
            Ubigeo,
            {"codigo": "040101"},
            {"departamento": "Arequipa", "provincia": "Arequipa", "distrito": "Arequipa", "localidad": "Demo"},
        )
        origin = _get_or_create(
            session,
            Establishment,
            {"codigo_renaes": "DEMO-0001"},
            {
                "id_microred": micro_network.id,
                "nombre": "IPRESS Demo Central",
                "abreviatura": "IPRESS DEMO",
                "ubigeo_codigo": ubigeo.codigo,
                "area_urbana": "URBANA",
            },
        )
        destination = _get_or_create(
            session,
            Establishment,
            {"codigo_renaes": "DEMO-0002"},
            {
                "id_microred": micro_network.id,
                "nombre": "IPRESS Demo Destino",
                "abreviatura": "IPRESS DESTINO",
                "ubigeo_codigo": ubigeo.codigo,
                "area_urbana": "URBANA",
            },
        )
        office = _get_or_create(
            session,
            Office,
            {"establecimiento_id": origin.id, "codigo": "MED-GEN"},
            {"nombre": "Consultorio de medicina general", "especialidad_codigo": specialty.codigo},
        )
        professional = _get_or_create(
            session,
            Professional,
            {"numero_documento": "70000001"},
            {"nombre_completo": "Dra. Andrea Prueba", "profesion_id": medicine.id, "colegiatura": "CMP-DEMO-001"},
        )
        registration_professional = _get_or_create(
            session,
            Professional,
            {"numero_documento": "70000002"},
            {
                "nombre_completo": "Rosa Registro Demo",
                "profesion_id": administration.id,
                "colegiatura": "ADM-DEMO-001",
            },
        )
        _get_or_create(
            session,
            ProfessionalSpecialty,
            {"profesional_id": professional.id, "especialidad_codigo": specialty.codigo},
            {"es_principal": True},
        )
        _get_or_create(
            session,
            OfficeProfessional,
            {
                "consultorio_id": office.id,
                "profesional_id": professional.id,
                "fecha_inicio": date(2020, 1, 1),
            },
            {"es_responsable": True},
        )
        demo_professional_user = _ensure_demo_professional_user(session, professional)

        adult = _get_or_create(
            session,
            Patient,
            {"tipo_documento_codigo": "DNI", "numero_documento": "99900001"},
            {
                "historia_clinica": "HC-DEMO-ADULTO",
                "fecha_nacimiento": date(1990, 5, 10),
                "apellido_paterno": "Prueba",
                "apellido_materno": "Demo",
                "primer_nombre": "Ana",
                "sexo_codigo": "F",
                "ubigeo_residencia_codigo": ubigeo.codigo,
                "establecimiento_registro_id": origin.id,
                "telefono_principal": "999888777",
            },
        )
        minor = _get_or_create(
            session,
            Patient,
            {"tipo_documento_codigo": "DNI", "numero_documento": "99900002"},
            {
                "historia_clinica": "HC-DEMO-MENOR",
                "fecha_nacimiento": date(2017, 5, 10),
                "apellido_paterno": "Prueba",
                "apellido_materno": "Demo",
                "primer_nombre": "Luis",
                "sexo_codigo": "M",
                "ubigeo_residencia_codigo": ubigeo.codigo,
                "establecimiento_registro_id": origin.id,
            },
        )
        _get_or_create(
            session,
            PatientResponsible,
            {"paciente_id": minor.id, "nombre_completo": "María Responsable Demo"},
            {"parentesco": "MADRE", "telefono": "988777666", "es_principal": True},
        )

        session.commit()
        return {
            "establishment_id": origin.id,
            "destination_establishment_id": destination.id,
            "office_id": office.id,
            "professional_id": professional.id,
            "professional_user_id": demo_professional_user.id,
            "registration_professional_id": registration_professional.id,
            "risk_group_id": risk.id,
            "adult_patient_id": adult.id,
            "minor_patient_id": minor.id,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    identifiers = seed_demo_data()
    print("Semillas de demostración creadas o verificadas.")
    for key, value in identifiers.items():
        print(f"{key}={value}")
    print(f"professional_username={DEMO_PROFESSIONAL_USERNAME}")
    print(f"professional_password={DEMO_PROFESSIONAL_PASSWORD}")


if __name__ == "__main__":
    main()
