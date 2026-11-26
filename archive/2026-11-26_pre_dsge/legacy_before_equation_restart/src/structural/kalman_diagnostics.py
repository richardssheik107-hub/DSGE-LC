"""Numerical and synthetic diagnostics for Phase 2B validation."""
from __future__ import annotations

import numpy as np

from .kalman import kalman_filter, rts_smoother
from .state_space import StateSpaceModel, stationary_initialization


def covariance_audit(values: np.ndarray, tolerance: float=1e-9) -> dict[str,float|int|bool]:
    finite=bool(np.isfinite(values).all()); sym=max(float(np.max(np.abs(x-x.T))) for x in values)
    minimum=min(float(np.linalg.eigvalsh(x).min()) for x in values)
    return {"finite":finite,"max_symmetry_error":sym,"minimum_eigenvalue":minimum,"violations":int((not finite) or sym>tolerance or minimum < -tolerance)}


def simulate_observations(model: StateSpaceModel, periods: int, burn: int, seed: int, controls=None):
    rng=np.random.default_rng(seed); total=periods+burn
    if controls is None: full_controls=np.zeros((total,model.control_dim))
    else:
        controls=np.asarray(controls,float)
        if controls.shape==(periods,model.control_dim): full_controls=np.vstack([np.zeros((burn,model.control_dim)),controls])
        elif controls.shape==(total,model.control_dim): full_controls=controls
        else: raise ValueError("synthetic controls dimensions invalid")
    _,P,_=stationary_initialization(model); x=rng.multivariate_normal(np.zeros(model.state_dim),P)
    states=[]; obs=[]
    for t in range(total):
        x=model.A@x+(model.G@full_controls[t] if model.control_dim else 0.)+model.B@rng.normal(size=model.B.shape[1])
        y=model.H@x; y[-1]+=rng.normal(scale=np.sqrt(model.R[-1,-1])); states.append(x.copy()); obs.append(y)
    return np.asarray(states[burn:]),np.asarray(obs[burn:]),full_controls[burn:]


def state_rmse(truth: np.ndarray, estimate: np.ndarray) -> np.ndarray:
    return np.sqrt(np.mean((np.asarray(truth)-np.asarray(estimate))**2,axis=0))


def innovation_summary(standardized: np.ndarray) -> list[dict[str,float|int]]:
    rows=[]
    for j in range(standardized.shape[1]):
        x=standardized[:,j]; x=x[np.isfinite(x)]
        rows.append({"channel":j,"n":len(x),"mean":float(x.mean()),"variance":float(x.var(ddof=1)),"lag1_autocorrelation":float(np.corrcoef(x[1:],x[:-1])[0,1])})
    return rows


def initialization_comparison(model: StateSpaceModel, y: np.ndarray, variants: dict[str,tuple[np.ndarray,np.ndarray]], **kwargs):
    primary=kalman_filter(model,y,initial_mean=variants["stationary"][0],initial_cov=variants["stationary"][1],**kwargs)
    rows=[]
    for name,(mean,cov) in variants.items():
        result=kalman_filter(model,y,initial_mean=mean,initial_cov=cov,**kwargs)
        rows.append({"initialization":name,"status":result.status,"loglik":result.loglik,
                     "loglik_difference":result.loglik-primary.loglik,
                     "first12_state_l2":float(np.linalg.norm(result.filtered_mean[:12]-primary.filtered_mean[:12])),
                     "last24_state_l2":float(np.linalg.norm(result.filtered_mean[-24:]-primary.filtered_mean[-24:])),
                     "terminal_state_l2":float(np.linalg.norm(result.filtered_mean[-1]-primary.filtered_mean[-1])),
                     "max_jitter":float(np.nanmax(result.jitter_used))})
    return rows


def run_filter_smoother(model: StateSpaceModel, y: np.ndarray, **kwargs):
    filtered=kalman_filter(model,y,**kwargs); return filtered,rts_smoother(model,filtered,kwargs.get("psd_tolerance",1e-9))
