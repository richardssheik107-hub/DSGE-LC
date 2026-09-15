"""Acceptance tests for Phase 1A-2 mechanism diagnostics."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.diagnostics.break_tests import bic_mean_segmentation  # noqa: E402
from src.diagnostics.lag_screening import LAG_CONVENTION, aligned_pairs, correlation_at_lag, month_of_year_residualize  # noqa: E402
from src.diagnostics.phase1a2 import margin_proxy_table  # noqa: E402


CONFIG = json.loads((ROOT / "configs" / "phase1.yaml").read_text(encoding="utf-8"))
FREEZE = ROOT / "data" / "processed" / "core_monthly_panel.csv"
DATASET = ROOT / "data" / "processed" / "phase1" / "monthly_structural_v1.csv"
TABLES = ROOT / "outputs" / "phase1" / "tables"
FIGURES = ROOT / "outputs" / "phase1" / "figures"
REQUIRED_MECHANISMS = {
    "Cost → Price", "Demand → Price", "Price → Demand", "Supply → Price",
    "Price → Future Supply", "Margin → Future Supply",
}


class Phase1A2DiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = pd.read_csv(DATASET)
        cls.stationarity = pd.read_csv(TABLES / "stationarity_results.csv")
        cls.za = pd.read_csv(TABLES / "zivot_andrews_results.csv")
        cls.correlations = pd.read_csv(TABLES / "lead_lag_correlations.csv")
        cls.candidates = pd.read_csv(TABLES / "lead_lag_candidate_regions.csv")
        cls.hac = pd.read_csv(TABLES / "lead_lag_hac_confirmation.csv")
        cls.breaks = pd.read_csv(TABLES / "structural_break_screening.csv")
        cls.evidence = pd.read_csv(TABLES / "mechanism_evidence_table.csv")

    def test_01_freeze_hash_unchanged(self):
        self.assertEqual(hashlib.sha256(FREEZE.read_bytes()).hexdigest(), CONFIG["data_freeze_sha256"])

    def test_02_exactly_69_rows(self):
        self.assertEqual(len(self.data), 69)

    def test_03_no_future_tail(self):
        self.assertFalse(self.data.month.gt("2025-09").any())

    def test_04_adf_inputs_and_results_finite(self):
        self.assertTrue(np.isfinite(self.stationarity[["adf_stat", "adf_p_value"]]).all().all())

    def test_05_kpss_inputs_and_results_finite(self):
        self.assertTrue(np.isfinite(self.stationarity[["kpss_stat", "kpss_p_value"]]).all().all())

    def test_06_za_breaks_inside_sample(self):
        self.assertTrue(self.za.break_index.between(0, len(self.data) - 1).all())

    def test_07_lag_convention_is_explicit(self):
        self.assertEqual(set(self.correlations.lag_convention), {LAG_CONVENTION})

    def test_08_positive_lag_means_x_leads_y(self):
        x = pd.Series([1.0, 2, 3, 4, 5])
        y = pd.Series([0.0, 1, 2, 3, 4])
        self.assertAlmostEqual(correlation_at_lag(x, y, 1)["pearson"], 1.0)

    def test_09_effective_sample_size(self):
        result = correlation_at_lag(pd.Series(range(10)), pd.Series(range(10)), 3)
        self.assertEqual(result["n_effective"], 7)

    def test_10_no_lookahead_alignment_error(self):
        pairs = aligned_pairs(pd.Series([10, 20, 30, 40]), pd.Series([1, 2, 3, 4]), 2)
        self.assertEqual(pairs.to_dict("list"), {"x": [10, 20], "y": [3.0, 4.0]})

    def test_11_pearson_spearman_use_same_pairs(self):
        x = pd.Series([1.0, np.nan, 3, 4, 8])
        y = pd.Series([2.0, 3, 5, np.nan, 9])
        pairs = aligned_pairs(x, y, 0)
        result = correlation_at_lag(x, y, 0)
        self.assertAlmostEqual(result["pearson"], pairs.x.corr(pairs.y, method="pearson"))
        self.assertAlmostEqual(result["spearman"], pairs.x.corr(pairs.y, method="spearman"))

    def test_12_moy_residualization_preserves_order(self):
        result = month_of_year_residualize(self.data, ["battery_install_dlog"])
        self.assertEqual(list(result.month), list(self.data.month))

    def test_13_moy_residual_means_are_zero(self):
        result = month_of_year_residualize(self.data, ["battery_install_dlog", "lc_output_dlog"])
        month_number = pd.PeriodIndex(result.month, freq="M").month
        means = result.iloc[:, 1:].groupby(month_number).mean()
        self.assertTrue(np.allclose(means.to_numpy(), 0.0, atol=1e-12, equal_nan=True))

    def test_14_margin_proxy_formula(self):
        margin = margin_proxy_table(self.data)
        z = lambda s: (s - s.mean()) / s.std(ddof=1)
        expected = z(self.data.lc_spot_log) - z(self.data.spodumene_cny_log)
        self.assertTrue(np.allclose(margin.margin_proxy_zlevel, expected, equal_nan=True))

    def test_15_margin_proxy_has_no_currency_unit(self):
        margin = pd.read_csv(ROOT / "data" / "processed" / "phase1" / "margin_proxy_diagnostics.csv")
        self.assertEqual(list(margin.columns), ["month", "margin_proxy_zlevel", "margin_proxy_dlog_gap"])

    def test_16_no_conversion_coefficient_introduced(self):
        files = [ROOT / "src/diagnostics/phase1a2.py", ROOT / "scripts/run_phase1a2_diagnostics.py"]
        code = "\n".join(path.read_text(encoding="utf-8").lower() for path in files)
        self.assertNotIn("theta", code)

    def test_17_robustness_sample_does_not_replace_full_sample(self):
        full = self.correlations.loc[self.correlations.sample_variant.eq("FULL_SAMPLE")]
        robust = self.correlations.loc[self.correlations.sample_variant.eq("EXCLUDE_EARLY_2020_ROBUSTNESS")]
        self.assertFalse(full.empty)
        self.assertFalse(robust.empty)
        self.assertEqual(len(self.data), 69)

    def test_18_maximum_two_breaks(self):
        selected = bic_mean_segmentation(self.data.lc_spot_log.to_numpy(), max_breaks=2, min_segment=18)
        self.assertLessEqual(len(selected["breaks"]), 2)

    def test_19_minimum_break_segment_18(self):
        selected = bic_mean_segmentation(self.data.lc_spot_log.to_numpy(), max_breaks=2, min_segment=18)
        bounds = (0, *selected["breaks"], len(self.data))
        self.assertTrue(all(b - a >= 18 for a, b in zip(bounds[:-1], bounds[1:])))

    def test_20_all_required_mechanisms_present(self):
        self.assertEqual(set(self.evidence.mechanism), REQUIRED_MECHANISMS)

    def test_21_no_commercial_validation_table_created_in_outputs(self):
        names = {path.name.lower() for path in TABLES.glob("*.csv")}
        self.assertFalse(any("mysteel" in name or "observed_margin" in name for name in names))

    def test_22_phase1_outputs_are_git_ignored(self):
        targets = ["data/processed/phase1/margin_proxy_diagnostics.csv", "outputs/phase1/tables/stationarity_results.csv"]
        for target in targets:
            result = subprocess.run(["git", "check-ignore", target], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)

    def test_23_no_interpolation_or_fill(self):
        paths = list((ROOT / "src/diagnostics").glob("*.py")) + [ROOT / "scripts/run_phase1a2_diagnostics.py"]
        code = "\n".join(path.read_text(encoding="utf-8").lower() for path in paths)
        for forbidden in (".interpolate(", ".ffill(", ".bfill("):
            self.assertNotIn(forbidden, code)

    def test_24_no_phase1b_model_execution(self):
        code = (ROOT / "scripts/run_phase1a2_diagnostics.py").read_text(encoding="utf-8").lower()
        for forbidden in ("random_walk", "bvar", "vecm", "kalman", "mcmc", "irf", "fevd"):
            self.assertNotIn(forbidden, code)

    def test_25_required_output_tables_exist(self):
        required = {"stationarity_results.csv", "zivot_andrews_results.csv", "lead_lag_correlations.csv",
                    "lead_lag_candidate_regions.csv", "lead_lag_hac_confirmation.csv",
                    "structural_break_screening.csv", "mechanism_evidence_table.csv"}
        self.assertTrue(required.issubset({path.name for path in TABLES.glob("*.csv")}))

    def test_26_candidate_regions_are_contiguous_ranges(self):
        self.assertTrue((self.candidates.candidate_lag_end - self.candidates.candidate_lag_start >= 1).all())
        self.assertTrue(self.candidates.groupby("mechanism").size().le(3).all())

    def test_27_hac_bandwidth_rule(self):
        expected = self.hac.n.pow(0.25).apply(np.floor).clip(upper=3).astype(int)
        self.assertTrue((self.hac.hac_bandwidth == expected).all())

    def test_28_low_effective_sample_is_flagged(self):
        low = self.correlations.loc[self.correlations.n_effective.lt(48)]
        self.assertTrue(low.sample_flag.eq("LOW_EFFECTIVE_SAMPLE").all())

    def test_29_stationarity_specifications_complete(self):
        counts = self.stationarity.groupby("variable").size()
        self.assertEqual(set(counts), {4})

    def test_30_margin_validation_overlap_below_six(self):
        observed = pd.read_csv(ROOT / "data/processed/validation/mysteel_spodumene_route_cost_margin_monthly.csv")
        overlap = observed.loc[observed.month.between("2020-01", "2025-09")]
        self.assertLess(len(overlap), 6)

    def test_31_new_figures_use_frozen_sample_metadata(self):
        expected = "2020-01 to 2025-09"
        for number in range(11, 19):
            path = next(FIGURES.glob(f"{number:02d}_*.png"))
            with Image.open(path) as image:
                self.assertEqual(image.info.get("Sample"), expected)


if __name__ == "__main__":
    unittest.main()
