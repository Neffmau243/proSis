"""Contract tests for the ETLSIS nutritional risk catalog migration."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.models import RiskGroup


@pytest.fixture
def migration():
    spec = importlib.util.spec_from_file_location(
        "nutritional_risk_groups_migration",
        Path("migrations/versions/20260929_0023_nutritional_risk_groups.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeBind:
    """Returns the risk-group codes that are already configured."""

    def __init__(self, existing: tuple[str, ...]):
        self._existing = existing

    def execute(self, statement, parameters=None):
        return Mock(scalars=lambda: list(self._existing))


def wire(migration, monkeypatch, existing: tuple[str, ...]):
    operations = Mock()
    operations.get_bind.return_value = FakeBind(existing)
    monkeypatch.setattr(migration, "op", operations)
    return operations


def test_revision_extends_the_current_head(migration) -> None:
    assert migration.revision == "20260929_0023_nutrition_risks"
    assert migration.down_revision == "20260926_0022_specialty_codes"


def test_upgrade_adds_only_missing_nutritional_risk_groups(migration, monkeypatch) -> None:
    existing = ("NUT_DELGADEZ", "RIESGO_LOCAL")
    operations = wire(migration, monkeypatch, existing)

    migration.upgrade()

    table, rows = operations.bulk_insert.call_args.args
    assert table.name == "grupos_riesgo"
    assert [row["codigo"] for row in rows] == [
        "NUT_DESN_AGUDA",
        "NUT_DESN_GLOBAL",
        "NUT_TALLA_BAJA",
    ]
    assert all(row["codigo"] not in existing for row in rows)
    operations.execute.assert_not_called()


def test_upgrade_is_safe_to_retry(migration, monkeypatch) -> None:
    existing = tuple(code for code, _name, _description in migration.NUTRITIONAL_RISK_GROUPS)
    operations = wire(migration, monkeypatch, existing)

    migration.upgrade()

    operations.bulk_insert.assert_not_called()
    operations.execute.assert_not_called()


def test_downgrade_keeps_catalog_rows_that_patients_may_reference(migration, monkeypatch) -> None:
    operations = wire(migration, monkeypatch, ())

    migration.downgrade()

    operations.execute.assert_not_called()
    operations.drop_table.assert_not_called()


def test_declared_risks_are_unique_and_fit_the_schema(migration) -> None:
    codes = [code for code, _name, _description in migration.NUTRITIONAL_RISK_GROUPS]
    names = [name for _code, name, _description in migration.NUTRITIONAL_RISK_GROUPS]
    descriptions = [description for _code, _name, description in migration.NUTRITIONAL_RISK_GROUPS]

    assert len(codes) == 4
    assert len(set(codes)) == len(codes)
    assert len(set(names)) == len(names)
    assert all(len(code) <= RiskGroup.__table__.c.codigo.type.length for code in codes)
    assert all(len(name) <= RiskGroup.__table__.c.nombre.type.length for name in names)
    assert all(
        len(description) <= RiskGroup.__table__.c.descripcion.type.length
        for description in descriptions
    )
