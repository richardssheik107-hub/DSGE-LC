"""Numerically audited Kalman filter and Rauch--Tung--Striebel smoother."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve, solve_triangular

from .state_space import StateSpaceModel, stationary_initialization


@dataclass
class KalmanFilterResult:
    loglik: float
    loglik_by_t: np.ndarray
    predicted_mean: np.ndarray
    predicted_cov: np.ndarray
    filtered_mean: np.ndarray
    filtered_cov: np.ndarray
    innovations: np.ndarray
    innovation_cov: np.ndarray
    standardized_innovations: np.ndarray
    kalman_gain: np.ndarray
    observed_mask: np.ndarray
    jitter_used: np.ndarray
    status: str
    failure_reason: str
    failure_time: int | None
    time_index: np.ndarray


@dataclass
class KalmanSmootherResult:
    smoothed_mean: np.ndarray
    smoothed_cov: np.ndarray
    smoother_gain: np.ndarray
    status: str
    failure_reason: str


def _factor_innovation(S: np.ndarray, ladder: tuple[float, ...]):
    dim = S.shape[0]; scale = max(1.0, float(np.trace(S) / dim))
    for multiplier in ladder:
        jitter = multiplier * scale
        try:
            adjusted = S + np.eye(dim) * jitter
            factor = cho_factor(adjusted, lower=True, check_finite=True)
            return factor, adjusted, jitter
        except np.linalg.LinAlgError:
            continue
    raise np.linalg.LinAlgError("innovation covariance Cholesky failed across jitter ladder")


def _audit_covariance(P: np.ndarray, tol: float, strict_pd: bool = False) -> None:
    if not np.isfinite(P).all(): raise ValueError("non-finite covariance")
    if not np.allclose(P, P.T, atol=tol): raise ValueError("asymmetric covariance")
    minimum = float(np.linalg.eigvalsh(P).min())
    if strict_pd and minimum <= 0: raise ValueError("covariance is not PD")
    if not strict_pd and minimum < -tol: raise ValueError("covariance is not PSD")


def kalman_filter(model: StateSpaceModel, observations: np.ndarray, *, time_index=None,
                  initial_mean=None, initial_cov=None, controls=None,
                  jitter_ladder=(0.0, 1e-12, 1e-10, 1e-8, 1e-6), psd_tolerance=1e-9,
                  maximum_jitter_multiplier=1e-6) -> KalmanFilterResult:
    y = np.asarray(observations, dtype=float)
    if y.ndim != 2 or y.shape[1] != model.observation_dim: raise ValueError("observation dimensions do not match model")
    T, m, n = y.shape[0], model.observation_dim, model.state_dim
    if initial_mean is None or initial_cov is None:
        default_mean, default_cov, _ = stationary_initialization(model)
        initial_mean = default_mean if initial_mean is None else initial_mean
        initial_cov = default_cov if initial_cov is None else initial_cov
    initial_mean = np.asarray(initial_mean, dtype=float); initial_cov = np.asarray(initial_cov, dtype=float)
    if initial_mean.shape != (n,) or initial_cov.shape != (n, n): raise ValueError("initialization dimensions do not match")
    if controls is None: controls = np.zeros((T, model.control_dim))
    controls = np.asarray(controls, dtype=float)
    if controls.shape != (T, model.control_dim): raise ValueError("control dimensions do not match")
    index = np.arange(T) if time_index is None else np.asarray(time_index)
    if len(index) != T: raise ValueError("time index length mismatch")
    pred_m=np.full((T,n),np.nan); filt_m=np.full((T,n),np.nan)
    pred_P=np.full((T,n,n),np.nan); filt_P=np.full((T,n,n),np.nan)
    innov=np.full((T,m),np.nan); innov_cov=np.full((T,m,m),np.nan)
    zinnov=np.full((T,m),np.nan); gain=np.full((T,n,m),np.nan)
    mask=np.isfinite(y); ll=np.full(T,np.nan); jitter=np.full(T,np.nan)
    mean = initial_mean + (model.G @ controls[0] if model.control_dim else 0.0)
    cov = 0.5 * (initial_cov + initial_cov.T)
    I = np.eye(n)
    try:
        for t in range(T):
            pred_m[t]=mean; pred_P[t]=cov; _audit_covariance(cov, psd_tolerance)
            obs = mask[t]
            if not obs.any():
                filt_m[t]=mean; filt_P[t]=cov; ll[t]=0.; jitter[t]=0.; gain[t]=0.
            else:
                Ht=model.H[obs]; Rt=model.R[np.ix_(obs,obs)]; error=y[t,obs]-Ht@mean
                S=0.5*(Ht@cov@Ht.T+Rt+(Ht@cov@Ht.T+Rt).T)
                factor, Sadj, used=_factor_innovation(S, tuple(jitter_ladder)); _audit_covariance(Sadj, psd_tolerance, strict_pd=True)
                scale=max(1.0,float(np.trace(S)/S.shape[0]))
                if used > maximum_jitter_multiplier*scale: raise ValueError("required innovation jitter exceeds allowed threshold")
                PHt=cov@Ht.T; K=cho_solve(factor,PHt.T).T
                updated_mean=mean+K@error
                IKH=I-K@Ht; updated_cov=IKH@cov@IKH.T+K@Rt@K.T; updated_cov=0.5*(updated_cov+updated_cov.T)
                _audit_covariance(updated_cov, psd_tolerance)
                solved=cho_solve(factor,error); logdet=2.*np.log(np.diag(factor[0])).sum()
                ll[t]=-.5*(obs.sum()*np.log(2*np.pi)+logdet+error@solved)
                white=solve_triangular(factor[0],error,lower=True,check_finite=True)
                innov[t,obs]=error; innov_cov[t][np.ix_(obs,obs)]=Sadj; zinnov[t,obs]=white
                gain[t][:,obs]=K; filt_m[t]=updated_mean; filt_P[t]=updated_cov; jitter[t]=used
            if t+1<T:
                mean=model.A@filt_m[t]+(model.G@controls[t+1] if model.control_dim else 0.0)
                cov=model.A@filt_P[t]@model.A.T+model.W; cov=0.5*(cov+cov.T)
        return KalmanFilterResult(float(ll.sum()),ll,pred_m,pred_P,filt_m,filt_P,innov,innov_cov,zinnov,gain,mask,jitter,"OK","",None,index)
    except (ValueError, np.linalg.LinAlgError) as exc:
        return KalmanFilterResult(float("-inf"),ll,pred_m,pred_P,filt_m,filt_P,innov,innov_cov,zinnov,gain,mask,jitter,"NUMERICAL_FAILURE",str(exc),t,index)


def rts_smoother(model: StateSpaceModel, filtered: KalmanFilterResult, psd_tolerance=1e-9) -> KalmanSmootherResult:
    if filtered.status != "OK": return KalmanSmootherResult(np.empty((0,model.state_dim)),np.empty((0,model.state_dim,model.state_dim)),np.empty((0,model.state_dim,model.state_dim)),"FILTER_FAILURE",filtered.failure_reason)
    means=filtered.filtered_mean.copy(); covs=filtered.filtered_cov.copy(); T,n=means.shape
    gains=np.zeros((max(0,T-1),n,n))
    try:
        for t in range(T-2,-1,-1):
            J=solve(filtered.predicted_cov[t+1],model.A@filtered.filtered_cov[t],assume_a="sym",check_finite=True).T
            means[t]=filtered.filtered_mean[t]+J@(means[t+1]-filtered.predicted_mean[t+1])
            covs[t]=filtered.filtered_cov[t]+J@(covs[t+1]-filtered.predicted_cov[t+1])@J.T
            covs[t]=0.5*(covs[t]+covs[t].T); _audit_covariance(covs[t],psd_tolerance); gains[t]=J
        return KalmanSmootherResult(means,covs,gains,"OK","")
    except (ValueError,np.linalg.LinAlgError) as exc:
        return KalmanSmootherResult(means,covs,gains,"NUMERICAL_FAILURE",str(exc))
