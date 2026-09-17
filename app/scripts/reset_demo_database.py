"""Destructively rebuild a local development database in one controlled step.

The command requires an explicit confirmation flag, refuses production-like
environments, and drops only the database named by the current ``.env``.  It
then rebuilds exclusively through Alembic, creates an ADMIN account, and loads
the fictional demonstration records.
"""

from __future__ import annotations

import argparse
import secrets
from getpass import getpass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.core.security import validate_password_format
from app.scripts.bootstrap_database import (
    _database_name,
    create_database_if_missing,
    upgrade_to_head,
)
from app.scripts.create_admin import create_admin
from app.scripts.seed_demo_data import (
    DEMO_ADMIN_PASSWORD,
    DEMO_ADMIN_USERNAME,
    DEMO_PROFESSIONAL_PASSWORD,
    DEMO_PROFESSIONAL_USERNAME,
    seed_demo_data,
)


def drop_configured_database(settings: Settings | None = None) -> str:
    """Drop exactly the configured MySQL application database."""

    configured_settings = settings or get_settings()
    if configured_settings.environment.lower() in {"production", "prod"}:
        raise ValueError("El reinicio destructivo está bloqueado en producción.")

    application_url = make_url(configured_settings.sqlalchemy_database_url)
    if not application_url.drivername.startswith("mysql"):
        raise ValueError("El reinicio solo admite una URL de conexión MySQL.")
    database_name = _database_name(configured_settings, application_url)

    # An empty component is a MySQL server-level URL.  ``None`` would preserve
    # the database component in SQLAlchemy's immutable URL object.
    server_url: URL = application_url.set(database="")
    engine = create_engine(
        server_url,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    try:
        with engine.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS `{database_name}`"))
    finally:
        engine.dispose()
    return database_name


def _read_password(cli_password: str | None, *, generate_password: bool) -> str:
    if generate_password:
        return f"{secrets.randbelow(100_000_000):08d}"
    if cli_password is not None:
        return cli_password
    password = getpass("Contraseña para el nuevo ADMIN (8 dígitos): ")
    confirmation = getpass("Repita la contraseña: ")
    if password != confirmation:
        raise ValueError("Las contraseñas no coinciden.")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ELIMINA y reconstruye la base local con admin y datos de demostración."
    )
    parser.add_argument("--username", default="admin", help="Usuario del nuevo ADMIN.")
    parser.add_argument(
        "--password",
        help="Evite usarla en línea de comandos; al omitirla se solicita de forma oculta.",
    )
    parser.add_argument(
        "--generate-password",
        action="store_true",
        help="Genera y muestra una contraseña segura para el ADMIN local.",
    )
    parser.add_argument(
        "--demo-credentials",
        action="store_true",
        help=(
            "Usa las credenciales fijas de desarrollo para admin y medico.demo. "
            "Solo apto para la base local desechable."
        ),
    )
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        help="Confirmación obligatoria para eliminar la base configurada.",
    )
    args = parser.parse_args()
    if not args.confirm_delete:
        parser.error("Debe indicar --confirm-delete para eliminar la base configurada.")
    selected_password_sources = sum(
        bool(value)
        for value in (args.password, args.generate_password, args.demo_credentials)
    )
    if selected_password_sources > 1:
        parser.error("Use solo --password, --generate-password o --demo-credentials.")

    username = DEMO_ADMIN_USERNAME if args.demo_credentials else args.username
    password = (
        DEMO_ADMIN_PASSWORD
        if args.demo_credentials
        else _read_password(args.password, generate_password=args.generate_password)
    )
    validate_password_format(password)

    deleted_database = drop_configured_database()
    database_name = create_database_if_missing()
    upgrade_to_head()
    admin_id = create_admin(username, password)
    identifiers = seed_demo_data()

    print(f"Base de datos '{deleted_database}' eliminada y '{database_name}' reconstruida.")
    print(f"Usuario ADMIN creado con id {admin_id}.")
    if args.demo_credentials:
        print(f"ADMIN demo: {DEMO_ADMIN_USERNAME} / {DEMO_ADMIN_PASSWORD}")
        print(f"PROFESIONAL demo: {DEMO_PROFESSIONAL_USERNAME} / {DEMO_PROFESSIONAL_PASSWORD}")
    elif args.generate_password:
        print(f"Contraseña temporal del ADMIN: {password}")
    print("Semillas de demostración creadas:")
    for key, value in identifiers.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
