"""Pure structural-shock reconstruction and historical-decomposition utilities."""
from __future__ import annotations

import numpy as np
from scipy.linalg import lstsq


def reconstruct_smoothed_shocks(smoothed_mean, A, B):
    """Recover conditional mean shocks with a full-column-rank QR/LAPACK solve."""
    states = np.asarray(smoothed_mean, float); A = np.asarray(A, float); B = np.asarray(B, float)
    if states.ndim != 2 or states.shape[1] != A.shape[0] or B.shape[0] != A.shape[0]:
        raise ValueError("historical reconstruction dimension mismatch")
    residual = states[1:] - states[:-1] @ A.T
    solution, _, rank, _ = lstsq(B, residual.T, lapack_driver="gelsy")
    if rank != B.shape[1]:
        raise ValueError("structural impact matrix is not full column rank")
    shocks = solution.T
    reconstruction = shocks @ B.T
    error = float(np.max(np.abs(residual - reconstruction))) if len(residual) else 0.0
    return shocks, residual, error, int(rank)


def historical_contributions(A, B, initial_state, shocks):
    """Propagate the initial condition and each structural shock separately."""
    A = np.asarray(A, float); B = np.asarray(B, float)
    initial_state = np.asarray(initial_state, float); shocks = np.asarray(shocks, float)
    periods = shocks.shape[0] + 1; states = A.shape[0]; shock_count = B.shape[1]
    if initial_state.shape != (states,) or shocks.shape[1:] != (shock_count,):
        raise ValueError("historical contribution dimension mismatch")
    initial = np.zeros((periods, states)); contribution = np.zeros((periods, shock_count, states))
    initial[0] = initial_state
    for t in range(1, periods):
        initial[t] = A @ initial[t - 1]
        contribution[t] = contribution[t - 1] @ A.T + shocks[t - 1, :, None] * B.T
    return initial, contribution


def decomposition_identity_error(states, initial, contributions):
    reconstructed = np.asarray(initial, float) + np.asarray(contributions, float).sum(axis=1)
    return float(np.max(np.abs(np.asarray(states, float) - reconstructed)))


def episode_contributions(price_contributions, indices):
    values = np.asarray(price_contributions, float)
    selected = np.asarray(indices, int)
    return values[..., selected, :].sum(axis=-2)


def activity_shares(price_contributions, indices):
    values = np.asarray(price_contributions, float)
    selected = np.asarray(indices, int)
    activity = np.abs(values[..., selected, :]).sum(axis=-2)
    total = activity.sum(axis=-1, keepdims=True)
    # No activity means a share is undefined, not a four-shock zero vector.
    shares = np.divide(activity, total, out=np.full_like(activity, np.nan), where=total > 0)
    return activity, shares


def select_equal_per_chain(theta, draws_per_chain, seed):
    """Fixed-seed equal-chain posterior integration subset; this is not thinning."""
    theta = np.asarray(theta, float)
    if theta.ndim != 3 or draws_per_chain > theta.shape[1]:
        raise ValueError("posterior subset dimensions invalid")
    rng = np.random.default_rng(seed); selected=[]; indices=[]
    for chain in range(theta.shape[0]):
        choice = np.sort(rng.choice(theta.shape[1], draws_per_chain, replace=False))
        selected.append(theta[chain, choice]); indices.append(choice)
    return np.stack(selected), np.stack(indices)


def subset_representativeness(full, subset):
    full = np.asarray(full, float).reshape(-1, np.asarray(full).shape[-1])
    subset = np.asarray(subset, float).reshape(-1, np.asarray(subset).shape[-1])
    sd = full.std(axis=0, ddof=1)
    standardized = np.divide(np.median(subset, axis=0) - np.median(full, axis=0), sd,
                             out=np.zeros_like(sd), where=sd > 0)
    return standardized
