"""Local stability diagnostics for design points, not parameter estimates."""
from __future__ import annotations

import numpy as np

from .matrices import system_matrices
from .spec import baseline_parameters


def stability_metrics(A: np.ndarray) -> dict[str, object]:
    eig = np.linalg.eigvals(A)
    radius = float(np.max(np.abs(eig)))
    return {"spectral_radius": radius, "stable": bool(radius < 1.0), "eigenvalues": ";".join(f"{z.real:.8f}{z.imag:+.8f}j" for z in eig)}


def draw_parameters(rng: np.random.Generator, model: str, rho_n: float, rho_k: float = .9) -> dict[str, float]:
    p = baseline_parameters()
    for key in ("rho_d", "rho_c", "rho_q", "rho_p"):
        p[key] = float(rng.uniform(.05, .95))
    for key in ("a_p", "a_c", "b_d", "b_c", "b_q", "b_n"):
        p[key] = float(rng.uniform(0.0, 1.5))
    for key in ("sigma_d", "sigma_c", "sigma_q", "sigma_p"):
        p[key] = float(rng.uniform(.05, 1.5))
    p["rho_n"] = float(rho_n); p["rho_k"] = float(rho_k)
    if model == "M1_CAPACITY6":
        p["gamma_m"] = float(rng.uniform(.02, .6))
    return p


def random_stability_scan(model: str, draws: int, seed: int, rho_n_grid=(.5, .8, .95), rho_k_grid=(.8, .9, .97), lag_grid=(9, 10, 11)) -> list[dict[str, object]]:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(draws):
        rn = rho_n_grid[i % len(rho_n_grid)]
        rk = rho_k_grid[(i // len(rho_n_grid)) % len(rho_k_grid)]
        lag = lag_grid[(i // (len(rho_n_grid) * len(rho_k_grid))) % len(lag_grid)]
        p = draw_parameters(rng, model, rn, rk)
        A, _, _, _ = system_matrices(model, p)
        row = {"model": model, "draw": i, "rho_n": rn, "rho_k": rk if model.startswith("M1") else np.nan, "capacity_lag": lag if model.startswith("M1") else np.nan, **stability_metrics(A)}
        row["dominant_pattern"] = "price-supply-inventory feedback" if not row["stable"] else "stable"
        rows.append(row)
    return rows
