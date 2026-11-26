import numpy as np
import pandas as pd

from src.futures.continuous_contract import (
    add_roll_safe_returns,
    aggregate_main_monthly,
    select_daily_main_contract,
)


def _panel():
    rows = [
        ("2023-07-21", "LC2401", 100.0, 100.0),
        ("2023-07-21", "LC2402", 110.0, 80.0),
        ("2023-07-24", "LC2401", 101.0, 90.0),
        ("2023-07-24", "LC2402", 111.0, 120.0),
        ("2023-08-01", "LC2402", 112.0, 130.0),
    ]
    frame = pd.DataFrame(rows, columns=["date", "contract", "daily_close", "daily_volume"])
    frame["date"] = pd.to_datetime(frame.date)
    return frame


def test_main_contract_is_deterministic_and_uses_same_day_volume_only():
    panel = _panel()
    selected = select_daily_main_contract(panel)
    assert selected.main_contract.tolist() == ["LC2401", "LC2402", "LC2402"]
    changed = panel.copy()
    changed.loc[changed.date.eq(pd.Timestamp("2023-07-24")) & changed.contract.eq("LC2402"), "daily_volume"] = 1_000_000
    selected_changed = select_daily_main_contract(changed)
    assert selected_changed.loc[selected_changed.date.eq(pd.Timestamp("2023-07-21")), "main_contract"].iloc[0] == "LC2401"
    assert selected.volume_share.between(0, 1).all()


def test_roll_switch_uses_new_contract_previous_close_not_cross_contract_gap():
    panel = _panel()
    selected = select_daily_main_contract(panel)
    result = add_roll_safe_returns(selected, panel)
    switched = result.loc[result.switch_flag.eq(1)].iloc[0]
    assert switched.roll_return_status == "SWITCH_NEW_CONTRACT_REFERENCE"
    assert np.isclose(switched.roll_safe_log_return, np.log(111.0 / 110.0))
    assert np.isclose(switched.raw_main_close_log_change, np.log(111.0 / 100.0))
    assert not np.isclose(switched.roll_safe_log_return, switched.raw_main_close_log_change)


def test_monthly_return_is_sum_of_complete_roll_safe_daily_returns():
    panel = _panel()
    daily = add_roll_safe_returns(select_daily_main_contract(panel), panel)
    monthly = aggregate_main_monthly(daily).set_index("month")
    assert np.isnan(monthly.loc["2023-07", "monthly_roll_safe_log_return"])
    assert np.isclose(monthly.loc["2023-07", "observed_period_roll_safe_log_return"], np.log(111 / 110))
    assert monthly.loc["2023-07", "coverage_status"] == "PARTIAL_LISTING_MONTH"
    assert np.isclose(monthly.loc["2023-08", "monthly_roll_safe_log_return"], np.log(112 / 111))
    assert monthly.loc["2023-07", "switch_count"] == 1


def test_delivery_month_tie_break_prefers_nearest_nonexpired_contract():
    frame = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-02"] * 3),
        "contract": ["LC2312", "LC2401", "LC2402"],
        "daily_close": [100.0, 101.0, 102.0],
        "daily_volume": [10.0, 10.0, 10.0],
    })
    selected = select_daily_main_contract(frame)
    assert selected.main_contract.iloc[0] == "LC2401"
