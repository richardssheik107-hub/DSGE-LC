"""Auditable adaptive random-walk Metropolis in unconstrained coordinates."""
from __future__ import annotations
from dataclasses import dataclass,field
import numpy as np
from .likelihood import evaluate_m0_likelihood
from .matrices import system_matrices
from .priors import log_prior_native
from .stability import stability_metrics


@dataclass(frozen=True)
class PosteriorEvaluation:
    total:float;loglik:float;logprior:float;logjacobian:float;status:str
    spectral_radius:float=np.nan;max_jitter:float=np.nan


@dataclass
class SamplerAudit:
    proposals:int=0;accepted:int=0;unstable:int=0;invalid:int=0;guard:int=0
    kalman_failures:int=0;nonfinite:int=0;nonzero_jitter:int=0
    rejection_reasons:dict[str,int]=field(default_factory=dict)
    def reject(self,reason):
        self.rejection_reasons[reason]=self.rejection_reasons.get(reason,0)+1
        if reason=="UNSTABLE":self.unstable+=1
        elif reason=="NUMERICAL_GUARD":self.guard+=1
        elif reason=="KALMAN_FAILURE":self.kalman_failures+=1
        elif reason=="NONFINITE":self.nonfinite+=1
        else:self.invalid+=1


def log_transform_jacobian(z,transform):
    z=np.asarray(z,float);width=np.array([transform.bounds[n][1]-transform.bounds[n][0] for n in transform.free_parameters])
    return float(np.log(width).sum()-np.logaddexp(0.,-z).sum()-np.logaddexp(0.,z).sum())


class PosteriorTarget:
    def __init__(self,transform,observations,prior,rho_n=.8,battery_sd=.25,guard=30.,kalman_options=None):
        self.transform=transform;self.y=np.asarray(observations,float);self.prior=prior;self.rho_n=float(rho_n);self.battery_sd=float(battery_sd);self.guard=float(guard);self.kalman_options=kalman_options or {}
    def __call__(self,z):
        z=np.asarray(z,float)
        if not np.isfinite(z).all() or np.max(np.abs(z))>self.guard:return PosteriorEvaluation(-np.inf,-np.inf,-np.inf,-np.inf,"NUMERICAL_GUARD")
        theta=self.transform.unconstrained_to_theta(z);p={**theta,"rho_n":self.rho_n}
        lp=log_prior_native(theta,self.transform.bounds,self.prior)
        if not np.isfinite(lp):return PosteriorEvaluation(-np.inf,-np.inf,lp,-np.inf,"INVALID_PRIOR")
        try:radius=float(stability_metrics(system_matrices("M0_CORE5",p)[0])["spectral_radius"])
        except Exception:return PosteriorEvaluation(-np.inf,-np.inf,lp,-np.inf,"INVALID")
        if radius>=1:return PosteriorEvaluation(-np.inf,-np.inf,lp,-np.inf,"UNSTABLE",radius)
        result=evaluate_m0_likelihood(p,self.battery_sd,self.y,**self.kalman_options)
        if result.status!="OK" or not np.isfinite(result.loglik):return PosteriorEvaluation(-np.inf,result.loglik,lp,-np.inf,"KALMAN_FAILURE",radius)
        lj=log_transform_jacobian(z,self.transform);jitter=float(np.nanmax(result.filter_result.jitter_used));total=result.loglik+lp+lj
        return PosteriorEvaluation(float(total),float(result.loglik),float(lp),lj,"OK",radius,jitter)


def random_walk_proposal(z,chol,scale,rng,mixture_probability=.9,small_scale=.1):
    if rng.random()<mixture_probability:return z+scale*(chol@rng.normal(size=len(z)))
    return z+small_scale*rng.normal(size=len(z))


def _run_steps(target,z,current,n,rng,chol,scale,mixture_probability,small_scale,audit,adapt=False,target_accept=.234,ridge=1e-6):
    d=len(z);zs=np.empty((n,d));theta=np.empty((n,d));components=np.empty((n,5));accepted=np.zeros(n,bool)
    mean=z.copy();scatter=np.zeros((d,d));log_scale=np.log(scale);proposal_chol=chol.copy()
    max_streak=0;streak=0
    for i in range(n):
        candidate=random_walk_proposal(z,proposal_chol,np.exp(log_scale),rng,mixture_probability,small_scale);evaluation=target(candidate);audit.proposals+=1
        accept=False
        if evaluation.status=="OK":accept=np.log(rng.random())<min(0.,evaluation.total-current.total)
        else:audit.reject(evaluation.status)
        if accept:z=candidate;current=evaluation;audit.accepted+=1;accepted[i]=True;streak=0
        else:streak+=1;max_streak=max(max_streak,streak)
        zs[i]=z;theta[i]=np.array(list(target.transform.unconstrained_to_theta(z).values()));components[i]=[current.total,current.loglik,current.logprior,current.logjacobian,current.spectral_radius]
        if current.max_jitter>0:audit.nonzero_jitter+=1
        if adapt:
            eta=min(.01,(i+10.)**-.6);log_scale+=eta*((1. if accept else 0.)-target_accept)
            delta=z-mean;mean+=delta/(i+1);scatter+=np.outer(delta,z-mean)
            if i>=max(100,d*20) and (i+1)%50==0:
                cov=scatter/max(1,i)+np.eye(d)*ridge;proposal_chol=np.linalg.cholesky(cov)
    kernel={"chol":proposal_chol,"scale":float(np.exp(log_scale)),"mixture_probability":mixture_probability,"small_scale":small_scale,"max_rejection_streak":max_streak}
    return z,current,zs,theta,components,accepted,kernel


def run_adaptive_chain(target,start_z,warmup_draws,production_draws,seed,*,target_accept=.234,mixture_probability=.9,ridge=1e-6,small_scale=.1,initial_chol=None,initial_scale=None):
    rng=np.random.default_rng(seed);z=np.asarray(start_z,float);current=target(z)
    if current.status!="OK":raise ValueError(f"invalid chain start: {current.status}")
    audit=SamplerAudit();chol=np.eye(len(z)) if initial_chol is None else np.asarray(initial_chol,float);initial_scale=.15 if initial_scale is None else float(initial_scale)
    z,current,*warm= _run_steps(target,z,current,warmup_draws,rng,chol,initial_scale,mixture_probability,small_scale,audit,True,target_accept,ridge)
    frozen=warm[-1];warm_accept=warm[-2]
    audit_prod=SamplerAudit();z,current,zs,theta,comp,accepted,kernel=_run_steps(target,z,current,production_draws,rng,frozen["chol"],frozen["scale"],frozen["mixture_probability"],frozen["small_scale"],audit_prod,False,target_accept,ridge)
    return {"z":zs,"theta":theta,"components":comp,"accepted":accepted,"warmup_acceptance":float(np.mean(warm_accept)),"audit":audit_prod,
            "kernel":frozen,"last_z":z,"last_evaluation":current,"rng_state":rng.bit_generator.state,"max_rejection_streak":kernel["max_rejection_streak"]}


def extend_chain(target,result,draws,seed=None):
    rng=np.random.default_rng(seed);rng.bit_generator.state=result["rng_state"];audit=SamplerAudit();k=result["kernel"]
    z,current,zs,theta,comp,accepted,kernel=_run_steps(target,result["last_z"],result["last_evaluation"],draws,rng,k["chol"],k["scale"],k["mixture_probability"],k["small_scale"],audit,False)
    additions={"z":zs,"theta":theta,"components":comp,"accepted":accepted}
    for key,new_values in additions.items():result[key]=np.concatenate([result[key],new_values],axis=0)
    for key in ("proposals","accepted","unstable","invalid","guard","kalman_failures","nonfinite","nonzero_jitter"):setattr(result["audit"],key,getattr(result["audit"],key)+getattr(audit,key))
    result.update(last_z=z,last_evaluation=current,rng_state=rng.bit_generator.state,max_rejection_streak=max(result["max_rejection_streak"],kernel["max_rejection_streak"]))
    return result
