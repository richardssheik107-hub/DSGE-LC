"""Structural equations evaluated in their explicit contemporaneous order."""
from __future__ import annotations

import numpy as np

from .spec import MODEL_SPECS


def transition(model: str, x_lag: np.ndarray, shocks: np.ndarray, p: dict[str, float], margin_lag: float = 0.0) -> np.ndarray:
    """Evaluate one monthly transition; shocks are ordered demand/cost/supply/price."""
    if model == "M0_CORE5":
        d0, c0, q0, n0, p0 = np.asarray(x_lag, dtype=float)
        d = p["rho_d"] * d0 + p["sigma_d"] * shocks[0]
        c = p["rho_c"] * c0 + p["sigma_c"] * shocks[1]
        q = p["rho_q"] * q0 + p["a_p"] * p0 - p["a_c"] * c0 + p["sigma_q"] * shocks[2]
        n = p["rho_n"] * n0 + q0 - d0
        price = p["rho_p"] * p0 + p["b_d"] * d + p["b_c"] * c - p["b_q"] * q - p["b_n"] * n + p["sigma_p"] * shocks[3]
        return np.array([d, c, q, n, price])
    if model == "M1_CAPACITY6":
        d0, c0, k0, q0, n0, p0 = np.asarray(x_lag, dtype=float)
        d = p["rho_d"] * d0 + p["sigma_d"] * shocks[0]
        c = p["rho_c"] * c0 + p["sigma_c"] * shocks[1]
        k = p["rho_k"] * k0 + p["gamma_m"] * margin_lag
        q = p["rho_q"] * q0 + k + p["a_p"] * p0 - p["a_c"] * c0 + p["sigma_q"] * shocks[2]
        n = p["rho_n"] * n0 + q0 - d0
        price = p["rho_p"] * p0 + p["b_d"] * d + p["b_c"] * c - p["b_q"] * q - p["b_n"] * n + p["sigma_p"] * shocks[3]
        return np.array([d, c, k, q, n, price])
    raise KeyError(model)


def zero_steady_state(model: str) -> np.ndarray:
    """All variables are centered stationary deviations, so x*=0."""
    return np.zeros(len(MODEL_SPECS[model].states))
