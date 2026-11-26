"""Synthetic counterexamples for R1 date-keyed spot/futures definitions."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.futures.r1_alignment import (
    build_interval_audit,
    build_monthly_matched_eom,
    build_monthly_matched_mean,
    keyed_lead_lag,
)


def _main(dates, closes, returns, switches=None):
    dates = pd.to_datetime(dates)
    if switches is None:
        switches = [0] * len(dates)
    return pd.DataFrame({
        "date": dates,
        "main_close": closes,
        "roll_safe_log_return": returns,
        "switch_flag": switches,
        "roll_reference_date": [pd.NaT, *dates[:-1]],
    })


def _spot(dates, prices):
    return pd.DataFrame({"date": pd.to_datetime(dates), "lc_spot": prices})


def test_missing_spot_quote_is_a_multisession_diagnostic_not_daily_pair():
    dates = ["2023-07-21", "2023-07-24", "2023-07-25", "2023-07-26"]
    main = _main(dates, [100, 101, 102, 103], [np.nan, .01, .01, .01])
    spot = _spot([dates[0], dates[2], dates[3]], [200, 220, 230])
    rows = build_interval_audit(main, spot).set_index("date")
    missing = rows.loc[pd.Timestamp(dates[1])]
    resumed = rows.loc[pd.Timestamp(dates[2])]
    next_day = rows.loc[pd.Timestamp(dates[3])]
    assert len(rows) == 4
    assert missing.eligibility_reason == "SPOT_END_MISSING"
    assert resumed.eligibility_reason == "SPOT_START_MISSING_MULTIDAY"
    assert resumed.spot_observed_elapsed_trading_days == 2
    assert np.isclose(resumed.spot_observed_interval_log_return, np.log(220 / 200))
    assert np.isnan(resumed.spot_log_return)
    assert np.isnan(resumed.futures_log_return)
    assert next_day.eligibility_reason == "ELIGIBLE_SINGLE_SESSION"
    assert np.isclose(next_day.spot_log_return, np.log(230 / 220))
    assert np.isclose(next_day.futures_log_return, .01)


def test_lagged_main_missing_close_stays_in_index_and_blocks_interval():
    dates = ["2023-07-21", "2023-07-24", "2023-07-25"]
    main = _main(dates, [100, np.nan, 103], [np.nan, np.nan, .02])
    main.loc[1, "switch_flag"] = np.nan
    spot = _spot(dates, [200, 201, 203])
    rows = build_interval_audit(main, spot)
    assert len(rows) == 3
    assert rows.loc[1, "eligibility_reason"] == "FUTURES_RETURN_INCOMPLETE"
    assert not rows.loc[1, "futures_complete_flag"]
    assert not rows.loc[1, "roll_flag"]
    assert rows.loc[2, "eligibility_reason"] == "ELIGIBLE_SINGLE_SESSION"
    assert np.isclose(rows.loc[2, "spot_log_return"], np.log(203 / 201))


def test_eom_uses_last_verified_common_endpoint_without_forward_fill():
    dates = ["2023-07-21", "2023-07-31", "2023-08-01", "2023-08-30",
             "2023-08-31", "2023-09-01", "2023-09-29"]
    main = _main(dates, [100, 101, 102, 103, 104, 105, 106],
                 [np.nan, .01, .02, .03, .04, .05, .06])
    # August 31 and September 1 have no assessment; the August common endpoint
    # is August 30, and the September return still includes futures Aug 31.
    spot = _spot([dates[0], dates[1], dates[2], dates[3], dates[6]],
                 [200, 201, 202, 203, 209])
    intervals = build_interval_audit(main, spot)
    monthly = build_monthly_matched_eom(intervals, main, spot).set_index("month")
    august = monthly.loc["2023-08"]
    september = monthly.loc["2023-09"]
    assert august.common_endpoint_date == pd.Timestamp("2023-08-30")
    assert august.futures_last_date == pd.Timestamp("2023-08-31")
    assert bool(august.endpoint_adjusted_flag)
    assert august.return_start_date == pd.Timestamp("2023-07-31")
    assert august.return_end_date == pd.Timestamp("2023-08-30")
    assert np.isclose(august.futures_log_return, .02 + .03)
    assert np.isclose(august.spot_log_return, np.log(203 / 201))
    assert september.return_start_date == pd.Timestamp("2023-08-30")
    assert np.isclose(september.futures_log_return, .04 + .05 + .06)
    assert np.isclose(september.spot_log_return, np.log(209 / 203))


def test_eom_never_uses_missing_futures_close_as_endpoint():
    dates = ["2023-07-21", "2023-07-31", "2023-08-30", "2023-08-31"]
    main = _main(dates, [100, 101, 102, np.nan], [np.nan, .01, .02, np.nan])
    spot = _spot(dates, [200, 201, 202, 203])
    monthly = build_monthly_matched_eom(build_interval_audit(main, spot), main, spot)
    august = monthly.loc[monthly.month.eq("2023-08")].iloc[0]
    assert august.common_endpoint_date == pd.Timestamp("2023-08-30")
    assert august.futures_last_date == pd.Timestamp("2023-08-30")
    assert august.spot_last_date == pd.Timestamp("2023-08-31")
    assert bool(august.endpoint_adjusted_flag)
    assert np.isclose(august.futures_log_return, .02)


def test_monthly_mean_excludes_listing_month_and_nonadjacent_months():
    dates = ["2023-07-21", "2023-07-31", "2023-08-01", "2023-08-31",
             "2023-09-01", "2023-09-29", "2023-11-01", "2023-11-30"]
    main = _main(dates, [100, 101, 102, 104, 105, 107, 109, 110],
                 [np.nan, .01, .01, .01, .01, .01, .01, .01],
                 [0, 0, 0, 0, 1, 0, 0, 0])
    spot = _spot(dates, [200, 201, 202, 204, 205, 207, 209, 210])
    monthly = build_monthly_matched_mean(main, spot).set_index("month")
    assert monthly.loc["2023-07", "coverage_status"] == "PARTIAL_LISTING_MONTH"
    assert monthly.loc["2023-08", "eligibility_reason"] == "PREVIOUS_MONTH_INCOMPLETE"
    assert np.isnan(monthly.loc["2023-08", "futures_log_return"])
    assert monthly.loc["2023-09", "eligibility_reason"] == "ELIGIBLE_COMPLETE_MONTH_MEANS"
    assert np.isclose(monthly.loc["2023-09", "futures_log_return"], np.log(106 / 103))
    assert bool(monthly.loc["2023-09", "switch_window_flag"])
    assert monthly.loc["2023-10", "coverage_status"] == "NO_FUTURES_DAYS"
    assert monthly.loc["2023-11", "eligibility_reason"] == "PREVIOUS_MONTH_INCOMPLETE"
    assert np.isnan(monthly.loc["2023-11", "spot_log_return"])


def test_monthly_mean_missing_futures_price_or_spot_date_is_not_complete():
    dates = ["2023-07-21", "2023-07-31", "2023-08-01", "2023-08-31",
             "2023-09-01", "2023-09-29"]
    main = _main(dates, [100, 101, 102, np.nan, 105, 107],
                 [np.nan, .01, .01, np.nan, .01, .01])
    spot = _spot(dates, [200, 201, 202, 204, 205, 207])
    monthly = build_monthly_matched_mean(main, spot).set_index("month")
    assert monthly.loc["2023-08", "coverage_status"] == "FUTURES_PRICE_MISSING"
    assert np.isnan(monthly.loc["2023-08", "futures_log_return"])
    assert monthly.loc["2023-09", "eligibility_reason"] == "PREVIOUS_MONTH_INCOMPLETE"

    main.loc[main.date.eq(pd.Timestamp("2023-08-31")), "main_close"] = 104
    spot = spot.loc[spot.date.ne(pd.Timestamp("2023-08-31"))]
    monthly = build_monthly_matched_mean(main, spot).set_index("month")
    assert monthly.loc["2023-08", "coverage_status"] == "NONCOMPARABLE_TRADING_DATES"
    assert monthly.loc["2023-08", "spot_missing_futures_days"] == 1


def test_daily_keyed_lag_keeps_missing_quote_day_and_uses_full_calendar():
    dates = pd.to_datetime(["2023-07-21", "2023-07-24", "2023-07-25",
                            "2023-07-26", "2023-07-27"])
    frame = pd.DataFrame({"date": dates, "futures": [1., 2., 3., 4., 5.],
                          "spot": [0., 1., np.nan, 3., 4.],
                          "roll_flag": [0, 0, 0, 1, 0]})
    result = keyed_lead_lag(frame, [1], frequency="daily", key_column="date",
                            futures_column="futures", spot_column="spot",
                            calendar_index=dates).iloc[0]
    assert result.candidate_pair_count == 4
    assert result.n == 3
    assert result.missing_pair_count == 1
    assert result.roll_pair_count == 1
    assert np.isclose(result.roll_pair_fraction, 1 / 3)
    # Filtering first must not turn July 24 into the predecessor of July 26.
    filtered = frame.loc[frame.spot.notna()]
    result = keyed_lead_lag(filtered, [1], frequency="daily", key_column="date",
                            futures_column="futures", spot_column="spot",
                            calendar_index=dates).iloc[0]
    assert result.n == 2
    assert result.missing_pair_count == 2


def test_monthly_keyed_lag_inserts_absent_month_and_rejects_duplicate_keys():
    frame = pd.DataFrame({"month": ["2023-09", "2023-11", "2023-12"],
                          "futures": [1., 2., 3.], "spot": [4., 5., 6.],
                          "roll_flag": [0, 1, 0]})
    result = keyed_lead_lag(frame, [1], frequency="monthly", key_column="month",
                            futures_column="futures", spot_column="spot").iloc[0]
    assert result.candidate_pair_count == 3  # September→October, etc.
    assert result.n == 1  # November→December only
    assert result.missing_pair_count == 2
    with pytest.raises(ValueError, match="unique"):
        keyed_lead_lag(pd.concat([frame, frame.iloc[[0]]]), [1], frequency="monthly",
                       key_column="month", futures_column="futures", spot_column="spot")
