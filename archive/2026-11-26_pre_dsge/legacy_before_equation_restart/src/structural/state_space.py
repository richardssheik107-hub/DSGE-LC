"""State-space assembly for the frozen Phase 2A structural designs."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.linalg import solve_discrete_lyapunov

from .matrices import measurement_covariance, system_matrices
from .spec import MODEL_SPECS
from .stability import stability_metrics


@dataclass(frozen=True)
class StateSpaceModel:
    model_name: str
    A: np.ndarray
    B: np.ndarray
    W: np.ndarray
    G: np.ndarray
    H: np.ndarray
    R: np.ndarray
    state_names: tuple[str, ...]
    observation_names: tuple[str, ...]
    shock_names: tuple[str, ...]
    parameter_metadata: dict[str, float]

    @property
    def state_dim(self) -> int: return self.A.shape[0]
    @property
    def observation_dim(self) -> int: return self.H.shape[0]
    @property
    def control_dim(self) -> int: return self.G.shape[1]


def process_covariance(B: np.ndarray) -> np.ndarray:
    """Structural shocks have unit covariance; sigma scales are already in B."""
    W = np.asarray(B, dtype=float) @ np.asarray(B, dtype=float).T
    if not np.isfinite(W).all() or not np.allclose(W, W.T, atol=1e-12):
        raise ValueError("invalid process covariance")
    if np.linalg.eigvalsh(W).min() < -1e-10:
        raise ValueError("process covariance is not PSD")
    return W


def from_phase2a_parameters(model_name: str, parameters: dict[str, float], battery_sd: float) -> StateSpaceModel:
    A, B, G, H = system_matrices(model_name, parameters)
    if not stability_metrics(A)["stable"]:
        raise ValueError("UNSTABLE_PARAMETERS")
    spec = MODEL_SPECS[model_name]
    return StateSpaceModel(model_name, A, B, process_covariance(B), G, H,
                           measurement_covariance(battery_sd), spec.states,
                           spec.observations, spec.shocks, dict(parameters))


def stationary_initialization(model: StateSpaceModel) -> tuple[np.ndarray, np.ndarray, float]:
    P = solve_discrete_lyapunov(model.A, model.W)
    P = 0.5 * (P + P.T)
    residual = float(np.linalg.norm(P - model.A @ P @ model.A.T - model.W))
    if not np.isfinite(P).all() or np.linalg.eigvalsh(P).min() < -1e-9:
        raise ValueError("invalid stationary covariance")
    return np.zeros(model.state_dim), P, residual


def diffuse_initialization(model: StateSpaceModel, scale: float) -> tuple[np.ndarray, np.ndarray]:
    if scale <= 0 or not np.isfinite(scale): raise ValueError("diffuse scale must be positive")
    return np.zeros(model.state_dim), np.eye(model.state_dim) * float(scale)
