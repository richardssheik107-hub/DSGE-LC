"""Fair common-origin metrics for level and cumulative log-change forecasts."""
from __future__ import annotations

import numpy as np
import pandas as pd


PRIMARY_MODELS = ["RW_NO_DRIFT", "AR_BIC", "VAR_SPEC_A", "VAR_SPEC_B", "BVAR_SPEC_A", "BVAR_SPEC_B"]


def direction_metrics(actual_change: np.ndarray, forecast_change: np.ndarray) -> dict:
    actual = np.sign(np.asarray(actual_change, dtype=float))
    forecast = np.sign(np.asarray(forecast_change, dtype=float))
    nonzero = actual != 0
    up = actual > 0
    down = actual < 0
    return {
        "direction_accuracy": float(np.mean(actual[nonzero] == forecast[nonzero])) if nonzero.any() else np.nan,
        "up_accuracy": float(np.mean(forecast[up] > 0)) if up.any() else np.nan,
        "down_accuracy": float(np.mean(forecast[down] < 0)) if down.any() else np.nan,
        "zero_actual_count": int((~nonzero).sum()),
    }


def common_origin_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Restrict every comparison cell to the intersection of primary-model targets."""
    chunks = []
    keys = ["information_set", "window_variant", "horizon"]
    for _, group in predictions.groupby(keys, sort=False):
        primary = group.loc[group.model.isin(PRIMARY_MODELS)]
        sets = [set(sub.target_month) for _, sub in primary.groupby("model")]
        common = set.intersection(*sets) if sets and len(sets) == len(PRIMARY_MODELS) else set()
        chunks.append(group.loc[group.target_month.isin(common)])
    return pd.concat(chunks, ignore_index=True) if chunks else predictions.iloc[0:0].copy()


def calculate_metrics(predictions: pd.DataFrame, failures: pd.DataFrame) -> pd.DataFrame:
    fair = common_origin_predictions(predictions)
    rows = []
    keys = ["model", "specification", "information_set", "window_variant", "horizon"]
    for key, group in fair.groupby(keys, sort=False):
        model, specification, information_set, window_variant, horizon = key
        level_error = group.forecast_spot.to_numpy() - group.actual_spot.to_numpy()
        change_error = group.forecast_log_change.to_numpy() - group.actual_log_change.to_numpy()
        rmse = float(np.sqrt(np.mean(level_error ** 2)))
        mae = float(np.mean(np.abs(level_error)))
        direction = direction_metrics(group.actual_log_change.to_numpy(), group.forecast_log_change.to_numpy())
        rw = fair.loc[
            fair.model.eq("RW_NO_DRIFT") & fair.information_set.eq(information_set)
            & fair.window_variant.eq(window_variant) & fair.horizon.eq(horizon)
        ]
        rw_error = rw.forecast_spot.to_numpy() - rw.actual_spot.to_numpy()
        rw_rmse = float(np.sqrt(np.mean(rw_error ** 2)))
        rw_mae = float(np.mean(np.abs(rw_error)))
        failure_count = 0 if failures.empty else int(len(failures.loc[
            failures.model.eq(model) & failures.spec.eq(specification) & failures.horizon.eq(horizon)
        ]))
        rows.append({
            "model": model, "specification": specification, "information_set": information_set,
            "window_variant": window_variant, "horizon": int(horizon), "n_forecasts": int(len(group)),
            "rmse_level": rmse, "mae_level": mae, "theil_u2": rmse / rw_rmse,
            "rmse_improvement_vs_rw_pct": 100 * (rw_rmse - rmse) / rw_rmse,
            "mae_improvement_vs_rw_pct": 100 * (rw_mae - mae) / rw_mae,
            "rmse_change": float(np.sqrt(np.mean(change_error ** 2))),
            "mae_change": float(np.mean(np.abs(change_error))), **direction,
            "failure_count": failure_count,
            "stable_share": float(group.model_stable.astype(bool).mean()),
        })
    return pd.DataFrame(rows)


def fundamental_increment_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    primary = metrics.loc[
        metrics.information_set.eq("RELEASE_SAFE_APPROXIMATION")
        & metrics.window_variant.eq("PRIMARY_48")
    ]
    challengers = ["VAR_SPEC_A", "VAR_SPEC_B", "BVAR_SPEC_A", "BVAR_SPEC_B"]
    rows = []
    for challenger in challengers:
        comparisons = []
        for horizon in (1, 3, 6):
            ar = primary.loc[primary.model.eq("AR_BIC") & primary.horizon.eq(horizon)].iloc[0]
            model = primary.loc[primary.model.eq(challenger) & primary.horizon.eq(horizon)].iloc[0]
            improvement = 100 * (ar.rmse_level - model.rmse_level) / ar.rmse_level
            comparisons.append(improvement > 0)
            rows.append({
                "challenger": challenger, "benchmark": "AR_BIC", "horizon": horizon,
                "rmse_challenger": model.rmse_level, "rmse_benchmark": ar.rmse_level,
                "rmse_improvement_vs_ar_pct": improvement,
                "mae_improvement_vs_ar_pct": 100 * (ar.mae_level - model.mae_level) / ar.mae_level,
                "information_set": "RELEASE_SAFE_APPROXIMATION", "window_variant": "PRIMARY_48",
                "overall_status": "PENDING",
            })
        status = "FUNDAMENTALS_ADD_PREDICTIVE_VALUE" if all(comparisons) else "HORIZON_DEPENDENT" if any(comparisons) else "NO_STABLE_PREDICTIVE_INCREMENT"
        for row in rows[-3:]:
            row["overall_status"] = status
    return pd.DataFrame(rows)
