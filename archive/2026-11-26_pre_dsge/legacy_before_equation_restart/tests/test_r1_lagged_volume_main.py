"""LAGGED_VOLUME_MAIN timing, tie-break and missing-reference counterexamples."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.futures.continuous_contract import (
    select_daily_main_contract,
    select_lagged_volume_main_contract,
)


def _panel():
    rows = [
        ('2023-07-21', 'LC2401', 100., 100.),
        ('2023-07-21', 'LC2402', 110., 80.),
        ('2023-07-24', 'LC2401', 101., 90.),
        ('2023-07-24', 'LC2402', 111., 120.),
        ('2023-07-25', 'LC2401', 102., 60.),
        ('2023-07-25', 'LC2402', 112., 130.),
        ('2023-07-26', 'LC2401', 103., 50.),
        ('2023-07-26', 'LC2402', 113., 140.),
    ]
    return pd.DataFrame(rows, columns=['date', 'contract', 'daily_close', 'daily_volume'])


def test_lagged_choice_uses_previous_day_volume_not_t_volume():
    panel = _panel()
    result = select_lagged_volume_main_contract(panel)
    by_date = result.set_index('date')
    first = by_date.loc[pd.Timestamp('2023-07-21')]
    assert pd.isna(first.main_contract)
    assert first.selection_status == 'NO_PRIOR_VOLUME'
    assert not first.prior_trading_date_present
    assert np.isnan(first.roll_safe_log_return)
    day2 = by_date.loc[pd.Timestamp('2023-07-24')]
    assert day2.main_contract == 'LC2401'  # t-1 A=100, B=80
    assert day2.known_volume == 100.
    assert day2.selection_asof_date == pd.Timestamp('2023-07-21')
    assert np.isclose(day2.roll_safe_log_return, np.log(101 / 100))
    assert day2.futures_complete_flag
    # Same-day ex-post rule would pick B; its old behavior remains available.
    ex_post = select_daily_main_contract(panel)
    assert ex_post.set_index('date').loc[pd.Timestamp('2023-07-24'), 'main_contract'] == 'LC2402'


def test_switch_uses_new_contract_t_minus_one_close_not_old_main_gap():
    result = select_lagged_volume_main_contract(_panel()).set_index('date')
    switch = result.loc[pd.Timestamp('2023-07-25')]
    assert switch.main_contract == 'LC2402'
    assert switch.switch_flag == 1
    assert switch.roll_return_status == 'SWITCH_NEW_CONTRACT_REFERENCE'
    assert switch.roll_reference_date == pd.Timestamp('2023-07-24')
    assert switch.roll_reference_close == 111.
    assert np.isclose(switch.roll_safe_log_return, np.log(112 / 111))
    assert np.isclose(switch.raw_main_close_log_change, np.log(112 / 101))


def test_missing_new_contract_prior_close_is_na_with_reason():
    panel = _panel()
    mask = panel.date.eq('2023-07-24') & panel.contract.eq('LC2402')
    panel.loc[mask, 'daily_close'] = np.nan
    result = select_lagged_volume_main_contract(panel).set_index('date')
    switch = result.loc[pd.Timestamp('2023-07-25')]
    assert switch.main_contract == 'LC2402'  # prior volume still 120
    assert switch.switch_flag == 1
    assert switch.roll_return_status == 'SWITCH_NEW_CONTRACT_REFERENCE_MISSING'
    assert np.isnan(switch.roll_safe_log_return)
    assert not switch.futures_complete_flag
    assert switch.eligibility_reason == 'SWITCH_NEW_CONTRACT_REFERENCE_MISSING'


def test_missing_selected_contract_t_quote_does_not_trigger_ex_post_fallback():
    panel = _panel()
    panel = panel.loc[~(panel.date.eq('2023-07-25') & panel.contract.eq('LC2402'))]
    result = select_lagged_volume_main_contract(panel).set_index('date')
    day = result.loc[pd.Timestamp('2023-07-25')]
    assert day.main_contract == 'LC2402'  # must not switch to the available A
    assert not day.selected_current_row_present
    assert day.roll_return_status == 'SELECTED_CONTRACT_NOT_QUOTED_TODAY'
    assert np.isnan(day.roll_safe_log_return)


def test_missing_selected_contract_t_close_keeps_date_and_reason():
    panel = _panel()
    panel.loc[panel.date.eq('2023-07-25') & panel.contract.eq('LC2402'), 'daily_close'] = np.nan
    result = select_lagged_volume_main_contract(panel).set_index('date')
    day = result.loc[pd.Timestamp('2023-07-25')]
    assert day.main_contract == 'LC2402'
    assert day.selected_current_row_present
    assert not day.selected_current_close_available
    assert day.roll_return_status == 'SELECTED_CONTRACT_CLOSE_MISSING_OR_NONPOSITIVE'
    assert np.isnan(day.roll_safe_log_return)


def test_equal_prior_volumes_prefer_nearest_known_valid_delivery():
    panel = pd.DataFrame([
        ('2024-01-02', 'LC2312', 100., 100.),
        ('2024-01-02', 'LC2401', 101., 100.),
        ('2024-01-02', 'LC2402', 102., 100.),
        ('2024-01-03', 'LC2401', 103., 1.),
        ('2024-01-03', 'LC2402', 104., 1000.),
    ], columns=['date', 'contract', 'daily_close', 'daily_volume'])
    day = select_lagged_volume_main_contract(panel).set_index('date').loc[pd.Timestamp('2024-01-03')]
    assert day.main_contract == 'LC2401'  # expired LC2312 excluded, nearer Jan beats Feb
    assert day.prior_candidate_count == 2
    assert day.known_volume == 100.
    assert day.selection_tie_break == 'PRIOR_VOLUME_DESC;NEAREST_VALID_DELIVERY;CONTRACT_ASC'


def test_t_and_future_quotes_cannot_change_existing_contract_selection():
    panel = _panel()
    base = select_lagged_volume_main_contract(panel).set_index('date')
    changed = panel.copy()
    changed.loc[changed.date.eq('2023-07-24') & changed.contract.eq('LC2402'), 'daily_volume'] = 1e9
    modified = select_lagged_volume_main_contract(changed).set_index('date')
    assert modified.loc[pd.Timestamp('2023-07-24'), 'main_contract'] == base.loc[pd.Timestamp('2023-07-24'), 'main_contract']
    assert modified.loc[pd.Timestamp('2023-07-25'), 'main_contract'] == 'LC2402'  # t-1 change may affect t+1
    future = panel.copy()
    future.loc[future.date.eq('2023-07-26'), ['daily_close', 'daily_volume']] = [1e6, 1e6]
    future_selected = select_lagged_volume_main_contract(future).set_index('date')
    assert future_selected.loc[pd.Timestamp('2023-07-25'), 'main_contract'] == base.loc[pd.Timestamp('2023-07-25'), 'main_contract']
    assert np.isclose(future_selected.loc[pd.Timestamp('2023-07-25'), 'roll_safe_log_return'],
                      base.loc[pd.Timestamp('2023-07-25'), 'roll_safe_log_return'])


def test_start_window_uses_prior_date_outside_window_and_exact_end_date():
    result = select_lagged_volume_main_contract(
        _panel(), start_date='2023-07-25', end_date='2023-07-25')
    assert len(result) == 1
    assert result.date.iloc[0] == pd.Timestamp('2023-07-25')
    assert result.selection_asof_date.iloc[0] == pd.Timestamp('2023-07-24')
    assert result.main_contract.iloc[0] == 'LC2402'


def test_no_prior_eligible_contract_keeps_date_and_missing_reason():
    panel = _panel()
    panel.loc[panel.date.eq('2023-07-21'), 'daily_volume'] = 0
    result = select_lagged_volume_main_contract(panel).set_index('date')
    day = result.loc[pd.Timestamp('2023-07-24')]
    assert day.selection_status == 'NO_ELIGIBLE_PRIOR_CONTRACT'
    assert pd.isna(day.main_contract)
    assert np.isnan(day.roll_safe_log_return)
    assert day.eligibility_reason == 'NO_ELIGIBLE_PRIOR_CONTRACT'


def test_duplicate_contract_day_rejected_instead_of_ambiguous_lookup():
    panel = _panel()
    with pytest.raises(ValueError, match='duplicate'):
        select_lagged_volume_main_contract(pd.concat([panel, panel.iloc[[0]]]))
