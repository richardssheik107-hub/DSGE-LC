"""Proper conditional profile-likelihood utilities."""
from __future__ import annotations
import numpy as np
from .estimation import EstimationObjective,optimize_start
from .parameter_transform import PARAMETER_ORDER,ParameterTransform,boundary_diagnostics


def profile_transform(base_transform,parameter,value):
    if parameter not in base_transform.free_parameters:raise ValueError("profile target must be free")
    fixed=dict(base_transform.fixed);fixed[parameter]=float(value)
    free=tuple(n for n in base_transform.free_parameters if n!=parameter)
    return ParameterTransform(base_transform.bounds,free,tuple(fixed.items()))


def profile_point(base_transform,observations,parameter,value,starts,*,rho_n=.8,battery_sd=.25,penalty=1e10,maxiter=500,ftol=1e-10,z_bound=8.,kalman_options=None):
    transform=profile_transform(base_transform,parameter,value);results=[]
    for i,(source,theta) in enumerate(starts):
        exact=dict(theta);exact[parameter]=float(value)
        obj=EstimationObjective(transform,observations,rho_n,battery_sd,"mle",penalty,kalman_options)
        results.append(optimize_start(obj,exact,i,source,"L-BFGS-B",maxiter,ftol,z_bound))
    valid=[r for r in results if r["valid"]]
    if not valid:return {"parameter":parameter,"fixed_value":value,"profile_loglik":-np.inf,"optimizer_success":False,"spectral_radius":np.nan,"boundary_flags":"","nfev":sum(r["nfev"] for r in results),"theta":None,"disagreement":True}
    best=max(valid,key=lambda r:r["loglik"]);spread=max(r["loglik"] for r in valid)-min(r["loglik"] for r in valid)
    flags=[r["parameter"] for r in boundary_diagnostics(best["theta"],base_transform.bounds) if r["boundary_flag"]]
    return {"parameter":parameter,"fixed_value":float(value),"profile_loglik":best["loglik"],"optimizer_success":best["success"],
            "spectral_radius":best["spectral_radius"],"boundary_flags":";".join(flags),"nfev":sum(r["nfev"] for r in results),
            "theta":best["theta"],"disagreement":bool(spread>1e-3),"optimizer_loglik_spread":spread}


def run_profile(base_transform,observations,parameter,grid,global_theta,**kwargs):
    rows=[];neighbor=global_theta
    for value in grid:
        starts=[("global_mle",global_theta),("neighbor_profile",neighbor)]
        row=profile_point(base_transform,observations,parameter,float(value),starts,**kwargs);rows.append(row)
        if row["theta"] is not None:neighbor=row["theta"]
    return rows


def summarize_profile(rows,global_loglik,support_delta=1.92):
    ordered=sorted(rows,key=lambda r:r["fixed_value"])
    values=np.array([r["fixed_value"] for r in ordered]);ll=np.array([r["profile_loglik"] for r in ordered])
    delta=global_loglik-ll;support=np.isfinite(ll)&(delta<=support_delta)
    finite=np.isfinite(ll);near_top=finite&(delta<1.)
    flat=bool(near_top.sum()>=max(3,int(np.ceil(.5*len(rows)))))
    open_boundary=bool(support.any() and (support[0] or support[-1]))
    peaks=0
    for i in range(1,len(ll)-1):
        if np.isfinite(ll[i]) and ll[i]>ll[i-1]+1e-3 and ll[i]>ll[i+1]+1e-3:peaks+=1
    return {"parameter":ordered[0]["parameter"],"support_low":float(values[support].min()) if support.any() else np.nan,
            "support_high":float(values[support].max()) if support.any() else np.nan,"support_boundary_open":open_boundary,
            "flat_profile":flat,"multimodal_profile":peaks>1,"local_peak_count":peaks,"max_delta_under_grid":float(np.nanmax(delta[finite])),
            "classification":"MULTIMODAL_PROFILE" if peaks>1 else "BOUNDARY_OPEN_PROFILE" if open_boundary else "FLAT_PROFILE" if flat else "PROFILE_INFORMATIVE"}


def attach_profile_deltas(rows,global_loglik):
    for row in rows:row["delta_loglik_from_global"]=float(global_loglik-row["profile_loglik"])
    return rows
