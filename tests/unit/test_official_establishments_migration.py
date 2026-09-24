"""The official establishment seed must stay a small, valid RENAES catalog."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def migration():
    spec = importlib.util.spec_from_file_location(
        "official_establishments_migration",
        Path("migrations/versions/20260924_0019_official_establishments.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_extends_the_locality_catalog(migration) -> None:
    assert migration.revision == "20260924_0019_eess_catalog"
    assert migration.down_revision == "20260924_0018_sis_localities"


def test_establishments_have_unique_renaes_and_names(migration) -> None:
    rows = migration.ESTABLISHMENTS

    assert len(rows) == 6
    renaes = [renaes for _legacy, _nombre, renaes in rows]
    names = [nombre for _legacy, nombre, _renaes in rows]
    assert len(set(renaes)) == len(renaes)
    assert len(set(names)) == len(names)
    assert all(code.isdigit() for code in renaes)
