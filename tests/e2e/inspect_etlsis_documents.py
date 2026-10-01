"""Read-only ETLSIS metadata/category audit. Never emits patient identities."""

import json
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[2] / "etlSis/private/ace-source"
manifest = json.loads((root / "manifest.json").read_text("utf-8"))
print("Tables:", len(manifest["tables"]))
for table in manifest["tables"]:
    columns = [c["name"] for c in table["columns"]]
    candidates = [c for c in columns if "tipodoc" in c.lower() or "tdi" == c.lower()]
    if table["name"] == "Pacientes":
        candidates += [c for c in columns if c.startswith("Anexo")]
    if not candidates:
        continue
    counts = {c: Counter() for c in candidates}
    with (root / table["file"]).open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            for col in candidates:
                value = str(row[col] or "").strip().upper()
                # Only known document labels/booleans: no arbitrary source text.
                category = (
                    value
                    if value
                    in {
                        "",
                        "DNI",
                        "CE",
                        "PAS",
                        "PASAPORTE",
                        "DE",
                        "OTRO",
                        "TRUE",
                        "FALSE",
                        "0",
                        "1",
                        "2",
                        "3",
                        "4",
                        "5",
                        "6",
                        "7",
                        "8",
                        "9",
                        "-1",
                    }
                    else "OTHER_REDACTED"
                )
                counts[col][category] += 1
    print(json.dumps({"table": table["name"], "counts": counts}, ensure_ascii=True))
