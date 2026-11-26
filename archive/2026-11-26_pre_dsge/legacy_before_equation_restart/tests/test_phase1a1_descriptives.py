"""Acceptance tests for Phase 1A-1 frozen-sample descriptive diagnostics."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "configs" / "phase1.yaml").read_text(encoding="utf-8"))
CORE = ROOT / "data" / "processed" / "core_monthly_panel.csv"
DATASET = ROOT / "data" / "processed" / "phase1" / "monthly_structural_v1.csv"
OUTPUT = ROOT / "outputs" / "phase1"
LEVELS = ["lc_spot", "lc_output", "spodumene_price", "spodumene_cny_t", "battery_install", "usd_cny_mean"]
PREFIXES = ["lc_spot", "lc_output", "spodumene_price", "spodumene_cny", "battery_install", "usd_cny"]


class Phase1A1DescriptiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.core = pd.read_csv(CORE)
        cls.data = pd.read_csv(DATASET)

    def test_01_data_freeze_v1_remains_unchanged(self) -> None:
        self.assertEqual(self.core.month.iloc[0], "2020-01")
        self.assertEqual(self.core.month.iloc[-1], "2025-09")
        self.assertEqual(len(self.core), 69)

    def test_02_structural_dataset_has_69_rows(self) -> None:
        self.assertEqual(len(self.data), CONFIG["expected_months"])

    def test_03_first_month(self) -> None:
        self.assertEqual(self.data.month.iloc[0], CONFIG["sample_start"])

    def test_04_last_month(self) -> None:
        self.assertEqual(self.data.month.iloc[-1], CONFIG["sample_end"])

    def test_05_no_duplicate_months(self) -> None:
        self.assertFalse(self.data.month.duplicated().any())

    def test_06_no_unexpected_missing_core_levels(self) -> None:
        self.assertFalse(self.data[LEVELS].isna().any().any())

    def test_07_log_inputs_are_positive(self) -> None:
        self.assertTrue(self.data[LEVELS].gt(0).all().all())

    def test_08_dlog_initial_missing_only(self) -> None:
        for prefix in PREFIXES:
            series = self.data[f"{prefix}_dlog"]
            self.assertTrue(pd.isna(series.iloc[0]))
            self.assertTrue(series.iloc[1:].notna().all())

    def test_09_yoy_initial_twelve_missing_only(self) -> None:
        for prefix in PREFIXES:
            for suffix in ("yoy_log", "yoy_pct"):
                series = self.data[f"{prefix}_{suffix}"]
                self.assertTrue(series.iloc[:12].isna().all())
                self.assertTrue(series.iloc[12:].notna().all())

    def test_10_mom_formula(self) -> None:
        expected = (self.data.lc_spot.iloc[1] / self.data.lc_spot.iloc[0] - 1) * 100
        self.assertAlmostEqual(self.data.lc_spot_mom_pct.iloc[1], expected)

    def test_11_yoy_formula(self) -> None:
        expected = (self.data.battery_install.iloc[12] / self.data.battery_install.iloc[0] - 1) * 100
        self.assertAlmostEqual(self.data.battery_install_yoy_pct.iloc[12], expected)

    def test_12_spodumene_cny_consistency(self) -> None:
        expected = self.data.spodumene_price * self.data.usd_cny_mean
        self.assertTrue(np.allclose(expected, self.data.spodumene_cny_t, rtol=1e-9, atol=1e-7))

    def test_13_no_interpolation(self) -> None:
        code = self._new_code()
        self.assertNotIn(".interpolate(", code)
        self.assertNotIn("spline", code.lower())

    def test_14_no_forward_or_backward_fill(self) -> None:
        code = self._new_code()
        self.assertNotIn(".ffill(", code)
        self.assertNotIn(".bfill(", code)

    def test_15_no_future_tail_observations(self) -> None:
        self.assertFalse(self.data.month.gt("2025-09").any())

    def test_16_commercial_workbook_hashes_unchanged(self) -> None:
        ledger = pd.read_csv(ROOT / "data" / "metadata" / "manual_industry_raw_hashes.csv", dtype=str)
        for item in ledger.itertuples(index=False):
            actual = hashlib.sha256((ROOT / item.file).read_bytes()).hexdigest()
            self.assertEqual(actual, item.sha256)

    def test_17_data_freeze_sha256_unchanged(self) -> None:
        actual = hashlib.sha256(CORE.read_bytes()).hexdigest()
        self.assertEqual(actual, CONFIG["data_freeze_sha256"])

    def test_18_figures_use_exact_configured_sample(self) -> None:
        figures = sorted(path for path in (OUTPUT / "figures").glob("*.png") if int(path.name.split("_", 1)[0]) <= 10)
        self.assertEqual(len(figures), 10)
        expected = f"{CONFIG['sample_start']} to {CONFIG['sample_end']}"
        for figure in figures:
            with Image.open(figure) as image:
                self.assertEqual(image.info.get("Sample"), expected)

    def test_19_annual_2025_is_ytd_sep(self) -> None:
        annual = pd.read_csv(OUTPUT / "tables" / "annual_summary.csv")
        labels = set(annual.loc[annual.year.eq(2025), "year_label"])
        self.assertEqual(labels, {"2025_YTD_SEP"})

    def test_20_robustness_data_not_merged_and_anomalies_kept(self) -> None:
        forbidden = {"lc_spot_mysteel", "spodumene_mysteel", "spodumene_concentrate_import_smm_filtered"}
        self.assertTrue(forbidden.isdisjoint(self.data.columns))
        changes = pd.read_csv(OUTPUT / "data_audit" / "phase1a1_large_changes.csv")
        known = changes.loc[changes.known_anomaly.astype(bool)]
        self.assertEqual(set(zip(known.variable, known.month)), {("lc_output", "2020-03"), ("battery_install", "2020-03")})
        self.assertEqual(set(known.decision), {"KEEP_REVIEW_FLAG"})

    @staticmethod
    def _new_code() -> str:
        paths = [
            ROOT / "src" / "diagnostics" / "transformations.py",
            ROOT / "src" / "diagnostics" / "descriptive.py",
            ROOT / "scripts" / "phase1" / "build_phase1a1_dataset.py",
            ROOT / "scripts" / "run_phase1a1_descriptives.py",
        ]
        return "\n".join(path.read_text(encoding="utf-8") for path in paths)


if __name__ == "__main__":
    unittest.main()
