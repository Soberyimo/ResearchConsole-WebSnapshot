#!/usr/bin/env python3
"""Preview or apply a GPT-owned Visualizer patch without deriving financial facts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from structured_data import load_records, validate_records


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = PROJECT_DIR / "structured_data/financial_records.json"
DEFAULT_CSV = PROJECT_DIR / "structured_data/financial_records.csv"
MERGE_FIELDS = (
    "company", "period", "metric", "scope", "business", "geography",
    "product", "basis", "measurement_basis",
)
PROTECTED_PATCH_FIELDS = (
    "value", "unit", "currency", "basis", "source_type", "formula", "source", "note",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def merge_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(record.get(field) for field in MERGE_FIELDS)


def atomic_write(path: Path, data: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def patch_records(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise ValueError("patch must be an object containing records")
    policy = payload.get("merge_policy") or {}
    if policy.get("mode") != "upsert_only" or tuple(policy.get("merge_key") or ()) != MERGE_FIELDS:
        raise ValueError("patch merge_policy does not match the Visualizer upsert contract")
    records = payload["records"]
    validate_records(records)
    if len({merge_key(record) for record in records}) != len(records):
        raise ValueError("patch contains duplicate merge keys")
    return payload, records


def merge(base: list[dict[str, Any]], patch: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    merged = [dict(record) for record in base]
    index = {merge_key(record): position for position, record in enumerate(merged)}
    overwritten = 0
    added = 0
    company_counts: dict[str, Counter[str]] = {}
    for patch_record in patch:
        key = merge_key(patch_record)
        company = str(patch_record["company"])
        company_counts.setdefault(company, Counter())
        if key in index:
            old = merged[index[key]]
            if old.get("status") != "needs_review" or patch_record.get("status") not in {"verified", "calculated"}:
                raise ValueError(f"upsert not allowed for key {key!r}")
            merged[index[key]] = dict(patch_record)
            overwritten += 1
            company_counts[company]["overwritten"] += 1
        else:
            index[key] = len(merged)
            merged.append(dict(patch_record))
            added += 1
            company_counts[company]["added"] += 1

    # The one authorized semantic replacement is conditional on the exact bad value.
    bad_cash_rows = [
        position for position, record in enumerate(merged)
        if record.get("company") == "小鹏汽车"
        and record.get("period") == "2026Q1"
        and record.get("metric") == "cash_and_equivalents"
        and record.get("value") == 42090.0
        and record.get("unit") == "CNY million"
    ]
    for position in reversed(bad_cash_rows):
        del merged[position]

    validate_records(merged)
    return merged, {
        "before": len(base),
        "patch": len(patch),
        "after": len(merged),
        "overwritten_needs_review": overwritten,
        "added": added,
        "semantic_replacements": len(bad_cash_rows),
        "companies": {company: dict(counts) for company, counts in sorted(company_counts.items())},
    }


def csv_bytes(records: list[dict[str, Any]]) -> bytes:
    preferred = [
        "company", "ticker", "period", "period_type", "period_start_date", "period_end_date",
        "metric", "metric_name", "value", "unit", "currency", "scope", "business", "geography",
        "product", "basis", "measurement_basis", "source_type", "source", "source_url",
        "source_location", "raw_value_text", "formula", "formula_inputs", "calculation_basis",
        "restated", "status", "metric_definition", "scope_note", "note", "yoy", "qoq", "yoy_pp",
    ]
    fields = [field for field in preferred if any(field in record for record in records)]
    fields += sorted(set().union(*(record.keys() for record in records)) - set(fields))
    with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", newline="", delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            row = {}
            for field in fields:
                value = record.get(field)
                row[field] = json.dumps(value, ensure_ascii=False, separators=(",", ":")) if field == "formula_inputs" and value is not None else value
            writer.writerow(row)
        temporary = Path(handle.name)
    try:
        return temporary.read_bytes()
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("patch", type=Path)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--expected-old-sha256")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        old_sha = sha256(args.target)
        if args.expected_old_sha256 and old_sha != args.expected_old_sha256:
            raise ValueError("target SHA256 changed after preview")
        base = load_records(args.target)
        _, patch = patch_records(args.patch)
        merged, report = merge(base, patch)
        report["old_sha256"] = old_sha
        if args.apply:
            json_data = (json.dumps(merged, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            atomic_write(args.target, json_data)
            atomic_write(args.csv, csv_bytes(merged))
            reopened = load_records(args.target)
            validate_records(reopened)
            if reopened != merged:
                raise ValueError("write verification mismatch")
            report["new_sha256"] = sha256(args.target)
            report["applied"] = True
        else:
            report["applied"] = False
        print(json.dumps({"status": "PASS", **report}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
