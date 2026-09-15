"""Leakage-safe measurement construction and coverage metadata."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


PRIMARY_COLUMNS = {
    "spot": "lc_spot_dlog", "ore_cost": "spodumene_cny_dlog",
    "output": "lc_output_yoy_log", "battery": "battery_install_yoy_log",
}
SECONDARY_COLUMNS = {
    "spot": "lc_spot_dlog", "ore_cost": "spodumene_cny_dlog",
    "output": "lc_output_dlog", "battery": "battery_install_dlog",
}


def _zscore(series: pd.Series) -> pd.Series:
    sd = series.std(ddof=1)
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("measurement has no finite variation")
    return (series - series.mean()) / sd


def load_frozen_panel(path: str | Path, sample_end: str = "2025-09") -> pd.DataFrame:
    frame = pd.read_csv(path)
    if frame["month"].max() > sample_end:
        frame = frame.loc[frame["month"].le(sample_end)].copy()
    if frame["month"].min() < "2020-01" or frame["month"].max() != sample_end:
        raise ValueError("unexpected Data Freeze v1 boundary")
    forbidden = [c for c in frame if "v2" in c.lower() or "candidate" in c.lower()]
    if forbidden:
        raise ValueError(f"future/candidate columns forbidden: {forbidden}")
    return frame


def build_measurements(frame: pd.DataFrame, specification: str) -> pd.DataFrame:
    mapping = PRIMARY_COLUMNS if specification == "OBS_MIXED4" else SECONDARY_COLUMNS if specification == "OBS_DLOG_MOY4" else None
    if mapping is None:
        raise KeyError(specification)
    out = pd.DataFrame({"month": frame["month"]})
    for label, column in mapping.items():
        values = frame[column].astype(float)
        if specification == "OBS_DLOG_MOY4":
            calendar_month = pd.PeriodIndex(frame["month"], freq="M").month
            values = values - values.groupby(calendar_month).transform("mean")
        out[label] = _zscore(values)
    return out.dropna().reset_index(drop=True)


def measurement_coverage(measurements: pd.DataFrame, name: str) -> dict[str, object]:
    return {"measurement": name, "start": measurements.month.iloc[0], "end": measurements.month.iloc[-1], "n": len(measurements), "missing": int(measurements.isna().sum().sum())}


def margin_proxy(frame: pd.DataFrame) -> pd.Series:
    """Dimensionless relative spot/cost environment; never interpreted as profit."""
    return _zscore(frame["lc_spot_log"]) - _zscore(frame["spodumene_cny_log"])


def capacity_effective_coverage(frame: pd.DataFrame, primary: pd.DataFrame, lag: int) -> dict[str, object]:
    margin = pd.DataFrame({"month": frame.month, "margin": margin_proxy(frame)})
    margin["available_month"] = margin["month"].shift(lag)
    joined = primary[["month"]].merge(margin[["month", "available_month"]], on="month", how="left")
    valid = joined.dropna()
    return {"lag": lag, "start": valid.month.iloc[0], "end": valid.month.iloc[-1], "n": len(valid)}
