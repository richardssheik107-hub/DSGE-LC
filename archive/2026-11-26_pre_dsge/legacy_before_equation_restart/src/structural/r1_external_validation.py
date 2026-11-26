"""R1-5 external-validation comparisons and time-sample uncertainty.

These helpers do not re-estimate the model.  Posterior draws describe parameter
uncertainty conditional on the frozen sample; the paired block bootstrap below
instead describes sensitivity to resampling *time blocks* of an aligned pair.
Neither is a prospective or causal validation interval.
"""
from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.stats import rankdata


Correlation = Literal["pearson", "spearman"]
Transformation = Literal[
    "raw_level",
    "log_level",
    "raw_change",
    "log_change",
    "detrended_log_level",
    "state_change_vs_log_change",
]


def _finite_vector(values: np.ndarray, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or len(array) < 3 or not np.isfinite(array).all():
        raise ValueError(f"{label} must be a finite one-dimensional series of at least three months")
    return array


def linear_detrend(values: np.ndarray) -> np.ndarray:
    """Remove an intercept and linear trend over the supplied *sample* only."""
    array = _finite_vector(values, "values")
    time = np.arange(len(array), dtype=float)
    time -= time.mean()
    slope = float(np.dot(time, array - array.mean()) / np.dot(time, time))
    return array - (array.mean() + slope * time)


def comparison_series(
    state: np.ndarray, external_level: np.ndarray, transformation: Transformation
) -> tuple[np.ndarray, np.ndarray]:
    """Align a latent state with an external positive level at common months.

    For an external change at t, the baseline comparison is state[t], not the
    change of state.  The separately named ``state_change_vs_log_change`` case
    checks the alternative change-versus-change definition.  Differencing
    reduces N by one; it never pads a fabricated first observation.
    """
    x = _finite_vector(state, "state")
    y = _finite_vector(external_level, "external_level")
    if len(x) != len(y):
        raise ValueError("state and external level must refer to the same months")
    if transformation == "raw_level":
        return x.copy(), y.copy()
    if transformation == "raw_change":
        return x[1:].copy(), np.diff(y)
    if transformation not in {
        "log_level", "log_change", "detrended_log_level", "state_change_vs_log_change"
    }:
        raise ValueError(f"unknown transformation: {transformation}")
    if np.any(y <= 0):
        raise ValueError("log transformation requires strictly positive external levels")
    log_y = np.log(y)
    if transformation == "log_level":
        return x.copy(), log_y
    if transformation == "log_change":
        return x[1:].copy(), np.diff(log_y)
    if transformation == "detrended_log_level":
        return linear_detrend(x), linear_detrend(log_y)
    return np.diff(x), np.diff(log_y)


def _correlation(x: np.ndarray, y: np.ndarray, statistic: Correlation) -> tuple[float, str]:
    if statistic == "spearman":
        x, y = rankdata(x), rankdata(y)
    elif statistic != "pearson":
        raise ValueError(f"unknown correlation statistic: {statistic}")
    x_centered = x - x.mean()
    y_centered = y - y.mean()
    sum_x = float(np.dot(x_centered, x_centered))
    sum_y = float(np.dot(y_centered, y_centered))
    if sum_x == 0 and sum_y == 0:
        return float("nan"), "BOTH_CONSTANT"
    if sum_x == 0:
        return float("nan"), "STATE_CONSTANT"
    if sum_y == 0:
        return float("nan"), "EXTERNAL_CONSTANT"
    denominator = np.sqrt(sum_x) * np.sqrt(sum_y)
    if not np.isfinite(denominator) or denominator <= 0:
        return float("nan"), "INVALID_DENOMINATOR"
    return float(np.clip(np.dot(x_centered, y_centered) / denominator, -1.0, 1.0)), "OK"


def paired_moving_block_indices(
    n_months: int, block_length: int, n_rep: int, seed: int
) -> np.ndarray:
    """Non-circular moving blocks, sampled as one index for both paired series."""
    if not isinstance(n_months, (int, np.integer)) or n_months < 3:
        raise ValueError("n_months must be at least 3")
    if not isinstance(block_length, (int, np.integer)) or not 1 <= block_length <= n_months:
        raise ValueError("block_length must be between 1 and n_months")
    if not isinstance(n_rep, (int, np.integer)) or n_rep < 1:
        raise ValueError("n_rep must be positive")
    if not isinstance(seed, (int, np.integer)):
        raise ValueError("seed must be an integer")
    rng = np.random.default_rng(seed)
    n_blocks = (n_months + block_length - 1) // block_length
    starts = rng.integers(0, n_months - block_length + 1, size=(n_rep, n_blocks))
    offsets = np.arange(block_length)
    return (starts[:, :, None] + offsets).reshape(n_rep, -1)[:, :n_months]


def paired_block_bootstrap_correlation(
    state: np.ndarray,
    external: np.ndarray,
    *,
    block_length: int,
    n_rep: int = 2000,
    seed: int,
    statistic: Correlation = "pearson",
) -> dict[str, object]:
    """Percentile interval from jointly resampled aligned time blocks.

    Undefined replicates are counted and excluded from quantiles, never
    substituted with zero.  The caller must pre-specify the block lengths and
    seed and assess whether a trend/short sample makes the interval unreliable.
    """
    x = _finite_vector(state, "state")
    y = _finite_vector(external, "external")
    if len(x) != len(y):
        raise ValueError("state/external month mismatch")
    point, point_status = _correlation(x, y, statistic)
    indices = paired_moving_block_indices(len(x), block_length, n_rep, seed)
    replicates = np.full(n_rep, np.nan, dtype=float)
    counts = {
        "both_constant_count": 0,
        "state_constant_count": 0,
        "external_constant_count": 0,
        "invalid_denominator_count": 0,
    }
    count_name = {
        "BOTH_CONSTANT": "both_constant_count",
        "STATE_CONSTANT": "state_constant_count",
        "EXTERNAL_CONSTANT": "external_constant_count",
        "INVALID_DENOMINATOR": "invalid_denominator_count",
    }
    for i, take in enumerate(indices):
        value, status = _correlation(x[take], y[take], statistic)
        if status == "OK":
            replicates[i] = value
        else:
            counts[count_name[status]] += 1
    valid = replicates[np.isfinite(replicates)]
    lower, upper = (np.quantile(valid, [.025, .975]) if len(valid) else (np.nan, np.nan))
    return {
        "point_correlation": point,
        "point_status": point_status,
        "interval_status": "COMPUTED" if len(valid) else "NO_VALID_REPLICATES",
        "ci025": float(lower),
        "ci975": float(upper),
        "n_months": len(x),
        "block_length": int(block_length),
        "n_rep": int(n_rep),
        "seed": int(seed),
        "statistic": statistic,
        "valid_replicates": len(valid),
        "invalid_replicates": int(n_rep - len(valid)),
        **counts,
        "replicate_correlations": replicates,
    }


def state_information_comparison(
    filtered_paths: np.ndarray,
    smoothed_paths: np.ndarray,
    external_level: np.ndarray,
    *,
    transformation: Transformation,
    statistic: Correlation = "pearson",
) -> dict[str, object]:
    """Same draws/months/target under filtered versus smoothed information.

    Both paths may still use full-sample parameters; filtered paths are not
    historical real-time predictions merely because RTS smoothing is omitted.
    """
    filtered = np.asarray(filtered_paths, dtype=float)
    smoothed = np.asarray(smoothed_paths, dtype=float)
    if filtered.ndim != 2 or filtered.shape != smoothed.shape or not np.isfinite(filtered).all() or not np.isfinite(smoothed).all():
        raise ValueError("filtered/smoothed paths must be finite matching draw-by-month arrays")
    target = _finite_vector(external_level, "external_level")
    if filtered.shape[0] < 1 or filtered.shape[1] != len(target):
        raise ValueError("path months must match external level")
    outcome: dict[str, object] = {"n_draws": filtered.shape[0], "transformation": transformation, "statistic": statistic}
    for label, paths in (("filtered", filtered), ("smoothed", smoothed)):
        correlations = np.full(paths.shape[0], np.nan)
        invalid = 0
        for i, path in enumerate(paths):
            x, y = comparison_series(path, target, transformation)
            correlations[i], status = _correlation(x, y, statistic)
            invalid += status != "OK"
        valid = correlations[np.isfinite(correlations)]
        outcome[f"{label}_correlations"] = correlations
        outcome[f"{label}_valid_draws"] = len(valid)
        outcome[f"{label}_invalid_draws"] = int(invalid)
        outcome[f"{label}_median"] = float(np.median(valid)) if len(valid) else float("nan")
        outcome[f"{label}_q05"] = float(np.quantile(valid, .05)) if len(valid) else float("nan")
        outcome[f"{label}_q95"] = float(np.quantile(valid, .95)) if len(valid) else float("nan")
    return outcome
