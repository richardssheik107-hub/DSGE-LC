"""Moment-Jacobian local numerical precheck without likelihood evaluation."""
from __future__ import annotations

import numpy as np

from .matrices import measurement_covariance, system_matrices
from .spec import parameter_names


def stationary_covariance(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    n = A.shape[0]
    vec = np.linalg.solve(np.eye(n * n) - np.kron(A, A), (B @ B.T).reshape(-1))
    P = vec.reshape(n, n)
    return (P + P.T) / 2.0


def moment_vector(model: str, p: dict[str, float], battery_sd: float = .25, lags=(0, 1, 2, 3), include_input: bool = False) -> np.ndarray:
    A, B, G, H = system_matrices(model, p)
    if np.max(np.abs(np.linalg.eigvals(A))) >= 1:
        raise ValueError("stationary moments require stable A")
    P = stationary_covariance(A, B)
    values = []
    for lag in lags:
        cov = H @ (P if lag == 0 else np.linalg.matrix_power(A, lag) @ P) @ H.T
        if lag == 0:
            cov = cov + measurement_covariance(battery_sd)
            values.extend(cov[np.triu_indices(4)])
        else:
            values.extend(cov.ravel())
    if include_input and model == "M1_CAPACITY6":
        # A deterministic one-unit margin innovation has response H A^h G.
        values.extend(np.concatenate([H @ np.linalg.matrix_power(A, h) @ G[:, 0] for h in (0, 1, 3, 6, 12)]))
    return np.asarray(values, dtype=float)


def numerical_jacobian(model: str, p: dict[str, float], battery_sd: float = .25, step: float = 1e-5, include_input: bool = False) -> tuple[np.ndarray, tuple[str, ...]]:
    names = parameter_names(model)
    cols = []
    for name in names:
        delta = step * max(1.0, abs(p[name]))
        hi, lo = dict(p), dict(p); hi[name] += delta; lo[name] -= delta
        cols.append((moment_vector(model, hi, battery_sd, include_input=include_input) - moment_vector(model, lo, battery_sd, include_input=include_input)) / (2 * delta))
    return np.column_stack(cols), names


def jacobian_metrics(J: np.ndarray) -> dict[str, float | int]:
    s = np.linalg.svd(J, compute_uv=False)
    tol = max(J.shape) * np.finfo(float).eps * s[0]
    rank = int(np.sum(s > tol))
    return {"rank": rank, "target_rank": J.shape[1], "min_singular": float(s[-1]), "max_singular": float(s[0]), "condition_number": float(s[0] / s[-1]) if s[-1] > 0 else float("inf")}


def weak_pairs(J: np.ndarray, names: tuple[str, ...], threshold: float = .95) -> list[dict[str, object]]:
    norms = np.linalg.norm(J, axis=0)
    corr = np.divide(J.T @ J, np.outer(norms, norms), out=np.zeros((J.shape[1], J.shape[1])), where=np.outer(norms, norms) > 0)
    return [{"parameter_1": names[i], "parameter_2": names[j], "absolute_column_cosine": float(abs(corr[i, j])), "threshold": threshold} for i in range(len(names)) for j in range(i + 1, len(names)) if abs(corr[i, j]) >= threshold]


def capacity_input_sensitivity(p: dict[str, float], lag: int = 10, periods: int = 240, seed: int = 20260915) -> dict[str, float | int]:
    rng = np.random.default_rng(seed)
    m = np.zeros(periods)
    noise = rng.normal(scale=.35, size=periods)
    for t in range(1, periods): m[t] = .7 * m[t - 1] + noise[t]
    m = np.clip(m, -2.0, 2.0)
    def path(gamma: float) -> np.ndarray:
        pp = dict(p); pp["gamma_m"] = gamma
        A, _, G, H = system_matrices("M1_CAPACITY6", pp)
        x = np.zeros(6); ys = []
        for t in range(periods):
            u = m[t - lag] if t >= lag else 0.0
            x = A @ x + G[:, 0] * u
            ys.append(H @ x)
        return np.asarray(ys)
    low, high = path(max(.001, p["gamma_m"] - .02)), path(p["gamma_m"] + .02)
    diff = high - low
    return {"lag": lag, "rho_k": p["rho_k"], "gamma_low": max(.001, p["gamma_m"] - .02), "gamma_high": p["gamma_m"] + .02, "output_path_l2": float(np.linalg.norm(diff[:, 2])), "price_path_l2": float(np.linalg.norm(diff[:, 0])), "output_variance_change": float(np.var(high[:, 2]) - np.var(low[:, 2])), "price_variance_change": float(np.var(high[:, 0]) - np.var(low[:, 0]))}
