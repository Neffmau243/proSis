"""Explicit local test targets. Never drops or changes the configured application database."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.core.config import get_settings

PRIVATE = Path(__file__).resolve().parent / "private"
TARGET = re.compile(r"^sistema_salud_ipress_etl_(baseline|pilot|full|unit)_test$")


def target_url(name: str):
    source = make_url(get_settings().sqlalchemy_database_url)
    if not TARGET.fullmatch(name) or name == source.database:
        raise ValueError("Only a named ETL test database is allowed; the active database is protected.")
    if source.host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("ETL sandbox operations require a local MySQL server.")
    return source.set(database=name)


def ensure_target(name: str):
    url = target_url(name)
    with create_engine(url.set(database=""), isolation_level="AUTOCOMMIT").connect() as db:
        db.execute(text(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"))
    return url


def fingerprint(url) -> dict:
    """Content digests, not patient values; independent of physical row order."""
    engine = create_engine(url)
    result = {}
    try:
        with engine.connect() as db:
            for name in sorted(inspect(db).get_table_names()):
                rows = db.execute(text("SELECT * FROM `" + name.replace("`", "``") + "`"))
                hashes = sorted(hashlib.sha256(json.dumps(list(row), default=str, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest() for row in rows)
                result[name] = {"rows": len(hashes), "sha256": hashlib.sha256("\n".join(hashes).encode()).hexdigest()}
    finally:
        engine.dispose()
    return result


def backup_and_verify() -> dict:
    """Restore a private backup into an empty baseline, verifying every table."""
    PRIVATE.mkdir(exist_ok=True)
    source = make_url(get_settings().sqlalchemy_database_url)
    baseline_name = "sistema_salud_ipress_etl_baseline_test"
    baseline = ensure_target(baseline_name)
    before = fingerprint(source)
    manifest = PRIVATE / "baseline-fingerprint.json"
    backup = PRIVATE / "baseline.sql"
    if manifest.exists():
        saved = json.loads(manifest.read_text(encoding="utf-8"))
        if before != saved or fingerprint(baseline) != saved:
            raise ValueError("Baseline or active database changed; review before proceeding.")
        return {"verified": True, "tables": len(before), "reused": True}
    if fingerprint(baseline):
        raise ValueError("Baseline target must be empty; no existing tables will be replaced.")
    binary = Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin")
    env = os.environ.copy()
    env["MYSQL_PWD"] = source.password or ""
    connection = ["--no-defaults", "--host=" + str(source.host), "--port=" + str(source.port or 3306), "--user=" + str(source.username), "--default-character-set=utf8mb4"]
    with backup.open("wb") as fh:
        run = subprocess.run([str(binary / "mysqldump.exe"), *connection, "--single-transaction", "--skip-lock-tables", "--no-tablespaces", str(source.database)], env=env, stdout=fh, stderr=subprocess.PIPE)
    if run.returncode:
        raise RuntimeError("Private backup failed; original database was not modified.")
    with backup.open("rb") as fh:
        run = subprocess.run([str(binary / "mysql.exe"), *connection, baseline_name], env=env, stdin=fh, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if run.returncode:
        raise RuntimeError("Baseline restoration failed; original database was not modified.")
    if before != fingerprint(source) or before != fingerprint(baseline):
        raise RuntimeError("Backup verification failed; stop before import.")
    manifest.write_text(json.dumps(before, indent=2), encoding="utf-8")
    return {"verified": True, "tables": len(before), "reused": False}


if __name__ == "__main__":
    print(json.dumps(backup_and_verify()))
