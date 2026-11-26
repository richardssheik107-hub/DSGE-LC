"""Regression tests for manual industry-data ingestion."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed" / "industry"
METADATA = ROOT / "data" / "metadata"
sys.path.insert(0, str(ROOT / "scripts" / "data"))
from build_industry_monthly import aggregate_price  # noqa: E402


class IndustryDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spot = pd.read_csv(PROCESSED / "lc_spot_monthly.csv", na_values=["NA"])
        cls.output = pd.read_csv(PROCESSED / "lc_output_monthly.csv", na_values=["NA"])
        cls.spod = pd.read_csv(PROCESSED / "spodumene_price_monthly.csv", na_values=["NA"])
        cls.battery = pd.read_csv(PROCESSED / "battery_install_monthly.csv", na_values=["NA"])
        cls.core = pd.read_csv(ROOT / "data" / "processed" / "core_monthly_panel.csv", na_values=["NA"])

    def test_manual_raw_hashes_match(self) -> None:
        ledger = pd.read_csv(METADATA / "manual_industry_raw_hashes.csv", dtype=str)
        self.assertEqual(set(ledger.protected_status), {"HASH_UNCHANGED"})
        for item in ledger.itertuples(index=False):
            digest = hashlib.sha256((ROOT / item.file).read_bytes()).hexdigest()
            self.assertEqual(digest, item.sha256)

    def test_spot_nonnegative_and_month_unique(self) -> None:
        self.assertTrue((self.spot.lc_spot_mean >= 0).all())
        self.assertFalse(self.spot.month.duplicated().any())

    def test_spot_unit_dictionary(self) -> None:
        dictionary = pd.read_csv(METADATA / "industry_series_dictionary.csv", dtype=str)
        row = dictionary.loc[dictionary.canonical_name.eq("lc_spot")].iloc[0]
        self.assertEqual(row.processed_unit, "CNY/t")

    def test_output_unique_nonnegative(self) -> None:
        self.assertFalse(self.output.month.duplicated().any())
        self.assertTrue((self.output.lc_output_total >= 0).all())

    def test_spodumene_nonnegative(self) -> None:
        self.assertTrue((self.spod.spodumene_price_mean >= 0).all())

    def test_spodumene_definition(self) -> None:
        dictionary = pd.read_csv(METADATA / "industry_series_dictionary.csv", dtype=str)
        row = dictionary.loc[dictionary.canonical_name.eq("spodumene_price")].iloc[0]
        self.assertEqual(row.grade, "6% Li2O")
        self.assertEqual(row.region, "CIF China")
        self.assertEqual(row.processed_unit, "USD/t")

    def test_battery_unique_nonnegative_gwh(self) -> None:
        self.assertFalse(self.battery.month.duplicated().any())
        self.assertTrue((self.battery.battery_install_total >= 0).all())
        self.assertEqual(set(self.battery.unit), {"GWh"})

    def test_daily_monthly_mean_calculation(self) -> None:
        daily = pd.read_csv(ROOT / "data" / "interim" / "industry" / "lc_spot_daily.csv", na_values=["NA"])
        daily["month"] = pd.to_datetime(daily.date).dt.to_period("M").astype(str)
        expected = daily.loc[daily.month.eq("2020-01"), "lc_spot"].mean()
        actual = self.spot.loc[self.spot.month.eq("2020-01"), "lc_spot_mean"].iloc[0]
        self.assertAlmostEqual(actual, expected)

    def test_eom_calculation(self) -> None:
        daily = pd.read_csv(ROOT / "data" / "interim" / "industry" / "lc_spot_daily.csv", na_values=["NA"])
        month = daily.loc[pd.to_datetime(daily.date).dt.to_period("M").astype(str).eq("2020-01")].dropna(subset=["lc_spot"])
        expected = month.sort_values("date").lc_spot.iloc[-1]
        actual = self.spot.loc[self.spot.month.eq("2020-01"), "lc_spot_eom"].iloc[0]
        self.assertEqual(actual, expected)

    def test_partial_final_month_excluded(self) -> None:
        self.assertNotIn("2025-10", set(self.spot.month))
        self.assertNotIn("2025-10", set(self.spod.month))

    def test_no_interpolation(self) -> None:
        code = (ROOT / "scripts" / "data" / "build_industry_monthly.py").read_text(encoding="utf-8")
        for forbidden in ("interpolate(", ".ffill(", ".bfill("):
            self.assertNotIn(forbidden, code)

    def test_core_panel_unique_and_complete(self) -> None:
        self.assertFalse(self.core.month.duplicated().any())
        cols = ["lc_spot", "lc_output_total", "spodumene_price", "usd_cny_mean", "battery_install"]
        self.assertFalse(self.core[cols].isna().any().any())

    def test_core_common_window_is_computed(self) -> None:
        audit = pd.read_csv(METADATA / "core_common_sample_audit.csv", dtype=str)
        common = audit.loc[audit.variable.eq("__COMMON__")].iloc[0]
        self.assertEqual(int(float(common.common_months)), len(self.core))
        self.assertGreaterEqual(len(self.core), 60)

    def test_usd_cny_raw_protection(self) -> None:
        ledger = pd.read_csv(METADATA / "protected_raw_hashes.csv", dtype=str)
        item = ledger.loc[ledger.path.eq("data/raw/public/pboc_cfets/fred_dexchus.csv")].iloc[0]
        self.assertEqual(hashlib.sha256((ROOT / item.path).read_bytes()).hexdigest(), item.sha256)

    def test_trade_reconciliation_calculation(self) -> None:
        data = pd.read_csv(METADATA / "lc_trade_reconciliation.csv", na_values=["NA"])
        valid = data.dropna(subset=["comtrade_import", "excel_import"]).iloc[0]
        self.assertAlmostEqual(valid.import_diff, valid.excel_import - valid.comtrade_import)
        self.assertAlmostEqual(valid.import_diff_pct, valid.import_diff / valid.comtrade_import)

    def test_route_output_sum_check(self) -> None:
        row = self.output.dropna(subset=["route_sum"]).iloc[0]
        expected = row.lc_output_brine + row.lc_output_lepidolite + row.lc_output_spodumene
        self.assertAlmostEqual(row.route_sum, expected)
        self.assertAlmostEqual(row.route_difference, row.lc_output_total - expected)

    def test_battery_chemistry_comparison(self) -> None:
        row = self.battery.dropna(subset=["battery_install_chemistry_sum"]).iloc[0]
        expected = row.battery_install_lfp + row.battery_install_ncm
        self.assertAlmostEqual(row.battery_install_chemistry_sum, expected)

    def test_metadata_completeness(self) -> None:
        dictionary = pd.read_csv(METADATA / "industry_series_dictionary.csv", dtype=str)
        required = ["canonical_name", "source_file", "sheet_name", "original_series_name", "original_source", "definition", "frequency", "processed_unit", "recommended_use", "status"]
        self.assertFalse(dictionary[required].isna().any().any())


if __name__ == "__main__":
    unittest.main()
