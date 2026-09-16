"""Deterministic volume main contract and roll-safe return construction."""
from __future__ import annotations

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
