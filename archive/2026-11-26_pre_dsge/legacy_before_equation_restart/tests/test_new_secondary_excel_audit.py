"""Acceptance tests for the Data Freeze v2 secondary-Excel audit."""
from __future__ import annotations

import subprocess
import sys
import unittest
from datetime import date, datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_audit.secondary_excel import (  # noqa: E402
    BATTERY_FILENAME,
    BATTERY_SHA256,
    DONGWU_FILENAME,
    DONGWU_SHA256,
    V1_SHA256,
    AuditPaths,
    build_quote_calendar_audit,
    quote_day_decision,
    read_dongwu_spot,
    search_valid_series,
    sha256,
)


class NewSecondaryExcelAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = AuditPaths(ROOT)
        cls.inventory = pd.read_csv(ROOT / "data/metadata/new_excel_secondary_audit.csv")
        cls.reconciliation = pd.read_csv(ROOT / "data/metadata/dongwu_smm_lc_spot_reconciliation.csv")
        cls.quote_audit = pd.read_csv(ROOT / "data/metadata/dongwu_smm_quote_calendar_audit.csv")
        cls.candidates = pd.read_csv(ROOT / "data/processed/candidates/lc_spot_dongwu_smm_tail_candidates.csv")
        cls.battery = pd.read_csv(ROOT / "data/metadata/battery_chemistry_tail_reconciliation.csv")

    def test_01_data_freeze_v1_hash_unchanged(self):
        self.assertEqual(sha256(ROOT / "data/processed/core_monthly_panel.csv"), V1_SHA256)

    def test_02_original_excel_hashes_unchanged(self):
        self.assertEqual(sha256(self.paths.dongwu), DONGWU_SHA256)
        self.assertEqual(sha256(self.paths.battery), BATTERY_SHA256)

    def test_03_original_workbooks_not_modified(self):
        expected = dict(zip(self.inventory.filename, self.inventory.modified_time))
        for path in (self.paths.dongwu, self.paths.battery):
            actual = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            self.assertEqual(actual, expected[path.name])

    def test_04_date_parsing_correct(self):
        raw, metadata = read_dongwu_spot(self.paths.dongwu)
        self.assertEqual((metadata["first_date"], metadata["last_date"]), ("2019-12-27", "2026-06-12"))
        self.assertIsInstance(raw.date.iloc[0], date)

    def test_05_unit_conversion_correct(self):
        row = self.candidates.loc[self.candidates.month.eq("2025-12")].iloc[0]
        self.assertAlmostEqual(row.value_cny_t, row.raw_mean * 10000)

    def test_06_duplicate_date_detection(self):
        raw, metadata = read_dongwu_spot(self.paths.dongwu)
        self.assertEqual(metadata["duplicate_dates"], 0)
        self.assertFalse(raw.date.duplicated().any())

    def test_07_holiday_carry_forward_rule_is_deterministic(self):
        canonical = pd.read_csv(ROOT / "data/interim/industry/lc_spot_daily.csv")
        canonical_dates = set(pd.to_datetime(canonical.date).dt.date)
        first = quote_day_decision(date(2025, 10, 1), canonical_dates, date(2025, 9, 30))
        second = quote_day_decision(date(2025, 10, 1), canonical_dates, date(2025, 9, 30))
        self.assertEqual(first, second)
        self.assertEqual(first, (False, True, "EXCLUDED_KNOWN_CHINA_HOLIDAY"))

    def test_08_2025_10_validation_checkpoint(self):
        row = self.reconciliation.loc[self.reconciliation.month.eq("2025-10")].iloc[0]
        self.assertAlmostEqual(row.dongwu_monthly_value, 75291.18, places=2)
        self.assertEqual(row.n_effective_quote_days, 17)
        self.assertEqual(row.match_status, "ROUNDING_MATCH")

    def test_09_partial_2026_06_cannot_be_promoted(self):
        row = self.candidates.loc[self.candidates.month.eq("2026-06")].iloc[0]
        self.assertEqual(row.coverage_status, "PARTIAL_MONTH")
        self.assertEqual(row.decision, "PARTIAL_MONTH_DO_NOT_USE")

    def test_10_candidate_months_complete_before_review_acceptance(self):
        reviewable = self.candidates.loc[self.candidates.decision.eq("ACCEPTABLE_WITH_REVIEW")]
        self.assertEqual(set(reviewable.month), {"2025-12", "2026-04", "2026-05"})
        self.assertTrue(reviewable.coverage_status.eq("FULL_MONTH_CANDIDATE").all())

    def test_11_battery_reconciliation_exact_where_expected(self):
        overlap = self.battery.loc[self.battery.month.between("2026-03", "2026-06")]
        self.assertTrue(overlap.total_reconciliation_status.eq("EXACT_MATCH").all())
        self.assertTrue(overlap.difference_vs_existing_gwh.eq(0).all())

    def test_12_no_2026_07_enters_v1(self):
        v1 = pd.read_csv(ROOT / "data/processed/core_monthly_panel.csv")
        self.assertNotIn("2026-07", set(v1.month))
        july = self.battery.loc[self.battery.month.eq("2026-07")].iloc[0]
        self.assertEqual(july.total_reconciliation_status, "NEW_TAIL_CANDIDATE")

    def test_13_sc6_false_match_prevented(self):
        sc6_hits, _ = search_valid_series([self.paths.dongwu, self.paths.battery])
        self.assertEqual(sc6_hits, [])

    def test_14_lc_output_false_match_prevented(self):
        _, output_hits = search_valid_series([self.paths.dongwu, self.paths.battery])
        self.assertEqual(output_hits, [])

    def test_15_commercial_derived_candidates_are_ignored(self):
        paths = [
            "data/processed/candidates/lc_spot_dongwu_smm_tail_candidates.csv",
            "data/metadata/dongwu_smm_quote_calendar_audit.csv",
            "data/metadata/dongwu_smm_lc_spot_reconciliation.csv",
        ]
        for path in paths:
            result = subprocess.run(["git", "check-ignore", path], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 0)

    def test_16_quote_calendar_audit_is_reproducible(self):
        raw, _ = read_dongwu_spot(self.paths.dongwu)
        canonical = pd.read_csv(ROOT / "data/interim/industry/lc_spot_daily.csv")
        rebuilt = build_quote_calendar_audit(raw, canonical)
        self.assertEqual(len(rebuilt), len(self.quote_audit))
        self.assertEqual(
            rebuilt.loc[rebuilt.date.eq("2025-10-01"), "effective_quote_day"].iloc[0], False
        )


if __name__ == "__main__":
    unittest.main()
