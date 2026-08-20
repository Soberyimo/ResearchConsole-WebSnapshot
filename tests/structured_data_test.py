import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

from build_visualizer_snapshot import build  # noqa: E402
from structured_data import StructuredDataError, validate_records, verify_json_csv  # noqa: E402


class StructuredDataTest(unittest.TestCase):
    def test_migrated_json_and_csv_are_equivalent(self):
        result = verify_json_csv(
            PROJECT_DIR / "structured_data/financial_records.json",
            PROJECT_DIR / "structured_data/financial_records.csv",
        )
        self.assertTrue(result["equivalent"])
        self.assertEqual(result["json"]["records"], 751)
        self.assertEqual(result["json"]["companies"], 7)
        self.assertEqual(result["json"]["verified"], 389)
        self.assertEqual(result["json"]["program_calculated"], 128)

    def test_missing_value_is_allowed_only_when_marked_missing(self):
        record = {
            "company": "Example",
            "period": "2026Q1",
            "metric": "revenue",
            "value": None,
            "unit": "USD million",
            "scope": "group",
            "source_type": "gpt_estimate",
            "source": "GPT input",
            "source_location": "input note",
            "status": "missing",
        }
        self.assertEqual(validate_records([record])["records"], 1)
        record["status"] = "verified"
        with self.assertRaisesRegex(StructuredDataError, "missing value"):
            validate_records([record])

    def test_calculated_record_requires_formula(self):
        record = {
            "company": "Example",
            "period": "2026Q1",
            "metric": "margin",
            "value": 12.3,
            "unit": "%",
            "scope": "group",
            "source_type": "program_calculated",
            "source": "GPT input",
            "source_location": "GPT input",
            "status": "verified",
        }
        with self.assertRaisesRegex(StructuredDataError, "requires formula"):
            validate_records([record])

    def test_legacy_governance_ids_are_rejected(self):
        record = {
            "company": "Example",
            "period": "2026Q1",
            "metric": "revenue",
            "value": 10,
            "unit": "USD million",
            "scope": "group",
            "source_type": "company_disclosed",
            "source": "company report",
            "source_location": "p.1",
            "status": "needs_review",
            "record_id": "legacy",
        }
        with self.assertRaisesRegex(StructuredDataError, "legacy governance IDs"):
            validate_records([record])

    def test_snapshot_is_display_only_and_contains_no_calendar(self):
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        self.assertEqual(payload["schema_version"], "Yunjian-VisualizerSnapshot-1")
        self.assertEqual(payload["summary"]["record_count"], 751)
        self.assertEqual(payload["summary"]["verified_count"], 389)
        self.assertNotIn("earnings_calendar", payload)
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("record_id", serialized)
        self.assertNotIn("evidence_id", serialized)

    def test_duplicate_display_key_fails_closed(self):
        record = {
            "company": "Example",
            "period": "2026Q1",
            "metric": "revenue",
            "value": 10,
            "unit": "CNY million",
            "currency": "CNY",
            "scope": "group",
            "source_type": "company_disclosed",
            "source": "company report",
            "source_location": "p.1",
            "status": "verified",
        }
        with self.assertRaisesRegex(StructuredDataError, "duplicate display key"):
            validate_records([record, dict(record)])

    def test_seres_uses_manifest_slug_and_separate_frequencies(self):
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        page = payload["company_pages"]["seres"]
        self.assertEqual(page["company"], "赛力斯")
        self.assertEqual(page["target_period"], "2026Q1")
        self.assertEqual(page["record_count"], 389)
        self.assertEqual(page["verified_record_count"], 389)
        groups = page["page_data"]["series_groups"]
        self.assertEqual(sum(len(series["records"]) for series in groups["financial"]), 165)
        self.assertEqual(sum(len(series["records"]) for series in groups["company_sales"]), 110)
        self.assertEqual(sum(len(series["records"]) for series in groups["model_sales"]), 114)
        for series in groups["financial"]:
            self.assertNotEqual(series["period_type"], "month")
        self.assertIn("A+H双上市公司", page["html"])
        self.assertIn("保证类质保成本", page["html"])
        self.assertIn("不等于问界品牌交付量", page["html"])

    def test_migration_manifest_records_formula_and_spot_checks(self):
        manifest = json.loads((PROJECT_DIR / "structured_data/migration_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["counts"]["legacy_current_records"], 362)
        self.assertEqual(manifest["counts"]["migrated"], 362)
        self.assertEqual(manifest["counts"]["skipped"], 0)
        self.assertEqual(manifest["formula_validation"]["checked"], 12)
        self.assertEqual(manifest["formula_validation"]["failed"], 0)
        self.assertEqual(len(manifest["spot_checks"]), 6)


if __name__ == "__main__":
    unittest.main()
