import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/export_snapshot.py"
SPEC = importlib.util.spec_from_file_location("export_snapshot", MODULE_PATH)
assert SPEC and SPEC.loader
export_snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(export_snapshot)


class FrontendRulesTest(unittest.TestCase):
    def test_missing_calendar_coverage_fails_closed(self):
        original = export_snapshot.load_calendar_coverage_reviews
        export_snapshot.load_calendar_coverage_reviews = lambda: []
        try:
            with self.assertRaisesRegex(export_snapshot.SnapshotError, "缺少下一次财报事件"):
                export_snapshot.verify_calendar_coverage({"co_missing"}, [])
        finally:
            export_snapshot.load_calendar_coverage_reviews = original

    def test_past_unreleased_event_fails_closed(self):
        original = export_snapshot.load_calendar_coverage_reviews
        export_snapshot.load_calendar_coverage_reviews = lambda: []
        stale_date = (date.today() - timedelta(days=1)).isoformat()
        try:
            with self.assertRaisesRegex(export_snapshot.SnapshotError, "未发布事件日期已过期"):
                export_snapshot.verify_calendar_coverage(
                    {"co_stale"},
                    [{
                        "company_id": "co_stale",
                        "period": "test",
                        "released": False,
                        "official_appointment_date": stale_date,
                    }],
                )
        finally:
            export_snapshot.load_calendar_coverage_reviews = original

    def test_duplicate_metric_display_names_fail_closed(self):
        duplicate_series = [
            {
                "series_id": "series_a",
                "base_label": "营业收入",
                "label": "营业收入",
                "period_type": "quarter",
                "basis": "GAAP",
            },
            {
                "series_id": "series_b",
                "base_label": "营业收入",
                "label": "营业收入",
                "period_type": "fy",
                "basis": "GAAP",
            },
        ]
        with self.assertRaisesRegex(export_snapshot.SnapshotError, "显示名称重复"):
            export_snapshot.verify_series_labels("co_test", duplicate_series)

    def test_disambiguation_makes_metric_names_unique(self):
        series = [
            {
                "series_id": "series_a",
                "base_label": "营业收入",
                "label": "营业收入",
                "period_type": "quarter",
                "basis": "GAAP",
                "records": [{"period": "2026Q1"}],
            },
            {
                "series_id": "series_b",
                "base_label": "营业收入",
                "label": "营业收入",
                "period_type": "fy",
                "basis": "GAAP",
                "records": [{"period": "FY2025"}],
            },
        ]
        export_snapshot.disambiguate_series_labels(series)
        export_snapshot.verify_series_labels("co_test", series)
        self.assertEqual(len({item["label"] for item in series}), 2)
        self.assertIn("单季", series[0]["label"])
        self.assertIn("全年", series[1]["label"])


if __name__ == "__main__":
    unittest.main()
