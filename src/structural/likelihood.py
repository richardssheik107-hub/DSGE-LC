"""Fixed-parameter Gaussian innovation likelihood evaluation; no optimizer."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .kalman import KalmanFilterResult, kalman_filter
from .state_space import StateSpaceModel, from_phase2a_parameters
from .stability import stability_metrics


@dataclass
class LikelihoodResult:
    loglik: float
    status: str
    failure_reason: str
    filter_result: KalmanFilterResult | None


def validate_m0_parameters(p: dict[str,float], battery_sd: float) -> tuple[bool,str]:
    for name in ("rho_d","rho_c","rho_q","rho_p"):
        if not 0 < p.get(name,np.nan) < 1: return False,f"INVALID_{name}"
    for name in ("a_p","a_c","b_d","b_c","b_q","b_n"):
        if not p.get(name,np.nan) >= 0: return False,f"INVALID_{name}"
    for name in ("sigma_d","sigma_c","sigma_q","sigma_p"):
        if not p.get(name,np.nan) > 0: return False,f"INVALID_{name}"
    if not 0 <= p.get("rho_n",np.nan) < 1: return False,"INVALID_rho_n"
    if not battery_sd > 0: return False,"INVALID_battery_sd"
    try:
        model=from_phase2a_parameters("M0_CORE5",p,battery_sd)
    except ValueError as exc: return False,str(exc)
    if not stability_metrics(model.A)["stable"]: return False,"UNSTABLE_PARAMETERS"
    return True,""


def gaussian_loglikelihood(model: StateSpaceModel, observations: np.ndarray, **kwargs) -> LikelihoodResult:
    result=kalman_filter(model,observations,**kwargs)
    return LikelihoodResult(result.loglik,"OK" if result.status=="OK" else result.status,result.failure_reason,result)


def evaluate_m0_likelihood(p: dict[str,float], battery_sd: float, observations: np.ndarray, **kwargs) -> LikelihoodResult:
    valid,reason=validate_m0_parameters(p,battery_sd)
    if not valid: return LikelihoodResult(float("-inf"),"UNSTABLE_PARAMETERS" if "UNSTABLE" in reason else "INVALID_PARAMETERS",reason,None)
    return gaussian_loglikelihood(from_phase2a_parameters("M0_CORE5",p,battery_sd),observations,**kwargs)
