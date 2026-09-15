"""Fixed-seed synthetic sanity simulation; no real-data structural fit."""
from __future__ import annotations

import numpy as np

from .equations import transition
from .spec import MODEL_SPECS


def lagged_value(values: np.ndarray, t: int, lag: int) -> float:
    """Return only predetermined input; pre-sample values are fixed at zero."""
    if lag not in (9, 10, 11):
        raise ValueError("unsupported capacity lag")
    return float(values[t - lag]) if t >= lag else 0.0


def simulate(model: str, p: dict[str, float], periods: int = 1000, burn: int = 200, seed: int = 20260915, capacity_lag: int = 10) -> np.ndarray:
    rng = np.random.default_rng(seed)
    shocks = rng.normal(size=(periods + burn, 4))
    margin = np.zeros(periods + burn)
    if model == "M1_CAPACITY6":
        innovations = rng.normal(scale=.35, size=len(margin))
        for t in range(1, len(margin)): margin[t] = np.clip(.7 * margin[t - 1] + innovations[t], -2., 2.)
    x = np.zeros(len(MODEL_SPECS[model].states)); out = []
    for t in range(len(shocks)):
        u = lagged_value(margin, t, capacity_lag) if model == "M1_CAPACITY6" else 0.0
        x = transition(model, x, shocks[t], p, u); out.append(x.copy())
    return np.asarray(out[burn:])


def simulation_summary(model: str, values: np.ndarray) -> list[dict[str, object]]:
    rows = []
    for i, state in enumerate(MODEL_SPECS[model].states):
        x = values[:, i]
        rows.append({"model": model, "state": state, "n": len(x), "finite": bool(np.isfinite(x).all()), "mean": float(np.mean(x)), "variance": float(np.var(x, ddof=1)), "lag1_autocorrelation": float(np.corrcoef(x[1:], x[:-1])[0, 1])})
    return rows
