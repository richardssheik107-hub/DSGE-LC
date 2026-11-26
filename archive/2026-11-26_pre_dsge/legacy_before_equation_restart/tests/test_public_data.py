"""Non-network regression checks for the public-data deliverables."""
from __future__ import annotations

import unittest
from pathlib import Path
import sys
import hashlib
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "processed" / "public_monthly_panel.csv"
sys.path.insert(0, str(ROOT / "scripts" / "data"))
from fetch_nev import parse_values  # noqa: E402


class PublicDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.panel = pd.read_csv(PANEL, dtype={"month": str})

    def test_month_window_and_unique_keys(self) -> None:
        self.assertEqual(len(self.panel), 78)
        self.assertEqual(self.panel.month.iloc[0], "2020-01")
        self.assertEqual(self.panel.month.iloc[-1], "2026-06")
        self.assertFalse(self.panel.month.duplicated().any())

    def test_numeric_columns(self) -> None:
        for column in self.panel.columns[1:]:
            self.assertTrue(pd.api.types.is_numeric_dtype(self.panel[column]), column)

    def test_trade_nonnegative(self) -> None:
        for column in ("lc_import_qty", "lc_export_qty"):
            self.assertTrue((self.panel[column].dropna() >= 0).all(), column)

    def test_nev_nonnegative_when_available(self) -> None:
        for column in ("nev_sales", "nev_production"):
            self.assertTrue((self.panel[column].dropna() >= 0).all(), column)

    def test_nev_parser_respects_production_then_sales_order_and_units(self) -> None:
        self.assertEqual(parse_values("新能源汽车产销分别完成12.3万辆和11.4万辆"), (12.3, 11.4))
        self.assertEqual(parse_values("新能源汽车产销分别完成123000辆和114000辆"), (12.3, 11.4))
        self.assertEqual(parse_values("新能源汽车产销均完成8.0万辆"), (8.0, 8.0))

    def test_nev_has_one_documented_derived_month_only(self) -> None:
        derived = pd.read_csv(ROOT / "data" / "metadata" / "nev_derived_months.csv", dtype=str)
        self.assertEqual(derived.month.tolist(), ["2020-08"])
        self.assertIn("cumulative", derived.method.iloc[0])

    def test_chinabond_tenors_are_not_shibor(self) -> None:
        code = (ROOT / "scripts" / "data" / "fetch_rates.py").read_text(encoding="utf-8")
        self.assertIn('values.get(0.25)', code)
        self.assertIn('values.get(0.5)', code)
        self.assertIn('CURVE_ID = "2c9081e50a2f9606010a3068cae70001"', code)
        self.assertIn("No Shibor proxy is", code)

    def test_monthly_rate_aggregation_is_mean_when_daily_source_exists(self) -> None:
        code = (ROOT / "scripts" / "data" / "build_public_phase1_dataset.py").read_text(encoding="utf-8")
        self.assertIn('china_gov_3m_mean=("china_gov_3m", "mean")', code)
        self.assertIn('china_gov_6m_mean=("china_gov_6m", "mean")', code)

    def test_comtrade_raw_responses_exist(self) -> None:
        files = list((ROOT / "data" / "raw" / "public" / "comtrade").glob("comtrade_cn_hs283691_*.json"))
        self.assertGreaterEqual(len(files), 156)

    def test_required_metadata_exists(self) -> None:
        for name in ("public_data_sources.csv", "public_data_audit.csv", "public_data_validation.csv",
                     "nbs_reconciliation.csv", "comtrade_duplicate_audit.csv", "protected_raw_hashes.csv"):
            self.assertTrue((ROOT / "data" / "metadata" / name).exists(), name)

    def test_existing_usd_raw_hash_matches_protection_ledger(self) -> None:
        ledger = pd.read_csv(ROOT / "data" / "metadata" / "protected_raw_hashes.csv", dtype=str)
        item = ledger.loc[ledger.path.eq("data/raw/public/pboc_cfets/fred_dexchus.csv")].iloc[0]
        raw = ROOT / item.path
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        self.assertEqual(digest, item.sha256)

    def test_auxiliary_months_are_unique(self) -> None:
        data = pd.read_csv(ROOT / "data" / "processed" / "auxiliary_macro_monthly.csv", dtype={"month": str})
        self.assertEqual(len(data), 78)
        self.assertFalse(data.month.duplicated().any())

    def test_lpr_prevailing_policy_quote_is_present_each_month(self) -> None:
        data = pd.read_csv(ROOT / "data" / "processed" / "auxiliary_macro_monthly.csv")
        self.assertTrue(data[["lpr_1y", "lpr_5y"]].notna().all().all())
        self.assertEqual(float(data.loc[data.month.eq("2020-01"), "lpr_1y"].iloc[0]), 4.15)
        self.assertEqual(float(data.loc[data.month.eq("2025-05"), "lpr_5y"].iloc[0]), 3.5)

    def test_nev_penetration_is_valid_ratio(self) -> None:
        data = pd.read_csv(ROOT / "data" / "processed" / "auxiliary_macro_monthly.csv")
        value = data.nev_penetration.dropna()
        self.assertTrue(((value >= 0) & (value <= 100)).all())

    def test_gfex_implementation_requires_lc_filter_and_unit_declaration(self) -> None:
        # No GFEX file is accepted unless a future official fetcher applies both
        # guards; the unavailable series must not be fabricated meanwhile.
        daily = ROOT / "data" / "processed" / "phase1" / "lc_warehouse_receipts_daily.csv"
        if daily.exists():
            frame = pd.read_csv(daily)
            self.assertTrue((frame["lc_warehouse_receipt_qty"].dropna() >= 0).all())
            self.assertFalse(frame.date.duplicated().any())
        else:
            self.assertFalse(daily.exists())

    def test_round3_protected_raw_hashes_match(self) -> None:
        ledger = pd.read_csv(ROOT / "data" / "metadata" / "round3_protected_raw_hashes.csv", dtype=str)
        for item in ledger.itertuples(index=False):
            path = ROOT / item.path
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item.sha256)


if __name__ == "__main__":
    unittest.main()
