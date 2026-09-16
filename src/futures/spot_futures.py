"""Spot-futures alignment and fixed-rule preliminary diagnostics."""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import rankdata
from statsmodels.tsa.stattools import adfuller, coint, kpss
from statsmodels.tsa.vector_ar.vecm import VECM


def reconcile_canonical_daily_spot(
    daily_path: str | Path,
    freeze_path: str | Path,
    *,
    sample_end: str,
    absolute_tolerance: float,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    daily = pd.read_csv(daily_path)
    required = {"date", "lc_spot", "source", "original_unit", "quality_flag"}
    if not required.issubset(daily.columns):
        raise ValueError(f"daily spot missing columns: {sorted(required - set(daily.columns))}")
    daily["date"] = pd.to_datetime(daily.date, errors="coerce")
    daily["lc_spot"] = pd.to_numeric(daily.lc_spot, errors="coerce")
    daily = daily.loc[daily.date.notna() & daily.date.dt.to_period("M").le(pd.Period(sample_end, freq="M"))].copy()
    duplicate_dates = int(daily.date.duplicated(keep=False).sum())
    source_ok = bool(daily.source.astype(str).str.upper().eq("SMM").all())
    unit_ok = bool(daily.original_unit.astype(str).str.upper().eq("CNY/T").all())
    values_ok = bool(daily.lc_spot.notna().all() and daily.lc_spot.gt(0).all())
    quality_ok = bool(daily.quality_flag.astype(str).str.upper().eq("OK").all())
    daily["month"] = daily.date.dt.to_period("M").astype(str)
    monthly = daily.groupby("month", sort=True).lc_spot.mean().rename("daily_spot_mean").reset_index()
    freeze = pd.read_csv(freeze_path, usecols=["month", "lc_spot"])
    freeze = freeze.loc[freeze.month.le(sample_end)].rename(columns={"lc_spot": "freeze_spot_mean"})
    reconciliation = freeze.merge(monthly, on="month", how="left", validate="one_to_one")
    reconciliation["difference"] = reconciliation.daily_spot_mean - reconciliation.freeze_spot_mean
    reconciliation["absolute_difference"] = reconciliation.difference.abs()
    coverage_ok = bool(reconciliation.daily_spot_mean.notna().all())
    max_difference = float(reconciliation.absolute_difference.max()) if coverage_ok else np.inf
    passed = bool(source_ok and unit_ok and values_ok and quality_ok and duplicate_dates == 0 and coverage_ok and max_difference <= absolute_tolerance)
    audit = {
        "status": "PASS" if passed else "DAILY_CANONICAL_SPOT_NOT_AVAILABLE",
        "rows": int(len(daily)),
        "first_date": daily.date.min(),
        "last_date": daily.date.max(),
        "source_smm": source_ok,
        "unit_cny_per_t": unit_ok,
        "quality_ok": quality_ok,
        "duplicate_dates": duplicate_dates,
        "freeze_months_reconciled": int(reconciliation.daily_spot_mean.notna().sum()),
        "max_abs_monthly_difference": max_difference,
        "absolute_tolerance": float(absolute_tolerance),
    }
    return daily.sort_values("date").reset_index(drop=True), reconciliation, audit


def build_monthly_spot_futures(
    freeze_path: str | Path,
    futures_monthly: pd.DataFrame,
    *,
    start_month: str,
    end_month: str,
    canonical_daily_spot: pd.DataFrame | None = None,
) -> pd.DataFrame:
    spot = pd.read_csv(freeze_path, usecols=["month", "lc_spot"]).rename(columns={"lc_spot": "spot_mean"})
    spot = spot.loc[spot.month.between(start_month, end_month)].copy()
    if canonical_daily_spot is not None:
        daily = canonical_daily_spot.copy().sort_values("date")
        daily["month"] = daily.date.dt.to_period("M").astype(str)
        eom = daily.groupby("month", sort=True).lc_spot.last().rename("spot_month_end").reset_index()
        spot = spot.merge(eom, on="month", how="left", validate="one_to_one")
    else:
        spot["spot_month_end"] = np.nan
    futures = futures_monthly.rename(columns={
        "mean_main_close": "futures_mean",
        "month_end_main_close": "futures_month_end",
        "monthly_roll_safe_log_return": "futures_monthly_return",
        "main_contract_at_month_end": "main_contract",
        "monthly_volume": "volume",
    })
    columns = ["month", "futures_mean", "futures_month_end", "futures_monthly_return", "main_contract", "volume", "switch_count"]
    for optional in ("first_trading_date", "last_trading_date", "coverage_status", "observed_period_roll_safe_log_return"):
        if optional in futures.columns:
            columns.append(optional)
    aligned = spot.merge(futures.loc[:, columns], on="month", how="inner", validate="one_to_one")
    aligned = aligned.loc[aligned.month.between(start_month, end_month)].sort_values("month").reset_index(drop=True)
    aligned["spot_monthly_return"] = np.log(aligned.spot_mean).diff()
    aligned["basis_mean_pct"] = aligned.futures_mean / aligned.spot_mean - 1.0
    aligned["basis_month_end_pct"] = aligned.futures_month_end / aligned.spot_month_end - 1.0
    return aligned


def _stationarity_row(name: str, values: np.ndarray, *, maxlag: int, autolag: str, alpha: float) -> dict[str, object]:
    values = np.asarray(values, float)
    values = values[np.isfinite(values)]
    adf_stat, adf_p, adf_lags, adf_nobs, adf_critical, _ = adfuller(
        values, regression="c", maxlag=maxlag, autolag=autolag
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        kpss_stat, kpss_p, kpss_lags, kpss_critical = kpss(values, regression="c", nlags="auto")
    if adf_p < alpha and kpss_p > alpha:
        classification = "STATIONARY"
    elif adf_p >= alpha and kpss_p <= alpha:
        classification = "NONSTATIONARY"
    else:
        classification = "BORDERLINE"
    return {
        "series": name,
        "n": len(values),
        "adf_stat": adf_stat,
        "adf_p_value": adf_p,
        "adf_lags": int(adf_lags),
        "adf_nobs": int(adf_nobs),
        "adf_critical_5pct": adf_critical["5%"],
        "kpss_stat": kpss_stat,
        "kpss_p_value": kpss_p,
        "kpss_lags": int(kpss_lags),
        "kpss_critical_5pct": kpss_critical["5%"],
        "classification": classification,
        "caution": "SMALL_SAMPLE_CAUTION",
    }


def stationarity_diagnostics(
    aligned: pd.DataFrame, *, maxlag: int, autolag: str, alpha: float
) -> pd.DataFrame:
    series = {
        "log_spot": np.log(aligned.spot_mean.to_numpy(float)),
        "log_futures": np.log(aligned.futures_mean.to_numpy(float)),
        "spot_return": aligned.spot_monthly_return.to_numpy(float),
        "futures_roll_safe_return": aligned.futures_monthly_return.to_numpy(float),
    }
    return pd.DataFrame([
        _stationarity_row(name, values, maxlag=maxlag, autolag=autolag, alpha=alpha)
        for name, values in series.items()
    ])


def assess_i1_from_adf(stationarity: pd.DataFrame, *, alpha: float) -> dict[str, bool]:
    indexed = stationarity.set_index("series")
    return {
        "spot_i1": bool(indexed.loc["log_spot", "adf_p_value"] >= alpha and indexed.loc["spot_return", "adf_p_value"] < alpha),
        "futures_i1": bool(indexed.loc["log_futures", "adf_p_value"] >= alpha and indexed.loc["futures_roll_safe_return", "adf_p_value"] < alpha),
    }


def cointegration_and_vecm(
    aligned: pd.DataFrame,
    stationarity: pd.DataFrame,
    *,
    minimum_n: int,
    maxlag: int,
    autolag: str,
    alpha: float,
    vecm_k_ar_diff: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    clean = aligned.dropna(subset=["spot_mean", "futures_mean"])
    i1 = assess_i1_from_adf(stationarity, alpha=alpha)
    eligible = bool(len(clean) >= minimum_n and all(i1.values()))
    row: dict[str, object] = {
        "n": int(len(clean)),
        "minimum_n": int(minimum_n),
        **i1,
        "gate_status": "ELIGIBLE" if eligible else "COINTEGRATION_NOT_JUSTIFIED_BY_I1_GATE",
        "trend": "c",
        "autolag": autolag,
        "maxlag": int(maxlag),
        "caution": "SMALL_SAMPLE_CAUTION",
    }
    if eligible:
        statistic, p_value, critical = coint(
            np.log(clean.spot_mean), np.log(clean.futures_mean), trend="c", maxlag=maxlag, autolag=autolag
        )
        row.update({
            "eg_stat": float(statistic),
            "eg_p_value": float(p_value),
            "critical_1pct": float(critical[0]),
            "critical_5pct": float(critical[1]),
            "critical_10pct": float(critical[2]),
            "cointegration_evidence": bool(p_value < alpha),
        })
    else:
        row.update({"eg_stat": np.nan, "eg_p_value": np.nan, "critical_1pct": np.nan, "critical_5pct": np.nan, "critical_10pct": np.nan, "cointegration_evidence": False})
    cointegration = pd.DataFrame([row])
    if not bool(row["cointegration_evidence"]):
        vecm = pd.DataFrame([{
            "status": "VECM_NOT_JUSTIFIED_BY_SAMPLE",
            "n": int(len(clean)),
            "k_ar_diff": int(vecm_k_ar_diff),
            "deterministic": "ci",
        }])
        return cointegration, vecm
    model = VECM(
        np.log(clean[["spot_mean", "futures_mean"]]).to_numpy(),
        k_ar_diff=vecm_k_ar_diff,
        coint_rank=1,
        deterministic="ci",
    ).fit()
    vecm_rows = []
    for equation, name in enumerate(("log_spot", "log_futures")):
        vecm_rows.append({
            "status": "EXPLORATORY_VECM_FIT",
            "equation": name,
            "n": int(len(clean)),
            "k_ar_diff": int(vecm_k_ar_diff),
            "deterministic": "ci",
            "adjustment_alpha": float(model.alpha[equation, 0]),
            "cointegrating_beta_spot": float(model.beta[0, 0]),
            "cointegrating_beta_futures": float(model.beta[1, 0]),
        })
    return cointegration, pd.DataFrame(vecm_rows)


def lead_lag_correlations(
    futures_returns: pd.Series,
    spot_returns: pd.Series,
    lags: Sequence[int],
    *,
    frequency: str,
) -> pd.DataFrame:
    """Positive lag compares futures(t) with spot(t+lag): futures leads spot."""
    futures = pd.Series(futures_returns, dtype=float).reset_index(drop=True)
    spot = pd.Series(spot_returns, dtype=float).reset_index(drop=True)
    rows = []
    for lag in lags:
        pair = pd.DataFrame({"futures": futures, "spot": spot.shift(-int(lag))}).dropna()
        rows.append({
            "frequency": frequency,
            "lag_spot_periods": int(lag),
            "n": int(len(pair)),
            "pearson": float(pair.futures.corr(pair.spot)) if len(pair) >= 3 else np.nan,
            "spearman": float(pair.futures.corr(pair.spot, method="spearman")) if len(pair) >= 3 else np.nan,
            "lag_convention": "positive=futures_t_vs_spot_t_plus_lag",
        })
    return pd.DataFrame(rows)


def build_daily_return_alignment(main_daily: pd.DataFrame, spot_daily: pd.DataFrame) -> pd.DataFrame:
    spot = spot_daily[["date", "lc_spot"]].copy().sort_values("date")
    spot["spot_log_return"] = np.log(spot.lc_spot).diff()
    futures = main_daily[["date", "main_contract", "main_close", "roll_safe_log_return", "switch_flag"]].copy()
    aligned = futures.merge(spot, on="date", how="inner", validate="one_to_one")
    return aligned.sort_values("date").reset_index(drop=True)


def hac_granger_diagnostics(daily: pd.DataFrame, *, max_lag: int) -> pd.DataFrame:
    data = daily[["spot_log_return", "roll_safe_log_return"]].dropna().reset_index(drop=True)
    rows: list[dict[str, object]] = []
    directions = (
        ("FUTURES_TO_SPOT", "spot_log_return", "roll_safe_log_return"),
        ("SPOT_TO_FUTURES", "roll_safe_log_return", "spot_log_return"),
    )
    for direction, dependent, driver in directions:
        for lag in range(1, max_lag + 1):
            design = pd.DataFrame({"y": data[dependent]})
            for index in range(1, lag + 1):
                design[f"y_lag_{index}"] = data[dependent].shift(index)
                design[f"x_lag_{index}"] = data[driver].shift(index)
            design = design.dropna()
            x_columns = [f"x_lag_{index}" for index in range(1, lag + 1)]
            regressors = sm.add_constant(design.drop(columns="y"), has_constant="add")
            fit = sm.OLS(design.y, regressors).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
            restrictions = np.zeros((lag, len(fit.params)))
            for row_index, column in enumerate(x_columns):
                restrictions[row_index, list(fit.params.index).index(column)] = 1.0
            test = fit.wald_test(restrictions, scalar=True)
            rows.append({
                "direction": direction,
                "lags": lag,
                "n": int(fit.nobs),
                "hac_wald_stat": float(np.asarray(test.statistic).squeeze()),
                "hac_p_value": float(test.pvalue),
                "covariance": f"HAC(maxlags={lag})",
                "caution": "PRELIMINARY_DAILY_PRICE_DISCOVERY_DIAGNOSTIC",
            })
    return pd.DataFrame(rows)


def _rowwise_correlation(paths: np.ndarray, target: np.ndarray, method: str) -> np.ndarray:
    x = np.asarray(paths, float)
    y = np.asarray(target, float)
    if method == "spearman":
        x = rankdata(x, axis=1)
        y = rankdata(y)
    xc = x - x.mean(axis=1, keepdims=True)
    yc = y - y.mean()
    denominator = np.sqrt(np.sum(xc * xc, axis=1) * np.sum(yc * yc))
    if np.any(denominator <= 0):
        raise ValueError("zero variance in basis-inventory correlation")
    return np.sum(xc * yc, axis=1) / denominator


def basis_inventory_summary(
    state_paths: Mapping[str, tuple[np.ndarray, Sequence[str]]],
    monthly: pd.DataFrame,
    *,
    lags: Sequence[int],
    basis_column: str = "basis_mean_pct",
) -> pd.DataFrame:
    """Positive lag compares state(t) with basis(t+lag): the state leads the basis."""
    basis = monthly[["month", basis_column]].dropna().copy()
    basis_period = pd.PeriodIndex(basis.month, freq="M")
    rows: list[dict[str, object]] = []
    for specification, (paths, months) in state_paths.items():
        paths = np.asarray(paths, float)
        month_index = {str(month): index for index, month in enumerate(months)}
        for lag in lags:
            state_months = (basis_period - int(lag)).astype(str)
            keep = [index for index, month in enumerate(state_months) if month in month_index]
            columns = [month_index[state_months[index]] for index in keep]
            target = basis.iloc[keep][basis_column].to_numpy(float)
            selected = paths[:, columns]
            for statistic in ("pearson", "spearman"):
                values = _rowwise_correlation(selected, target, statistic)
                quantiles = np.quantile(values, [.05, .16, .50, .84, .95])
                rows.append({
                    "specification": specification,
                    "basis_series": basis_column,
                    "statistic": statistic,
                    "lag_basis_months": int(lag),
                    "n_months": int(len(target)),
                    "q05": float(quantiles[0]),
                    "q16": float(quantiles[1]),
                    "median": float(quantiles[2]),
                    "q84": float(quantiles[3]),
                    "q95": float(quantiles[4]),
                    "p_positive": float(np.mean(values > 0)),
                    "lag_convention": "positive=inventory_state_t_vs_basis_t_plus_lag",
                })
    return pd.DataFrame(rows)
