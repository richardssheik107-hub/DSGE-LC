"""Normalize interim industry series and aggregate daily/weekly observations."""
from __future__ import annotations

import numpy as np
import pandas as pd

from industry_common import INTERIM_DIR, PROCESSED_DIR, write_csv


def aggregate_price(path, value: str, prefix: str) -> pd.DataFrame:
    frame = pd.read_csv(path, na_values=["NA"])
    frame["date"] = pd.to_datetime(frame.date)
    valid = frame.loc[frame[value].notna()].copy().sort_values("date")
    valid["month"] = valid.date.dt.to_period("M")
    grouped = valid.groupby("month")[value]
    monthly = grouped.agg(["mean", "median", "count"]).rename(
        columns={"mean": f"{prefix}_mean", "median": f"{prefix}_median", "count": "observed_days"}
    )
    monthly[f"{prefix}_eom"] = valid.groupby("month").tail(1).set_index("month")[value]
    counts = monthly.observed_days.astype(float)
    expected = []
    for idx in range(len(monthly)):
        history = counts.iloc[max(0, idx - 12):idx]
        expected.append(float(history.median()) if len(history) else float(counts.iloc[idx]))
    monthly["expected_quote_days"] = expected
    monthly["coverage_ratio"] = (monthly.observed_days / monthly.expected_quote_days).clip(upper=1.0)
    monthly["quality_flag"] = "OK"
    if len(monthly):
        last = monthly.index[-1]
        if monthly.loc[last, "coverage_ratio"] < 0.75:
            monthly.loc[last, "quality_flag"] = "PARTIAL_MONTH"
    monthly = monthly.reset_index()
    monthly["month"] = monthly.month.astype(str)
    monthly["source"] = "SMM"
    monthly = monthly.loc[monthly.quality_flag.ne("PARTIAL_MONTH")].copy()
    return monthly


def normalize_monthly() -> None:
    spot = aggregate_price(INTERIM_DIR / "lc_spot_daily.csv", "lc_spot", "lc_spot")
    write_csv(spot, PROCESSED_DIR / "lc_spot_monthly.csv")
    spod = aggregate_price(INTERIM_DIR / "spodumene_price_daily.csv", "spodumene_price", "spodumene_price")
    write_csv(spod, PROCESSED_DIR / "spodumene_price_monthly.csv")

    output = pd.read_csv(INTERIM_DIR / "lc_output_monthly_raw.csv", na_values=["NA"])
    output = output.sort_values("month").drop_duplicates("month", keep="last")
    route_cols = ["lc_output_brine", "lc_output_lepidolite", "lc_output_spodumene"]
    output["route_sum"] = output[route_cols].sum(axis=1, min_count=len(route_cols))
    output["route_difference"] = output.lc_output_total - output.route_sum
    output["route_difference_pct"] = output.route_difference / output.lc_output_total.replace(0, np.nan)
    output["quality_flag"] = np.where(output.lc_output_total.ge(0), "OK", "NEGATIVE_REVIEW")
    write_csv(output, PROCESSED_DIR / "lc_output_monthly.csv")

    battery = pd.read_csv(INTERIM_DIR / "battery_install_monthly_raw.csv", na_values=["NA"])
    battery = battery.sort_values("month").drop_duplicates("month", keep="last")
    battery["battery_install_chemistry_sum"] = battery[["battery_install_lfp", "battery_install_ncm"]].sum(axis=1, min_count=2)
    battery["chemistry_difference"] = battery.battery_install_total - battery.battery_install_chemistry_sum
    battery["chemistry_difference_pct"] = battery.chemistry_difference / battery.battery_install_total.replace(0, np.nan)
    battery["quality_flag"] = np.where(battery.battery_install_total.ge(0), "OK", "NEGATIVE_REVIEW")
    write_csv(battery, PROCESSED_DIR / "battery_install_monthly.csv")

    inventory = pd.read_csv(INTERIM_DIR / "lc_inventory_weekly_raw.csv", na_values=["NA"])
    inventory = inventory.sort_values("date").drop_duplicates("date", keep="last")
    inventory["quality_flag"] = "OK"
    write_csv(inventory, PROCESSED_DIR / "lc_inventory_weekly.csv")
    inventory["date"] = pd.to_datetime(inventory.date)
    inventory["month"] = inventory.date.dt.to_period("M").astype(str)
    inv_cols = ["lc_inventory_total", "lc_inventory_smelter", "lc_inventory_downstream", "lc_inventory_other"]
    means = inventory.groupby("month")[inv_cols].mean().add_suffix("_mean")
    eom = inventory.groupby("month").tail(1).set_index("month")[inv_cols].add_suffix("_eom")
    inv_monthly = means.join(eom).reset_index()
    inv_monthly["source"] = "SMM"
    inv_monthly["unit"] = "metric tons"
    write_csv(inv_monthly, PROCESSED_DIR / "lc_inventory_monthly.csv")

    costs = pd.read_csv(INTERIM_DIR / "lc_cost_margin_daily_raw.csv", na_values=["NA"])
    costs["date"] = pd.to_datetime(costs.date)
    value_cols = ["lc_cost_lepidolite", "lc_cost_spodumene", "lc_margin_lepidolite", "lc_margin_spodumene"]
    weekly = costs.set_index("date")[value_cols].resample("W-FRI").mean().dropna(how="all").reset_index()
    weekly["date"] = weekly.date.dt.strftime("%Y-%m-%d")
    weekly["source"] = "SMM"
    weekly["unit"] = "CNY/t lithium carbonate"
    write_csv(weekly, PROCESSED_DIR / "lc_cost_margin_weekly.csv")
    costs["month"] = costs.date.dt.to_period("M").astype(str)
    cost_monthly = costs.groupby("month")[value_cols].mean().reset_index()
    cost_monthly["source"] = "SMM"
    cost_monthly["unit"] = "CNY/t lithium carbonate"
    write_csv(cost_monthly, PROCESSED_DIR / "lc_cost_margin_monthly.csv")

    trade = pd.read_csv(INTERIM_DIR / "lc_trade_monthly_raw.csv", na_values=["NA"])
    write_csv(trade.sort_values("month"), PROCESSED_DIR / "lc_trade_monthly_industry.csv")
    concentrate = pd.read_csv(INTERIM_DIR / "lithium_concentrate_import_monthly_raw.csv", na_values=["NA"])
    write_csv(concentrate.sort_values("month"), PROCESSED_DIR / "lithium_concentrate_import_monthly.csv")


if __name__ == "__main__":
    normalize_monthly()
