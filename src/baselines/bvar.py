"""Independent-equation Minnesota-style conjugate BVAR for stationary transforms."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .var import var_design


@dataclass
class BVARFit:
    lag: int
    coefficients: np.ndarray
    posterior_covariance: list[np.ndarray]
    residual_variance_posterior: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    condition_number: float
    stable: bool
    roots: np.ndarray
    nobs: int
    lambda_: float
    theta_cross: float
    lag_decay: float


def training_zscore(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Scale exclusively from the supplied training window."""
    values = np.asarray(values, dtype=float)
    means = values.mean(axis=0)
    scales = values.std(axis=0, ddof=1)
    if not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError("non-positive training scale")
    return (values - means) / scales, means, scales


def _prior_variance(equation: int, variables: int, lag: int, lambda_: float,
                    theta_cross: float, lag_decay: float) -> np.ndarray:
    variance = np.empty(1 + variables * lag)
    variance[0] = 1e6
    for step in range(1, lag + 1):
        for variable in range(variables):
            index = 1 + (step - 1) * variables + variable
            cross = 1.0 if variable == equation else theta_cross ** 2
            variance[index] = lambda_ ** 2 * cross / step ** (2 * lag_decay)
    return variance


def fit_bvar(values: np.ndarray, lag: int = 2, lambda_: float = 0.20,
             theta_cross: float = 0.50, lag_decay: float = 2.0) -> BVARFit:
    standardized, means, scales = training_zscore(values)
    x, y = var_design(standardized, lag)
    variables = y.shape[1]
    coefficients = np.zeros((x.shape[1], variables))
    posterior_covariance = []
    residual_variance = np.zeros(variables)
    a0, d0 = 2.0, 0.01
    for equation in range(variables):
        prior_mean = np.zeros(x.shape[1])
        prior_variance = _prior_variance(equation, variables, lag, lambda_, theta_cross, lag_decay)
        prior_precision = np.diag(1.0 / prior_variance)
        posterior_precision = x.T @ x + prior_precision
        posterior_base_cov = np.linalg.inv(posterior_precision)
        posterior_mean = posterior_base_cov @ (x.T @ y[:, equation] + prior_precision @ prior_mean)
        shape = a0 + len(y) / 2
        scale = d0 + 0.5 * (
            y[:, equation] @ y[:, equation]
            + prior_mean @ prior_precision @ prior_mean
            - posterior_mean @ posterior_precision @ posterior_mean
        )
        sigma2 = float(scale / (shape - 1))
        if not np.isfinite(sigma2) or sigma2 <= 0:
            raise np.linalg.LinAlgError("invalid residual variance posterior")
        coefficients[:, equation] = posterior_mean
        posterior_covariance.append(posterior_base_cov * sigma2)
        residual_variance[equation] = sigma2
    from .var import companion_roots
    roots = companion_roots(coefficients, lag)
    return BVARFit(lag, coefficients, posterior_covariance, residual_variance, means, scales,
                   float(np.linalg.cond(x.T @ x + np.eye(x.shape[1]))),
                   bool(np.all(np.abs(roots) < 1.0)), roots, len(y), lambda_, theta_cross, lag_decay)


def forecast_bvar(fit: BVARFit, history: np.ndarray, horizon: int) -> np.ndarray:
    standardized = (np.asarray(history, dtype=float) - fit.means) / fit.scales
    path = [row.copy() for row in standardized]
    forecasts = []
    for _ in range(int(horizon)):
        regressors = [1.0]
        for step in range(1, fit.lag + 1):
            regressors.extend(path[-step])
        value = np.asarray(regressors) @ fit.coefficients
        path.append(value)
        forecasts.append(value * fit.scales + fit.means)
    return np.asarray(forecasts)
