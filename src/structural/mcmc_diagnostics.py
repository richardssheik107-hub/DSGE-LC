"""Multi-chain diagnostics for the frozen Phase 2D posterior.

The rank/fold/split definitions and Geyer initial-monotone ESS follow the
Stan Reference Manual and are checked against ArviZ in the audit tests.
Frozen *free-parameter* chains fail; constant quantile indicators are handled
inside the ESS estimator without being mistaken for frozen parameters.
Historical summaries are not overwritten; rerun diagnostics on stored draws.
"""
from __future__ import annotations
import numpy as np
from scipy.stats import norm, rankdata
from scipy.stats.mstats import mquantiles

DIAGNOSTIC_VERSION = "geyer_pairs_v3"


def _chains(value):
    x = np.asarray(value, dtype=float)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] < 2:
        raise ValueError("expected at least two chains and two draws")
    if not np.isfinite(x).all():
        raise ValueError("chain values must be finite")
    return x


def split_chains(chains):
    x = _chains(chains)
    half = x.shape[1] // 2
    if half < 2:
        raise ValueError("chains too short to split")
    return np.concatenate([x[:, :half], x[:, -half:]], axis=0)


def _rank_normalize(x):
    ranks = rankdata(np.asarray(x).ravel(), method="average")
    return norm.ppf((ranks - 3/8) / (len(ranks) + 1/4)).reshape(x.shape)


def _basic_rhat(chains):
    m, n = chains.shape
    within = float(np.mean(np.var(chains, axis=1, ddof=1)))
    between = n * float(np.var(chains.mean(axis=1), ddof=1))
    if within == 0:
        return np.nan
    return float(np.sqrt(((n-1)/n*within + between/n) / within))


def rank_normalized_split_rhat(chains):
    x = _chains(chains)
    # A frozen free-parameter chain cannot certify convergence.
    if np.any(np.ptp(x, axis=1) == 0):
        return np.inf
    split = split_chains(x)
    rank = _basic_rhat(_rank_normalize(split))
    folded = _basic_rhat(_rank_normalize(np.abs(split - np.median(split))))
    return float(np.maximum(rank, folded))


def _autocovariance(x):
    centered = np.asarray(x, float) - np.mean(x)
    n = len(centered)
    fft = np.fft.rfft(centered, n=2*n)
    return np.fft.irfft(fft * fft.conj(), n=2*n)[:n] / n


def _ess_core(x):
    """Estimate ESS for an already prepared chain/estimand array.

    Geyer's pairs start at (rho_0 + rho_1).  A positive even lag from the
    first rejected pair is retained, as in the reference implementation.
    The guard against a stuck *parameter* belongs at the public boundary,
    not here: a quantile indicator can legitimately be constant in one chain.
    """
    m, n = x.shape
    if n < 4:
        return np.nan
    if np.ptp(x) < np.finfo(float).resolution:
        return float(m * n)
    acov = np.array([_autocovariance(c) for c in x])
    within = float(np.mean(np.var(x, axis=1, ddof=1)))
    var_plus = (n-1)/n*within + float(np.var(x.mean(axis=1), ddof=1))
    if var_plus <= 0 or not np.isfinite(var_plus):
        return np.nan
    rho = 1.0 - (within - acov.mean(axis=0)) / var_plus
    rho[0] = 1.0
    if not np.isfinite(rho).all():
        return np.nan
    retained = np.zeros(n, dtype=float)
    retained[:2] = rho[:2]
    even, odd = 1.0, float(rho[1])
    lag = 1
    while lag < n - 3 and even + odd > 0:
        even, odd = float(rho[lag + 1]), float(rho[lag + 2])
        if even + odd >= 0:
            retained[lag + 1:lag + 3] = (even, odd)
        lag += 2
    last_full_lag = lag - 2
    if even > 0:
        retained[last_full_lag + 1] = even
    for pair_start in range(1, last_full_lag - 1, 2):
        previous = retained[pair_start - 1] + retained[pair_start]
        following = retained[pair_start + 1] + retained[pair_start + 2]
        if following > previous:
            retained[pair_start + 1:pair_start + 3] = previous / 2
    tau = (-1.0 + 2.0 * retained[:last_full_lag + 1].sum()
           + retained[last_full_lag + 1])
    # Permit antithetic ESS > N, using the standard finite-sample cap.
    tau = max(float(tau), 1.0/np.log10(m*n))
    return float(m*n/tau)


def effective_sample_size(chains):
    """Raw free-parameter ESS; any entirely frozen source chain is invalid."""
    x = _chains(chains)
    if np.any(np.ptp(x, axis=1) == 0):
        return 0.0
    return _ess_core(x)


def bulk_ess(chains):
    x = _chains(chains)
    if np.any(np.ptp(x, axis=1) == 0):
        return 0.0
    return _ess_core(_rank_normalize(split_chains(x)))


def mean_ess(chains):
    x = _chains(chains)
    if np.any(np.ptp(x, axis=1) == 0):
        return 0.0
    return _ess_core(split_chains(x))


def tail_ess(chains):
    x = _chains(chains)
    if np.any(np.ptp(x, axis=1) == 0):
        return 0.0
    # ArviZ uses SciPy's R type-7 mquantiles; repeated RWM states can sit
    # exactly on a percentile and differ from np.quantile's rounded threshold.
    lo, hi = mquantiles(x, [.05, .95], alphap=1, betap=1)
    return float(min(_ess_core(split_chains((x <= lo).astype(float))),
                     _ess_core(split_chains((x <= hi).astype(float)))))


def diagnostic_table(theta_chains, names):
    theta = np.asarray(theta_chains, float)
    if theta.ndim != 3 or theta.shape[2] != len(names) or not names:
        raise ValueError("parameter names do not match chain dimensions")
    if len(set(names)) != len(names):
        raise ValueError("parameter names must be unique")
    if not np.isfinite(theta).all():
        raise ValueError("posterior chains must be finite")
    rows = []
    for j, name in enumerate(names):
        x = theta[:, :, j]
        frozen = bool(np.any(np.ptp(x, axis=1) == 0))
        bulk, tail, ess_mean = bulk_ess(x), tail_ess(x), mean_ess(x)
        sd = float(np.std(x, ddof=1))
        mcse = sd/np.sqrt(ess_mean) if ess_mean > 0 and sd > 0 else np.inf
        rows.append({"parameter": name, "rhat": rank_normalized_split_rhat(x),
                     "bulk_ess": bulk, "tail_ess": tail, "mean_ess": ess_mean,
                     "mcse": mcse, "posterior_sd": sd,
                     "mcse_sd": mcse/sd if sd > 0 else np.inf,
                     "diagnostic_status": "FROZEN_FREE_PARAMETER" if frozen else "OK",
                     "diagnostic_version": DIAGNOSTIC_VERSION})
    return rows


def convergence_pass(rows, config):
    if not rows:
        return False
    for r in rows:
        if r.get("diagnostic_status", "OK") != "OK":
            return False
        keys = ("rhat", "bulk_ess", "tail_ess", "mcse_sd")
        if any(k not in r for k in keys):
            return False
        if not np.isfinite([r[k] for k in keys]).all():
            return False
        if not (r["rhat"] <= config["rhat_threshold"]
                and r["bulk_ess"] >= config["bulk_ess_threshold"]
                and r["tail_ess"] >= config["tail_ess_threshold"]
                and r["mcse_sd"] <= config["mcse_sd_threshold"]):
            return False
    return True


def acceptance_summary(results):
    rows = []
    for i, r in enumerate(results):
        audit = r["audit"]
        n = len(r["accepted"])
        rows.append({"chain": i+1, "production_draws": n,
                     "warmup_acceptance": r["warmup_acceptance"],
                     "production_acceptance": float(r["accepted"].mean()),
                     "max_rejection_streak": r["max_rejection_streak"],
                     "unique_state_fraction": len(np.unique(r["z"], axis=0))/n,
                     "unstable_rejection_fraction": audit.unstable/max(1, audit.proposals),
                     "invalid_rejection_fraction": audit.invalid/max(1, audit.proposals),
                     "guard_rejections": audit.guard, "kalman_failures": audit.kalman_failures,
                     "nonfinite": audit.nonfinite, "nonzero_jitter_states": audit.nonzero_jitter})
    return rows
