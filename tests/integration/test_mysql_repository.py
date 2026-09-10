import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.repositories.patient import PatientRepository


@pytest.mark.integration
def test_migration_creates_seeded_catalogs_for_repositories(migrated_mysql_engine) -> None:
    inspector = inspect(migrated_mysql_engine)
    assert {"pacientes", "atenciones", "fua", "documento_series", "auditoria"} <= set(
        inspector.get_table_names()
    )

    with Session(migrated_mysql_engine) as session:
        assert PatientRepository(session).get_active_document_type("DNI") is not None
