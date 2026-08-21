#!/usr/bin/env python3
"""Parse and validate schema-lite JSON/CSV inputs for the Visualizer."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "company",
    "period",
    "metric",
    "value",
    "unit",
    "scope",
    "source_type",
    "source",
    "source_location",
    "status",
)
ALLOWED_SOURCE_TYPES = {
    "company_disclosed",
    "program_calculated",
    "management_forward_looking",
    "external_research",
    "gpt_estimate",
    "user_material",
}
ALLOWED_STATUSES = {"verified", "calculated", "needs_review", "missing"}
LEGACY_ID_FIELDS = {"record_id", "observation_key", "evidence_id", "material_id"}
JSON_FIELDS = {"formula_inputs"}
BOOLEAN_FIELDS = {"restated"}
NUMBER_FIELDS = {"value", "yoy", "yoy_pp", "qoq"}
DISPLAY_KEY_FIELDS = (
    "company",
    "period",
    "metric",
    "scope",
    "business",
    "geography",
    "product",
    "basis",
    "measurement_basis",
    "unit",
    "currency",
)


class StructuredDataError(ValueError):
    """Raised when input data is not safe to display."""


def _parse_csv_value(field: str, value: str) -> Any:
    if value == "":
        return None
    if field in JSON_FIELDS:
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise StructuredDataError(f"{field} is not valid JSON") from exc
    if field in BOOLEAN_FIELDS:
        normalized = value.strip().lower()
        if normalized not in {"true", "false"}:
            raise StructuredDataError(f"{field} must be true or false")
        return normalized == "true"
    if field in NUMBER_FIELDS:
        try:
            return float(value)
        except ValueError as exc:
            raise StructuredDataError(f"{field} must be numeric") from exc
    return value


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records") if isinstance(payload, dict) else payload
    elif path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            records = [
                {field: _parse_csv_value(field, value or "") for field, value in row.items()}
                for row in csv.DictReader(handle)
            ]
    else:
        raise StructuredDataError("input must be .json or .csv")
    if not isinstance(records, list) or not records:
        raise StructuredDataError("input must contain a non-empty record list")
    if not all(isinstance(record, dict) for record in records):
        raise StructuredDataError("every input record must be an object")
    return records


def validate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[str] = []
    seen_keys: dict[tuple[Any, ...], int] = {}
    for index, record in enumerate(records):
        missing = []
        for field in REQUIRED_FIELDS:
            if field not in record:
                missing.append(field)
            elif field == "source_location":
                # GPT-owned patches may deliberately leave the exact location blank.
                # The Visualizer must preserve that absence instead of inventing one.
                continue
            elif field == "value" and record.get("status") == "missing":
                continue
            elif record[field] is None or record[field] == "":
                missing.append(field)
        if missing:
            issues.append(f"record {index}: missing {', '.join(missing)}")
        if any(field in record for field in LEGACY_ID_FIELDS):
            issues.append(f"record {index}: legacy governance IDs are not display inputs")
        value = record.get("value")
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            issues.append(f"record {index}: value must be numeric")
        if record.get("source_type") not in ALLOWED_SOURCE_TYPES:
            issues.append(f"record {index}: unsupported source_type")
        if record.get("status") not in ALLOWED_STATUSES:
            issues.append(f"record {index}: unsupported status")
        if record.get("source_type") == "program_calculated" and not record.get("formula"):
            issues.append(f"record {index}: program_calculated requires formula")
        if record.get("status") == "calculated" and record.get("source_type") != "program_calculated":
            issues.append(f"record {index}: calculated status requires program_calculated source_type")
        for field in ("yoy", "yoy_pp", "qoq"):
            comparison = record.get(field)
            if comparison is not None and (isinstance(comparison, bool) or not isinstance(comparison, (int, float))):
                issues.append(f"record {index}: {field} must be numeric when provided")
        display_key = tuple(record.get(field) for field in DISPLAY_KEY_FIELDS)
        if display_key in seen_keys:
            issues.append(f"record {index}: duplicate display key with record {seen_keys[display_key]}")
        else:
            seen_keys[display_key] = index
    if issues:
        raise StructuredDataError("; ".join(issues[:20]))
    return {
        "status": "PASS",
        "records": len(records),
        "companies": len({str(record["company"]) for record in records}),
        "verified": sum(record.get("status") == "verified" for record in records),
        "calculated": sum(record.get("status") == "calculated" for record in records),
        "needs_review": sum(record.get("status") == "needs_review" for record in records),
        "program_calculated": sum(record.get("source_type") == "program_calculated" for record in records),
    }


def normalized_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in sorted(record.items())
        if value is not None and value != ""
    }


def verify_json_csv(json_path: Path, csv_path: Path) -> dict[str, Any]:
    json_records = load_records(json_path)
    csv_records = load_records(csv_path)
    json_result = validate_records(json_records)
    csv_result = validate_records(csv_records)
    if [normalized_record(row) for row in json_records] != [normalized_record(row) for row in csv_records]:
        raise StructuredDataError("JSON and CSV records differ")
    return {"status": "PASS", "json": json_result, "csv": csv_result, "equivalent": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--csv-pair", type=Path)
    args = parser.parse_args()
    try:
        result = (
            verify_json_csv(args.input, args.csv_pair)
            if args.csv_pair
            else validate_records(load_records(args.input))
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, json.JSONDecodeError, StructuredDataError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
