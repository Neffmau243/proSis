"""Verified, lossless ACE snapshots. This module never opens a database for writing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("ascii")).hexdigest()


def file_digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_snapshot(directory: Path, source: Path) -> tuple[dict, dict[str, list[dict]]]:
    directory = directory.resolve()
    manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
    if manifest.get("version") != 1 or manifest.get("reader") != "Microsoft.ACE.OLEDB.16.0":
        raise ValueError("Unsupported snapshot format or reader")
    if file_digest(source) != manifest["source_sha256"]:
        raise ValueError("Source fingerprint does not match the snapshot")
    tables = {}
    for table in manifest["tables"]:
        name = table["name"]
        path = (directory / table["file"]).resolve()
        if path.parent != directory or name in tables:
            raise ValueError("Invalid or duplicate snapshot table")
        if file_digest(path) != table["sha256"]:
            raise ValueError(f"Snapshot checksum mismatch: {name}")
        columns = [c["name"] for c in table["columns"]]
        if len(columns) != len(set(columns)):
            raise ValueError(f"Duplicate source columns: {name}")
        rows = []
        with path.open(encoding="utf-8", errors="strict") as stream:
            for line in stream:
                row = json.loads(line)
                if not isinstance(row, dict) or set(row) != set(columns):
                    raise ValueError(f"Unexpected row structure: {name}")
                rows.append(row)
        if len(rows) != table["rows"]:
            raise ValueError(f"Snapshot row count mismatch: {name}")
        tables[name] = rows
    if not {"Pacientes", "Atencion", "Provincia", "EESS", "Pacientes_ref"} <= tables.keys():
        raise ValueError("Required source tables are missing")
    return manifest, tables
