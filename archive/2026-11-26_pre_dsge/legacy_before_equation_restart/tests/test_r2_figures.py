"""Portable safety checks for R2 read-only figure selection; no private data needed."""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.build_r2_figures import (
    EQUATIONS_SOURCE_SHA256, HORIZONS, MECHANISM_EQUATIONS,
    MECHANISM_LAG_LINKS, MECHANISM_PRICE_LINKS, MODELS, ROOT, file_hash,
    select_forecast, select_inventory, select_lags, select_posterior,
    select_price_irf,
)


def forecast_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    revision_rows = []
    archive_rows = []
    for model in MODELS:
        for horizon, n in zip(HORIZONS, (21, 19, 16)):
            rmse = 1000.0 + horizon
            u2 = 1.0 if model == "RW_NO_DRIFT" else 0.9
            revision_rows.append({"model": model, "horizon": horizon,
                                  "n_r1": n, "n_archived": n,
                                  "rmse_level_r1": rmse,
                                  "mae_level_absolute_difference": 0.0,
                                  "theil_u2_r1": u2, "status": "PASS"})
            archive_rows.append({"model": model, "horizon": horizon, "n": n,
                                 "rmse_level": rmse, "mae_level": 800.0 + horizon,
                                 "theil_u2": u2})
    return pd.DataFrame(revision_rows), pd.DataFrame(archive_rows)


def test_forecast_requires_complete_verified_grid_and_common_n() -> None:
    revision, archive = forecast_fixture()
    assert len(select_forecast(revision, archive)) == 15
    with pytest.raises(ValueError, match="grid"):
        select_forecast(revision.iloc[:-1], archive)
    archive.loc[(archive.model == "AR_BIC") & (archive.horizon == 1), "n"] = 20
    with pytest.raises(ValueError, match="status/N"):
        select_forecast(revision, archive)


def inventory_fixture() -> pd.DataFrame:
    rows = []
    for transformation, n, point in (("log_level", 28, 0.65), ("log_change", 27, 0.15)):
        for block in (3, 6):
            rows.append({"specification": "BASELINE", "external_series": "lc_inventory_total_mean",
                         "information_use": "SMOOTHED", "transformation": transformation,
                         "block_length": block, "n_months": n, "point_correlation": point,
                         "ci025": point - 0.2, "ci975": point + 0.2,
                         "point_status": "OK", "interval_status": "COMPUTED",
                         "valid_replicates": 2000, "n_rep": 2000, "invalid_replicates": 0})
    return pd.DataFrame(rows)


def test_inventory_block_lengths_share_one_point_estimate() -> None:
    rows = inventory_fixture()
    assert len(select_inventory(rows)) == 4
    rows.loc[(rows.transformation == "log_change") & (rows.block_length == 6), "point_correlation"] = 0.25
    with pytest.raises(ValueError, match="Same correlation"):
        select_inventory(rows)


def lags_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    lag_rows = []
    for spec, frequency, lag_range in (
        ("MATCHED_EOM_PRIMARY", "monthly", range(-3, 4)),
        ("DAILY_MATCHED_INTERVAL_PRIMARY", "daily", range(-5, 6)),
    ):
        for rule in ("EX_POST_DESCRIPTIVE_MAIN", "LAGGED_VOLUME_MAIN"):
            for lag in lag_range:
                lag_rows.append({"specification": spec, "main_rule": rule, "stratum": "ALL",
                                 "frequency": frequency, "lag_spot_periods": lag,
                                 "pearson": 0.5 if lag == 1 else 0.1})
    claims = pd.DataFrame([
        {"claim": claim, "matched_ex_post_pearson": 0.5,
         "matched_lagged_main_pearson": 0.5}
        for claim in ("MONTHLY_LAG_PLUS_ONE", "DAILY_LAG_PLUS_ONE")
    ])
    return pd.DataFrame(lag_rows), claims


def test_futures_requires_full_lag_family_matching_final_claim() -> None:
    lags, claims = lags_fixture()
    assert len(select_lags(lags, claims)) == 36
    bad = lags.loc[~((lags.specification == "MATCHED_EOM_PRIMARY") &
                     (lags.main_rule == "LAGGED_VOLUME_MAIN") &
                     (lags.lag_spot_periods == -2))]
    with pytest.raises(ValueError, match="Incomplete"):
        select_lags(bad, claims)
    claims.loc[claims.claim == "DAILY_LAG_PLUS_ONE", "matched_ex_post_pearson"] = 0.4
    with pytest.raises(ValueError, match="does not match"):
        select_lags(lags, claims)


def test_posterior_rejects_invalid_quantile_order() -> None:
    rows = pd.DataFrame({"parameter": [f"p{i}" for i in range(14)],
                         "q05": [0.1] * 14, "median": [0.2] * 14,
                         "q95": [0.3] * 14})
    assert len(select_posterior(rows)) == 14
    rows.loc[0, "q95"] = 0.15
    with pytest.raises(ValueError, match="order"):
        select_posterior(rows)


def test_price_irf_requires_posterior_quantiles_for_all_four_full_horizons() -> None:
    rows = pd.DataFrame([
        {"shock": shock, "state": "p", "horizon": horizon,
         "q05": -0.2, "q16": -0.1, "median": 0.0,
         "q84": 0.1, "q95": 0.2}
        for shock in ("demand", "cost", "supply", "price")
        for horizon in range(25)
    ])
    assert len(select_price_irf(rows)) == 100
    with pytest.raises(ValueError, match="four 25-month"):
        select_price_irf(rows.iloc[:-1])
    rows.loc[0, "q84"] = -0.01
    with pytest.raises(ValueError, match="unordered"):
        select_price_irf(rows)


def test_mechanism_diagram_matches_frozen_core5_timing() -> None:
    assert file_hash(ROOT / "src/structural/equations.py") == EQUATIONS_SOURCE_SHA256
    assert (r"$c_{t-1}$", r"$q_t$", r"$-a_c$") in MECHANISM_LAG_LINKS
    assert (r"$p_{t-1}$", r"$q_t$", r"$+a_p$") in MECHANISM_LAG_LINKS
    assert (r"$q_{t-1}$", r"$n_t$", r"$+1$") in MECHANISM_LAG_LINKS
    assert (r"$d_{t-1}$", r"$n_t$", r"$-1$") in MECHANISM_LAG_LINKS
    assert (r"$n_t$", r"$-b_n$") in MECHANISM_PRICE_LINKS
    assert r"-a_c c_{t-1}" in MECHANISM_EQUATIONS[2]
    assert r"q_{t-1}-d_{t-1}" in MECHANISM_EQUATIONS[3]
    assert r"-b_n n_t" in MECHANISM_EQUATIONS[4]
