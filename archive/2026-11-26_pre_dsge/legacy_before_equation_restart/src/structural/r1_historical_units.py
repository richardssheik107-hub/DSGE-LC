"""Restore R1 historical price-pressure means to additive raw log changes.

The fitted LEGACY spot scaler is an input, not re-estimated here.  A raw log
change is ``mu + sd * standardized_pressure``; ``mu`` is a separate additive
component each month.  Neither per-component simple percentages nor CNY/tonne
price-level contributions follow from this identity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


SHOCK_COMPONENTS = ("demand", "cost", "supply", "price")
ADDITIVE_COMPONENTS = ("initial_condition", *SHOCK_COMPONENTS)
HISTORICAL_COMPONENTS = set(ADDITIVE_COMPONENTS) | {"smoothed_state"}
MEAN_COMPONENT = "DETERMINISTIC_MEAN_COMPONENT"
TOTAL_COMPONENT = "TOTAL_RAW_LOG_CHANGE"
LOG_UNIT = "DIMENSIONLESS_LOG_CHANGE"


def _require_columns(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {sorted(missing)}")


def _month_series(frame: pd.DataFrame, value: str, label: str) -> pd.Series:
    _require_columns(frame, {"month", value}, label)
    months = pd.PeriodIndex(frame.month.astype(str), freq="M")
    if months.hasnans or months.has_duplicates:
        raise ValueError(f"{label} months must be valid and unique")
    return pd.Series(pd.to_numeric(frame[value], errors="raise").to_numpy(float),
                     index=months).sort_index()


def _finite_value(series: pd.Series, month: pd.Period, label: str) -> float:
    if month not in series.index:
        raise ValueError(f"{label} missing month {month}")
    value = float(series.loc[month])
    if not np.isfinite(value):
        raise ValueError(f"{label} nonfinite at {month}")
    return value


def _endpoint_log_change(prices: pd.Series, start: pd.Period,
                         end: pd.Period) -> float:
    prior = _finite_value(prices, start - 1, "spot price prior endpoint")
    last = _finite_value(prices, end, "spot price final endpoint")
    if prior <= 0 or last <= 0:
        raise ValueError("spot price endpoint must be positive")
    return float(np.log(last / prior))


def _assert_close(actual: float, expected: float, atol: float, label: str) -> None:
    if not np.isfinite(actual) or not np.isclose(actual, expected, rtol=0, atol=atol):
        raise ValueError(f"{label} identity failed: actual={actual}, expected={expected}")


def _historical_rows(frame: pd.DataFrame, key_columns: list[str], label: str
                     ) -> pd.DataFrame:
    _require_columns(frame, set(key_columns) | {"component", "posterior_mean"}, label)
    data = frame.loc[:, [*key_columns, "component", "posterior_mean"]].copy()
    data["posterior_mean"] = pd.to_numeric(data.posterior_mean, errors="raise")
    if not np.isfinite(data.posterior_mean.to_numpy(float)).all():
        raise ValueError(f"{label} has nonfinite posterior means")
    if data.duplicated([*key_columns, "component"]).any():
        raise ValueError(f"{label} has duplicate component keys")
    return data


def restore_historical_log_units(
    monthly: pd.DataFrame,
    episodes: pd.DataFrame,
    spot_dlog: pd.DataFrame,
    spot_price: pd.DataFrame,
    *,
    spot_mean: float,
    spot_sd: float,
    identity_atol: float,
    endpoint_atol: float,
    baseline_specification: str = "BASELINE",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return monthly and episode posterior-mean decompositions in log units.

    ``spot_dlog`` has ``month, lc_spot_dlog``; ``spot_price`` has ``month,
    lc_spot`` (the frozen monthly *mean* price).  All window months, including
    both named boundaries, contribute.  Their price endpoints are the month
    immediately *before* ``start`` and month ``end``.  Both tolerances are
    caller-specified, and all comparisons use zero relative tolerance.

    Output rows with ``component_role == 'ADDEND'`` add to the observed raw log
    change.  ``TOTAL_RAW_LOG_CHANGE`` is a check row and must not be summed
    again.  Only that total row carries a simple percent change.  No shock
    percent or CNY/tonne contribution is calculated.
    """
    for label, value in (("spot_mean", spot_mean), ("spot_sd", spot_sd),
                         ("identity_atol", identity_atol), ("endpoint_atol", endpoint_atol)):
        if not np.isfinite(value):
            raise ValueError(f"{label} must be finite")
    if spot_sd <= 0 or identity_atol < 0 or endpoint_atol < 0:
        raise ValueError("spot_sd must be positive and tolerances nonnegative")
    spot_dlogs = _month_series(spot_dlog, "lc_spot_dlog", "spot_dlog")
    prices = _month_series(spot_price, "lc_spot", "spot_price")
    _require_columns(monthly, {"month", "observed_standardized_spot_dlog"}, "monthly")
    m = _historical_rows(monthly, ["month"], "monthly")
    m["month"] = pd.PeriodIndex(m.month.astype(str), freq="M")
    observed = monthly.loc[:, ["month", "observed_standardized_spot_dlog"]].copy()
    observed["month"] = pd.PeriodIndex(observed.month.astype(str), freq="M")
    observed["observed_standardized_spot_dlog"] = pd.to_numeric(
        observed.observed_standardized_spot_dlog, errors="raise")
    if not np.isfinite(observed.observed_standardized_spot_dlog.to_numpy(float)).all():
        raise ValueError("monthly has nonfinite observed standardized spot dlog")
    months = sorted(m.month.unique())
    if not months or months != list(pd.period_range(months[0], months[-1], freq="M")):
        raise ValueError("monthly must contain a contiguous observed month index")
    monthly_rows: list[dict[str, object]] = []
    monthly_pivots: dict[pd.Period, dict[str, float]] = {}
    for month in months:
        group = m.loc[m.month.eq(month)]
        if set(group.component) != HISTORICAL_COMPONENTS or len(group) != len(HISTORICAL_COMPONENTS):
            raise ValueError(f"monthly components incomplete at {month}")
        components = dict(zip(group.component, group.posterior_mean))
        monthly_pivots[month] = components
        state = float(components["smoothed_state"])
        standardized_addends = float(sum(components[name] for name in ADDITIVE_COMPONENTS))
        _assert_close(standardized_addends, state, identity_atol,
                      f"monthly standardized components at {month}")
        for observed_value in observed.loc[observed.month.eq(month),
                                           "observed_standardized_spot_dlog"]:
            _assert_close(float(observed_value), state, identity_atol,
                          f"monthly observed standardized spot at {month}")
        raw = _finite_value(spot_dlogs, month, "spot_dlog")
        restored = float(spot_mean + spot_sd * state)
        endpoint = _endpoint_log_change(prices, month, month)
        _assert_close(restored, raw, identity_atol,
                      f"monthly scaler restoration at {month}")
        _assert_close(raw, endpoint, endpoint_atol,
                      f"monthly frozen price endpoint at {month}")
        metadata = {"month": str(month), "return_start_endpoint_month": str(month - 1),
                    "return_end_endpoint_month": str(month), "log_change_unit": LOG_UNIT,
                    "observed_raw_log_change": raw,
                    "frozen_price_endpoint_log_change": endpoint,
                    "additive_identity_error": float(restored - raw)}
        for name in ADDITIVE_COMPONENTS:
            monthly_rows.append({**metadata, "component": name, "source_component": name,
                                 "component_role": "ADDEND",
                                 "standardized_pressure_posterior_mean": float(components[name]),
                                 "raw_log_change_contribution": float(spot_sd * components[name]),
                                 "total_simple_percent_change": np.nan})
        monthly_rows.append({**metadata, "component": MEAN_COMPONENT,
                             "source_component": "legacy_spot_scaler_mean",
                             "component_role": "ADDEND",
                             "standardized_pressure_posterior_mean": np.nan,
                             "raw_log_change_contribution": float(spot_mean),
                             "total_simple_percent_change": np.nan})
        monthly_rows.append({**metadata, "component": TOTAL_COMPONENT,
                             "source_component": "smoothed_state",
                             "component_role": "CHECK_TOTAL",
                             "standardized_pressure_posterior_mean": state,
                             "raw_log_change_contribution": restored,
                             "total_simple_percent_change": float(100 * np.expm1(restored))})

    e = _historical_rows(episodes, ["specification", "window", "start", "end"], "episodes")
    e["start"] = pd.PeriodIndex(e.start.astype(str), freq="M")
    e["end"] = pd.PeriodIndex(e.end.astype(str), freq="M")
    if e.empty:
        raise ValueError("episodes is empty")
    if baseline_specification not in set(e.specification):
        raise ValueError("episodes missing baseline specification for monthly cross-check")
    episode_rows: list[dict[str, object]] = []
    window_boundaries: dict[str, tuple[pd.Period, pd.Period]] = {}
    for (specification, window), group in e.groupby(["specification", "window"], sort=True):
        if set(group.component) != HISTORICAL_COMPONENTS or len(group) != len(HISTORICAL_COMPONENTS):
            raise ValueError(f"episode components incomplete: {specification}/{window}")
        if len(group[["start", "end"]].drop_duplicates()) != 1:
            raise ValueError(f"episode has conflicting boundaries: {specification}/{window}")
        start, end = group[["start", "end"]].iloc[0]
        if start > end:
            raise ValueError(f"episode start after end: {specification}/{window}")
        if window in window_boundaries and window_boundaries[window] != (start, end):
            raise ValueError(f"episode window boundaries differ across specifications: {window}")
        window_boundaries[window] = (start, end)
        window_months = list(pd.period_range(start, end, freq="M"))
        if any(month not in monthly_pivots for month in window_months):
            raise ValueError(f"episode contains month outside complete historical path: {window}")
        components = dict(zip(group.component, group.posterior_mean))
        state = float(components["smoothed_state"])
        standardized_addends = float(sum(components[name] for name in ADDITIVE_COMPONENTS))
        _assert_close(standardized_addends, state, identity_atol,
                      f"episode standardized components {specification}/{window}")
        raw = float(sum(_finite_value(spot_dlogs, month, "spot_dlog") for month in window_months))
        restored = float(len(window_months) * spot_mean + spot_sd * state)
        endpoint = _endpoint_log_change(prices, start, end)
        _assert_close(restored, raw, identity_atol,
                      f"episode scaler restoration {specification}/{window}")
        _assert_close(raw, endpoint, endpoint_atol,
                      f"episode frozen price endpoints {specification}/{window}")
        if specification == baseline_specification:
            for name in HISTORICAL_COMPONENTS:
                monthly_sum = float(sum(monthly_pivots[month][name] for month in window_months))
                _assert_close(float(components[name]), monthly_sum, identity_atol,
                              f"baseline episode/monthly sum {window}/{name}")
        metadata = {"specification": specification, "window": window,
                    "start": str(start), "end": str(end), "n_months": len(window_months),
                    "return_start_endpoint_month": str(start - 1),
                    "return_end_endpoint_month": str(end), "log_change_unit": LOG_UNIT,
                    "observed_raw_log_change": raw,
                    "frozen_price_endpoint_log_change": endpoint,
                    "additive_identity_error": float(restored - raw)}
        for name in ADDITIVE_COMPONENTS:
            episode_rows.append({**metadata, "component": name, "source_component": name,
                                 "component_role": "ADDEND",
                                 "standardized_pressure_posterior_mean": float(components[name]),
                                 "raw_log_change_contribution": float(spot_sd * components[name]),
                                 "total_simple_percent_change": np.nan})
        episode_rows.append({**metadata, "component": MEAN_COMPONENT,
                             "source_component": "legacy_spot_scaler_mean",
                             "component_role": "ADDEND",
                             "standardized_pressure_posterior_mean": np.nan,
                             "raw_log_change_contribution": float(len(window_months) * spot_mean),
                             "total_simple_percent_change": np.nan})
        episode_rows.append({**metadata, "component": TOTAL_COMPONENT,
                             "source_component": "smoothed_state",
                             "component_role": "CHECK_TOTAL",
                             "standardized_pressure_posterior_mean": state,
                             "raw_log_change_contribution": restored,
                             "total_simple_percent_change": float(100 * np.expm1(restored))})
    return pd.DataFrame(monthly_rows), pd.DataFrame(episode_rows)
