"""Strict temporal splits and conservative information-set construction."""
from __future__ import annotations

import pandas as pd


SPECIFICATIONS = {
    "SPEC_A_DLOG4": ["spot_dlog", "ore_cny_dlog", "output_dlog", "battery_dlog"],
    "SPEC_B_MIXED4": ["spot_dlog", "ore_cny_dlog", "output_yoy_log", "battery_yoy_log"],
    "SPEC_C_FX5": ["spot_dlog", "ore_cny_dlog", "output_dlog", "battery_dlog", "fx_dlog"],
}

SOURCE_COLUMNS = {
    "spot_dlog": "lc_spot_dlog",
    "ore_cny_dlog": "spodumene_cny_dlog",
    "output_dlog": "lc_output_dlog",
    "battery_dlog": "battery_install_dlog",
    "output_yoy_log": "lc_output_yoy_log",
    "battery_yoy_log": "battery_install_yoy_log",
    "fx_dlog": "usd_cny_dlog",
}


def build_information_set(data: pd.DataFrame, specification: str, information_set: str,
                          release_lag_output: int = 1, release_lag_battery: int = 1) -> pd.DataFrame:
    columns = SPECIFICATIONS[specification]
    frame = pd.DataFrame({"month": data.month.copy()})
    for name in columns:
        values = data[SOURCE_COLUMNS[name]].copy()
        if information_set == "RELEASE_SAFE_APPROXIMATION":
            if name.startswith("output_"):
                values = values.shift(release_lag_output)
            elif name.startswith("battery_"):
                values = values.shift(release_lag_battery)
        elif information_set != "MONTH_INDEX_IDEALIZED":
            raise ValueError(f"Unknown information set: {information_set}")
        frame[name] = values
    return frame


def forecast_origins(data: pd.DataFrame, initial_train_months: int, horizons: list[int],
                     train_start_index: int = 0) -> list[int]:
    """Return origin indexes; first origin is the final initial-training month."""
    first_origin = initial_train_months - 1
    if first_origin < train_start_index:
        raise ValueError("initial training window ends before training start")
    return list(range(first_origin, len(data) - min(horizons)))


def training_slice(frame: pd.DataFrame, origin_index: int, train_start_index: int = 0) -> pd.DataFrame:
    """No row later than origin can enter estimation or scaling."""
    return frame.iloc[train_start_index:origin_index + 1].dropna().copy()
