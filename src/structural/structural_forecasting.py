"""Leakage-safe expanding-window MAP estimation and forecasts for M0_CORE5."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from .likelihood import evaluate_m0_likelihood
from .matrices import system_matrices
from .priors import log_prior_native
from .state_space import from_phase2a_parameters
from .stability import stability_metrics

MEASUREMENT_COLUMNS = {
    "spot": "lc_spot_dlog", "ore_cost": "spodumene_cny_dlog",
    "output": "lc_output_yoy_log", "battery": "battery_install_yoy_log",
}

@dataclass(frozen=True)
class TrainingScaler:
    mean: dict[str, float]
    sd: dict[str, float]


def build_release_safe_training_measurements(frame: pd.DataFrame, origin_index: int):
    train = frame.iloc[:origin_index + 1].copy()
    mask = train["lc_spot_dlog"].notna() & train["lc_output_yoy_log"].notna() & train["battery_install_yoy_log"].notna()
    valid_start = int(np.flatnonzero(mask)[0])
    work = train.iloc[valid_start:].reset_index(drop=True)
    means, sds, values = {}, {}, {}
    for label, column in MEASUREMENT_COLUMNS.items():
        raw = work[column].astype(float).copy()
        available = raw.copy()
        if label in ("output", "battery"):
            available.iloc[-1] = np.nan
        mu = float(available.mean()); sd = float(available.std(ddof=1))
        if not np.isfinite(sd) or sd <= 0:
            raise ValueError(f"invalid scaler for {label}")
        means[label], sds[label] = mu, sd
        z = (raw - mu) / sd
        if label in ("output", "battery"):
            z.iloc[-1] = np.nan
        values[label] = z.to_numpy(float)
    y = np.column_stack([values[x] for x in ("spot", "ore_cost", "output", "battery")])
    return y, TrainingScaler(means, sds), work["month"].tolist()


class NativeMapObjective:
    def __init__(self, transform, observations, bounds, prior, rho_n=.8, battery_sd=.25, penalty=1e12):
        self.transform = transform; self.y = np.asarray(observations, float)
        self.bounds = bounds; self.prior = prior; self.rho_n = float(rho_n)
        self.battery_sd = float(battery_sd); self.penalty = float(penalty)
    def __call__(self, z):
        theta = self.transform.unconstrained_to_theta(np.asarray(z, float)); p = {**theta, "rho_n": self.rho_n}
        try:
            A = system_matrices("M0_CORE5", p)[0]
            if stability_metrics(A)["spectral_radius"] >= 1:
                return self.penalty
            lik = evaluate_m0_likelihood(p, self.battery_sd, self.y)
            lp = log_prior_native(theta, self.bounds, self.prior)
            if lik.status != "OK" or not np.isfinite(lik.loglik) or not np.isfinite(lp):
                return self.penalty
            return float(-(lik.loglik + lp))
        except Exception:
            return self.penalty


def fit_map_multistart(transform, observations, bounds, prior, starts, rho_n=.8, battery_sd=.25, maxiter=400, ftol=1e-9, z_bound=8.):
    rows = []
    for i, start in enumerate(starts):
        obj = NativeMapObjective(transform, observations, bounds, prior, rho_n, battery_sd)
        z0 = np.clip(transform.theta_to_unconstrained(start), -z_bound, z_bound)
        res = minimize(obj, z0, method="L-BFGS-B", bounds=[(-z_bound, z_bound)] * len(z0), options={"maxiter": maxiter, "ftol": ftol})
        theta = transform.unconstrained_to_theta(res.x)
        reasons = []
        if not bool(res.success):
            reasons.append("OPTIMIZER_NOT_CONVERGED")
        within_support = all(
            name in theta and np.isfinite(theta[name]) and lo <= theta[name] <= hi
            for name, (lo, hi) in bounds.items()
        )
        if not within_support:
            reasons.append("OUTSIDE_NATIVE_SUPPORT")
        radius = float("nan")
        if within_support:
            try:
                p = {**theta, "rho_n": rho_n}
                radius = float(stability_metrics(system_matrices("M0_CORE5", p)[0])["spectral_radius"])
            except (ValueError, np.linalg.LinAlgError, OverflowError, FloatingPointError):
                pass
        stable = bool(np.isfinite(radius) and radius < 1)
        if not stable:
            reasons.append("UNSTABLE_OR_INVALID_SYSTEM")
        loglik = float("nan")
        likelihood_status = "NOT_EVALUATED"
        logprior = float("nan")
        if within_support and stable:
            try:
                lik = evaluate_m0_likelihood(p, battery_sd, obj.y)
                likelihood_status = lik.status
                loglik = float(lik.loglik)
            except (ValueError, np.linalg.LinAlgError, OverflowError, FloatingPointError):
                likelihood_status = "EVALUATION_ERROR"
            try:
                logprior = float(log_prior_native(theta, bounds, prior))
            except (ValueError, OverflowError, FloatingPointError):
                pass
        if likelihood_status != "OK" or not np.isfinite(loglik):
            reasons.append("INVALID_LIKELIHOOD")
        if not np.isfinite(logprior):
            reasons.append("INVALID_PRIOR_OR_SUPPORT")
        value = (
            float(-(loglik + logprior))
            if likelihood_status == "OK" and np.isfinite(loglik) and np.isfinite(logprior)
            else obj.penalty
        )
        if not np.isfinite(value) or value == obj.penalty:
            reasons.append("INVALID_OBJECTIVE")
        rows.append({"start_id": i, "success": bool(res.success), "admissible": not reasons,
                     "failure_reasons": reasons, "objective": value, "theta": theta,
                     "within_support": within_support, "likelihood_status": likelihood_status,
                     "loglik": loglik, "logprior": logprior, "spectral_radius": radius,
                     "nit": int(getattr(res, "nit", 0)), "nfev": int(res.nfev), "message": str(res.message)})
    valid = [r for r in rows if r["admissible"]]
    if not valid:
        detail = "; ".join(
            f"start {r['start_id']}: {','.join(r['failure_reasons'])}; optimizer={r['message']}"
            for r in rows
        ) or "no starts supplied"
        raise RuntimeError(f"no converged, valid structural MAP solution ({detail})")
    return min(valid, key=lambda r: r["objective"]), rows


def structural_forecast(theta, observations, scaler: TrainingScaler, origin_log_price: float, horizons, rho_n=.8, battery_sd=.25):
    p = {**theta, "rho_n": rho_n}; model = from_phase2a_parameters("M0_CORE5", p, battery_sd)
    from .kalman import kalman_filter
    filt = kalman_filter(model, np.asarray(observations, float))
    if filt.status != "OK":
        raise RuntimeError(f"filter failed: {filt.failure_reason}")
    state = filt.filtered_mean[-1].copy(); max_h = max(horizons); dlogs = []
    for _ in range(max_h):
        state = model.A @ state
        spot_z = float(model.H[0] @ state)
        dlogs.append(scaler.mean["spot"] + scaler.sd["spot"] * spot_z)
    log_path = origin_log_price + np.cumsum(dlogs)
    return np.asarray(dlogs), np.asarray(log_path), filt
