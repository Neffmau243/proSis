"""Download and normalize official WHO 2007 LMS tables for offline use.

Run explicitly during reference-data maintenance; never at application startup.
Only numeric reference coefficients and source URLs are stored.
"""

from __future__ import annotations

import hashlib
import io
import json
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import httpx

BASE = "https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators/"
PAGES = {"bmi": "bmi-for-age", "height": "height-for-age", "weight": "weight-for-age-5to10-years"}
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            url = dict(attrs).get("href", "")
            if ".xlsx" in url and "who.int/" in url:
                self.urls.append(url)


def read_rows(raw):
    with ZipFile(io.BytesIO(raw)) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = [
                "".join(si.itertext()) for si in ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ]
        tree = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in tree.findall(".//s:row", NS):
            values = {}
            for cell in row.findall("s:c", NS):
                column = "".join(c for c in cell.attrib["r"] if c.isalpha())
                value = cell.find("s:v", NS)
                if value is not None:
                    values[column] = (
                        strings[int(value.text)] if cell.attrib.get("t") == "s" else value.text
                    )
                elif cell.attrib.get("t") == "inlineStr":
                    values[column] = "".join(cell.itertext())
            rows.append(values)
        return rows


def main():
    output = {"sources": [], "tables": {}}
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        for kind, page in PAGES.items():
            response = client.get(BASE + page)
            response.raise_for_status()
            parser = Links()
            parser.feed(response.text)
            for sex, label in [("F", "girls"), ("M", "boys")]:
                urls = [
                    url
                    for url in parser.urls
                    if label in url and "exp" in url and "z" in url.split("?")[0]
                ]
                if not urls:
                    raise RuntimeError(f"No official table found: {kind}/{sex}: {parser.urls}")
                url = urls[0]
                response = client.get(url)
                response.raise_for_status()
                rows = read_rows(response.content)
                print(f"Downloaded {kind}/{sex} from {url}")
                headers = next(row for row in rows if {"L", "M", "S"}.issubset(set(row.values())))
                columns = {str(value).lower(): column for column, value in headers.items()}
                age_column = columns.get("month") or columns.get("months") or columns.get("age")
                if not age_column:
                    raise RuntimeError(f"Unknown age column: {headers}")
                table = {}
                for row in rows:
                    try:
                        age = float(row[age_column])
                        if not age.is_integer():
                            continue
                        table[str(int(age))] = [float(row[columns[key]]) for key in ("l", "m", "s")]
                    except (KeyError, ValueError):
                        continue
                expected = set(range(61, (120 if kind == "weight" else 228) + 1))
                if not expected.issubset({int(age) for age in table}):
                    raise RuntimeError(f"Incomplete monthly table {kind}/{sex}: {len(table)}")
                output["tables"][f"{kind}_{sex}"] = {
                    str(age): table[str(age)] for age in sorted(expected)
                }
                output["sources"].append(
                    {
                        "table": f"{kind}_{sex}",
                        "url": url,
                        "sha256": hashlib.sha256(response.content).hexdigest(),
                    }
                )
    target = Path(__file__).resolve().parents[1] / "data" / "who2007_lms.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {target}")


if __name__ == "__main__":
    main()
