"""End-to-end expanding-window forecast engine for the frozen Phase 1B model set."""
from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pandas as pd

from src.baselines.ar import forecast_ar, select_ar_lag
from src.baselines.bvar import fit_bvar, forecast_bvar
from src.baselines.random_walk import forecast_no_drift, forecast_with_drift
from src.baselines.var import forecast_var, select_var_lag
from src.evaluation.splits import build_information_set, forecast_origins, training_slice


MODEL_DEFINITIONS = [
    {"model": "RW_NO_DRIFT", "spec": "UNIVARIATE", "kind": "rw"},
    {"model": "RW_DRIFT", "spec": "UNIVARIATE", "kind": "rw_drift"},
    {"model": "AR_BIC", "spec": "UNIVARIATE", "kind": "ar"},
    {"model": "VAR_SPEC_A", "spec": "SPEC_A_DLOG4", "kind": "var"},
    {"model": "VAR_SPEC_B", "spec": "SPEC_B_MIXED4", "kind": "var"},
    {"model": "BVAR_SPEC_A", "spec": "SPEC_A_DLOG4", "kind": "bvar", "lambda": 0.20},
    {"model": "BVAR_SPEC_B", "spec": "SPEC_B_MIXED4", "kind": "bvar", "lambda": 0.20},
    {"model": "VAR_SPEC_C_FX5", "spec": "SPEC_C_FX5", "kind": "var"},
    {"model": "BVAR_SPEC_C_FX5", "spec": "SPEC_C_FX5", "kind": "bvar", "lambda": 0.20},
    {"model": "BVAR_SPEC_A_L010", "spec": "SPEC_A_DLOG4", "kind": "bvar", "lambda": 0.10},
    {"model": "BVAR_SPEC_A_L030", "spec": "SPEC_A_DLOG4", "kind": "bvar", "lambda": 0.30},
]


def failure_records(model: str, spec: str, origin: str, horizons: list[int], reason: str) -> list[dict]:
    """Create explicit audit rows for every affected, still-observable horizon."""
    return [
        {"model": model, "spec": spec, "origin": origin, "horizon": horizon, "reason": reason}
        for horizon in horizons
    ]


def _diagnostic(origin: str, definition: dict, train_n: int, selected_lag: int,
                aic: float, bic: float, stable: bool, condition: float,
                information_set: str, window_variant: str, notes: str = "") -> dict:
    return {
        "origin": origin, "model": definition["model"], "spec": definition["spec"],
        "information_set": information_set, "window_variant": window_variant,
        "selected_lag": selected_lag, "train_n": train_n, "AIC": aic, "BIC": bic,
        "stable": stable, "condition_number": condition, "notes": notes,
    }


def run_expanding_forecasts(data: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    phase = config["phase1b"]
    horizons = list(phase["horizons"])
    max_horizon = max(horizons)
    windows = [
        ("PRIMARY_48", phase["initial_train_months"], 0, ["RELEASE_SAFE_APPROXIMATION", "MONTH_INDEX_IDEALIZED"]),
        ("EARLIER_INITIAL_42", phase["robustness_train_months"], 0, ["RELEASE_SAFE_APPROXIMATION"]),
        ("EXCLUDE_EARLY_2020", phase["initial_train_months"], 3, ["RELEASE_SAFE_APPROXIMATION"]),
    ]
    prediction_rows, diagnostic_rows, failure_rows = [], [], []
    for window_variant, initial_months, train_start, information_sets in windows:
        origins = forecast_origins(data, initial_months, horizons, train_start)
        for information_set in information_sets:
            frames = {
                spec: build_information_set(data, spec, information_set,
                                            phase["release_lag_output"], phase["release_lag_battery"])
                for spec in ("SPEC_A_DLOG4", "SPEC_B_MIXED4", "SPEC_C_FX5")
            }
            for origin_index in origins:
                origin_month = data.month.iloc[origin_index]
                origin_log = float(data.lc_spot_log.iloc[origin_index])
                univariate = data.iloc[train_start:origin_index + 1].lc_spot_dlog.dropna().to_numpy(float)
                for definition in MODEL_DEFINITIONS:
                    try:
                        kind = definition["kind"]
                        if kind == "rw":
                            log_path = forecast_no_drift(origin_log, max_horizon)
                            spot_dlog_path = np.diff(np.r_[origin_log, log_path])
                            diag = _diagnostic(origin_month, definition, len(univariate), 0, np.nan, np.nan, True, 1.0, information_set, window_variant)
                        elif kind == "rw_drift":
                            log_path = forecast_with_drift(origin_log, univariate, max_horizon)
                            spot_dlog_path = np.diff(np.r_[origin_log, log_path])
                            diag = _diagnostic(origin_month, definition, len(univariate), 0, np.nan, np.nan, True, 1.0, information_set, window_variant)
                        elif kind == "ar":
                            fit, fits = select_ar_lag(univariate, phase["ar_max_lag"])
                            spot_dlog_path = forecast_ar(fit, univariate, max_horizon)
                            log_path = origin_log + np.cumsum(spot_dlog_path)
                            diag = _diagnostic(origin_month, definition, len(univariate), fit.lag, fit.aic, fit.bic, True, fit.condition_number, information_set, window_variant,
                                               "AIC-selected lag=" + str(min(fits, key=lambda item: item.aic).lag))
                        else:
                            train = training_slice(frames[definition["spec"]], origin_index, train_start)
                            values = train.iloc[:, 1:].to_numpy(float)
                            if kind == "var":
                                fit, fits = select_var_lag(values, phase["var_max_lag"])
                                forecast = forecast_var(fit, values, max_horizon)
                                diag = _diagnostic(origin_month, definition, len(values), fit.lag, fit.aic, fit.bic, fit.stable, fit.condition_number, information_set, window_variant,
                                                   fit.fallback_reason or "BIC within training window")
                            else:
                                fit = fit_bvar(values, phase["bvar_lag"], definition["lambda"],
                                               phase["bvar_theta_cross"], phase["bvar_lag_decay"])
                                forecast = forecast_bvar(fit, values, max_horizon)
                                diag = _diagnostic(origin_month, definition, len(values), fit.lag, np.nan, np.nan, fit.stable, fit.condition_number, information_set, window_variant,
                                                   f"INDEPENDENT-EQUATION MINNESOTA BVAR; lambda={definition['lambda']:.2f}")
                            spot_dlog_path = forecast[:, 0]
                            log_path = origin_log + np.cumsum(spot_dlog_path)
                            if not fit.stable:
                                observable_horizons = [h for h in horizons if origin_index + h < len(data)]
                                failure_rows.extend(failure_records(
                                    definition["model"], definition["spec"], origin_month,
                                    observable_horizons, "UNSTABLE_VAR" if kind == "var" else "UNSTABLE_BVAR",
                                ))
                        diagnostic_rows.append(diag)
                        for horizon in horizons:
                            target_index = origin_index + horizon
                            if target_index >= len(data):
                                continue
                            target_month = data.month.iloc[target_index]
                            forecast_log_change = float(log_path[horizon - 1] - origin_log)
                            prediction_rows.append({
                                "model": definition["model"], "specification": definition["spec"],
                                "information_set": information_set, "window_variant": window_variant,
                                "forecast_origin": origin_month, "target_month": target_month, "horizon": horizon,
                                "actual_spot": float(data.lc_spot.iloc[target_index]),
                                "forecast_spot": float(np.exp(log_path[horizon - 1])),
                                "actual_log_change": float(data.lc_spot_log.iloc[target_index] - origin_log),
                                "forecast_log_change": forecast_log_change,
                                "selected_lag": int(diag["selected_lag"]),
                                "train_start": str(data.month.iloc[train_start]), "train_end": origin_month,
                                "n_train": int(diag["train_n"]), "model_stable": bool(diag["stable"]),
                                "notes": "STRICT_TEMPORAL_OOS; recursive predictors; no future actual fundamentals",
                            })
                    except Exception as exc:  # audit every numerical failure without changing the sample
                        observable_horizons = [h for h in horizons if origin_index + h < len(data)]
                        failure_rows.extend(failure_records(
                            definition["model"], definition["spec"], origin_month,
                            observable_horizons, f"{type(exc).__name__}: {exc}",
                        ))
    predictions = pd.DataFrame(prediction_rows)
    if not predictions.empty:
        predictions["n_eval"] = predictions.groupby(["model", "specification", "information_set", "window_variant", "horizon"])["target_month"].transform("count")
    return predictions, pd.DataFrame(diagnostic_rows), pd.DataFrame(failure_rows, columns=["model", "spec", "origin", "horizon", "reason"])
