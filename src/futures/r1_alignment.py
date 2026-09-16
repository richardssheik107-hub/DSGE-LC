"""Date-keyed R1 spot/futures return definitions.

These functions do not select a main contract or alter the Phase 2I series.
They retain the full observed futures trading-day index, so a missing SMM
assessment cannot silently turn a multi-session move into a one-session pair.
"""
from __future__ import annotations

from bisect import bisect_left
from collections.abc import Iterable

import numpy as np
import pandas as pd


def _end_date(sample_end: str) -> pd.Timestamp:
    return pd.Period(sample_end, freq="M").end_time.normalize()


def _prepare_daily(
    frame: pd.DataFrame,
    required: set[str],
    *,
    analysis_start_date: str,
    sample_end: str,
    label: str,
) -> pd.DataFrame:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {sorted(missing)}")
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    result = result.loc[result.date.between(pd.Timestamp(analysis_start_date), _end_date(sample_end))]
    result = result.sort_values("date", kind="mergesort").reset_index(drop=True)
    if result.empty or result.date.isna().any() or result.date.duplicated().any():
        raise ValueError(f"{label} needs nonempty unique daily dates")
    return result


def _prepare_main(
    main_daily: pd.DataFrame, *, analysis_start_date: str, sample_end: str
) -> pd.DataFrame:
    main = _prepare_daily(
        main_daily,
        {"date", "main_close", "roll_safe_log_return", "switch_flag"},
        analysis_start_date=analysis_start_date,
        sample_end=sample_end,
        label="main_daily",
    )
    main["main_close"] = pd.to_numeric(main.main_close, errors="raise")
    main["roll_safe_log_return"] = pd.to_numeric(main.roll_safe_log_return, errors="raise")
    switches = pd.to_numeric(main.switch_flag, errors="raise")
    if not switches.dropna().isin([0, 1]).all():
        raise ValueError("main_daily switch_flag must be 0, 1, or missing")
    main["switch_flag"] = switches.fillna(0).astype(bool)
    # A lagged-volume choice can legitimately have no current close. Retain
    # that trading-day row as missing, rather than compressing the calendar.
    quoted = main.main_close.notna()
    if np.isinf(main.main_close.to_numpy(float)).any() or not main.loc[quoted, "main_close"].gt(0).all():
        raise ValueError("main_daily has invalid observed prices")
    if np.isinf(main.roll_safe_log_return.to_numpy(float)).any():
        raise ValueError("main_daily has infinite roll-safe returns")
    if "roll_reference_date" in main:
        main["roll_reference_date"] = pd.to_datetime(main.roll_reference_date, errors="coerce").dt.normalize()
    return main


def _prepare_spot(
    spot_daily: pd.DataFrame, *, analysis_start_date: str, sample_end: str
) -> pd.DataFrame:
    spot = _prepare_daily(
        spot_daily,
        {"date", "lc_spot"},
        analysis_start_date=analysis_start_date,
        sample_end=sample_end,
        label="spot_daily",
    )
    spot["lc_spot"] = pd.to_numeric(spot.lc_spot, errors="raise")
    if not (np.isfinite(spot.lc_spot).all() and spot.lc_spot.gt(0).all()):
        raise ValueError("spot_daily has invalid prices")
    return spot


def build_interval_audit(
    main_daily: pd.DataFrame,
    spot_daily: pd.DataFrame,
    *,
    analysis_start_date: str = "2023-07-21",
    sample_end: str = "2025-09",
) -> pd.DataFrame:
    """One row per observed futures session, with strictly matched daily returns.

    ``spot_observed_interval_log_return`` records a longer SMM gap separately.
    Only an exact previous/current futures-date SMM pair is placed in the main
    ``spot_log_return``/``futures_log_return`` columns.
    """
    main = _prepare_main(main_daily, analysis_start_date=analysis_start_date, sample_end=sample_end)
    spot = _prepare_spot(spot_daily, analysis_start_date=analysis_start_date, sample_end=sample_end)
    spot_prices = dict(zip(spot.date, spot.lc_spot))
    spot_dates = spot.date.tolist()
    future_position = {date: index for index, date in enumerate(main.date)}
    rows: list[dict[str, object]] = []
    for index, item in main.iterrows():
        end = item.date
        start = main.iloc[index - 1].date if index else pd.NaT
        end_seen = end in spot_prices
        start_seen = bool(index and start in spot_prices)
        previous_spot_pos = bisect_left(spot_dates, end) - 1
        previous_spot = spot_dates[previous_spot_pos] if previous_spot_pos >= 0 else pd.NaT
        observed_span = (index - future_position[previous_spot]
                         if end_seen and previous_spot in future_position else np.nan)
        observed_return = (float(np.log(spot_prices[end] / spot_prices[previous_spot]))
                           if end_seen and pd.notna(previous_spot) else np.nan)
        raw_future = float(item.roll_safe_log_return) if pd.notna(item.roll_safe_log_return) else np.nan
        reference_ok = ("roll_reference_date" not in main or
                        (index > 0 and item.roll_reference_date == start))
        futures_complete = bool(index and pd.notna(item.main_close) and
                                np.isfinite(raw_future) and reference_ok)
        if index == 0:
            reason = "INITIAL_NO_PREVIOUS_TRADING_DAY"
        elif not futures_complete:
            reason = "FUTURES_RETURN_INCOMPLETE"
        elif not end_seen:
            reason = "SPOT_END_MISSING"
        elif not start_seen:
            reason = ("SPOT_START_MISSING_MULTIDAY" if previous_spot in future_position
                      else "SPOT_INTERVAL_ENDPOINT_NOT_TRADING_DAY" if pd.notna(previous_spot)
                      else "SPOT_START_MISSING")
        else:
            reason = "ELIGIBLE_SINGLE_SESSION"
        eligible = reason == "ELIGIBLE_SINGLE_SESSION"
        rows.append({
            "date": end,
            "return_start_date": start,
            "return_end_date": end,
            "elapsed_trading_days": 1 if index else 0,
            "spot_observed_flag": bool(end_seen),
            "spot_start_observed_flag": bool(start_seen),
            "futures_complete_flag": futures_complete,
            "roll_flag": bool(item.switch_flag),
            "spot_observed_return_start_date": previous_spot,
            "spot_observed_elapsed_trading_days": observed_span,
            "spot_observed_interval_log_return": observed_return,
            "roll_safe_log_return_raw": raw_future,
            "spot_log_return": (float(np.log(spot_prices[end] / spot_prices[start]))
                                if eligible else np.nan),
            "futures_log_return": raw_future if eligible else np.nan,
            "eligibility_reason": reason,
        })
    return pd.DataFrame(rows)


def build_monthly_matched_eom(
    intervals: pd.DataFrame,
    main_daily: pd.DataFrame,
    spot_daily: pd.DataFrame,
    *,
    analysis_start_date: str = "2023-07-21",
    sample_end: str = "2025-09",
) -> pd.DataFrame:
    """Monthly endpoints shared by both markets; futures sum spans those dates."""
    main = _prepare_main(main_daily, analysis_start_date=analysis_start_date, sample_end=sample_end)
    spot = _prepare_spot(spot_daily, analysis_start_date=analysis_start_date, sample_end=sample_end)
    needed = {"date", "futures_complete_flag", "roll_safe_log_return_raw", "roll_flag"}
    if not needed.issubset(intervals.columns):
        raise ValueError(f"intervals missing columns: {sorted(needed - set(intervals.columns))}")
    intervals = intervals.copy()
    intervals["date"] = pd.to_datetime(intervals.date, errors="raise").dt.normalize()
    if (intervals.date.duplicated().any() or
            not intervals.date.sort_values().reset_index(drop=True).equals(main.date)):
        raise ValueError("intervals must contain the complete main_daily date index")
    intervals = intervals.sort_values("date", kind="mergesort").reset_index(drop=True)
    spot_prices = dict(zip(spot.date, spot.lc_spot))
    # A session with no selected-contract close remains in the trading index
    # but cannot serve as a price endpoint.
    future_dates = set(main.loc[main.main_close.notna(), "date"])
    spot_dates = set(spot.date)
    rows: list[dict[str, object]] = []
    previous_common = pd.NaT
    for period in pd.period_range(pd.Timestamp(analysis_start_date).to_period("M"),
                                  pd.Period(sample_end, freq="M"), freq="M"):
        f_dates = sorted(date for date in future_dates if date.to_period("M") == period)
        s_dates = sorted(date for date in spot_dates if date.to_period("M") == period)
        common_dates = sorted(set(f_dates) & set(s_dates))
        current_common = common_dates[-1] if common_dates else pd.NaT
        future_last = f_dates[-1] if f_dates else pd.NaT
        spot_last = s_dates[-1] if s_dates else pd.NaT
        adjusted = bool(pd.notna(current_common) and
                        (current_common != future_last or current_common != spot_last))
        if pd.isna(previous_common):
            window = intervals.iloc[0:0]
        elif pd.isna(current_common):
            window = intervals.iloc[0:0]
        else:
            window = intervals.loc[intervals.date.gt(previous_common) & intervals.date.le(current_common)]
        expected_count = (int(main.date.gt(previous_common).mul(main.date.le(current_common)).sum())
                          if pd.notna(previous_common) and pd.notna(current_common) else 0)
        complete = bool(expected_count > 0 and len(window) == expected_count and
                        window.futures_complete_flag.fillna(False).astype(bool).all() and
                        np.isfinite(window.roll_safe_log_return_raw.to_numpy(float)).all())
        if period == pd.Timestamp(analysis_start_date).to_period("M"):
            reason = "FIRST_MONTH_NO_PREVIOUS_ENDPOINT"
        elif pd.isna(previous_common):
            reason = "NO_COMMON_ENDPOINT_PREVIOUS_MONTH"
        elif pd.isna(current_common):
            reason = "NO_COMMON_ENDPOINT_CURRENT_MONTH"
        elif not complete:
            reason = "FUTURES_INTERVAL_INCOMPLETE"
        else:
            reason = "ELIGIBLE_COMMON_ENDPOINT"
        eligible = reason == "ELIGIBLE_COMMON_ENDPOINT"
        rows.append({
            "month": str(period),
            "date": current_common,
            "futures_last_date": future_last,
            "spot_last_date": spot_last,
            "common_endpoint_date": current_common,
            "endpoint_adjusted_flag": adjusted,
            "return_start_date": previous_common,
            "return_end_date": current_common,
            "elapsed_trading_days": len(window) if eligible else np.nan,
            "futures_complete_flag": complete,
            "roll_flag": bool(window.roll_flag.fillna(False).astype(bool).any()) if len(window) else False,
            "switch_count": int(window.roll_flag.fillna(False).astype(bool).sum()) if len(window) else 0,
            "spot_log_return": (float(np.log(spot_prices[current_common] / spot_prices[previous_common]))
                                if eligible else np.nan),
            "futures_log_return": (float(window.roll_safe_log_return_raw.sum())
                                   if eligible else np.nan),
            "eligibility_reason": reason,
        })
        previous_common = current_common
    return pd.DataFrame(rows)


def build_monthly_matched_mean(
    main_daily: pd.DataFrame,
    spot_daily: pd.DataFrame,
    *,
    analysis_start_date: str = "2023-07-21",
    sample_end: str = "2025-09",
    partial_listing_month: str = "2023-07",
) -> pd.DataFrame:
    """Comparable monthly means, with incomplete/partial months kept as NA rows."""
    main = _prepare_main(main_daily, analysis_start_date=analysis_start_date, sample_end=sample_end)
    spot = _prepare_spot(spot_daily, analysis_start_date=analysis_start_date, sample_end=sample_end)
    rows: list[dict[str, object]] = []
    previous: dict[str, object] | None = None
    for period in pd.period_range(pd.Timestamp(analysis_start_date).to_period("M"),
                                  pd.Period(sample_end, freq="M"), freq="M"):
        f = main.loc[main.date.dt.to_period("M").eq(period)]
        s = spot.loc[spot.date.dt.to_period("M").eq(period)]
        f_dates, s_dates = set(f.date), set(s.date)
        missing_spot = len(f_dates - s_dates)
        extra_spot = len(s_dates - f_dates)
        if str(period) == partial_listing_month:
            coverage = "PARTIAL_LISTING_MONTH"
        elif not len(f):
            coverage = "NO_FUTURES_DAYS"
        elif not len(s):
            coverage = "NO_SPOT_QUOTES"
        elif f.main_close.isna().any():
            coverage = "FUTURES_PRICE_MISSING"
        elif missing_spot or extra_spot:
            coverage = "NONCOMPARABLE_TRADING_DATES"
        else:
            coverage = "COMPLETE_COMPARABLE_MONTH"
        full = coverage == "COMPLETE_COMPARABLE_MONTH"
        f_mean = float(f.main_close.mean()) if len(f) else np.nan
        s_mean = float(s.lc_spot.mean()) if len(s) else np.nan
        current_switch_count = int(pd.to_numeric(f.switch_flag, errors="raise").sum()) if len(f) else 0
        if previous is None:
            reason = "NO_PREVIOUS_MONTH"
        elif not full:
            reason = "CURRENT_MONTH_INCOMPLETE"
        elif not previous["full_comparable_month"]:
            reason = "PREVIOUS_MONTH_INCOMPLETE"
        else:
            reason = "ELIGIBLE_COMPLETE_MONTH_MEANS"
        eligible = reason == "ELIGIBLE_COMPLETE_MONTH_MEANS"
        rows.append({
            "month": str(period),
            "date": period.to_timestamp(how="end").normalize(),
            "trading_days": len(f),
            "spot_quote_days": len(s),
            "common_quote_days": len(f_dates & s_dates),
            "spot_missing_futures_days": missing_spot,
            "spot_extra_nonfutures_days": extra_spot,
            "coverage_status": coverage,
            "full_comparable_month": full,
            "futures_mean": f_mean,
            "spot_mean": s_mean,
            "switch_count": current_switch_count,
            "roll_flag": bool(current_switch_count),
            "switch_window_flag": bool(current_switch_count or
                                       (previous["switch_count"] if previous else 0)),
            "futures_log_return": (float(np.log(f_mean / previous["futures_mean"]))
                                   if eligible else np.nan),
            "spot_log_return": (float(np.log(s_mean / previous["spot_mean"]))
                                if eligible else np.nan),
            "eligibility_reason": reason,
        })
        previous = {"full_comparable_month": full, "futures_mean": f_mean,
                    "spot_mean": s_mean, "switch_count": current_switch_count}
    return pd.DataFrame(rows)


def keyed_lead_lag(
    frame: pd.DataFrame,
    lags: Iterable[int],
    *,
    frequency: str,
    key_column: str,
    futures_column: str,
    spot_column: str,
    switch_column: str | None = "roll_flag",
    calendar_index: Iterable[object] | None = None,
) -> pd.DataFrame:
    """Cross-correlations on complete session/month keys, never compressed rows.

    For daily data, pass the full verified futures trading calendar when the
    supplied frame may have been filtered. Monthly missing months are inserted
    automatically between the first and last observed month.
    """
    required = {key_column, futures_column, spot_column}
    if switch_column is not None:
        required.add(switch_column)
    if not required.issubset(frame.columns):
        raise ValueError(f"lead-lag frame missing columns: {sorted(required - set(frame.columns))}")
    is_monthly = frequency.lower().startswith("month")
    is_daily = frequency.lower().startswith("dai")
    if not (is_monthly or is_daily):
        raise ValueError("frequency must be daily or monthly")
    source = frame.copy()
    if is_monthly:
        source.index = pd.PeriodIndex(source[key_column], freq="M")
    else:
        source.index = pd.DatetimeIndex(pd.to_datetime(source[key_column], errors="raise")).normalize()
    if source.index.has_duplicates or source.index.hasnans or source.empty:
        raise ValueError("lead-lag keys must be nonempty, unique and valid")
    if calendar_index is None:
        calendar = (pd.period_range(source.index.min(), source.index.max(), freq="M")
                    if is_monthly else source.index.sort_values())
    elif is_monthly:
        calendar = pd.PeriodIndex(calendar_index, freq="M")
    else:
        calendar = pd.DatetimeIndex(pd.to_datetime(list(calendar_index), errors="raise")).normalize()
    if calendar.has_duplicates or calendar.hasnans or len(calendar) == 0:
        raise ValueError("calendar_index must have unique valid keys")
    calendar = calendar.sort_values()
    if not source.index.isin(calendar).all():
        raise ValueError("frame contains keys outside calendar_index")
    expanded = source.reindex(calendar)
    futures = pd.to_numeric(expanded[futures_column], errors="raise").to_numpy(float)
    spot = pd.to_numeric(expanded[spot_column], errors="raise").to_numpy(float)
    if np.isinf(futures).any() or np.isinf(spot).any():
        raise ValueError("infinite lead-lag return")
    switches = (np.zeros(len(calendar), dtype=bool) if switch_column is None else
                pd.to_numeric(expanded[switch_column].fillna(0), errors="raise").to_numpy(float) != 0)
    rows: list[dict[str, object]] = []
    for raw_lag in lags:
        if not isinstance(raw_lag, (int, np.integer)):
            raise ValueError("lags must be integers")
        lag = int(raw_lag)
        source_positions = np.arange(len(calendar))
        target_positions = source_positions + lag
        within = (target_positions >= 0) & (target_positions < len(calendar))
        source_positions = source_positions[within]
        target_positions = target_positions[within]
        valid = np.isfinite(futures[source_positions]) & np.isfinite(spot[target_positions])
        candidate_count = len(source_positions)
        n = int(valid.sum())
        x = futures[source_positions[valid]]
        y = spot[target_positions[valid]]
        if n >= 3 and np.ptp(x) > 0 and np.ptp(y) > 0:
            pearson = float(np.corrcoef(x, y)[0, 1])
            spearman = float(pd.Series(x).corr(pd.Series(y), method="spearman"))
        else:
            pearson = spearman = np.nan
        roll_count = int(switches[source_positions[valid]].sum())
        rows.append({
            "frequency": frequency,
            "lag_spot_periods": lag,
            "n": n,
            "pearson": pearson,
            "spearman": spearman,
            "candidate_pair_count": candidate_count,
            "missing_pair_count": candidate_count - n,
            "missing_pair_fraction": ((candidate_count - n) / candidate_count
                                      if candidate_count else np.nan),
            "roll_pair_count": roll_count,
            "roll_pair_fraction": roll_count / n if n else np.nan,
            "lag_convention": "positive=futures_t_vs_spot_t_plus_lag",
        })
    return pd.DataFrame(rows)
