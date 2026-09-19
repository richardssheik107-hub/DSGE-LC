"""Candidate C0 state-space bridge derived from the conditional 1P1D equilibrium.

This module is a theory-audit helper, not an estimator. It converts the interior
C0 equations into an affine transition for deviations around a fixed conditional
reference point. It does not imply empirical identification, a calibrated model,
or supervisor approval.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

STATE_ORDER = ("z_demand", "c_unit_cost", "q_reference", "i_physical")
SHOCK_ORDER = ("eps_demand", "eps_cost")
CONTROL_ORDER = ("v_non_lc", "u_other", "j_net_stock", "n_net_import", "r_other_output")
OUTPUT_ORDER = ("p_lc", "y_material")


@dataclass(frozen=True)
class C0StateParams:
    g: float
    kappa: float
    b: float
    a: float
    rho_d: float
    rho_c: float
    sigma_d: float
    sigma_c: float
    inventory_loss: float = 0.0

    def validate(self) -> None:
        vals = np.asarray(list(vars(self).values()), dtype=float)
        if not np.all(np.isfinite(vals)):
            raise ValueError("all parameters must be finite")
        if self.g <= 0 or self.kappa < 0 or self.b <= 0 or self.a <= 0:
            raise ValueError("economic curvature/intensity restrictions violated")
        if not (-1 < self.rho_d < 1 and -1 < self.rho_c < 1):
            raise ValueError("candidate AR states require |rho|<1")
        if self.sigma_d < 0 or self.sigma_c < 0:
            raise ValueError("shock scales must be nonnegative")
        if not (0 <= self.inventory_loss < 1):
            raise ValueError("inventory loss must lie in [0,1)")


def reduced_coefficients(p: C0StateParams) -> dict[str, float]:
    p.validate()
    G = p.g + p.kappa
    D = p.a * p.a / p.b + 1.0 / G
    phi_a = (p.a / p.b) / D
    phi_m = (1.0 / G) / D
    phi_q = -(p.kappa / G) / D
    phi_f = 1.0 / D
    q_z = phi_a / G
    q_c = (phi_m - 1.0) / G
    q_q = p.kappa / G + phi_q / G
    return {
        "G": G, "D": D,
        "phi_a": phi_a, "phi_m": phi_m, "phi_q": phi_q, "phi_f": phi_f,
        "q_z": q_z, "q_c": q_c, "q_q": q_q,
    }


def transition_matrices(p: C0StateParams) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return A, B, C for x_t = A x_(t-1) + B eps_t + C u_t."""
    c = reduced_coefficients(p)
    A = np.zeros((4, 4), dtype=float)
    B = np.zeros((4, 2), dtype=float)
    C = np.zeros((4, 5), dtype=float)

    A[0, 0] = p.rho_d
    A[1, 1] = p.rho_c
    B[0, 0] = p.sigma_d
    B[1, 1] = p.sigma_c

    A[2, 0] = c["q_z"] * p.rho_d
    A[2, 1] = c["q_c"] * p.rho_c
    A[2, 2] = c["q_q"]
    B[2, 0] = c["q_z"] * p.sigma_d
    B[2, 1] = c["q_c"] * p.sigma_c

    price_controls = np.array([-c["phi_a"], c["phi_f"], c["phi_f"], -c["phi_f"], -c["phi_f"]])
    C[2, :] = price_controls / c["G"]

    A[3, 3] = 1.0 - p.inventory_loss
    C[3, 2] = 1.0
    return A, B, C


def output_matrices(p: C0StateParams) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return H, D_eps, F for [p_t,y_t]' from lagged state, shocks and controls."""
    c = reduced_coefficients(p)
    H = np.zeros((2, 4), dtype=float)
    D_eps = np.zeros((2, 2), dtype=float)
    F = np.zeros((2, 5), dtype=float)

    H[0, 0] = c["phi_a"] * p.rho_d
    H[0, 1] = c["phi_m"] * p.rho_c
    H[0, 2] = c["phi_q"]
    D_eps[0, 0] = c["phi_a"] * p.sigma_d
    D_eps[0, 1] = c["phi_m"] * p.sigma_c
    F[0, :] = np.array([-c["phi_a"], c["phi_f"], c["phi_f"], -c["phi_f"], -c["phi_f"]])

    H[1, :] = -p.a / p.b * H[0, :]
    H[1, 0] += p.rho_d / p.b
    D_eps[1, :] = -p.a / p.b * D_eps[0, :]
    D_eps[1, 0] += p.sigma_d / p.b
    F[1, :] = -p.a / p.b * F[0, :]
    F[1, 0] += -1.0 / p.b
    return H, D_eps, F


def one_step(p: C0StateParams, x_lag, shocks, controls):
    """Evaluate transition and equilibrium outputs in deviation form."""
    x_lag = np.asarray(x_lag, dtype=float)
    shocks = np.asarray(shocks, dtype=float)
    controls = np.asarray(controls, dtype=float)
    if x_lag.shape != (4,) or shocks.shape != (2,) or controls.shape != (5,):
        raise ValueError("unexpected vector shape")
    A, B, C = transition_matrices(p)
    H, D_eps, F = output_matrices(p)
    x = A @ x_lag + B @ shocks + C @ controls
    outputs = H @ x_lag + D_eps @ shocks + F @ controls
    return x, outputs
