"""Small-sample stationarity diagnostics for the frozen Phase 1 sample."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss, zivot_andrews


VARIABLE_PREFIXES = {
    "lc_spot": "lc_spot",
    "lc_output": "lc_output",
    "spodumene_cny_t": "spodumene_cny",
    "battery_install": "battery_install",
    "usd_cny_mean": "usd_cny",
}


def classify_stationarity(adf_p: float, kpss_p: float, alpha: float = 0.05) -> str:
    """Combine tests with opposite nulls without overstating boundary results."""
    if abs(adf_p - alpha) <= 0.005 or abs(kpss_p - alpha) <= 0.005:
        return "BORDERLINE"
    if adf_p < alpha and kpss_p > alpha:
        return "STATIONARY"
    if adf_p >= alpha and kpss_p <= alpha:
        return "NONSTATIONARY"
    return "BORDERLINE"


def stationarity_table(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    specifications = (("log", "c"), ("log", "ct"), ("dlog", "c"), ("yoy_log", "c"))
    for variable, prefix in VARIABLE_PREFIXES.items():
        for transform, deterministic in specifications:
            values = data[f"{prefix}_{transform}"].dropna().to_numpy(dtype=float)
            if values.size < 24 or not np.isfinite(values).all():
                raise ValueError(f"Invalid stationarity input for {variable} {transform}")
            adf_stat, adf_p, adf_lags, adf_nobs, adf_crit, _ = adfuller(
                values, regression=deterministic, autolag="AIC", result_object=False
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                kpss_stat, kpss_p, kpss_lags, kpss_crit = kpss(
                    values, regression=deterministic, nlags="auto"
                )
            rows.append({
                "variable": variable,
                "transform": transform,
                "deterministic": deterministic,
                "adf_stat": adf_stat,
                "adf_p_value": adf_p,
                "adf_lags": int(adf_lags),
                "adf_nobs": int(adf_nobs),
                "adf_critical_1pct": adf_crit["1%"],
                "adf_critical_5pct": adf_crit["5%"],
                "adf_critical_10pct": adf_crit["10%"],
                "kpss_stat": kpss_stat,
                "kpss_p_value": kpss_p,
                "kpss_lags": int(kpss_lags),
                "kpss_critical_1pct": kpss_crit["1%"],
                "kpss_critical_5pct": kpss_crit["5%"],
                "kpss_critical_10pct": kpss_crit["10%"],
                "classification": classify_stationarity(float(adf_p), float(kpss_p)),
                "notes": "ADF null: unit root; KPSS null: stationarity; 5% diagnostic rule",
            })
    return pd.DataFrame(rows)


def zivot_andrews_table(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for variable in ("lc_spot", "spodumene_cny_t", "lc_output", "battery_install"):
        prefix = VARIABLE_PREFIXES[variable]
        values = data[f"{prefix}_log"].to_numpy(dtype=float)
        for deterministic in ("c", "ct"):
            stat, p_value, critical, used_lag, break_index = zivot_andrews(
                values, regression=deterministic, maxlag=6, autolag="AIC"
            )
            rows.append({
                "variable": variable,
                "transform": "log",
                "deterministic": deterministic,
                "za_stat": stat,
                "p_value": p_value,
                "critical_1pct": critical["1%"],
                "critical_5pct": critical["5%"],
                "critical_10pct": critical["10%"],
                "used_lag": int(used_lag),
                "break_index": int(break_index),
                "break_date": data.iloc[int(break_index)]["month"],
                "reject_5pct": bool(p_value < 0.05),
                "interpretation": "ENDOGENOUS_SINGLE_BREAK_DIAGNOSTIC_ONLY; maxlag=6, selected by AIC",
            })
    return pd.DataFrame(rows)
