"""Structural-column FEVD without secondary orthogonalization.

The columns of ``B`` already contain shock standard deviations and any
contemporaneous price transmission. A state with zero forecast variance at a
given horizon has an undefined FEVD, represented by NaN rather than zero.
"""
from __future__ import annotations

import numpy as np


def structural_fevd(A, B, horizons=(1, 3, 6, 12, 24)):
    """Return per-horizon shares and shock-variance contributions.

    ``C_ij(H)`` is the sum of squared entries of ``A**h @ B`` for
    ``h = 0, ..., H-1``. Shares are NaN only where the denominator is zero.
    """
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    horizons = tuple(horizons)
    if (A.ndim != 2 or A.shape[0] != A.shape[1] or B.ndim != 2
            or B.shape[0] != A.shape[0] or B.shape[1] == 0
            or not np.isfinite(A).all() or not np.isfinite(B).all()):
        raise ValueError("invalid FEVD matrices")
    if not horizons or any(not isinstance(h, (int, np.integer)) or h < 1 for h in horizons):
        raise ValueError("FEVD horizons must be positive integers")
    responses = B.copy()
    cumulative = np.zeros_like(B)
    saved = {}
    for h in range(1, max(horizons) + 1):
        cumulative += responses**2
        if not np.isfinite(cumulative).all():
            raise ValueError("non-finite FEVD contribution")
        if h in horizons:
            total = cumulative.sum(axis=1)
            shares = np.full_like(cumulative, np.nan)
            np.divide(cumulative, total[:, None], out=shares, where=total[:, None] > 0)
            saved[h] = (shares, cumulative.copy())
        responses = A @ responses
    return (np.stack([saved[h][0] for h in horizons]),
            np.stack([saved[h][1] for h in horizons]))


def posterior_fevd_summary(values, horizons, state_names, shock_names):
    """Summarize shares, preserving undefined states and unnormalized medians.

    The mean is computed *after* each draw's contribution is normalized.
    A partially defined cell uses the same defined draws for every shock.
    """
    x = np.asarray(values, dtype=float)
    horizons, state_names, shock_names = tuple(horizons), tuple(state_names), tuple(shock_names)
    if (x.ndim != 4 or x.shape != (x.shape[0], len(horizons), len(state_names), len(shock_names))
            or x.shape[0] == 0 or np.isinf(x).any()):
        raise ValueError("invalid posterior FEVD shape or values")
    defined = np.isfinite(x).all(axis=-1)
    if np.any(np.isfinite(x).any(axis=-1) != defined):
        raise ValueError("partially undefined shock vector")
    rows = []
    for k, horizon in enumerate(horizons):
        for i, state in enumerate(state_names):
            valid = x[defined[:, k, i], k, i, :]
            status = ("NOT_DEFINED" if len(valid) == 0 else
                      "PARTIALLY_DEFINED" if len(valid) < len(x) else "DEFINED")
            for j, shock in enumerate(shock_names):
                if len(valid):
                    v = valid[:, j]
                    q05, q16, median, q84, q95 = np.quantile(v, [.05, .16, .5, .84, .95])
                    mean = float(v.mean())
                    sd = float(v.std(ddof=1)) if len(v) > 1 else np.nan
                else:
                    q05 = q16 = median = q84 = q95 = mean = sd = np.nan
                rows.append({"state": state, "shock": shock, "horizon": horizon,
                             "q05": q05, "q16": q16, "median": median,
                             "q84": q84, "q95": q95,
                             "mean": mean, "sd": sd, "status": status,
                             "valid_draws": len(valid), "total_draws": len(x)})
    return rows


def fevd_additivity_audit(shares, contributions, price_state_index=4, atol=1e-10):
    """Audit draw-level and posterior-mean additivity, including zero variance.

    Accepts either one draw ``(horizon, state, shock)`` or a posterior cube
    ``(draw, horizon, state, shock)``. The price state's denominator must be
    strictly positive for every draw and horizon.
    """
    shares = np.asarray(shares, dtype=float)
    contributions = np.asarray(contributions, dtype=float)
    if shares.ndim == 3:
        shares = shares[None, ...]
        contributions = contributions[None, ...]
    if (shares.ndim != 4 or contributions.shape != shares.shape or shares.shape[0] == 0
            or any(dim == 0 for dim in shares.shape[1:])
            or not 0 <= price_state_index < shares.shape[2] or atol < 0):
        raise ValueError("invalid FEVD audit inputs")
    total = contributions.sum(axis=-1)
    defined = total > 0
    all_or_none_finite = np.isfinite(shares).all(axis=-1) == defined
    undefined_all_nan = np.isnan(shares[~defined]).all()
    defined_shares = shares[defined]
    sum_error = (float(np.max(np.abs(defined_shares.sum(axis=-1) - 1)))
                 if len(defined_shares) else np.nan)
    bounds_pass = bool(np.all((defined_shares >= -atol) & (defined_shares <= 1 + atol)))
    expected = np.full_like(shares, np.nan)
    np.divide(contributions, total[..., None], out=expected, where=defined[..., None])
    ratio_error = (float(np.max(np.abs(defined_shares - expected[defined])))
                   if len(defined_shares) else np.nan)
    mean_sum_error = 0.0
    for h in range(shares.shape[1]):
        for state in range(shares.shape[2]):
            valid = defined[:, h, state]
            if valid.any():
                mean_sum_error = max(mean_sum_error,
                                     float(abs(shares[valid, h, state, :].mean(axis=0).sum() - 1)))
    price_min = float(np.min(total[:, :, price_state_index]))
    passed = (np.isfinite(contributions).all() and np.all(contributions >= 0)
              and np.isfinite(total).all() and bool(all_or_none_finite.all())
              and undefined_all_nan and bounds_pass and np.isfinite(price_min)
              and price_min > 0 and np.isfinite(sum_error) and sum_error <= atol
              and np.isfinite(ratio_error) and ratio_error <= atol
              and mean_sum_error <= atol)
    return {"status": "PASS" if passed else "FAIL",
            "zero_forecast_variance_count": int((~defined).sum()),
            "price_min_denominator": price_min,
            "max_draw_share_sum_error": sum_error,
            "max_share_ratio_error": ratio_error,
            "max_mean_share_sum_error": mean_sum_error,
            "all_undefined_are_nan": bool(undefined_all_nan)}


def forecast_variance_identity_check(A, B, horizon):
    A = np.asarray(A, float)
    B = np.asarray(B, float)
    W = B @ B.T
    power = np.eye(A.shape[0])
    cov = np.zeros_like(W)
    columns = np.zeros(A.shape[0])
    for _ in range(horizon):
        cov += power @ W @ power.T
        columns += np.sum((power @ B)**2, axis=1)
        power = A @ power
    return float(np.max(np.abs(np.diag(cov) - columns)))


def residual_dominance(price_shares, moderate=.5, high=.7):
    value = float(np.median(np.asarray(price_shares)))
    return ("HIGH_RESIDUAL_DOMINANCE" if value > high else
            "MODERATE_RESIDUAL_DOMINANCE" if value >= moderate else
            "LOW_RESIDUAL_DOMINANCE")
