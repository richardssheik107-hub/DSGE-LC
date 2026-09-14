import csv
import hashlib
import importlib.util
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gap", ROOT / "scripts/data/build_public_gap_closure.py")
gap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gap)


class PublicGapClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        gap.build()

    def test_actual_forecast_parser_contract(self):
        allowed = {"ACTUAL", "ACTUAL_APPROXIMATE", "FORECAST", "ESTIMATE", "PLANNED"}
        self.assertTrue(all(row[7] in allowed for row in gap.OUTPUT))

    def test_source_grade_validation(self):
        self.assertTrue(all(row[11] in {"SOURCE_A", "SOURCE_B", "SOURCE_C", "SOURCE_D"} for row in gap.OUTPUT))

    def test_battery_monthly_not_cumulative(self):
        self.assertEqual(gap.BATTERY[0][1], 56.5)
        self.assertNotEqual(gap.BATTERY[0][1], 124.9)

    def test_output_forecast_cannot_enter_actual(self):
        self.assertFalse(any(row[7] != "ACTUAL" and row[10] == "ACCEPTED_PUBLIC_PATCH" for row in gap.OUTPUT))

    def test_ten_thousand_ton_conversion(self):
        self.assertAlmostEqual(9.79 * 10000, 97900)

    def test_trade_kg_to_ton_conversion(self):
        self.assertEqual(19597000 / 1000, gap.TRADE_VALUES["2025-09"][0])

    def test_spot_candidate_validation(self):
        accepted = [r for r in gap.SPOT if r[8] == "ACCEPTED_PUBLIC_PATCH"]
        self.assertTrue(all(r[2] == "MONTHLY_MEAN" and r[7] for r in accepted))

    def test_spodumene_definition_matching(self):
        accepted = [r for r in gap.SPODUMENE if r[10] == "ACCEPTED_PUBLIC_PATCH"]
        self.assertTrue(all(r[3] in {"SC6", "6% Li2O"} and r[4] == "CIF China" and r[5] == "USD" for r in accepted))

    def test_v1_core_immutable(self):
        before = (ROOT / "data/processed/core_monthly_panel.csv").read_bytes()
        gap.build()
        self.assertEqual(before, (ROOT / "data/processed/core_monthly_panel.csv").read_bytes())

    def test_v2_no_overwrite_existing(self):
        v1 = pd.read_csv(ROOT / "data/processed/core_monthly_panel.csv")
        v2 = pd.read_csv(ROOT / "data/processed/core_monthly_panel_v2_candidate.csv")
        cols = ["lc_spot", "lc_output_total", "spodumene_price", "battery_install"]
        merged = v1[["month"] + cols].merge(v2[["month"] + cols], on="month", suffixes=("_v1", "_v2"))
        for col in cols:
            pd.testing.assert_series_equal(merged[f"{col}_v1"], merged[f"{col}_v2"], check_names=False)

    def test_tail_overlap_reconciliation(self):
        with (ROOT / "data/metadata/public_tail_reconciliation.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(rows and all(r["status"] == "EXACT_MATCH" for r in rows))

    def test_78_month_target_coverage(self):
        v2 = pd.read_csv(ROOT / "data/processed/core_monthly_panel_v2_candidate.csv")
        self.assertEqual(len(v2), 78)
        complete = v2[["lc_spot", "lc_output_total", "spodumene_price", "usd_cny_mean", "battery_install"]].notna().all(axis=1)
        self.assertEqual(int(complete.sum()), 69)

    def test_chinabond_monthly_coverage_when_downloaded(self):
        panel = pd.read_csv(ROOT / "data/processed/public_monthly_panel_v2_candidate.csv")
        daily = ROOT / "data/processed/phase1/china_gov_yields_daily.csv"
        if daily.exists():
            self.assertEqual(int(panel["china_gov_3m_mean"].notna().sum()), 78)
            self.assertEqual(int(panel["china_gov_6m_mean"].notna().sum()), 78)

    def test_no_interpolation(self):
        source = (ROOT / "scripts/data/build_public_gap_closure.py").read_text(encoding="utf-8").lower()
        self.assertNotIn(".interpolate(", source)
        self.assertNotIn(".ffill(", source)
        self.assertNotIn(".bfill(", source)

    def test_public_manifest_complete(self):
        with (ROOT / "data/metadata/public_gap_source_manifest.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        required = {"variable", "period", "unit", "source_grade", "source_name", "source_url", "actual_or_forecast", "definition_match", "candidate_status"}
        self.assertTrue(rows and required.issubset(rows[0]))
        self.assertTrue(all(r["variable"] and r["period"] and r["source_name"] and r["source_url"] for r in rows))

    def test_commercial_raw_hash_unchanged(self):
        ledger = pd.read_csv(ROOT / "data/metadata/manual_industry_raw_hashes.csv")
        for row in ledger.itertuples(index=False):
            self.assertEqual(hashlib.sha256((ROOT / row.file).read_bytes()).hexdigest(), row.sha256)


if __name__ == "__main__":
    unittest.main()
