"""Independent read comparison. Output contains counts only, never source values."""
from __future__ import annotations

from collections import Counter
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
import io
import json
from pathlib import Path

from access_parser import AccessParser

from .snapshot import digest, read_snapshot


def normalized(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, str):
        try:
            if len(value) >= 19 and value[4] == "-" and value[10] == "T":
                return datetime.fromisoformat(value).isoformat(timespec="seconds")
        except ValueError:
            pass
    return value


def compare(directory: Path, source: Path) -> dict:
    manifest, tables = read_snapshot(directory, source)
    result = {"source_sha256": manifest["source_sha256"], "tables": {}}
    # The third party parser sometimes writes raw corrupted values to stderr.
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        parser = AccessParser(str(source))
        for name in ("Pacientes", "Atencion", "Pacientes_ref", "Profesionales", "Provincia", "EESS"):
            parsed = parser.get_table(name).parse()
            count = len(next(iter(parsed.values()))) if parsed else 0
            differences = {}
            for field in tables[name][0] if tables[name] else []:
                a = Counter(digest(normalized(r[field])) for r in tables[name])
                b = Counter(digest(normalized(v)) for v in parsed.get(field, []))
                if a != b:
                    differences[field] = {"ace_only": sum((a-b).values()), "parser_only": sum((b-a).values())}
            result["tables"][name] = {"ace_rows": len(tables[name]), "parser_rows": count, "column_differences": differences}
    return result


if __name__ == "__main__":
    private = Path(__file__).resolve().parent / "private"
    report = compare(private / "ace-source", private / "source.mdb")
    (private / "reader-comparison.json").write_text(json.dumps(report, indent=2), "utf-8")
    print(json.dumps(report, ensure_ascii=True))
