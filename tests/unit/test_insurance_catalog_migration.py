"""The insurance catalog must represent every type the source can contain.

``Data_base.mdb`` uses ten values (``EESS_SIS`` 001..009 plus the junk ``'7'``).
The initial catalog only declared the generic ``SIS``, so a subsidized regime and
``SANIDAD`` were indistinguishable once loaded. These tests pin the six rows that
close that gap and the guarantee that nothing already in use is touched.
"""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.models import Insurance


@pytest.fixture
def migration():
    spec = importlib.util.spec_from_file_location(
        "insurance_plans_migration",
        Path("migrations/versions/20260923_0017_insurance_plans.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


#: Códigos que la migración 0001 ya dejó en ``seguros``.
SEEDED = ("SIN_SEGURO", "SIS", "ESSALUD", "PARTICULAR", "OTRO")

NEW_CODES = (
    "SIS_GRATUITO",
    "SIS_PARA_TODOS",
    "SIS_AFILIACION_TEMPORAL",
    "SIS_SEMI_SUBSIDIADO",
    "SIS_NRUS",
    "SANIDAD",
)


class FakeBind:
    """Devuelve el código de cada fila de ``seguros`` ya presente."""

    def __init__(self, existing):
        self._existing = list(existing)

    def execute(self, statement, parameters=None):
        return Mock(scalars=lambda: list(self._existing))


def wire(migration, monkeypatch, existing):
    operations = Mock()
    operations.get_bind.return_value = FakeBind(existing)
    monkeypatch.setattr(migration, "op", operations)
    return operations


def test_upgrade_adds_the_missing_source_types_and_keeps_the_existing_ones(migration, monkeypatch):
    operations = wire(migration, monkeypatch, SEEDED)

    migration.upgrade()

    table, rows = operations.bulk_insert.call_args.args
    assert table.name == "seguros"
    assert [row["codigo"] for row in rows] == list(NEW_CODES)
    # Ninguna fila en uso se reescribe: la migración solo inserta.
    operations.execute.assert_not_called()
    assert not set(NEW_CODES) & set(SEEDED)


def test_upgrade_is_safe_to_retry_and_skips_codes_that_already_exist(migration, monkeypatch):
    operations = wire(migration, monkeypatch, SEEDED + NEW_CODES)

    migration.upgrade()

    operations.bulk_insert.assert_not_called()
    operations.execute.assert_not_called()


def test_downgrade_never_deletes_a_catalog_row_a_patient_may_reference(migration, monkeypatch):
    operations = wire(migration, monkeypatch, SEEDED + NEW_CODES)

    migration.downgrade()

    operations.execute.assert_not_called()
    operations.drop_table.assert_not_called()


def test_declared_codes_and_names_fit_and_are_unique(migration):
    codes = [codigo for codigo, _ in migration.INSURANCES]
    names = [nombre for _, nombre in migration.INSURANCES]

    assert codes == list(NEW_CODES)
    assert len(set(codes)) == len(codes)
    assert len(set(names)) == len(names)
    for codigo, nombre in migration.INSURANCES:
        assert len(codigo) <= Insurance.__table__.c.codigo.type.length
        assert len(nombre) <= Insurance.__table__.c.nombre.type.length
