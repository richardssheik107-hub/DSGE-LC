"""Phase 2C objective wrappers and constrained deterministic mode search."""
from __future__ import annotations
from dataclasses import dataclass,field
import math
import numpy as np
from scipy.optimize import minimize
from .likelihood import evaluate_m0_likelihood
from .matrices import system_matrices
from .stability import stability_metrics


@dataclass
class ObjectiveAudit:
    evaluations:int=0; valid_evaluations:int=0; unstable_evaluations:int=0
    invalid_evaluations:int=0; kalman_failures:int=0; nonfinite_evaluations:int=0
    max_jitter:float=0.; statuses:dict[str,int]=field(default_factory=dict)
    def record(self,status,jitter=0.):
        self.evaluations+=1;self.statuses[status]=self.statuses.get(status,0)+1
        if status=="OK":self.valid_evaluations+=1
        elif status=="UNSTABLE_EVALUATION":self.unstable_evaluations+=1
        elif status=="INVALID_EVALUATION":self.invalid_evaluations+=1
        else:self.kalman_failures+=1
        if np.isfinite(jitter):self.max_jitter=max(self.max_jitter,float(jitter))


def logprior_native(theta):
    """Documented weak diagnostic prior in native theta space; no Jacobian."""
    total=0.
    for n in ("rho_d","rho_c","rho_q","rho_p"):
        x=float(theta[n])
        if not 0<x<1:return -np.inf
        total += .5*math.log(x)+.5*math.log(1-x)-math.lgamma(1.5)*2+math.lgamma(3.)
    constant=.5*math.log(2/math.pi)
    for n in ("a_p","a_c","b_d","b_c","b_q","b_n","sigma_d","sigma_c","sigma_q","sigma_p"):
        x=float(theta[n])
        if x<0:return -np.inf
        total += constant-.5*x*x
    return float(total)


class EstimationObjective:
    def __init__(self,transform,observations,rho_n=.8,battery_sd=.25,kind="mle",penalty=1e10,kalman_options=None):
        self.transform=transform;self.y=np.asarray(observations,float);self.rho_n=float(rho_n);self.battery_sd=float(battery_sd)
        self.kind=kind;self.penalty=float(penalty);self.kalman_options=kalman_options or {};self.audit=ObjectiveAudit()
    def evaluate_theta(self,theta,return_result=False):
        p=dict(theta);p["rho_n"]=self.rho_n
        try:
            radius=float(stability_metrics(system_matrices("M0_CORE5",p)[0])["spectral_radius"])
        except Exception:
            self.audit.record("INVALID_EVALUATION");return (self.penalty,None) if return_result else self.penalty
        if not np.isfinite(radius) or radius>=1:
            self.audit.record("UNSTABLE_EVALUATION");value=self.penalty+1e6*max(0.,radius-1.)
            return (value,None) if return_result else value
        result=evaluate_m0_likelihood(p,self.battery_sd,self.y,**self.kalman_options)
        if result.status!="OK" or not np.isfinite(result.loglik):
            status="KALMAN_FAILURE" if result.status!="INVALID_PARAMETERS" else "INVALID_EVALUATION";self.audit.record(status)
            return (self.penalty,None) if return_result else self.penalty
        jitter=float(np.nanmax(result.filter_result.jitter_used));self.audit.record("OK",jitter)
        value=-result.loglik
        if self.kind=="map":
            prior=logprior_native(theta)
            if not np.isfinite(prior):value=self.penalty
            else:value-=prior
        return (float(value),result) if return_result else float(value)
    def __call__(self,z): return self.evaluate_theta(self.transform.unconstrained_to_theta(z))


def optimize_start(objective,start_theta,start_id=0,source="",method="L-BFGS-B",maxiter=500,ftol=1e-10,z_bound=8.):
    z0=np.clip(objective.transform.theta_to_unconstrained(start_theta),-z_bound,z_bound)
    options={"maxiter":maxiter}
    if method=="L-BFGS-B":options["ftol"]=ftol
    iteration_objectives=[]
    def callback(xk):iteration_objectives.append(float(objective(np.asarray(xk,float))))
    result=minimize(objective,z0,method=method,bounds=[(-z_bound,z_bound)]*len(z0),options=options,callback=callback)
    theta=objective.transform.unconstrained_to_theta(result.x);value,lik=objective.evaluate_theta(theta,True)
    radius=np.nan
    try:radius=stability_metrics(system_matrices("M0_CORE5",{**theta,"rho_n":objective.rho_n})[0])["spectral_radius"]
    except Exception:pass
    jac=getattr(result,"jac",None);gnorm=float(np.linalg.norm(jac)) if jac is not None else np.nan
    projected=np.asarray(jac,float).copy() if jac is not None else None
    if projected is not None:
        projected[(result.x<=-z_bound+1e-8)&(projected>0)]=0.
        projected[(result.x>= z_bound-1e-8)&(projected<0)]=0.
    pgnorm=float(np.linalg.norm(projected)) if projected is not None else np.nan
    final_improvement=abs(iteration_objectives[-1]-iteration_objectives[-2]) if len(iteration_objectives)>=2 else np.nan
    recent=np.max(np.abs(np.diff(iteration_objectives[-6:]))) if len(iteration_objectives)>=2 else np.nan
    return {"start_id":start_id,"start_source":source,"method":method,"success":bool(result.success),"status":int(result.status),
            "message":str(result.message),"iterations":int(getattr(result,"nit",0)),"nfev":int(result.nfev),"gradient_norm":gnorm,
            "objective":float(value),"loglik":float(lik.loglik) if lik else -np.inf,"valid":lik is not None,"spectral_radius":float(radius),
            "max_jitter":float(np.nanmax(lik.filter_result.jitter_used)) if lik else np.nan,"theta":theta,
            "projected_gradient_norm":pgnorm,"final_step_objective_improvement":float(final_improvement),
            "recent_objective_improvement":float(recent),"terminated_at_iteration_cap":bool(int(result.status)==1 and ("ITERATION" in str(result.message).upper() or "LIMIT" in str(result.message).upper())),
            "prior":logprior_native(theta) if objective.kind=="map" else 0.,"audit":objective.audit}


def run_multistart(transform,observations,starts,*,rho_n=.8,battery_sd=.25,kind="mle",penalty=1e10,maxiter=500,ftol=1e-10,z_bound=8.,kalman_options=None):
    rows=[]
    for i,start in enumerate(starts):
        objective=EstimationObjective(transform,observations,rho_n,battery_sd,kind,penalty,kalman_options)
        rows.append(optimize_start(objective,start["theta"],i,start.get("source",""),"L-BFGS-B",maxiter,ftol,z_bound))
    return rows


def information_criteria(loglik,k,n):
    aic=-2*loglik+2*k;correction=2*k*(k+1)/(n-k-1)
    return {"AIC":aic,"AICc":aic+correction,"AICc_penalty":correction,"BIC":-2*loglik+k*np.log(n)}
