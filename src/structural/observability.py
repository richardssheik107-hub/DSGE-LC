"""Observability and reachability rank diagnostics."""
from __future__ import annotations

import numpy as np


def block_matrix(A: np.ndarray, C: np.ndarray) -> np.ndarray:
    return np.vstack([C @ np.linalg.matrix_power(A, i) for i in range(A.shape[0])])


def observability_metrics(A: np.ndarray, H: np.ndarray) -> dict[str, float | int]:
    O = block_matrix(A, H)
    s = np.linalg.svd(O, compute_uv=False)
    return {"rank": int(np.linalg.matrix_rank(O)), "target_rank": A.shape[0], "min_singular": float(s[-1]), "condition_number": float(s[0] / s[-1]) if s[-1] > 0 else float("inf")}


def controllability_matrix(A: np.ndarray, inputs: np.ndarray) -> np.ndarray:
    return np.hstack([np.linalg.matrix_power(A, i) @ inputs for i in range(A.shape[0])])


def reachability_metrics(A: np.ndarray, inputs: np.ndarray) -> dict[str, float | int]:
    C = controllability_matrix(A, inputs)
    s = np.linalg.svd(C, compute_uv=False)
    return {"rank": int(np.linalg.matrix_rank(C)), "target_rank": A.shape[0], "min_singular": float(s[-1]), "condition_number": float(s[0] / s[-1]) if s[-1] > 0 else float("inf")}
