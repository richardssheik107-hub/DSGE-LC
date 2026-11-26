"""Random-walk spot-price baselines."""
from __future__ import annotations

import numpy as np


def forecast_no_drift(origin_log_price: float, horizon: int) -> np.ndarray:
    """Return a flat log-price path for the formal random-walk reference."""
    return np.repeat(float(origin_log_price), int(horizon))


def forecast_with_drift(origin_log_price: float, training_dlog: np.ndarray, horizon: int) -> np.ndarray:
    """Estimate drift from the current training window only."""
    values = np.asarray(training_dlog, dtype=float)
    values = values[np.isfinite(values)]
    drift = float(values.mean()) if values.size else 0.0
    return float(origin_log_price) + drift * np.arange(1, int(horizon) + 1)
