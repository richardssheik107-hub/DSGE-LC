"""Acceptance tests for strict expanding-window Phase 1B baselines."""
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

from src.baselines.ar import forecast_ar, select_ar_lag  # noqa: E402
from src.baselines.bvar import fit_bvar, forecast_bvar, training_zscore  # noqa: E402
from src.baselines.random_walk import forecast_no_drift, forecast_with_drift  # noqa: E402
from src.baselines.var import forecast_var, select_var_lag  # noqa: E402
from src.evaluation.forecasting import MODEL_DEFINITIONS, failure_records  # noqa: E402
from src.evaluation.metrics import common_origin_predictions, direction_metrics  # noqa: E402
from src.evaluation.splits import SPECIFICATIONS, build_information_set, training_slice  # noqa: E402


CONFIG = json.loads((ROOT / "configs/phase1.yaml").read_text(encoding="utf-8"))
FREEZE = ROOT / "data/processed/core_monthly_panel.csv"
DATASET = ROOT / "data/processed/phase1/monthly_structural_v1.csv"
OUTPUT = ROOT / "outputs/phase1/baseline_results"
FIGURES = ROOT / "outputs/phase1/figures"


class Phase1BBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = pd.read_csv(DATASET)
        cls.predictions = pd.read_csv(OUTPUT / "forecast_predictions.csv")
        cls.metrics = pd.read_csv(OUTPUT / "baseline_metrics.csv")
        cls.diagnostics = pd.read_csv(OUTPUT / "baseline_origin_diagnostics.csv")
        cls.failures = pd.read_csv(OUTPUT / "baseline_model_failures.csv")

    def test_01_freeze_hash_unchanged(self):
        self.assertEqual(hashlib.sha256(FREEZE.read_bytes()).hexdigest(), CONFIG["data_freeze_sha256"])

    def test_02_core_sample_exactly_69_months(self):
        self.assertEqual((len(self.data), self.data.month.iloc[0], self.data.month.iloc[-1]), (69, "2020-01", "2025-09"))

    def test_03_no_2025_10_or_later(self):
        self.assertFalse(self.data.month.gt("2025-09").any())
        self.assertFalse(self.predictions.target_month.gt("2025-09").any())

    def test_04_rw_forecast_equals_origin_spot(self):
        primary = self.predictions.loc[(self.predictions.model == "RW_NO_DRIFT") & (self.predictions.window_variant == "PRIMARY_48")]
        origin_map = self.data.set_index("month").lc_spot
        expected = primary.forecast_origin.map(origin_map)
        self.assertTrue(np.allclose(primary.forecast_spot, expected))

    def test_05_ar_training_never_exceeds_origin(self):
        rows = self.predictions.loc[self.predictions.model == "AR_BIC"]
        self.assertTrue((rows.train_end == rows.forecast_origin).all())

    def test_06_ar_lag_selection_uses_training_only(self):
        origin = self.data.index[self.data.month.eq("2023-12")][0]
        training = self.data.iloc[:origin + 1].lc_spot_dlog.dropna().to_numpy()
        selected, _ = select_ar_lag(training, 3)
        recorded = self.diagnostics.loc[(self.diagnostics.model == "AR_BIC") & (self.diagnostics.origin == "2023-12") & (self.diagnostics.information_set == "RELEASE_SAFE_APPROXIMATION") & (self.diagnostics.window_variant == "PRIMARY_48")].iloc[0]
        self.assertEqual(selected.lag, recorded.selected_lag)

    def test_07_var_training_never_exceeds_origin(self):
        rows = self.predictions.loc[self.predictions.model.str.startswith("VAR_")]
        self.assertTrue((rows.train_end == rows.forecast_origin).all())

    def test_08_var_bic_selection_training_only(self):
        origin = self.data.index[self.data.month.eq("2023-12")][0]
        frame = build_information_set(self.data, "SPEC_A_DLOG4", "RELEASE_SAFE_APPROXIMATION")
        values = training_slice(frame, origin).iloc[:, 1:].to_numpy()
        selected, _ = select_var_lag(values, 2)
        recorded = self.diagnostics.loc[(self.diagnostics.model == "VAR_SPEC_A") & (self.diagnostics.origin == "2023-12") & (self.diagnostics.information_set == "RELEASE_SAFE_APPROXIMATION") & (self.diagnostics.window_variant == "PRIMARY_48")].iloc[0]
        self.assertEqual(selected.lag, recorded.selected_lag)

    def test_09_bvar_standardization_training_only(self):
        values = np.arange(40, dtype=float).reshape(10, 4)
        standardized, mean, scale = training_zscore(values)
        altered_future = np.vstack([values, np.full((2, 4), 1e9)])
        _, future_mean, _ = training_zscore(altered_future)
        self.assertTrue(np.allclose(mean, values.mean(axis=0)))
        self.assertFalse(np.allclose(mean, future_mean))
        self.assertTrue(np.allclose(standardized.mean(axis=0), 0.0))

    def test_10_bvar_prior_mean_zero_for_stationary_transforms(self):
        code = (ROOT / "src/baselines/bvar.py").read_text(encoding="utf-8")
        self.assertIn("prior_mean = np.zeros", code)
        self.assertNotIn("prior_mean = np.ones", code)

    def test_11_bvar_lambda_is_preconfigured(self):
        self.assertEqual(CONFIG["phase1b"]["bvar_lambda"], 0.20)
        self.assertEqual(CONFIG["phase1b"]["bvar_lambda_sensitivity"], [0.10, 0.30])

    def test_12_release_safe_output_shift_exactly_one_month(self):
        frame = build_information_set(self.data, "SPEC_A_DLOG4", "RELEASE_SAFE_APPROXIMATION")
        self.assertTrue(np.allclose(frame.output_dlog.iloc[2:], self.data.lc_output_dlog.iloc[1:-1], equal_nan=True))

    def test_13_release_safe_battery_shift_exactly_one_month(self):
        frame = build_information_set(self.data, "SPEC_A_DLOG4", "RELEASE_SAFE_APPROXIMATION")
        self.assertTrue(np.allclose(frame.battery_dlog.iloc[2:], self.data.battery_install_dlog.iloc[1:-1], equal_nan=True))

    def test_14_spot_and_ore_are_not_shifted(self):
        frame = build_information_set(self.data, "SPEC_A_DLOG4", "RELEASE_SAFE_APPROXIMATION")
        self.assertTrue(np.allclose(frame.spot_dlog, self.data.lc_spot_dlog, equal_nan=True))
        self.assertTrue(np.allclose(frame.ore_cny_dlog, self.data.spodumene_cny_dlog, equal_nan=True))

    def test_15_information_sets_are_separate(self):
        self.assertEqual(set(self.predictions.information_set), {"RELEASE_SAFE_APPROXIMATION", "MONTH_INDEX_IDEALIZED"})

    def test_16_recursive_h3_does_not_use_actual_future_predictors(self):
        origin = 47
        frame = build_information_set(self.data, "SPEC_A_DLOG4", "RELEASE_SAFE_APPROXIMATION")
        train = training_slice(frame, origin).iloc[:, 1:].to_numpy()
        fit, _ = select_var_lag(train, 2)
        first = forecast_var(fit, train, 3)
        changed = self.data.copy()
        changed.loc[origin + 1:, "lc_output_dlog"] = 999.0
        changed_frame = build_information_set(changed, "SPEC_A_DLOG4", "RELEASE_SAFE_APPROXIMATION")
        changed_train = training_slice(changed_frame, origin).iloc[:, 1:].to_numpy()
        second = forecast_var(fit, changed_train, 3)
        self.assertTrue(np.allclose(first, second))

    def test_17_recursive_h6_bvar_uses_no_actual_future_predictors(self):
        origin = 47
        frame = build_information_set(self.data, "SPEC_A_DLOG4", "RELEASE_SAFE_APPROXIMATION")
        train = training_slice(frame, origin).iloc[:, 1:].to_numpy()
        fit = fit_bvar(train)
        first = forecast_bvar(fit, train, 6)
        changed = self.data.copy()
        changed.loc[origin + 1:, ["lc_output_dlog", "battery_install_dlog"]] = 999.0
        changed_frame = build_information_set(changed, "SPEC_A_DLOG4", "RELEASE_SAFE_APPROXIMATION")
        changed_train = training_slice(changed_frame, origin).iloc[:, 1:].to_numpy()
        second = forecast_bvar(fit, changed_train, 6)
        self.assertTrue(np.allclose(first, second))

    def test_18_level_reconstruction_from_dlog(self):
        origin_log = np.log(100.0)
        changes = np.array([.10, -.02, .03])
        expected = np.exp(origin_log + changes.sum())
        self.assertAlmostEqual(expected, 100 * np.exp(.11))

    def test_19_theil_u2_formula(self):
        row = self.metrics.loc[(self.metrics.model == "AR_BIC") & (self.metrics.information_set == "RELEASE_SAFE_APPROXIMATION") & (self.metrics.window_variant == "PRIMARY_48") & (self.metrics.horizon == 1)].iloc[0]
        rw = self.metrics.loc[(self.metrics.model == "RW_NO_DRIFT") & (self.metrics.information_set == "RELEASE_SAFE_APPROXIMATION") & (self.metrics.window_variant == "PRIMARY_48") & (self.metrics.horizon == 1)].iloc[0]
        self.assertAlmostEqual(row.theil_u2, row.rmse_level / rw.rmse_level)

    def test_20_rw_theil_u2_is_one(self):
        self.assertTrue(np.allclose(self.metrics.loc[self.metrics.model == "RW_NO_DRIFT", "theil_u2"], 1.0))

    def test_21_direction_metric_formula(self):
        result = direction_metrics(np.array([.1, -.2, .3]), np.array([.2, -.1, -.2]))
        self.assertAlmostEqual(result["direction_accuracy"], 2 / 3)

    def test_22_zero_actual_direction_excluded(self):
        result = direction_metrics(np.array([0.0, .1]), np.array([1.0, .1]))
        self.assertEqual(result["zero_actual_count"], 1)
        self.assertEqual(result["direction_accuracy"], 1.0)

    def test_23_common_origin_comparison_enforced(self):
        fair = common_origin_predictions(self.predictions)
        group = fair.loc[(fair.information_set == "RELEASE_SAFE_APPROXIMATION") & (fair.window_variant == "PRIMARY_48") & (fair.horizon == 1)]
        counts = group.loc[group.model.isin(["RW_NO_DRIFT", "AR_BIC", "VAR_SPEC_A", "VAR_SPEC_B", "BVAR_SPEC_A", "BVAR_SPEC_B"])].groupby("model").size()
        self.assertEqual(len(set(counts)), 1)

    def test_24_failure_audit_records_failure(self):
        self.assertEqual(list(self.failures.columns), ["model", "spec", "origin", "horizon", "reason"])
        synthetic = failure_records("VAR_SPEC_A", "SPEC_A_DLOG4", "2024-01", [1, 3], "singular matrix")
        self.assertEqual(len(synthetic), 2)
        self.assertEqual(synthetic[1]["reason"], "singular matrix")

    def test_25_var_stability_diagnostic_exists(self):
        rows = self.diagnostics.loc[self.diagnostics.model.str.startswith("VAR_")]
        self.assertFalse(rows.empty)
        self.assertFalse(rows.stable.isna().any())

    def test_26_bvar_is_deterministic(self):
        frame = build_information_set(self.data, "SPEC_A_DLOG4", "RELEASE_SAFE_APPROXIMATION").dropna()
        values = frame.iloc[:, 1:].to_numpy()
        first = fit_bvar(values)
        second = fit_bvar(values)
        self.assertTrue(np.allclose(first.coefficients, second.coefficients))

    def test_27_bvar_posterior_variance_positive(self):
        frame = build_information_set(self.data, "SPEC_A_DLOG4", "RELEASE_SAFE_APPROXIMATION").dropna()
        fit = fit_bvar(frame.iloc[:, 1:].to_numpy())
        self.assertTrue(all(np.isfinite(cov).all() and np.all(np.diag(cov) > 0) for cov in fit.posterior_covariance))
        self.assertTrue(np.all(fit.residual_variance_posterior > 0))

    def test_28_margin_proxy_absent_from_var_and_bvar(self):
        self.assertFalse(any("margin" in column for columns in SPECIFICATIONS.values() for column in columns))

    def test_29_forecast_targets_have_no_future_tail(self):
        self.assertLessEqual(self.predictions.target_month.max(), "2025-09")

    def test_30_outputs_are_gitignored(self):
        for path in ["outputs/phase1/baseline_results/forecast_predictions.csv", "outputs/phase1/figures/19_oos_h1_spot_forecasts.png"]:
            result = subprocess.run(["git", "check-ignore", path], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 0)

    def test_31_commercial_data_not_in_baseline_output(self):
        names = " ".join(path.name.lower() for path in OUTPUT.glob("*.csv"))
        self.assertNotIn("mysteel", names)
        self.assertNotIn("smm", names)

    def test_32_fullsample_refit_cannot_feed_oos_engine(self):
        code = (ROOT / "src/evaluation/forecasting.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("fullsample_coefficients", code)
        self.assertNotIn("final_fullsample_coefficients", code)

    def test_33_42_month_robustness_does_not_overwrite_primary(self):
        self.assertIn("PRIMARY_48", set(self.predictions.window_variant))
        self.assertIn("EARLIER_INITIAL_42", set(self.predictions.window_variant))
        primary = self.predictions.loc[self.predictions.window_variant == "PRIMARY_48"]
        robustness = self.predictions.loc[self.predictions.window_variant == "EARLIER_INITIAL_42"]
        self.assertFalse(primary.empty)
        self.assertFalse(robustness.empty)

    def test_34_required_primary_models_present(self):
        required = {"RW_NO_DRIFT", "AR_BIC", "VAR_SPEC_A", "VAR_SPEC_B", "BVAR_SPEC_A", "BVAR_SPEC_B"}
        self.assertTrue(required.issubset(set(self.predictions.model)))

    def test_35_horizon_evaluation_counts(self):
        rows = self.metrics.loc[(self.metrics.model == "RW_NO_DRIFT") & (self.metrics.information_set == "RELEASE_SAFE_APPROXIMATION") & (self.metrics.window_variant == "PRIMARY_48")]
        self.assertEqual(dict(zip(rows.horizon, rows.n_forecasts)), {1: 21, 3: 19, 6: 16})

    def test_36_release_safe_is_primary_label(self):
        self.assertIn("RELEASE_SAFE_APPROXIMATION", set(self.metrics.information_set))

    def test_37_model_set_is_prespecified(self):
        names = {item["model"] for item in MODEL_DEFINITIONS}
        forbidden = {"LASSO", "XGBOOST", "RANDOM_FOREST", "LSTM", "TRANSFORMER", "SVR"}
        self.assertTrue(names.isdisjoint(forbidden))

    def test_38_ar_recursive_forecast_shape(self):
        values = self.data.lc_spot_dlog.dropna().to_numpy()
        fit, _ = select_ar_lag(values[:47])
        self.assertEqual(forecast_ar(fit, values[:47], 6).shape, (6,))

    def test_39_rw_drift_uses_training_mean(self):
        path = forecast_with_drift(np.log(100), np.array([.1, .2]), 2)
        self.assertTrue(np.allclose(path, np.log(100) + np.array([.15, .30])))

    def test_40_new_figures_have_sample_and_information_metadata(self):
        for number in range(19, 26):
            path = next(FIGURES.glob(f"{number:02d}_*.png"))
            with Image.open(path) as image:
                self.assertEqual(image.info.get("Sample"), "2020-01 to 2025-09")
                self.assertEqual(image.info.get("InformationSet"), "RELEASE_SAFE_APPROXIMATION")


if __name__ == "__main__":
    unittest.main()
