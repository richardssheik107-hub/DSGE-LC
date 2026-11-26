"""Build the licensed local core panel from canonical industry series and FX."""
from __future__ import annotations

import pandas as pd

from industry_common import PROCESSED_DIR, ROOT, write_csv


def longest_complete_run(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    complete = frame.loc[frame[columns].notna().all(axis=1)].copy()
    complete["period"] = pd.PeriodIndex(complete.month, freq="M")
    complete = complete.sort_values("period")
    complete["group"] = (complete.period.astype("int64").diff().fillna(1).ne(1)).cumsum()
    group = complete.groupby("group").size().idxmax()
    return complete.loc[complete.group.eq(group)].drop(columns=["period", "group"])


def main() -> None:
    spot = pd.read_csv(PROCESSED_DIR / "lc_spot_monthly.csv", na_values=["NA"])[["month", "lc_spot_mean"]]
    output = pd.read_csv(PROCESSED_DIR / "lc_output_monthly.csv", na_values=["NA"])[["month", "lc_output_total"]]
    spod = pd.read_csv(PROCESSED_DIR / "spodumene_price_monthly.csv", na_values=["NA"])[["month", "spodumene_price_mean"]]
    battery = pd.read_csv(PROCESSED_DIR / "battery_install_monthly.csv", na_values=["NA"])[["month", "battery_install_total", "battery_install_lfp", "battery_install_ncm"]]
    fx = pd.read_csv(ROOT / "data" / "processed" / "public_monthly_panel.csv", na_values=["NA"])[["month", "usd_cny_mean"]]
    panel = spot.merge(output, on="month", how="outer").merge(spod, on="month", how="outer").merge(battery, on="month", how="outer").merge(fx, on="month", how="outer")
    panel = panel.rename(columns={"lc_spot_mean": "lc_spot", "spodumene_price_mean": "spodumene_price", "battery_install_total": "battery_install"})
    core = ["lc_spot", "lc_output_total", "spodumene_price", "usd_cny_mean", "battery_install"]
    panel = longest_complete_run(panel, core)
    panel["spodumene_cny_t"] = panel.spodumene_price * panel.usd_cny_mean
    order = ["month", "lc_spot", "lc_output_total", "spodumene_price", "usd_cny_mean", "spodumene_cny_t", "battery_install", "battery_install_lfp", "battery_install_ncm"]
    write_csv(panel[order], ROOT / "data" / "processed" / "core_monthly_panel.csv")


if __name__ == "__main__":
    main()
