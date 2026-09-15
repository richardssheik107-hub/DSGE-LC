"""Deterministic transformations for the Phase 1A-1 frozen monthly sample."""
from __future__ import annotations

import numpy as np
import pandas as pd


SOURCE_TO_LEVEL = {
    "lc_spot": "lc_spot",
    "lc_output_total": "lc_output",
    "spodumene_price": "spodumene_price",
    "spodumene_cny_t": "spodumene_cny_t",
    "battery_install": "battery_install",
    "usd_cny_mean": "usd_cny_mean",
}

PREFIX = {
    "lc_spot": "lc_spot",
    "lc_output": "lc_output",
    "spodumene_price": "spodumene_price",
    "spodumene_cny_t": "spodumene_cny",
    "battery_install": "battery_install",
    "usd_cny_mean": "usd_cny",
}

ZSCORE_LEVELS = [
    "lc_spot",
    "lc_output",
    "spodumene_price",
    "spodumene_cny_t",
    "battery_install",
]

ROLLING_LEVELS = ["lc_spot", "lc_output", "spodumene_price", "battery_install"]


def validate_core_input(frame: pd.DataFrame) -> None:
    """Fail on any defect that would make the transformations misleading."""
    missing_columns = sorted(set(SOURCE_TO_LEVEL) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required core columns: {missing_columns}")
    if frame["month"].isna().any() or frame["month"].duplicated().any():
        raise ValueError("Month must be non-missing and unique")
    parsed = pd.PeriodIndex(frame["month"], freq="M")
    if not parsed.is_monotonic_increasing:
        raise ValueError("Month must be monotonically increasing")
    levels = list(SOURCE_TO_LEVEL)
    if frame[levels].isna().any().any():
        raise ValueError("Core level fields contain unexpected missing values")
    numeric = frame[levels].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("Core level fields must be finite numeric values")
    if (numeric <= 0).any().any():
        bad = (numeric <= 0).sum().loc[lambda x: x.gt(0)].to_dict()
        raise ValueError(f"Log inputs must be strictly positive: {bad}")
    expected_proxy = numeric["spodumene_price"] * numeric["usd_cny_mean"]
    if not np.allclose(expected_proxy, numeric["spodumene_cny_t"], rtol=1e-10, atol=1e-8):
        raise ValueError("spodumene_cny_t is inconsistent with price times FX")


def build_structural_dataset(frame: pd.DataFrame, rolling_window: int = 12) -> pd.DataFrame:
    """Return levels plus transparent log, growth and visualization fields."""
    validate_core_input(frame)
    out = frame[["month", *SOURCE_TO_LEVEL]].rename(columns=SOURCE_TO_LEVEL).copy()

    for level, prefix in PREFIX.items():
        log_col = f"{prefix}_log"
        out[log_col] = np.log(out[level])
        out[f"{prefix}_dlog"] = out[log_col].diff(1)
        out[f"{prefix}_mom_pct"] = out[level].pct_change(1, fill_method=None) * 100.0
        out[f"{prefix}_yoy_log"] = out[log_col].diff(12)
        out[f"{prefix}_yoy_pct"] = out[level].pct_change(12, fill_method=None) * 100.0

    for level in ZSCORE_LEVELS:
        prefix = PREFIX[level]
        sample_std = out[level].std(ddof=1)
        if not np.isfinite(sample_std) or sample_std <= 0:
            raise ValueError(f"Cannot calculate z-score for {level}")
        out[f"{prefix}_z"] = (out[level] - out[level].mean()) / sample_std

    for level in ROLLING_LEVELS:
        prefix = PREFIX[level]
        out[f"{prefix}_rolling_mean_{rolling_window}m"] = out[level].rolling(rolling_window).mean()
        out[f"{prefix}_rolling_std_{rolling_window}m"] = out[level].rolling(rolling_window).std(ddof=1)
        out[f"{prefix}_dlog_rolling_std_{rolling_window}m"] = out[f"{prefix}_dlog"].rolling(rolling_window).std(ddof=1)
    return out
