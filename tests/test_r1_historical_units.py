"""Synthetic counterexamples for additive R1 historical log-unit restoration."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.structural.r1_historical_units import (
    LOG_UNIT, MEAN_COMPONENT, TOTAL_COMPONENT, restore_historical_log_units,
)


def _example():
    mu, sd = 0.1, 2.0
    contributions = {
        "2021-01": {"initial_condition": 0.4, "demand": 0.1, "cost": 0.2,
                    "supply": 0.1, "price": 0.2},
        "2021-02": {"initial_condition": 0.3, "demand": -0.5, "cost": -0.4,
                    "supply": -0.2, "price": -0.2},
        "2021-03": {"initial_condition": 0.2, "demand": 0.1, "cost": 0.1,
                    "supply": 0.05, "price": 0.05},
    }
    monthly_rows = []
    raw_rows = []
    price_rows = [{"month": "2020-12", "lc_spot": 100.0}]
    last_price = 100.0
    for month, pieces in contributions.items():
        state = sum(pieces.values())
        raw = mu + sd * state
        raw_rows.append({"month": month, "lc_spot_dlog": raw})
        last_price *= np.exp(raw)
        price_rows.append({"month": month, "lc_spot": last_price})
        for name, value in [*pieces.items(), ("smoothed_state", state)]:
            monthly_rows.append({"month": month, "component": name,
                                 "posterior_mean": value,
                                 "observed_standardized_spot_dlog": state})
    episode_rows = []
    for name in (*contributions["2021-02"], "smoothed_state"):
        value = sum((sum(contributions[month].values()) if name == "smoothed_state"
                     else contributions[month][name]) for month in ("2021-02", "2021-03"))
        episode_rows.append({"specification": "BASELINE", "window": "FEB_MAR",
                             "start": "2021-02", "end": "2021-03", "component": name,
                             "posterior_mean": value})
    return (pd.DataFrame(monthly_rows), pd.DataFrame(episode_rows),
            pd.DataFrame(raw_rows), pd.DataFrame(price_rows), mu, sd)


def _restore(example):
    monthly, episodes, raw, prices, mu, sd = example
    return restore_historical_log_units(
        monthly, episodes, raw, prices, spot_mean=mu, spot_sd=sd,
        identity_atol=1e-12, endpoint_atol=1e-12)


def test_mean_is_separate_addend_and_initial_condition_is_preserved():
    monthly, episodes = _restore(_example())
    for month, group in monthly.groupby("month"):
        addends = group.loc[group.component_role.eq("ADDEND")]
        total = group.loc[group.component.eq(TOTAL_COMPONENT)].iloc[0]
        assert len(addends) == 6  # mean, IC, four shocks
        assert np.isclose(addends.raw_log_change_contribution.sum(),
                          total.raw_log_change_contribution)
        assert np.isclose(addends.loc[addends.component.eq(MEAN_COMPONENT),
                                      "raw_log_change_contribution"].iloc[0], 0.1)
        assert np.isclose(addends.loc[addends.component.eq("initial_condition"),
                                      "raw_log_change_contribution"].iloc[0],
                          2 * {"2021-01": 0.4, "2021-02": 0.3, "2021-03": 0.2}[month])
        # The five stochastic/IC terms alone are not the raw price change.
        assert not np.isclose(addends.loc[addends.component.ne(MEAN_COMPONENT),
                                           "raw_log_change_contribution"].sum(),
                              total.raw_log_change_contribution)
    assert set(episodes.component) == set(monthly.component)


def test_episode_boundaries_include_feb_and_mar_but_not_jan():
    monthly, episode = _restore(_example())
    total = episode.loc[episode.component.eq(TOTAL_COMPONENT)].iloc[0]
    assert total.start == "2021-02" and total.end == "2021-03"
    assert total.n_months == 2
    assert total.return_start_endpoint_month == "2021-01"
    assert total.return_end_endpoint_month == "2021-03"
    assert np.isclose(total.raw_log_change_contribution, -0.8)  # -1.9 + 1.1
    assert np.isclose(total.frozen_price_endpoint_log_change,
                      total.raw_log_change_contribution)
    mean = episode.loc[episode.component.eq(MEAN_COMPONENT)].iloc[0]
    assert np.isclose(mean.raw_log_change_contribution, 2 * 0.1)
    assert np.isclose(episode.loc[episode.component_role.eq("ADDEND"),
                                  "raw_log_change_contribution"].sum(), -0.8)
    assert np.isclose(monthly.loc[monthly.month.isin(["2021-02", "2021-03"])
                                  & monthly.component.eq("initial_condition"),
                                  "raw_log_change_contribution"].sum(), 2 * 0.5)


def test_nonbaseline_episode_may_have_other_shock_allocation_but_same_observed_total():
    monthly, episodes, raw, prices, mu, sd = _example()
    other = episodes.copy()
    other["specification"] = "ALTERNATIVE"
    other.loc[other.component.eq("demand"), "posterior_mean"] += 0.2
    other.loc[other.component.eq("price"), "posterior_mean"] -= 0.2
    _, restored = _restore((monthly, pd.concat([episodes, other]), raw, prices, mu, sd))
    assert set(restored.specification) == {"BASELINE", "ALTERNATIVE"}
    assert np.isclose(restored.loc[restored.specification.eq("ALTERNATIVE")
                                    & restored.component.eq(TOTAL_COMPONENT),
                                    "raw_log_change_contribution"].iloc[0], -0.8)


def test_missing_ic_or_wrong_episode_monthly_sum_is_rejected():
    monthly, episodes, raw, prices, mu, sd = _example()
    missing_ic = monthly.loc[~(monthly.month.eq("2021-02")
                                & monthly.component.eq("initial_condition"))]
    with pytest.raises(ValueError, match="components incomplete"):
        _restore((missing_ic, episodes, raw, prices, mu, sd))
    wrong_episode = episodes.copy()
    wrong_episode.loc[wrong_episode.component.eq("demand"), "posterior_mean"] += 0.1
    wrong_episode.loc[wrong_episode.component.eq("price"), "posterior_mean"] -= 0.1
    with pytest.raises(ValueError, match="baseline episode/monthly sum"):
        _restore((monthly, wrong_episode, raw, prices, mu, sd))


def test_wrong_frozen_endpoint_or_missing_month_is_rejected():
    monthly, episodes, raw, prices, mu, sd = _example()
    bad_prices = prices.copy()
    bad_prices.loc[bad_prices.month.eq("2021-03"), "lc_spot"] *= 1.01
    with pytest.raises(ValueError, match="frozen price endpoint"):
        _restore((monthly, episodes, raw, bad_prices, mu, sd))
    missing_feb = monthly.loc[monthly.month.ne("2021-02")]
    with pytest.raises(ValueError, match="contiguous"):
        _restore((missing_feb, episodes, raw, prices, mu, sd))


def test_units_and_percent_are_not_misrepresented_as_additive_percent_or_cny():
    monthly, episodes = _restore(_example())
    for table in (monthly, episodes):
        assert set(table.log_change_unit) == {LOG_UNIT}
        assert table.loc[table.component_role.eq("ADDEND"),
                         "total_simple_percent_change"].isna().all()
        totals = table.loc[table.component.eq(TOTAL_COMPONENT)]
        assert np.allclose(totals.total_simple_percent_change,
                           100 * np.expm1(totals.raw_log_change_contribution))
        assert not any("cny" in column.lower() or "tonne" in column.lower()
                       for column in table.columns)


def test_invalid_scaler_cannot_silently_restore_units():
    monthly, episodes, raw, prices, mu, _ = _example()
    with pytest.raises(ValueError, match="spot_sd must be positive"):
        restore_historical_log_units(monthly, episodes, raw, prices,
                                     spot_mean=mu, spot_sd=0,
                                     identity_atol=1e-12, endpoint_atol=1e-12)


def test_missing_baseline_episode_cannot_bypass_monthly_cross_check():
    monthly, episodes, raw, prices, mu, sd = _example()
    episodes["specification"] = "ALTERNATIVE"
    with pytest.raises(ValueError, match="missing baseline"):
        _restore((monthly, episodes, raw, prices, mu, sd))
