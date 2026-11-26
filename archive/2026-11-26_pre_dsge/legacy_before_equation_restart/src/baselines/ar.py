"""Transparent autoregression with origin-specific information-criterion selection."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ARFit:
    lag: int
    coefficients: np.ndarray
    aic: float
    bic: float
    condition_number: float
    nobs: int


def _design(values: np.ndarray, lag: int) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=float)
    y = values[lag:]
    x = np.ones((len(y), 1 + lag))
    for step in range(1, lag + 1):
        x[:, step] = values[lag - step:len(values) - step]
    return x, y


def fit_ar(values: np.ndarray, lag: int) -> ARFit:
    x, y = _design(np.asarray(values, dtype=float), lag)
    if len(y) <= x.shape[1]:
        raise ValueError("insufficient observations for AR fit")
    coefficients, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    residual = y - x @ coefficients
    sse = max(float(residual @ residual), np.finfo(float).tiny)
    n, k = len(y), x.shape[1]
    aic = n * np.log(sse / n) + 2 * k
    bic = n * np.log(sse / n) + np.log(n) * k
    return ARFit(lag, coefficients, float(aic), float(bic), float(np.linalg.cond(x)), n)


def select_ar_lag(values: np.ndarray, max_lag: int = 3) -> tuple[ARFit, list[ARFit]]:
    """Select BIC using only values passed by the forecast origin."""
    fits = [fit_ar(values, lag) for lag in range(1, max_lag + 1)]
    return min(fits, key=lambda fit: fit.bic), fits


def forecast_ar(fit: ARFit, history: np.ndarray, horizon: int) -> np.ndarray:
    path = list(np.asarray(history, dtype=float))
    forecasts = []
    for _ in range(int(horizon)):
        regressors = [1.0] + [path[-step] for step in range(1, fit.lag + 1)]
        value = float(np.asarray(regressors) @ fit.coefficients)
        path.append(value)
        forecasts.append(value)
    return np.asarray(forecasts)
