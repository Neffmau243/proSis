"""Create a clinical user linked to a real, already-seeded professional.

Unlike ``seed_demo_data``, this command adds no fictional patients or
encounters: it only links a PROFESIONAL account to a professional of the
catalog. Use it to test the admission flow on a database that carries only real
catalogs and real professionals.
"""

from __future__ import annotations

import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_format
from app.models.audit import AuditLog
from app.models.organization import OfficeProfessional
from app.models.security import Professional, Role, User, UserRole


def _select_professional(session, numero_documento: str | None) -> Professional:
    """Return the requested professional, or one with an active assignment.

    Preferring a professional with a current office assignment keeps the created
    account immediately usable for registering attentions.
    """

    if numero_documento is not None:
        professional = session.scalar(
            select(Professional).where(
                Professional.numero_documento == numero_documento.strip()
            )
        )
        if professional is None:
            raise RuntimeError(
                f"No existe un profesional con documento {numero_documento!r}; "
                "ejecute las migraciones antes de crear la cuenta."
            )
        return professional

    professional = session.scalar(
        select(Professional)
        .join(OfficeProfessional, OfficeProfessional.profesional_id == Professional.id)
        .where(Professional.activo.is_(True), OfficeProfessional.fecha_fin.is_(None))
        .where(~Professional.usuario.has())
        .order_by(Professional.id)
    )
    if professional is None:
        raise RuntimeError(
            "No hay profesionales libres con asignación vigente; ejecute las "
            "migraciones antes de crear la cuenta clínica."
        )
    return professional


def create_professional_user(
    username: str,
    password: str,
    *,
    numero_documento: str | None = None,
) -> int:
    normalized_username = username.strip()
    if len(normalized_username) < 3:
        raise ValueError("El nombre de usuario debe tener al menos 3 caracteres.")
    validate_password_format(password)

    session = SessionLocal()
    try:
        if session.scalar(
            select(User.id).where(User.nombre_usuario == normalized_username)
        ):
            raise ValueError("Ese usuario ya existe; no se creó ninguna cuenta.")
        professional_role = session.scalar(
            select(Role).where(Role.codigo == "PROFESIONAL")
        )
        if professional_role is None:
            raise RuntimeError("No existe el rol PROFESIONAL. Ejecute las migraciones.")
        professional = _select_professional(session, numero_documento)
        linked = session.scalar(
            select(User).where(User.profesional_id == professional.id)
        )
        if linked is not None:
            raise RuntimeError(
                f"El profesional {professional.nombre_completo!r} ya está vinculado "
                f"al usuario {linked.nombre_usuario!r}; no se puede reutilizar."
            )
        user = User(
            profesional_id=professional.id,
            nombre_usuario=normalized_username,
            password_hash=hash_password(password),
        )
        session.add(user)
        session.flush()
        session.add(UserRole(usuario_id=user.id, rol_id=professional_role.id))
        session.add(
            AuditLog(
                usuario_id=None,
                tabla_nombre="usuarios",
                registro_id=user.id,
                accion="BOOTSTRAP",
                datos_anteriores=None,
                datos_nuevos={
                    "id": user.id,
                    "nombre_usuario": user.nombre_usuario,
                    "roles": ["PROFESIONAL"],
                    "profesional_id": professional.id,
                    "profesional": professional.nombre_completo,
                },
            )
        )
        session.commit()
        return user.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crea un usuario PROFESIONAL vinculado a un profesional real."
    )
    parser.add_argument("--username", required=True, help="Nombre de usuario clínico.")
    parser.add_argument(
        "--password",
        help="Evite pasarla por línea de comandos; si se omite se solicita de forma oculta.",
    )
    parser.add_argument(
        "--documento",
        help="DNI del profesional a vincular; si se omite se elige uno con asignación vigente.",
    )
    args = parser.parse_args()
    password = args.password or getpass("Contraseña inicial (8 dígitos): ")
    confirmation = password if args.password else getpass("Repita la contraseña: ")
    if password != confirmation:
        raise ValueError("Las contraseñas no coinciden.")
    user_id = create_professional_user(
        args.username, password, numero_documento=args.documento
    )
    print(f"Usuario PROFESIONAL creado con id {user_id}.")


if __name__ == "__main__":
    main()
