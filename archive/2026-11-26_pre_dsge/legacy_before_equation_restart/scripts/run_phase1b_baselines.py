"""Run the pre-specified Phase 1B reduced-form forecast baselines."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.baselines.ar import select_ar_lag  # noqa: E402
from src.baselines.bvar import fit_bvar  # noqa: E402
from src.baselines.var import select_var_lag  # noqa: E402
from src.evaluation.baseline_figures import (  # noqa: E402
    direction_bars, forecast_error_figure, forecast_figure, metric_bars,
)
from src.evaluation.forecasting import run_expanding_forecasts  # noqa: E402
from src.evaluation.metrics import calculate_metrics, fundamental_increment_summary  # noqa: E402
from src.evaluation.splits import build_information_set  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fullsample_coefficients(data: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows = []
    phase = config["phase1b"]
    ar_values = data.lc_spot_dlog.dropna().to_numpy(float)
    ar_fit, _ = select_ar_lag(ar_values, phase["ar_max_lag"])
    for index, coefficient in enumerate(ar_fit.coefficients):
        rows.append({"model": "AR_BIC", "specification": "UNIVARIATE", "equation": "spot_dlog",
                     "term": "intercept" if index == 0 else f"spot_dlog_L{index}", "coefficient": coefficient,
                     "posterior_variance": np.nan, "estimation_scope": "FULL_SAMPLE_POST_OOS_REFERENCE_ONLY"})
    for specification in ("SPEC_A_DLOG4", "SPEC_B_MIXED4", "SPEC_C_FX5"):
        frame = build_information_set(data, specification, "RELEASE_SAFE_APPROXIMATION").dropna()
        values = frame.iloc[:, 1:].to_numpy(float)
        names = list(frame.columns[1:])
        var_fit, _ = select_var_lag(values, phase["var_max_lag"])
        for equation, name in enumerate(names):
            for index, coefficient in enumerate(var_fit.coefficients[:, equation]):
                rows.append({"model": "VAR", "specification": specification, "equation": name,
                             "term": "intercept" if index == 0 else f"lag_term_{index}", "coefficient": coefficient,
                             "posterior_variance": np.nan, "estimation_scope": "FULL_SAMPLE_POST_OOS_REFERENCE_ONLY"})
        bvar_fit = fit_bvar(values, phase["bvar_lag"], phase["bvar_lambda"], phase["bvar_theta_cross"], phase["bvar_lag_decay"])
        for equation, name in enumerate(names):
            for index, coefficient in enumerate(bvar_fit.coefficients[:, equation]):
                rows.append({"model": "BVAR", "specification": specification, "equation": name,
                             "term": "intercept" if index == 0 else f"lag_term_{index}", "coefficient": coefficient,
                             "posterior_variance": bvar_fit.posterior_covariance[equation][index, index],
                             "estimation_scope": "FULL_SAMPLE_POST_OOS_REFERENCE_ONLY"})
    return pd.DataFrame(rows)


def phase2_recommendations(increment: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    statuses = set(increment.overall_status)
    increment_text = "HORIZON_DEPENDENT" if "HORIZON_DEPENDENT" in statuses else next(iter(statuses))
    fx = metrics.loc[(metrics.model == "BVAR_SPEC_C_FX5") & (metrics.information_set == "RELEASE_SAFE_APPROXIMATION") & (metrics.window_variant == "PRIMARY_48")]
    fx_text = "secondary extension; mixed horizon performance" if not fx.empty else "not estimable"
    rows = [
        ("cost_pass_through", "0–1M STRONG", increment_text, "KEEP structural cost channel; calibrate prior strength from combined evidence", "MEDIUM", "Forecastability is distinct from contemporaneous pass-through"),
        ("short_run_supply_response", "1–2M WEAK", increment_text, "KEEP but use weak prior and explicit robustness", "LOW", "Do not freeze a single lag"),
        ("slow_capacity_channel", "Margin → output growth 9–11M MODERATE", "Margin excluded from VAR by design", "KEEP CANDIDATE", "MEDIUM", "Test a lag range in Phase 2"),
        ("demand_observation", "Demand → price NO_CLEAR_EVIDENCE", increment_text, "KEEP AS NOISY LATENT ANCHOR", "MEDIUM", "Observed installation has seasonality and release delay"),
        ("inventory_state", "UNRESOLVED", "Not observed in Phase 1B", "UNRESOLVED", "LOW", "Retain for identification pre-check rather than forecast claim"),
        ("FX_control", "FX dlog stationary", fx_text, "EXTENSION", "LOW", "Do not promote to core from test performance"),
        ("output_break", "2022-02/03 STRONG_CANDIDATE", "Training-start robustness completed", "REQUIRED", "HIGH", "Formal break-aware model postponed"),
    ]
    return pd.DataFrame(rows, columns=["item", "phase1a2_evidence", "phase1b_evidence", "recommended_phase2_treatment", "confidence", "notes"])


def main() -> None:
    config = json.loads((ROOT / "configs/phase1.yaml").read_text(encoding="utf-8"))
    freeze = ROOT / "data/processed/core_monthly_panel.csv"
    dataset_path = ROOT / "data/processed/phase1/monthly_structural_v1.csv"
    if not dataset_path.exists():
        raise FileNotFoundError("Protected Phase 1 structural dataset is unavailable")
    if sha256(freeze) != config["data_freeze_sha256"]:
        raise RuntimeError("Data Freeze v1 hash mismatch")
    data = pd.read_csv(dataset_path)
    if (len(data), data.month.iloc[0], data.month.iloc[-1]) != (69, "2020-01", "2025-09"):
        raise RuntimeError("Phase 1B requires exactly the frozen 69-month sample")

    predictions, diagnostics, failures = run_expanding_forecasts(data, config)
    metrics = calculate_metrics(predictions, failures)
    increment = fundamental_increment_summary(metrics)
    recommendations = phase2_recommendations(increment, metrics)
    coefficients = fullsample_coefficients(data, config)

    output = ROOT / "outputs/phase1/baseline_results"
    figures = ROOT / "outputs/phase1/figures"
    output.mkdir(parents=True, exist_ok=True)
    frames = {
        "forecast_predictions.csv": predictions,
        "baseline_metrics.csv": metrics,
        "baseline_origin_diagnostics.csv": diagnostics,
        "baseline_model_failures.csv": failures,
        "fundamental_increment_summary.csv": increment,
        "phase2_model_input_recommendations.csv": recommendations,
        "final_fullsample_coefficients.csv": coefficients,
    }
    for name, frame in frames.items():
        frame.to_csv(output / name, index=False, encoding="utf-8-sig", float_format="%.10g")

    for horizon, number in zip((1, 3, 6), (19, 20, 21)):
        forecast_figure(predictions, horizon, figures / f"{number:02d}_oos_h{horizon}_spot_forecasts.png")
    metric_bars(metrics, "rmse_level", figures / "22_rmse_by_model_horizon.png", "Spot Level RMSE by Model and Horizon")
    metric_bars(metrics, "theil_u2", figures / "23_theil_u2_by_model_horizon.png", "Theil U2 by Model and Horizon")
    direction_bars(metrics, figures / "24_direction_accuracy_by_model.png")
    forecast_error_figure(predictions, figures / "25_forecast_error_over_time.png")
    print(f"Phase 1B complete: {len(predictions)} forecasts, {len(metrics)} metric rows, {len(failures)} audit flags")


if __name__ == "__main__":
    main()
