"""R1-5 read-only audit of the existing recursive forecast archive.

No origin is refitted here. Historical success is assessed from the frozen
per-origin start counts; future optimizer candidate protection is unit-tested.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evaluation.metrics import direction_metrics
from src.structural.parameter_transform import PARAMETER_ORDER, load_phase2a_bounds
from src.structural.posterior_artifacts import file_sha256

BASE = ROOT / "outputs/phase1/baseline_results/forecast_predictions.csv"
OLD = ROOT / "outputs/phase2/phase2g"
PANEL = ROOT / "data/processed/phase1/monthly_structural_v1.csv"
MODELS = ("RW_NO_DRIFT", "AR_BIC", "VAR_SPEC_B", "BVAR_SPEC_B", "STRUCTURAL_MAP_M0")
KEY = ("forecast_origin", "target_month", "horizon")
FIELDS = (*KEY, "actual_spot", "forecast_spot", "actual_log_change", "forecast_log_change")
OUTPUTS = ("forecast_origin_integrity.csv", "forecast_estimand_registry.csv",
           "forecast_common_key_audit.csv", "forecast_metric_revision.csv",
           "forecast_audit_input_hashes.json")


def selected_histories_are_admissible(fits: pd.DataFrame, first_starts: int,
                                      later_starts: int, bounds: dict,
                                      planned_origins: list[str]) -> pd.DataFrame:
    """Historical evidence: every origin's *all* attempted starts succeeded.

    The old archive has per-origin counts, not each start's message. Only an
    all-starts-success record proves that the selected minimum was successful.
    Ambiguous counts must be marked REVIEW, never silently certified.
    """
    if fits.origin.duplicated().any() or not fits.origin.is_monotonic_increasing:
        raise ValueError("origin diagnostics must be unique and ordered")
    rows = []
    if set(fits.origin) - set(planned_origins):
        raise ValueError("fit diagnostics contain unplanned origins")
    indexed = fits.set_index("origin")
    for i, month in enumerate(planned_origins):
        expected = first_starts if i == 0 else later_starts
        if month not in indexed.index:
            rows.append({"forecast_origin": month, "expected_starts": expected,
                         "archived_successful_starts": 0,
                         "archived_old_valid_starts": 0,
                         "all_attempted_starts_success": False,
                         "finite_objective": False, "stable": False,
                         "parameter_support": False,
                         "selected_objective": np.nan,
                         "selected_spectral_radius": np.nan,
                         "status": "MISSING_FIT_DIAGNOSTIC"})
            continue
        row = indexed.loc[month]
        success = int(row.successful_starts)
        old_valid = int(row.valid_starts)
        support = all(bounds[name][0] <= float(row[f"theta_{name}"]) <= bounds[name][1]
                      for name in PARAMETER_ORDER)
        numerical = np.isfinite(float(row.objective)) and np.isfinite(float(row.spectral_radius))
        stable = numerical and float(row.spectral_radius) < 1
        all_success = success == expected and old_valid == expected
        status = "PASS_ALL_STARTS_SUCCESS" if all_success and numerical and stable and support else "REVIEW_OR_TARGETED_REFIT"
        rows.append({"forecast_origin": month, "expected_starts": expected,
                     "archived_successful_starts": success,
                     "archived_old_valid_starts": old_valid,
                     "all_attempted_starts_success": all_success,
                     "finite_objective": numerical, "stable": stable,
                     "parameter_support": support,
                     "selected_objective": float(row.objective),
                     "selected_spectral_radius": float(row.spectral_radius),
                     "status": status})
    return pd.DataFrame(rows)


def expected_grid(panel: pd.DataFrame, horizons: list[int], first_origin: str) -> pd.DataFrame:
    """Build all evaluable keys from configuration and frozen months, not forecasts/fits."""
    if panel.month.duplicated().any() or not panel.month.is_monotonic_increasing:
        raise ValueError("frozen panel months must be unique and ordered")
    pos = {month: i for i, month in enumerate(panel.month)}
    if first_origin not in pos or not horizons or min(horizons) < 1:
        raise ValueError("invalid configured origin or horizons")
    rows = []
    for i in range(pos[first_origin], len(panel)):
        origin = panel.month.iloc[i]
        for h in horizons:
            if i + h >= len(panel):
                continue
            target = panel.iloc[i + h]
            rows.append({"forecast_origin": origin, "target_month": target.month,
                         "horizon": int(h), "true_actual_spot": float(target.lc_spot),
                         "true_actual_log_change": float(target.lc_spot_log - panel.iloc[i].lc_spot_log)})
    result = pd.DataFrame(rows)
    if result.duplicated(list(KEY)).any():
        raise ValueError("expected forecast grid has duplicate keys")
    return result


def key_audit(predictions: pd.DataFrame, actual_atol: float,
              expected: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Use complete (origin,target,horizon) keys; expose missing/duplicate/wrong actual."""
    if set(predictions.model) - set(MODELS):
        raise ValueError("unexpected forecast model")
    data = predictions.copy()
    data["horizon"] = data["horizon"].astype(int)
    observed = set(data.loc[:, list(KEY)].itertuples(index=False, name=None))
    expected_keys = observed if expected is None else set(expected.loc[:, list(KEY)].itertuples(index=False, name=None))
    if expected is not None and expected.duplicated(list(KEY)).any():
        raise ValueError("expected keys are duplicated")
    truth = {} if expected is None else {
        key: (float(row.true_actual_spot), float(row.true_actual_log_change))
        for key, row in ((tuple(r[col] for col in KEY), r) for _, r in expected.iterrows())
    }
    union = sorted(observed | expected_keys)
    rows, accepted = [], []
    for key in union:
        per_key = data.loc[(data.forecast_origin == key[0]) &
                           (data.target_month == key[1]) &
                           (data.horizon == key[2])]
        expected_target = str(pd.Period(key[0], freq="M") + key[2])
        target_ok = key[1] == expected_target
        actual_gap = max(float(per_key.actual_spot.max() - per_key.actual_spot.min()),
                         float(per_key.actual_log_change.max() - per_key.actual_log_change.min())) if len(per_key) else float("nan")
        actual_ok = np.isfinite(actual_gap) and actual_gap <= actual_atol
        if key in truth and len(per_key):
            spot_truth_diff = float(np.max(np.abs(per_key.actual_spot.to_numpy(float) - truth[key][0])))
            log_truth_diff = float(np.max(np.abs(per_key.actual_log_change.to_numpy(float) - truth[key][1])))
        else:
            spot_truth_diff = log_truth_diff = float("nan") if expected is not None else 0.0
        panel_truth_ok = expected is None or (np.isfinite(spot_truth_diff) and np.isfinite(log_truth_diff)
                                              and max(spot_truth_diff, log_truth_diff) <= actual_atol)
        all_present = True
        for model in MODELS:
            member = per_key.loc[per_key.model.eq(model)]
            count = len(member)
            status = ("UNEXPECTED_KEY" if key not in expected_keys else
                      "MISSING" if count == 0 else "DUPLICATE" if count > 1 else
                      "TARGET_MISMATCH" if not target_ok else
                      "ACTUAL_MISMATCH" if not actual_ok else
                      "PANEL_TRUTH_MISMATCH" if not panel_truth_ok else "PASS")
            rows.append(dict(zip(KEY, key)) | {"model": model, "row_count": count,
                                                "target_month_from_origin_plus_horizon": expected_target,
                                                "actual_spot_max_pairwise_difference": float(per_key.actual_spot.max() - per_key.actual_spot.min()),
                                                "actual_log_change_max_pairwise_difference": float(per_key.actual_log_change.max() - per_key.actual_log_change.min()),
                                                "actual_spot_max_difference_from_frozen_panel": spot_truth_diff,
                                                "actual_log_change_max_difference_from_frozen_panel": log_truth_diff,
                                                "status": status})
            all_present &= status == "PASS"
        if all_present:
            accepted.extend(per_key.index.tolist())
    audit = pd.DataFrame(rows)
    common = data.loc[accepted].sort_values(["horizon", *KEY, "model"]).reset_index(drop=True)
    return audit, common


def independent_metrics(common: pd.DataFrame) -> pd.DataFrame:
    """Metrics from sorted matched keys, with same-horizon RW denominator."""
    rows = []
    for (model, horizon), part in common.groupby(["model", "horizon"], sort=True):
        part = part.sort_values(list(KEY))
        rw = common.loc[common.model.eq("RW_NO_DRIFT") & common.horizon.eq(horizon)].sort_values(list(KEY))
        if list(part.loc[:, list(KEY)].itertuples(index=False, name=None)) != list(rw.loc[:, list(KEY)].itertuples(index=False, name=None)):
            raise RuntimeError("common metric keys differ from same-horizon RW")
        error = part.forecast_spot.to_numpy(float) - part.actual_spot.to_numpy(float)
        log_error = part.forecast_log_change.to_numpy(float) - part.actual_log_change.to_numpy(float)
        rw_error = rw.forecast_spot.to_numpy(float) - rw.actual_spot.to_numpy(float)
        rw_rmse = float(np.sqrt(np.mean(rw_error ** 2)))
        rmse = float(np.sqrt(np.mean(error ** 2)))
        rows.append({"model": model, "horizon": int(horizon), "n": len(part),
                     "rmse_level": rmse, "mae_level": float(np.mean(np.abs(error))),
                     "theil_u2": rmse / rw_rmse,
                     "rmse_change": float(np.sqrt(np.mean(log_error ** 2))),
                     **direction_metrics(part.actual_log_change.to_numpy(float),
                                         part.forecast_log_change.to_numpy(float))})
    return pd.DataFrame(rows)


def metric_comparison(revised: pd.DataFrame, archived: pd.DataFrame,
                      atol: float) -> pd.DataFrame:
    merged = revised.merge(archived, on=["model", "horizon"], how="outer", suffixes=("_r1", "_archived"), indicator=True)
    rows = []
    for _, row in merged.iterrows():
        differences = {}
        for column in ("rmse_level", "mae_level", "theil_u2", "rmse_change",
                       "direction_accuracy", "up_accuracy", "down_accuracy"):
            differences[f"{column}_absolute_difference"] = abs(float(row[f"{column}_r1"]) - float(row[f"{column}_archived"]))
        count_ok = int(row.n_r1) == int(row.n_archived)
        status = "PASS" if row._merge == "both" and count_ok and all(value <= atol for value in differences.values()) else "REVIEW"
        rows.append({"model": row.model, "horizon": int(row.horizon),
                     "n_r1": int(row.n_r1), "n_archived": int(row.n_archived),
                     "rmse_level_r1": float(row.rmse_level_r1),
                     "rmse_level_archived": float(row.rmse_level_archived),
                     "theil_u2_r1": float(row.theil_u2_r1),
                     "theil_u2_archived": float(row.theil_u2_archived),
                     **differences, "status": status})
    return pd.DataFrame(rows)


def estimand_registry() -> pd.DataFrame:
    rows = []
    for model, method in (
        ("RW_NO_DRIFT", "exp(last observed log price) = last observed level"),
        ("AR_BIC", "exp(origin log price + accumulated AR point forecasts of monthly log changes)"),
        ("VAR_SPEC_B", "exp(origin log price + accumulated VAR point forecasts of monthly log changes)"),
        ("BVAR_SPEC_B", "exp(origin log price + accumulated BVAR plug-in point forecasts of monthly log changes)"),
        ("STRUCTURAL_MAP_M0", "exp(origin log price + accumulated conditional log changes from filtered state/MAP)"),
    ):
        rows.append({"model": model, "stored_level_forecast": method,
                     "forecast_object": "conditional log point exponentiated; median-like level under symmetric log forecast distribution",
                     "is_conditional_mean_level_E_P": False,
                     "jensen_variance_correction": "NOT_APPLIED",
                     "scoring": "observed-level RMSE/MAE remains valid descriptive point-forecast loss",
                     "information_set": "RELEASE_SAFE_APPROXIMATION, given-selected-specification recursive historical OOS",
                     "not_claimed": "untouched model selection; complete real-time vintage; prospective validation",
                     "source": "src/evaluation/forecasting.py:123; src/structural/structural_forecasting.py:structural_forecast"})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-subdir", default="forecast_verified")
    args = parser.parse_args()
    if args.output_subdir in (".", "..") or "/" in args.output_subdir or "\\" in args.output_subdir:
        raise ValueError("output-subdir must be one directory name")
    rev = ROOT / "outputs/revisions" / args.run_id
    out = rev / args.output_subdir
    if not rev.is_dir() or any((out / name).exists() for name in OUTPUTS):
        raise FileExistsError("revision missing or forecast audit exists; never overwrite")
    cfg = json.loads((ROOT / "configs/r1_revision.json").read_text(encoding="utf-8"))["forecast_external_validation"]
    p2g = json.loads((ROOT / "configs/phase2g.yaml").read_text(encoding="utf-8-sig"))
    preflight = json.loads((rev / "preflight/inputs_before.json").read_text(encoding="utf-8"))
    if file_sha256(PANEL) != preflight["transformed_panel"]["sha256"]:
        raise RuntimeError("frozen Phase 1 transformed panel changed")
    paths = (BASE, OLD / "structural_oos_predictions.csv", OLD / "structural_oos_fit_diagnostics.csv",
             OLD / "structural_vs_baseline_common_predictions.csv", OLD / "structural_oos_metrics.csv", PANEL)
    before = {str(path.relative_to(ROOT)): file_sha256(path) for path in paths}
    fit = pd.read_csv(paths[2])
    panel = pd.read_csv(PANEL)
    planned = expected_grid(panel, p2g["horizons"], p2g["first_origin"])
    origin = selected_histories_are_admissible(
        fit, p2g["starts_first_origin"], p2g["starts_later_origin"],
        load_phase2a_bounds(ROOT / "configs/phase2a.yaml"),
        planned.forecast_origin.drop_duplicates().tolist())
    base = pd.read_csv(BASE)
    base = base.loc[base.information_set.eq("RELEASE_SAFE_APPROXIMATION") &
                    base.window_variant.eq("PRIMARY_48") & base.model.isin(MODELS)]
    structure = pd.read_csv(paths[1])
    predictions = pd.concat([base[["model", *FIELDS]], structure[["model", *FIELDS]]], ignore_index=True)
    keys, common = key_audit(predictions, cfg["forecast_actual_absolute_tolerance"], planned)
    archive_common = pd.read_csv(paths[3])
    if len(common) != len(archive_common) or not common.sort_values(["model", *KEY]).reset_index(drop=True).equals(
        archive_common[["model", *FIELDS]].sort_values(["model", *KEY]).reset_index(drop=True)):
        raise RuntimeError("R1 common forecasts do not reproduce the archived common table")
    metric = metric_comparison(independent_metrics(common), pd.read_csv(paths[4]),
                               cfg["forecast_metric_absolute_tolerance"])
    after = {relative: file_sha256(ROOT / relative) for relative in before}
    if before != after:
        raise RuntimeError("R1-5 forecast inputs changed")
    out.mkdir(parents=True, exist_ok=False)
    origin.to_csv(out / OUTPUTS[0], index=False)
    estimand_registry().to_csv(out / OUTPUTS[1], index=False)
    keys.to_csv(out / OUTPUTS[2], index=False)
    metric.to_csv(out / OUTPUTS[3], index=False)
    (out / OUTPUTS[4]).write_text(json.dumps({"before": before, "after": after}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"origins": len(origin), "origin_statuses": origin.status.value_counts().to_dict(),
                      "full_keys": len(keys) // len(MODELS), "key_statuses": keys.status.value_counts().to_dict(),
                      "metric_statuses": metric.status.value_counts().to_dict()}, indent=2))


if __name__ == "__main__":
    main()
