import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

from build_visualizer_snapshot import (  # noqa: E402
    all_data_html,
    build,
    semantic_metric_label,
)
from structured_data import StructuredDataError, validate_records, verify_json_csv  # noqa: E402


class StructuredDataTest(unittest.TestCase):
    def test_migrated_json_and_csv_are_equivalent(self):
        result = verify_json_csv(
            PROJECT_DIR / "structured_data/financial_records.json",
            PROJECT_DIR / "structured_data/financial_records.csv",
        )
        self.assertTrue(result["equivalent"])
        self.assertEqual(result["json"]["records"], 898)
        self.assertEqual(result["json"]["companies"], 8)
        self.assertEqual(result["json"]["verified"], 512)
        self.assertEqual(result["json"]["calculated"], 24)
        self.assertEqual(result["json"]["program_calculated"], 152)

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
        self.assertEqual(payload["summary"]["record_count"], 898)
        self.assertEqual(payload["summary"]["verified_count"], 512)
        self.assertEqual(payload["summary"]["calculated_count"], 24)
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
        self.assertEqual(sum(len(series["records"]) for group in ("scale", "profitability", "operations") for series in groups[group]), 165)
        self.assertEqual(sum(len(series["records"]) for series in groups["company_sales"]), 110)
        self.assertEqual(sum(len(series["records"]) for series in groups["model_sales"]), 114)
        self.assertIn("直接看销量", page["html"])
        self.assertIn("查看全部数据与来源", page["html"])
        self.assertNotIn("已核实", page["html"])
        self.assertIn("A+H双上市公司", page["html"])
        self.assertIn("保证类质保成本", page["html"])
        self.assertIn("不等于问界品牌交付量", page["html"])

    def test_seres_v2_gross_margin_is_displayed_without_rescaling(self):
        records = json.loads((PROJECT_DIR / "structured_data/financial_records.json").read_text(encoding="utf-8"))
        margin = [row for row in records if row.get("company") == "赛力斯" and row.get("period") == "2025H1" and row.get("metric") == "gross_margin"]
        self.assertEqual(len(margin), 1)
        self.assertEqual(margin[0]["value"], 28.93)
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        self.assertIn("28.93", payload["company_pages"]["seres"]["html"])
        self.assertNotIn("2,893", payload["company_pages"]["seres"]["html"])

    def test_attributable_profit_labels_preserve_ownership_semantics(self):
        self.assertEqual(semantic_metric_label({"metric": "net_income", "basis": "PRC_GAAP_attributable_to_parent"}), "归母净利润")
        self.assertEqual(semantic_metric_label({"metric": "net_income", "basis": "US_GAAP_attributable_to_ordinary_shareholders"}), "归属普通股股东净利润")
        self.assertEqual(semantic_metric_label({"metric": "net_income", "basis": "Non_GAAP_attributable_to_ordinary_shareholders"}), "Non-GAAP 归属普通股股东净利润")

    def test_xpeng_cash_position_keeps_composite_semantics(self):
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        page = next(page for page in payload["company_pages"].values() if page["company"] == "小鹏汽车")
        self.assertIn("420.9亿元为公司定义的复合 cash position", page["html"])
        self.assertIn("公司定义现金储备", page["html"])

    def test_qualcomm_business_hierarchy_is_explicit(self):
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        page = next(page for page in payload["company_pages"].values() if page["company"] == "高通")
        self.assertIn("QCT 与 QTL 并列，汽车业务属于 QCT", page["html"])
        self.assertRegex(page["html"], r"<h3>QCT</h3>[\s\S]*Automotive[\s\S]*</article><article><h3>QTL</h3>")

    def test_nvidia_recast_and_legacy_series_are_separated(self):
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        page = next(page for page in payload["company_pages"].values() if page["company"] == "英伟达")
        series = [item for group in page["page_data"]["series_groups"].values() for item in group]
        self.assertTrue(any(item["label"].startswith("Data Center ·") and not item["legacy"] for item in series))
        self.assertTrue(any("Data Center compute" in item["label"] and item["legacy"] for item in series))
        self.assertIn("旧披露口径 / legacy", page["html"])

    def test_yoy_pp_uses_percentage_points_and_empty_comparison_columns_hide(self):
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        catl = next(page for page in payload["company_pages"].values() if page["company"] == "宁德时代")
        self.assertIn("个百分点", catl["html"])
        synthetic = [{
            "label": "测试指标", "period_type": "quarter", "unit": "CNY million", "display_unit": "亿元",
            "records": [{"period": "2026Q1", "display_period": "2026Q1", "value": 100, "qoq": None, "yoy": None, "yoy_pp": None,
                         "source": "test", "source_type": "company_disclosed", "basis": "GAAP"}],
        }]
        table = all_data_html(synthetic, "财务期间")
        self.assertNotIn("<th>环比</th>", table)
        self.assertNotIn("<th>同比 / 变化</th>", table)

    def test_display_conversion_does_not_mutate_raw_inputs(self):
        records = json.loads((PROJECT_DIR / "structured_data/financial_records.json").read_text(encoding="utf-8"))
        catl = next(row for row in records if row.get("company") == "宁德时代" and row.get("period") == "2026H1" and row.get("metric") == "revenue" and row.get("scope") == "group")
        nvidia = next(row for row in records if row.get("company") == "英伟达" and row.get("period") == "FY2027Q1" and row.get("metric") == "revenue" and row.get("scope") == "group" and row.get("basis") == "US_GAAP")
        self.assertEqual((catl["value"], catl["unit"]), (276916.58, "CNY million"))
        self.assertEqual((nvidia["value"], nvidia["unit"]), (81615, "USD million"))
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        catl_page = next(page for page in payload["company_pages"].values() if page["company"] == "宁德时代")
        self.assertIn("2,769.17", catl_page["html"])
        self.assertIn("亿元", catl_page["html"])

    def test_patch_financial_facts_and_formulas_are_preserved_exactly(self):
        patch = json.loads((PROJECT_DIR / "structured_data/patches/VISUALIZER_DATA_PATCH_2026-08-20.json").read_text(encoding="utf-8-sig"))["records"]
        merged = json.loads((PROJECT_DIR / "structured_data/financial_records.json").read_text(encoding="utf-8"))
        fields = ("company", "period", "metric", "scope", "business", "geography", "product", "basis", "measurement_basis")
        index = {tuple(row.get(field) for field in fields): row for row in merged}
        protected = ("value", "unit", "currency", "basis", "source_type", "formula", "source", "note")
        for row in patch:
            merged_row = index[tuple(row.get(field) for field in fields)]
            self.assertEqual({field: merged_row.get(field) for field in protected}, {field: row.get(field) for field in protected})
        calculated = [row for row in patch if row.get("source_type") == "program_calculated"]
        self.assertEqual(len(calculated), 24)
        for row in calculated:
            self.assertEqual(index[tuple(row.get(field) for field in fields)].get("formula"), row.get("formula"))

    def test_battery_production_is_not_relabelled_as_shipments(self):
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        page = next(page for page in payload["company_pages"].values() if page["company"] == "宁德时代")
        self.assertIn("498GWh 为电池系统产量", page["html"])
        overview = page["html"].split('</section><nav class="section-nav"', 1)[0]
        self.assertNotIn("单Wh", overview)

    def test_geely_restated_warning_is_visible_and_history_is_retained(self):
        records = json.loads((PROJECT_DIR / "structured_data/financial_records.json").read_text(encoding="utf-8"))
        old_rows = [row for row in records if row.get("company") == "吉利汽车控股有限公司" and row.get("period") == "2025H1"]
        self.assertEqual(len(old_rows), 4)
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        page = next(page for page in payload["company_pages"].values() if page["company"] == "吉利汽车")
        self.assertIn("旧 as-reported 历史继续保留", page["html"])

    def test_ratio_records_are_not_derived_by_parser(self):
        records = json.loads((PROJECT_DIR / "structured_data/financial_records.json").read_text(encoding="utf-8"))
        ratio_metrics = {"gross_margin", "operating_margin", "segment_ebt_margin", "nev_sales_share", "export_sales_share"}
        expected = sum(row.get("metric") in ratio_metrics for row in records)
        payload = build(PROJECT_DIR / "structured_data/financial_records.json")
        actual = 0
        for page in payload["company_pages"].values():
            for group in page["page_data"]["series_groups"].values():
                actual += sum(len(item["records"]) for item in group if any(metric in item["label"] for metric in ()))
        self.assertEqual(payload["summary"]["record_count"], len(records))
        self.assertGreater(expected, 0)

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
