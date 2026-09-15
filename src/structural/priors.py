"""Proper native-parameter priors and stable effective-prior sampling."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from scipy.special import betaln,ndtr,ndtri
from scipy.stats import beta as beta_dist
from .matrices import system_matrices
from .parameter_transform import PARAMETER_ORDER,PERSISTENCE,EFFECT,SHOCK_SD
from .stability import stability_metrics


@dataclass(frozen=True)
class PriorSpec:
    name:str
    persistence_beta:tuple[float,float]|None=None
    effect_halfnormal_scale:float|None=None
    shock_halfnormal_scale:float|None=None
    uniform_bounded:bool=False


def prior_specs(config):
    out={}
    for name,p in config["priors"].items():
        out[name]=PriorSpec(name,tuple(p["persistence_beta"]) if "persistence_beta" in p else None,
                            p.get("effect_halfnormal_scale"),p.get("shock_halfnormal_scale"),bool(p.get("uniform_bounded",False)))
    return out


def _log_truncated_halfnormal(x,scale,lo,hi):
    if not lo<=x<=hi:return -np.inf
    mass=2.*(ndtr(hi/scale)-ndtr(lo/scale))
    return float(.5*math.log(2/math.pi)-math.log(scale)-.5*(x/scale)**2-math.log(mass))


def log_prior_native(theta,bounds,spec:PriorSpec):
    total=0.
    for name in PARAMETER_ORDER:
        x=float(theta[name]);lo,hi=bounds[name]
        if not lo<=x<=hi:return -np.inf
        if spec.uniform_bounded:total-=math.log(hi-lo)
        elif name in PERSISTENCE:
            a,b=spec.persistence_beta;u=(x-lo)/(hi-lo)
            if not 0<u<1:return -np.inf
            total+=(a-1)*math.log(u)+(b-1)*math.log1p(-u)-betaln(a,b)-math.log(hi-lo)
        elif name in EFFECT:total+=_log_truncated_halfnormal(x,spec.effect_halfnormal_scale,lo,hi)
        elif name in SHOCK_SD:total+=_log_truncated_halfnormal(x,spec.shock_halfnormal_scale,lo,hi)
    return float(total)


def _draw_halfnormal_truncated(rng,scale,lo,hi,size):
    flo=2*ndtr(lo/scale)-1;fhi=2*ndtr(hi/scale)-1
    u=rng.uniform(flo,fhi,size=size);return scale*ndtri((u+1)/2)


def draw_prior_native(spec,bounds,count,seed):
    rng=np.random.default_rng(seed);draws=np.empty((count,len(PARAMETER_ORDER)))
    for j,name in enumerate(PARAMETER_ORDER):
        lo,hi=bounds[name]
        if spec.uniform_bounded:draws[:,j]=rng.uniform(lo,hi,count)
        elif name in PERSISTENCE:
            a,b=spec.persistence_beta;draws[:,j]=lo+(hi-lo)*rng.beta(a,b,count)
        elif name in EFFECT:draws[:,j]=_draw_halfnormal_truncated(rng,spec.effect_halfnormal_scale,lo,hi,count)
        else:draws[:,j]=_draw_halfnormal_truncated(rng,spec.shock_halfnormal_scale,lo,hi,count)
    return draws


def theta_from_array(row):return {n:float(v) for n,v in zip(PARAMETER_ORDER,row)}


def stable_mask(draws,rho_n=.8):
    mask=np.zeros(len(draws),bool);radii=np.full(len(draws),np.nan)
    for i,row in enumerate(draws):
        theta=theta_from_array(row);theta["rho_n"]=float(rho_n)
        try:radii[i]=stability_metrics(system_matrices("M0_CORE5",theta)[0])["spectral_radius"];mask[i]=radii[i]<1
        except (ValueError,np.linalg.LinAlgError):pass
    return mask,radii


def effective_prior_audit(spec,bounds,count,seed,rho_n=.8):
    draws=draw_prior_native(spec,bounds,count,seed);mask,radii=stable_mask(draws,rho_n)
    return draws,mask,radii


def draw_stable_prior(spec,bounds,count,seed,rho_n=.8,batch=2048):
    accepted=[];generated=0;round_id=0
    while sum(len(x) for x in accepted)<count:
        draws=draw_prior_native(spec,bounds,batch,seed+round_id);mask,_=stable_mask(draws,rho_n);accepted.append(draws[mask]);generated+=batch;round_id+=1
        if round_id>10000:raise RuntimeError("unable to draw stable prior values")
    return np.vstack(accepted)[:count],generated
