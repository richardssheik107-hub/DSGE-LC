"""Lead-lag diagnostics using the convention corr(X_t, Y_{t+k})."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import statsmodels.api as sm


LAG_CONVENTION = "corr(X_t,Y_{t+k}); positive lag means X leads Y"

MECHANISMS = [
    ("Cost → Price", "spodumene_cny", "lc_spot", 0, 12, 1),
    ("Demand → Price", "battery_install", "lc_spot", 0, 12, 1),
    ("Price → Demand", "lc_spot", "battery_install", 0, 12, 1),
    ("Supply → Price", "lc_output", "lc_spot", 0, 12, -1),
    ("Price → Future Supply", "lc_spot", "lc_output", 1, 12, 1),
]


def month_of_year_residualize(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Residualize with intercept plus month dummies via within-month demeaning."""
    out = pd.DataFrame({"month": data["month"].copy()})
    calendar_month = pd.PeriodIndex(data["month"], freq="M").month
    for column in columns:
        values = data[column].astype(float)
        out[f"{column}_moy_resid"] = values - values.groupby(calendar_month).transform("mean")
    return out


def aligned_pairs(x: pd.Series, y: pd.Series, lag: int) -> pd.DataFrame:
    """Pair X_t with Y_(t+k); shifting Y backward prevents lookahead mistakes."""
    return pd.DataFrame({"x": x, "y": y.shift(-lag)}).dropna()


def correlation_at_lag(x: pd.Series, y: pd.Series, lag: int) -> dict:
    pairs = aligned_pairs(x, y, lag)
    return {
        "n_effective": int(len(pairs)),
        "pearson": pairs.x.corr(pairs.y, method="pearson"),
        "spearman": pairs.x.corr(pairs.y, method="spearman"),
    }


def _sample(data: pd.DataFrame, variant: str) -> pd.DataFrame:
    if variant == "FULL_SAMPLE":
        return data
    if variant == "EXCLUDE_EARLY_2020_ROBUSTNESS":
        return data.loc[data.month.ge("2020-04")].copy()
    raise ValueError(variant)


def lead_lag_table(data: pd.DataFrame, margin: pd.DataFrame) -> pd.DataFrame:
    dlog_columns = [
        "lc_spot_dlog", "lc_output_dlog", "spodumene_cny_dlog", "battery_install_dlog"
    ]
    residuals = month_of_year_residualize(data, dlog_columns)
    work = data.copy()
    for column in dlog_columns:
        work[f"{column}_moy_resid"] = residuals[f"{column}_moy_resid"]
    work = work.merge(margin, on="month", how="left", validate="one_to_one")

    rows: list[dict] = []
    transforms = (
        ("dlog", "_dlog", "_dlog"),
        ("yoy_log", "_yoy_log", "_yoy_log"),
        ("dlog_moy_resid", "_dlog_moy_resid", "_dlog_moy_resid"),
        ("log_descriptive", "_log", "_log"),
    )
    for mechanism, x, y, _, _, _ in MECHANISMS:
        variants = ("FULL_SAMPLE", "EXCLUDE_EARLY_2020_ROBUSTNESS") if (
            "battery" in x or "battery" in y or "output" in x or "output" in y
        ) else ("FULL_SAMPLE",)
        for variant in variants:
            sample = _sample(work, variant)
            for transform, x_suffix, y_suffix in transforms:
                for lag in range(-12, 13):
                    result = correlation_at_lag(sample[f"{x}{x_suffix}"], sample[f"{y}{y_suffix}"], lag)
                    rows.append({
                        "mechanism": mechanism, "x": x, "y": y,
                        "transform": transform, "sample_variant": variant, "lag": lag,
                        "lag_convention": LAG_CONVENTION, **result,
                    })

    margin_pairs = [
        ("margin_proxy_zlevel", "lc_output", "log_descriptive", "margin_proxy_zlevel", "lc_output_log"),
        ("margin_proxy_zlevel", "lc_output", "yoy_log", "margin_proxy_zlevel", "lc_output_yoy_log"),
        ("margin_proxy_dlog_gap", "lc_output", "dlog", "margin_proxy_dlog_gap", "lc_output_dlog"),
        ("margin_proxy_dlog_gap", "lc_output", "dlog_moy_resid", "margin_proxy_dlog_gap", "lc_output_dlog_moy_resid"),
    ]
    for variant in ("FULL_SAMPLE", "EXCLUDE_EARLY_2020_ROBUSTNESS"):
        sample = _sample(work, variant)
        for x, y, transform, x_col, y_col in margin_pairs:
            for lag in range(1, 13):
                result = correlation_at_lag(sample[x_col], sample[y_col], lag)
                rows.append({
                    "mechanism": "Margin → Future Supply", "x": x, "y": y,
                    "transform": transform, "sample_variant": variant, "lag": lag,
                    "lag_convention": LAG_CONVENTION, **result,
                })

    table = pd.DataFrame(rows)
    table["sign"] = np.where(table.pearson.gt(0), "POSITIVE", np.where(table.pearson.lt(0), "NEGATIVE", "ZERO"))
    table["local_stability_flag"] = False
    keys = ["mechanism", "x", "y", "transform", "sample_variant"]
    for _, group in table.groupby(keys, sort=False):
        indexed = group.set_index("lag")
        for idx, row in group.iterrows():
            lag = int(row.lag)
            neighbors = indexed.loc[indexed.index.isin([lag - 1, lag + 1])]
            same = neighbors.loc[np.sign(neighbors.pearson) == np.sign(row.pearson)]
            no_spike = (not same.empty) and abs(row.pearson) <= 2.0 * max(abs(same.pearson).max(), 1e-12)
            table.loc[idx, "local_stability_flag"] = bool(len(same) >= 1 and no_spike)
    table["sample_flag"] = np.where(table.n_effective.lt(48), "LOW_EFFECTIVE_SAMPLE", "ADEQUATE_EFFECTIVE_SAMPLE")
    return table


def candidate_regions(correlations: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    definitions = {m: (lo, hi, expected) for m, _, _, lo, hi, expected in MECHANISMS}
    definitions["Margin → Future Supply"] = (1, 12, 1)
    for mechanism, (low, high, expected) in definitions.items():
        transform = "yoy_log" if mechanism == "Margin → Future Supply" else "dlog"
        group = correlations.loc[
            correlations.mechanism.eq(mechanism)
            & correlations["transform"].eq(transform)
            & correlations.sample_variant.eq("FULL_SAMPLE")
            & correlations.lag.between(low, high)
        ].copy()
        if mechanism == "Margin → Future Supply":
            group = group.loc[group.x.eq("margin_proxy_zlevel")]
        stable = group.loc[group.local_stability_flag & np.sign(group.pearson).eq(expected)].copy()
        pool = stable if not stable.empty else group.loc[group.local_stability_flag].copy()
        if pool.empty:
            pool = group.copy()
        peak_abs = pool.pearson.abs().max()
        selected = pool.loc[pool.pearson.abs().ge(max(0.10, 0.60 * peak_abs))].sort_values("lag")
        forced_peak = False
        if selected.empty:
            selected = group.loc[[group.pearson.abs().idxmax()]].sort_values("lag")
            forced_peak = True
        regions: list[list[int]] = []
        for lag in selected.lag.astype(int):
            if not regions or lag != regions[-1][-1] + 1:
                regions.append([lag])
            else:
                regions[-1].append(lag)
        ranked = sorted(regions, key=lambda r: selected.loc[selected.lag.isin(r), "pearson"].abs().max(), reverse=True)[:3]
        expanded: list[list[int]] = []
        for region in ranked:
            if len(region) == 1:
                lag = region[0]
                adjacent = group.loc[group.lag.isin([lag - 1, lag + 1])].copy()
                same_sign = adjacent.loc[np.sign(adjacent.pearson) == np.sign(group.loc[group.lag.eq(lag), "pearson"].iloc[0])]
                choice = same_sign if not same_sign.empty else adjacent
                if not choice.empty:
                    region = sorted([lag, int(choice.loc[choice.pearson.abs().idxmax(), "lag"])])
            expanded.append(region)
        ranked = expanded
        for rank, region in enumerate(ranked, 1):
            region_rows = selected.loc[selected.lag.isin(region)]
            peak_idx = region_rows.pearson.abs().idxmax()
            peak = correlations.loc[peak_idx]
            rows.append({
                "mechanism": mechanism, "x": peak.x, "y": peak.y, "transform": transform,
                "sample_variant": "FULL_SAMPLE", "region_rank": rank,
                "candidate_lag_start": min(region), "candidate_lag_end": max(region),
                "peak_lag": int(peak.lag), "peak_pearson": peak.pearson,
                "peak_spearman": peak.spearman, "sign": peak.sign,
                "local_stability": bool(peak.local_stability_flag),
                "n_effective": int(peak.n_effective),
                "notes": ("Peak-centered weak region because no stable correlation exceeded 0.10; " if forced_peak else "")
                + "contiguous diagnostic region, not a fixed structural lag",
            })
    return pd.DataFrame(rows)


def hac_confirmation(data: pd.DataFrame, margin: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    residuals = month_of_year_residualize(data, ["lc_spot_dlog", "lc_output_dlog", "spodumene_cny_dlog", "battery_install_dlog"])
    work = data.copy()
    for column in residuals.columns[1:]:
        work[column] = residuals[column]
    work = work.merge(margin, on="month", how="left", validate="one_to_one")
    rows = []
    for item in candidates.itertuples(index=False):
        if item.region_rank != 1:
            continue
        x_col = item.x if item.mechanism == "Margin → Future Supply" else f"{item.x}_{item.transform}"
        y_col = f"{item.y}_log" if item.transform == "log_descriptive" else f"{item.y}_{item.transform}"
        pairs = aligned_pairs(work[x_col], work[y_col], int(item.peak_lag))
        bandwidth = min(3, math.floor(len(pairs) ** 0.25))
        fit = sm.OLS(pairs.y, sm.add_constant(pairs.x)).fit(cov_type="HAC", cov_kwds={"maxlags": bandwidth})
        rows.append({
            "mechanism": item.mechanism, "lag": int(item.peak_lag), "transform": item.transform,
            "sample": "FULL_SAMPLE", "beta": fit.params["x"], "hac_se": fit.bse["x"],
            "t_stat": fit.tvalues["x"], "p_value": fit.pvalues["x"], "r2": fit.rsquared,
            "n": int(fit.nobs), "hac_bandwidth": bandwidth,
            "interpretation": "DIAGNOSTIC_CONFIRMATION_NOT_CAUSAL",
        })
    return pd.DataFrame(rows)
