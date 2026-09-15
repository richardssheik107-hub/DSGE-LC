"""Reduced-form A/B/G/H matrices implied by the ordered equations."""
from __future__ import annotations

import numpy as np

from .equations import transition
from .spec import MODEL_SPECS


def system_matrices(model: str, p: dict[str, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = len(MODEL_SPECS[model].states)
    A = np.column_stack([transition(model, np.eye(n)[j], np.zeros(4), p, 0.0) for j in range(n)])
    B = np.column_stack([transition(model, np.zeros(n), np.eye(4)[j], p, 0.0) for j in range(4)])
    if model == "M1_CAPACITY6":
        G = transition(model, np.zeros(n), np.zeros(4), p, 1.0).reshape(-1, 1)
        H = np.zeros((4, n)); H[0, 5] = 1.; H[1, 1] = 1.; H[2, 3] = 1.; H[3, 0] = 1.
    else:
        G = np.zeros((n, 0))
        H = np.zeros((4, n)); H[0, 4] = 1.; H[1, 1] = 1.; H[2, 2] = 1.; H[3, 0] = 1.
    return A, B, G, H


def measurement_covariance(battery_sd: float) -> np.ndarray:
    return np.diag([0.0, 0.0, 0.0, float(battery_sd) ** 2])
