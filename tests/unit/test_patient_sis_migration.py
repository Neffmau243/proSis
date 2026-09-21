"""Regression for an interrupted MySQL upgrade at the ethnicity foreign key."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import mysql

from app.models import Ethnicity, Patient


@pytest.fixture
def migration():
    spec = importlib.util.spec_from_file_location(
        "patient_sis_migration_regression",
        Path("migrations/versions/20260919_0015_patient_sis.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_orm_foreign_key_uses_identical_explicit_text_settings():
    parent = Ethnicity.__table__.c.codigo.type
    child = Patient.__table__.c.etnia_codigo.type
    assert child.charset == parent.charset == "utf8mb4"
    assert child.collation == parent.collation == "utf8mb4_unicode_ci"
    assert child.length == parent.length == 2


@pytest.mark.parametrize("collation", [None, "utf8mb4_0900_ai_ci", "utf8mb4_unicode_ci"])
def test_partial_upgrade_repairs_only_incompatible_ethnicity_column(migration, monkeypatch, collation):
    existing_type = mysql.VARCHAR(2, collation=collation)
    inspector = SimpleNamespace(get_columns=lambda table: [
        {"name": "etnia_codigo", "type": existing_type, "nullable": True},
        {"name": "sis_numero", "type": mysql.VARCHAR(9), "nullable": True},
    ])
    monkeypatch.setattr(migration.sa, "inspect", lambda bind: inspector)
    operations = Mock()
    monkeypatch.setattr(migration, "op", operations)

    migration._ensure_patient_ethnicity_column(object())

    operations.add_column.assert_not_called()
    if collation == "utf8mb4_unicode_ci":
        operations.alter_column.assert_not_called()
    else:
        operations.alter_column.assert_called_once()
        args, kwargs = operations.alter_column.call_args
        assert args == ("pacientes", "etnia_codigo")
        assert kwargs["existing_type"] is existing_type
        assert kwargs["type_"].collation == "utf8mb4_unicode_ci"
        assert kwargs["type_"].charset == "utf8mb4"
        assert kwargs["existing_nullable"] is True
    operations.drop_column.assert_not_called()
    operations.drop_table.assert_not_called()


def test_fresh_upgrade_creates_compatible_column(migration, monkeypatch):
    monkeypatch.setattr(migration.sa, "inspect", lambda bind: SimpleNamespace(get_columns=lambda table: []))
    operations = Mock()
    monkeypatch.setattr(migration, "op", operations)
    migration._ensure_patient_ethnicity_column(object())
    operations.add_column.assert_called_once()
    table, column = operations.add_column.call_args.args
    assert table == "pacientes"
    assert column.name == "etnia_codigo"
    assert column.type.compile(dialect=mysql.dialect()) == "VARCHAR(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    assert column.nullable
    operations.alter_column.assert_not_called()
