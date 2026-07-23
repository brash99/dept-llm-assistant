#!/usr/bin/env python3
"""Extract the three requested academic years from the ISO SCH timeline."""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path


YEARS = ("2022-23", "2023-24", "2024-25")


def build_three_year_report(timeline):
    rows = []
    for department in timeline["departments"]:
        by_year = {
            item["academic_year"]: float(item["sch"])
            for item in department["academic_years"]
        }
        missing = [year for year in YEARS if year not in by_year]
        if missing:
            raise ValueError(
                f"{department['department_name']} lacks required years: {missing}"
            )
        values = [by_year[year] for year in YEARS]
        rows.append({
            "Department": department["department_name"],
            "AY22-23": values[0],
            "AY23-24": values[1],
            "AY24-25": values[2],
            "3-Year Avg": round(sum(values) / 3, 2),
        })
    rows.sort(key=lambda item: item["Department"].casefold())
    payload = {
        "academic_years": list(YEARS),
        "average_formula": "(AY22-23 + AY23-24 + AY24-25) / 3",
        "department_count": len(rows),
        "rows": rows,
    }
    payload["deterministic_fingerprint"] = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    timeline = json.loads(args.timeline.read_text(encoding="utf-8"))
    payload = build_three_year_report(timeline)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output_dir / "department_three_year_sch.csv", payload["rows"])
    (args.output_dir / "department_three_year_sch.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "department_three_year_sch.md").write_text(
        _markdown(payload), encoding="utf-8"
    )
    print(json.dumps({
        "department_count": payload["department_count"],
        "academic_years": payload["academic_years"],
        "deterministic_fingerprint": payload["deterministic_fingerprint"],
    }, indent=2, sort_keys=True))
    return 0


def _write_csv(path, rows):
    fields = ("Department", "AY22-23", "AY23-24", "AY24-25", "3-Year Avg")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _markdown(payload):
    lines = [
        "# Department Three-Year SCH",
        "",
        f"- Academic years: {', '.join(payload['academic_years'])}",
        f"- Average: {payload['average_formula']}",
        "",
        "| Department | AY22-23 | AY23-24 | AY24-25 | 3-Year Avg |",
        "|---|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {item['Department']} | {item['AY22-23']} | {item['AY23-24']} | "
        f"{item['AY24-25']} | {item['3-Year Avg']} |"
        for item in payload["rows"]
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
