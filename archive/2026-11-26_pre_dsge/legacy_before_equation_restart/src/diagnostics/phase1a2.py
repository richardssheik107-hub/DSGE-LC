"""Assembly helpers for Phase 1A-2 mechanism diagnostics."""
from __future__ import annotations

import numpy as np
import pandas as pd


def margin_proxy_table(data: pd.DataFrame) -> pd.DataFrame:
    """Build two dimensionless diagnostics; neither is an observed profit measure."""
    def z(series: pd.Series) -> pd.Series:
        return (series - series.mean()) / series.std(ddof=1)

    return pd.DataFrame({
        "month": data.month.copy(),
        "margin_proxy_zlevel": z(data.lc_spot_log) - z(data.spodumene_cny_log),
        "margin_proxy_dlog_gap": z(data.lc_spot_dlog) - z(data.spodumene_cny_dlog),
    })


def mechanism_evidence(
    correlations: pd.DataFrame,
    candidates: pd.DataFrame,
    breaks: pd.DataFrame,
) -> pd.DataFrame:
    implications = {
        "Cost → Price": "Test a short cost pass-through window; do not impose contemporaneous causality.",
        "Demand → Price": "Treat realized battery installation as an observable with possible timing mismatch.",
        "Price → Demand": "Do not treat installation as a purely contemporaneous exogenous demand state.",
        "Supply → Price": "Test supply timing only if sign and robustness remain economically coherent.",
        "Price → Future Supply": "Use the region as a capacity-response lag candidate, not a fixed lag.",
        "Margin → Future Supply": "Use as a latent investment/capacity timing prior candidate only.",
    }
    expected_sign = {
        "Cost → Price": "POSITIVE", "Demand → Price": "POSITIVE",
        "Price → Demand": "POSITIVE", "Supply → Price": "NEGATIVE",
        "Price → Future Supply": "POSITIVE", "Margin → Future Supply": "POSITIVE",
    }
    rows = []
    for item in candidates.loc[candidates.region_rank.eq(1)].itertuples(index=False):
        full = correlations.loc[
            correlations.mechanism.eq(item.mechanism)
            & correlations.x.eq(item.x)
            & correlations["transform"].eq(item.transform)
            & correlations.sample_variant.eq("FULL_SAMPLE")
            & correlations.lag.eq(item.peak_lag)
        ].iloc[0]
        robust_rows = correlations.loc[
            correlations.mechanism.eq(item.mechanism)
            & correlations.x.eq(item.x)
            & correlations["transform"].eq(item.transform)
            & correlations.sample_variant.eq("EXCLUDE_EARLY_2020_ROBUSTNESS")
            & correlations.lag.eq(item.peak_lag)
        ]
        early_ok = robust_rows.empty or np.sign(robust_rows.iloc[0].pearson) == np.sign(full.pearson)
        related = correlations.loc[
            correlations.mechanism.eq(item.mechanism)
            & correlations.sample_variant.eq("FULL_SAMPLE")
            & correlations.lag.eq(item.peak_lag)
        ]
        yoy = related.loc[related["transform"].eq("yoy_log")]
        season = related.loc[related["transform"].eq("dlog_moy_resid")]
        yoy_ok = not yoy.empty and np.sign(yoy.iloc[0].pearson) == np.sign(full.pearson)
        season_ok = not season.empty and np.sign(season.iloc[0].pearson) == np.sign(full.pearson)
        spearman_ok = np.sign(full.spearman) == np.sign(full.pearson)
        scores = sum([bool(full.local_stability_flag), bool(yoy_ok), bool(season_ok), bool(early_ok), bool(spearman_ok), full.n_effective >= 48])
        strength = "STRONG" if scores >= 5 and abs(full.pearson) >= 0.30 else "MODERATE" if scores >= 4 and abs(full.pearson) >= 0.20 else "WEAK" if bool(full.local_stability_flag) and abs(full.pearson) >= 0.10 else "NO_CLEAR_EVIDENCE"
        if full.sign != expected_sign[item.mechanism]:
            strength = "NO_CLEAR_EVIDENCE"
        if item.mechanism == "Margin → Future Supply" and strength == "STRONG":
            # Level-output correlation has the opposite sign and the secondary dlog rank evidence is weak.
            strength = "MODERATE"
        # A simple sensitivity flag: statistical break evidence in either linked variable.
        linked_breaks = breaks.loc[breaks.variable.isin({item.x, item.y, "spodumene_cny_t"})]
        break_sensitive = linked_breaks.strength.isin({"STRONG_CANDIDATE", "MODERATE_CANDIDATE"}).any()
        rows.append({
            "mechanism": item.mechanism, "x_variable": item.x, "y_variable": item.y,
            "primary_transform": item.transform,
            "candidate_lag_start": int(item.candidate_lag_start), "candidate_lag_end": int(item.candidate_lag_end),
            "peak_lag": int(item.peak_lag), "peak_pearson": full.pearson, "peak_spearman": full.spearman,
            "sign": full.sign, "yoy_consistent": bool(yoy_ok), "seasonality_robust": bool(season_ok),
            "early2020_robust": bool(early_ok), "local_stability": bool(full.local_stability_flag),
            "break_sensitive": bool(break_sensitive), "evidence_strength": strength,
            "structural_implication": implications[item.mechanism],
            "notes": ("Observed sign conflicts with the mechanism prior; " if full.sign != expected_sign[item.mechanism] else "")
            + "descriptive/predictive lead-lag evidence; multiple-lag scan; not causal proof.",
        })
    return pd.DataFrame(rows)
