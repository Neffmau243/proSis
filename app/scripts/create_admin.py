"""Create the first ADMIN user after the database has been migrated."""

from __future__ import annotations

import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_format
from app.models.audit import AuditLog
from app.models.security import Role, User, UserRole


def create_admin(username: str, password: str) -> int:
    normalized_username = username.strip()
    if len(normalized_username) < 3:
        raise ValueError("El nombre de usuario debe tener al menos 3 caracteres.")
    validate_password_format(password)

    session = SessionLocal()
    try:
        if session.scalar(select(User.id).where(User.nombre_usuario == normalized_username)):
            raise ValueError("Ese usuario ya existe; no se creó ningún administrador.")
        admin_role = session.scalar(select(Role).where(Role.codigo == "ADMIN"))
        if admin_role is None:
            raise RuntimeError("No existe el rol ADMIN. Ejecute primero las migraciones.")
        user = User(nombre_usuario=normalized_username, password_hash=hash_password(password))
        session.add(user)
        session.flush()
        session.add(UserRole(usuario_id=user.id, rol_id=admin_role.id))
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
                    "roles": ["ADMIN"],
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
    parser = argparse.ArgumentParser(description="Crea el primer usuario ADMIN de IPRESS.")
    parser.add_argument("--username", required=True, help="Nombre de usuario inicial.")
    parser.add_argument(
        "--password",
        help="Evite pasarla por línea de comandos; si se omite se solicita de forma oculta.",
    )
    args = parser.parse_args()
    password = args.password or getpass("Contraseña inicial (8 dígitos): ")
    confirmation = password if args.password else getpass("Repita la contraseña: ")
    if password != confirmation:
        raise ValueError("Las contraseñas no coinciden.")
    user_id = create_admin(args.username, password)
    print(f"Usuario ADMIN creado con id {user_id}.")


if __name__ == "__main__":
    main()
