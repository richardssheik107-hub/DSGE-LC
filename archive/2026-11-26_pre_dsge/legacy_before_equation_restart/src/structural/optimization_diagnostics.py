"""Deterministic starts, distances, solution clustering and ridge diagnostics."""
from __future__ import annotations
import numpy as np
from scipy.stats import qmc
from .matrices import system_matrices
from .parameter_transform import PARAMETER_ORDER
from .stability import stability_metrics


def normalized_parameter_distance(a, b, bounds, names=PARAMETER_ORDER):
    delta=[(float(a[n])-float(b[n]))/(bounds[n][1]-bounds[n][0]) for n in names]
    return float(np.linalg.norm(delta))


def is_stable_theta(theta, rho_n=.8):
    p=dict(theta);p["rho_n"]=float(rho_n)
    try: return bool(stability_metrics(system_matrices("M0_CORE5",p)[0])["stable"])
    except (ValueError,np.linalg.LinAlgError): return False


def generate_stable_starts(transform, baseline, count, seed, rho_n=.8):
    """Baseline, seven deterministic neighbors, then stable scrambled LHS starts."""
    if count < 1: return [], {"generated":0,"stable":0,"rejected_unstable":0}
    starts=[]; seen=set(); generated=rejected=0
    def add(theta, source):
        nonlocal generated,rejected
        generated += 1
        candidate={n:float(theta[n]) for n in PARAMETER_ORDER}
        key=tuple(round(candidate[n],12) for n in PARAMETER_ORDER)
        if key in seen: return
        if not is_stable_theta(candidate,rho_n): rejected += 1; return
        seen.add(key); starts.append({"theta":candidate,"source":source})
    add(baseline,"baseline")
    base_z=np.clip(transform.theta_to_unconstrained(baseline),-6,6)
    patterns=(.25,-.25,.5,-.5,.75,-.75,1.0)
    for i,scale in enumerate(patterns):
        direction=np.sin(np.arange(len(base_z))+1+i)
        add(transform.unconstrained_to_theta(np.clip(base_z+scale*direction,-6,6)),f"baseline_neighbor_{i+1}")
        if len(starts)>=count: break
    batch=64; round_id=0
    while len(starts)<count:
        sampler=qmc.LatinHypercube(d=len(PARAMETER_ORDER),seed=seed+round_id)
        values=sampler.random(batch); round_id+=1
        for u in values:
            theta={n:transform.bounds[n][0]+(transform.bounds[n][1]-transform.bounds[n][0])*float(v) for n,v in zip(PARAMETER_ORDER,u)}
            if transform.fixed: theta.update(transform.fixed)
            add(theta,"stable_lhs")
            if len(starts)>=count: break
        if round_id>1000: raise RuntimeError("unable to generate requested stable starts")
    return starts[:count],{"generated":generated,"stable":len(starts[:count]),"rejected_unstable":rejected}


def cluster_solutions(solutions,bounds,ll_tol=.001,distance_tol=.05):
    valid=[s for s in solutions if s.get("valid") and np.isfinite(s.get("loglik",np.nan))]
    valid=sorted(valid,key=lambda x:-x["loglik"]); clusters=[]
    for solution in valid:
        assigned=None
        for i,c in enumerate(clusters):
            if abs(solution["loglik"]-c[0]["loglik"])<=ll_tol and normalized_parameter_distance(solution["theta"],c[0]["theta"],bounds)<=distance_tol:
                assigned=i;break
        if assigned is None: clusters.append([solution])
        else: clusters[assigned].append(solution)
    rows=[]
    for i,c in enumerate(clusters,1):
        rows.append({"cluster":i,"size":len(c),"best_loglik":max(x["loglik"] for x in c),
                     "worst_loglik":min(x["loglik"] for x in c),"representative_start":c[0]["start_id"],
                     "distance_from_best":normalized_parameter_distance(c[0]["theta"],clusters[0][0]["theta"],bounds)})
    return rows


def detect_ridge(solutions,bounds,ll_tol=1.,distance_threshold=.2):
    valid=sorted([s for s in solutions if s.get("valid")],key=lambda x:-x["loglik"])
    if not valid:return False,[]
    best=valid[0];pairs=[]
    for s in valid[1:]:
        dll=best["loglik"]-s["loglik"];distance=normalized_parameter_distance(best["theta"],s["theta"],bounds)
        if dll<=ll_tol and distance>distance_threshold:pairs.append({"start_id":s["start_id"],"delta_loglik":dll,"distance":distance})
    return bool(pairs),pairs
