"""Deterministic volume main contract and roll-safe return construction."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd


def contract_delivery_month(contract: str) -> pd.Period:
    code = str(contract).upper().strip()
    if len(code) != 6 or not code.startswith("LC") or not code[2:].isdigit():
        raise ValueError(f"invalid LC contract code: {contract}")
    return pd.Period(f"20{code[2:4]}-{code[4:6]}", freq="M")


def _choose_for_day(group: pd.DataFrame) -> pd.Series:
    date = pd.Timestamp(group.name)
    valid = group.loc[
        group.daily_close.notna()
        & group.daily_close.gt(0)
        & group.daily_volume.notna()
        & group.daily_volume.gt(0)
    ].copy()
    if valid.empty:
        raise ValueError(f"no eligible contract on {date.date()}")
    current_month = date.to_period("M")
    valid["delivery_period"] = valid.contract.map(contract_delivery_month)
    valid["delivery_not_expired"] = valid.delivery_period.ge(current_month)
    valid["delivery_distance"] = valid.delivery_period.map(lambda value: abs(value.ordinal - current_month.ordinal))
    valid = valid.sort_values(
        ["daily_volume", "delivery_not_expired", "delivery_distance", "delivery_period", "contract"],
        ascending=[False, False, True, True, True],
        kind="mergesort",
    )
    chosen = valid.iloc[0]
    total_volume = float(valid.daily_volume.sum())
    return pd.Series({
        "main_contract": chosen.contract,
        "main_close": float(chosen.daily_close),
        "main_volume": float(chosen.daily_volume),
        "total_market_volume": total_volume,
        "volume_share": float(chosen.daily_volume / total_volume),
    })


def select_daily_main_contract(
    daily_contracts: pd.DataFrame,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    frame = daily_contracts.copy()
    frame["date"] = pd.to_datetime(frame.date)
    if start_date is not None:
        frame = frame.loc[frame.date.ge(pd.Timestamp(start_date))]
    if end_date is not None:
        frame = frame.loc[frame.date.le(pd.Period(end_date, freq="M").end_time.normalize())]
    eligible_dates = frame.loc[frame.daily_close.gt(0) & frame.daily_volume.gt(0), "date"].drop_duplicates()
    if eligible_dates.empty:
        raise ValueError("no eligible trading days in requested window")
    selected = frame.groupby("date", sort=True, group_keys=False).apply(_choose_for_day, include_groups=False).reset_index()
    selected["switch_flag"] = selected.main_contract.ne(selected.main_contract.shift()).astype(int)
    selected.loc[selected.index[0], "switch_flag"] = 0
    if not selected.volume_share.between(0, 1).all():
        raise ValueError("main-contract volume share is outside [0,1]")
    return selected


def select_lagged_volume_main_contract(
    daily_contracts: pd.DataFrame,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Select day ``t``'s contract using only ``t-1`` volume and known expiry.

    Every date present in the supplied verified trading-day panel is retained,
    even when no contract or price is eligible.  The contract decision is made
    *before* looking up day ``t``'s close/volume.  The close is used solely to
    value the chosen contract; no ex-post replacement is allowed.  A roll-safe
    return always uses the chosen contract's own ``t-1`` close, including on a
    switch.  This is a timing audit, not a claim of executable close-to-close
    strategy returns after observing the prior close's final volume.

    Tie-break: highest prior volume, nearest nonexpired delivery month, then
    lexicographically smallest normalized contract code.  ``end_date`` may be
    an exact date or ``YYYY-MM`` (inclusive calendar-month end).
    """
    required = {"date", "contract", "daily_close", "daily_volume"}
    if not required.issubset(daily_contracts.columns):
        raise ValueError(f"daily contract columns missing: {sorted(required - set(daily_contracts.columns))}")
    frame = daily_contracts.loc[:, ["date", "contract", "daily_close", "daily_volume"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    if frame.date.isna().any():
        raise ValueError("invalid trading date")
    frame["contract"] = frame.contract.astype(str).str.upper().str.strip()
    frame["daily_close"] = pd.to_numeric(frame.daily_close, errors="coerce")
    frame["daily_volume"] = pd.to_numeric(frame.daily_volume, errors="coerce")
    if frame.duplicated(["date", "contract"]).any():
        raise ValueError("duplicate date/contract rows in daily panel")
    if frame.empty:
        raise ValueError("empty daily contract panel")
    delivery = {code: contract_delivery_month(code) for code in frame.contract.unique()}
    groups = {date: group.set_index("contract", drop=False)
              for date, group in frame.groupby("date", sort=True)}
    dates = sorted(groups)
    selected: list[dict[str, object]] = []
    previous_main: str | None = None
    previous_main_close = np.nan
    for index, date in enumerate(dates):
        prior_date = dates[index - 1] if index else pd.NaT
        current = groups[date]
        observed_volume = current.daily_volume.where(current.daily_volume.gt(0)).sum(min_count=1)
        today_total_volume = float(observed_volume) if pd.notna(observed_volume) else np.nan
        main: str | None = None
        prior_volume = np.nan
        prior_total_volume = np.nan
        prior_candidates = 0
        reference_close = np.nan
        today_close = np.nan
        today_volume = np.nan
        current_row_present = False
        if pd.isna(prior_date):
            selection_status = "NO_PRIOR_VOLUME"
        else:
            prior = groups[prior_date]
            candidates = prior.loc[prior.daily_volume.gt(0) & prior.daily_volume.notna()].copy()
            candidates = candidates.loc[
                candidates.contract.map(delivery).ge(date.to_period("M"))
            ].copy()
            prior_candidates = len(candidates)
            if not prior_candidates:
                selection_status = "NO_ELIGIBLE_PRIOR_CONTRACT"
            else:
                candidates["delivery_period"] = candidates.contract.map(delivery)
                candidates["delivery_distance"] = candidates.delivery_period.map(
                    lambda period: period.ordinal - date.to_period("M").ordinal)
                candidates = candidates.reset_index(drop=True).sort_values(
                    ["daily_volume", "delivery_distance", "contract"],
                    ascending=[False, True, True], kind="mergesort")
                chosen = candidates.iloc[0]
                main = str(chosen.contract)
                prior_volume = float(chosen.daily_volume)
                prior_total_volume = float(candidates.daily_volume.sum())
                previous_close = chosen.daily_close
                if pd.notna(previous_close) and np.isfinite(previous_close) and previous_close > 0:
                    reference_close = float(previous_close)
                selection_status = "SELECTED"
                current_row_present = main in current.index
                if current_row_present:
                    quote = current.loc[main]
                    today_close = float(quote.daily_close) if pd.notna(quote.daily_close) else np.nan
                    today_volume = float(quote.daily_volume) if pd.notna(quote.daily_volume) else np.nan
        close_available = bool(np.isfinite(today_close) and today_close > 0)
        reference_available = bool(np.isfinite(reference_close) and reference_close > 0)
        switch_assessable = bool(main is not None and previous_main is not None)
        switch = int(switch_assessable and main != previous_main)
        roll_return = np.nan
        raw_return = np.nan
        if close_available and np.isfinite(previous_main_close) and previous_main_close > 0:
            raw_return = float(np.log(today_close / previous_main_close))
        if main is None:
            return_status = selection_status
        elif not current_row_present:
            return_status = "SELECTED_CONTRACT_NOT_QUOTED_TODAY"
        elif not close_available:
            return_status = "SELECTED_CONTRACT_CLOSE_MISSING_OR_NONPOSITIVE"
        elif not reference_available:
            return_status = ("SWITCH_NEW_CONTRACT_REFERENCE_MISSING" if switch else
                             "SELECTED_CONTRACT_PRIOR_CLOSE_MISSING")
        else:
            roll_return = float(np.log(today_close / reference_close))
            return_status = ("SWITCH_NEW_CONTRACT_REFERENCE" if switch else
                             "SAME_CONTRACT" if switch_assessable else
                             "PRIOR_MAIN_UNAVAILABLE_VALID_REFERENCE")
        selected.append({
            "date": date,
            "return_start_date": prior_date,
            "return_end_date": date,
            "elapsed_trading_days": 1 if pd.notna(prior_date) else np.nan,
            "main_contract": main,
            "main_close": today_close,
            "main_volume": today_volume,
            "total_market_volume": today_total_volume,
            "volume_share": (float(today_volume / today_total_volume)
                             if np.isfinite(today_volume) and np.isfinite(today_total_volume)
                             and today_total_volume > 0 else np.nan),
            "selection_rule": "LAGGED_VOLUME_MAIN",
            "selection_status": selection_status,
            "selection_asof_date": prior_date,
            "selection_information_date": prior_date,
            "prior_trading_date_present": bool(pd.notna(prior_date)),
            "known_volume": prior_volume,
            "prior_selection_volume": prior_volume,
            "prior_total_eligible_volume": prior_total_volume,
            "prior_volume_share": (float(prior_volume / prior_total_volume)
                                   if np.isfinite(prior_total_volume) and prior_total_volume > 0
                                   else np.nan),
            "prior_candidate_count": prior_candidates,
            "selection_tie_break": "PRIOR_VOLUME_DESC;NEAREST_VALID_DELIVERY;CONTRACT_ASC",
            "contract_validity_rule": "DELIVERY_MONTH_NOT_BEFORE_TARGET_MONTH",
            "selected_current_row_present": current_row_present,
            "selected_current_close_available": close_available,
            "prior_main_contract": previous_main,
            "switch_assessable": switch_assessable,
            "switch_flag": switch,
            "roll_flag": switch,
            "roll_reference_date": prior_date,
            "roll_reference_close": reference_close,
            "roll_safe_log_return": roll_return,
            "raw_main_close_log_change": raw_return,
            "roll_return_status": return_status,
            "futures_complete_flag": bool(np.isfinite(roll_return)),
            "eligibility_reason": "ELIGIBLE" if np.isfinite(roll_return) else return_status,
        })
        previous_main = main
        previous_main_close = today_close
    result = pd.DataFrame(selected)
    if start_date is not None:
        result = result.loc[result.date.ge(pd.Timestamp(start_date).normalize())]
    if end_date is not None:
        end = (pd.Period(end_date, freq="M").end_time.normalize()
               if re.fullmatch(r"\d{4}-\d{2}", str(end_date))
               else pd.Timestamp(end_date).normalize())
        result = result.loc[result.date.le(end)]
    if result.empty:
        raise ValueError("no verified trading dates in requested window")
    return result.reset_index(drop=True)


def add_roll_safe_returns(main_daily: pd.DataFrame, daily_contracts: pd.DataFrame) -> pd.DataFrame:
    main = main_daily.copy().sort_values("date", kind="mergesort").reset_index(drop=True)
    panel = daily_contracts.copy()
    panel["date"] = pd.to_datetime(panel.date)
    close_lookup = panel.set_index(["date", "contract"]).daily_close
    roll_return = np.full(len(main), np.nan)
    raw_return = np.full(len(main), np.nan)
    reference_close = np.full(len(main), np.nan)
    reference_date: list[pd.Timestamp | pd.NaT] = [pd.NaT] * len(main)
    status = ["INITIAL"] * len(main)
    for index in range(1, len(main)):
        current = main.iloc[index]
        previous = main.iloc[index - 1]
        if current.main_close <= 0 or previous.main_close <= 0:
            raise ValueError("nonpositive main-contract close")
        raw_return[index] = np.log(current.main_close / previous.main_close)
        reference_date[index] = previous.date
        if current.main_contract == previous.main_contract:
            reference_close[index] = previous.main_close
            roll_return[index] = raw_return[index]
            status[index] = "SAME_CONTRACT"
        else:
            key = (previous.date, current.main_contract)
            prior_new_close = close_lookup.get(key, np.nan)
            if pd.notna(prior_new_close) and prior_new_close > 0:
                reference_close[index] = float(prior_new_close)
                roll_return[index] = np.log(current.main_close / prior_new_close)
                status[index] = "SWITCH_NEW_CONTRACT_REFERENCE"
            else:
                status[index] = "SWITCH_REFERENCE_MISSING"
    main["roll_reference_date"] = reference_date
    main["roll_reference_close"] = reference_close
    main["roll_safe_log_return"] = roll_return
    main["raw_main_close_log_change"] = raw_return
    main["roll_return_status"] = status
    return main


def aggregate_main_monthly(main_daily: pd.DataFrame) -> pd.DataFrame:
    frame = main_daily.copy().sort_values("date", kind="mergesort").reset_index(drop=True)
    frame["month"] = frame.date.dt.to_period("M").astype(str)
    first_global_date = frame.date.iloc[0]
    rows: list[dict[str, object]] = []
    for month, group in frame.groupby("month", sort=True):
        group = group.sort_values("date", kind="mergesort")
        expected = group.loc[group.date.ne(first_global_date), "roll_safe_log_return"]
        observed_period_return = float(expected.sum()) if len(expected) and expected.notna().all() else np.nan
        partial_listing_month = bool(group.date.iloc[0] == first_global_date and first_global_date.day > 7)
        monthly_return = np.nan if partial_listing_month else observed_period_return
        rows.append({
            "month": month,
            "first_trading_date": group.date.iloc[0],
            "last_trading_date": group.date.iloc[-1],
            "coverage_status": "PARTIAL_LISTING_MONTH" if partial_listing_month else "OBSERVED_TRADING_MONTH",
            "mean_main_close": float(group.main_close.mean()),
            "month_end_main_close": float(group.main_close.iloc[-1]),
            "monthly_roll_safe_log_return": monthly_return,
            "observed_period_roll_safe_log_return": observed_period_return,
            "monthly_volume": float(group.main_volume.sum()),
            "total_market_volume": float(group.total_market_volume.sum()),
            "main_contract_at_month_end": group.main_contract.iloc[-1],
            "switch_count": int(group.switch_flag.sum()),
            "trading_days": int(len(group)),
            "missing_roll_returns": int(expected.isna().sum()),
        })
    return pd.DataFrame(rows)
