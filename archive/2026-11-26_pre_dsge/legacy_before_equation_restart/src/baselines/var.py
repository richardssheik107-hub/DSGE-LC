"""Small VAR baseline with within-origin BIC lag selection and stability audit."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class VARFit:
    lag: int
    coefficients: np.ndarray
    aic: float
    bic: float
    condition_number: float
    stable: bool
    roots: np.ndarray
    nobs: int
    fallback_reason: str = ""


def var_design(values: np.ndarray, lag: int) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=float)
    n, variables = values.shape
    y = values[lag:]
    x = np.ones((n - lag, 1 + variables * lag))
    for step in range(1, lag + 1):
        start = 1 + (step - 1) * variables
        x[:, start:start + variables] = values[lag - step:n - step]
    return x, y


def companion_roots(coefficients: np.ndarray, lag: int) -> np.ndarray:
    variables = coefficients.shape[1]
    companion = np.zeros((variables * lag, variables * lag))
    lag_blocks = coefficients[1:].reshape(lag, variables, variables)
    companion[:variables, :] = np.concatenate([block.T for block in lag_blocks], axis=1)
    if lag > 1:
        companion[variables:, :-variables] = np.eye(variables * (lag - 1))
    return np.linalg.eigvals(companion)


def fit_var(values: np.ndarray, lag: int) -> VARFit:
    x, y = var_design(values, lag)
    if len(y) <= x.shape[1]:
        raise ValueError("insufficient observations for VAR fit")
    coefficients, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    residual = y - x @ coefficients
    sigma = residual.T @ residual / len(y)
    sign, logdet = np.linalg.slogdet(sigma)
    if sign <= 0 or not np.isfinite(logdet):
        raise np.linalg.LinAlgError("singular residual covariance")
    variables = y.shape[1]
    parameters_per_equation = x.shape[1]
    aic = logdet + 2 * parameters_per_equation * variables / len(y)
    bic = logdet + np.log(len(y)) * parameters_per_equation * variables / len(y)
    roots = companion_roots(coefficients, lag)
    return VARFit(lag, coefficients, float(aic), float(bic), float(np.linalg.cond(x)),
                  bool(np.all(np.abs(roots) < 1.0)), roots, len(y))


def select_var_lag(values: np.ndarray, max_lag: int = 2) -> tuple[VARFit, list[VARFit]]:
    fits = []
    errors = []
    for lag in range(1, max_lag + 1):
        try:
            fits.append(fit_var(values, lag))
        except (ValueError, np.linalg.LinAlgError) as exc:
            errors.append(f"p={lag}: {exc}")
    if not fits:
        raise np.linalg.LinAlgError("; ".join(errors) or "no estimable VAR lag")
    selected = min(fits, key=lambda fit: fit.bic)
    if selected.lag != min(range(1, max_lag + 1), default=1) and errors:
        selected.fallback_reason = "; ".join(errors)
    return selected, fits


def forecast_var(fit: VARFit, history: np.ndarray, horizon: int) -> np.ndarray:
    path = [row.copy() for row in np.asarray(history, dtype=float)]
    forecasts = []
    variables = fit.coefficients.shape[1]
    for _ in range(int(horizon)):
        regressors = [1.0]
        for step in range(1, fit.lag + 1):
            regressors.extend(path[-step])
        value = np.asarray(regressors) @ fit.coefficients
        value = np.asarray(value, dtype=float).reshape(variables)
        path.append(value)
        forecasts.append(value)
    return np.asarray(forecasts)
