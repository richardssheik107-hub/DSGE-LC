"""Posterior summaries, boundaries, contraction, sensitivity and PPC moments."""
from __future__ import annotations
import numpy as np
from .parameter_transform import PARAMETER_ORDER


def posterior_summary(theta_chains,diagnostics,bounds,boundary_fraction=.02):
    pooled=np.asarray(theta_chains).reshape(-1,len(PARAMETER_ORDER));diag={r["parameter"]:r for r in diagnostics};rows=[]
    for j,name in enumerate(PARAMETER_ORDER):
        x=pooled[:,j];q=np.quantile(x,[.025,.05,.25,.5,.75,.95,.975]);lo,hi=bounds[name];width=hi-lo
        rows.append({"parameter":name,"mean":float(x.mean()),"median":float(q[3]),"sd":float(x.std(ddof=1)),"q025":q[0],"q05":q[1],"q25":q[2],"q50":q[3],"q75":q[4],"q95":q[5],"q975":q[6],
                     "lower_boundary_mass":float(np.mean(x<lo+boundary_fraction*width)),"upper_boundary_mass":float(np.mean(x>hi-boundary_fraction*width)),**diag[name]})
    return rows


def posterior_correlation(theta_chains,names=PARAMETER_ORDER,threshold=.9):
    pooled=np.asarray(theta_chains).reshape(-1,len(names));corr=np.corrcoef(pooled,rowvar=False);pairs=[]
    for i in range(len(names)):
        for j in range(i+1,len(names)):
            if abs(corr[i,j])>threshold:pairs.append({"parameter_1":names[i],"parameter_2":names[j],"correlation":float(corr[i,j]),"absolute_correlation":float(abs(corr[i,j]))})
    return corr,pairs


def covariance_weak_directions(theta_chains,names=PARAMETER_ORDER,count=3):
    pooled=np.asarray(theta_chains).reshape(-1,len(names));cov=np.cov(pooled,rowvar=False);eigval,eigvec=np.linalg.eigh(cov);rows=[]
    for k in range(min(count,len(names))):
        idx=np.argsort(np.abs(eigvec[:,k]))[-3:][::-1];rows.append({"direction":k+1,"eigenvalue":float(eigval[k]),"largest_loadings":";".join(f"{names[j]}:{eigvec[j,k]:.6g}" for j in idx)})
    return rows


def prior_posterior_contraction(prior_draws,summary,names=PARAMETER_ORDER):
    prior=np.asarray(prior_draws);s={r["parameter"]:r for r in summary};rows=[]
    for j,name in enumerate(names):
        psd=float(prior[:,j].std(ddof=1));post=s[name]["sd"];rows.append({"parameter":name,"prior_sd":psd,"posterior_sd":post,"contraction_ratio":post/psd})
    return rows


def sensitivity_shift(baseline_summary,other_summary,label):
    base={r["parameter"]:r for r in baseline_summary};other={r["parameter"]:r for r in other_summary};rows=[]
    for name in PARAMETER_ORDER:
        shift=(other[name]["median"]-base[name]["median"])/base[name]["sd"]
        overlap=max(0.,min(base[name]["q975"],other[name]["q975"])-max(base[name]["q025"],other[name]["q025"]))
        union=max(base[name]["q975"],other[name]["q975"])-min(base[name]["q025"],other[name]["q025"])
        rows.append({"specification":label,"parameter":name,"baseline_median":base[name]["median"],"sensitivity_median":other[name]["median"],"standardized_posterior_shift":shift,
                     "credible_interval_overlap_ratio":overlap/union if union>0 else 1.,"lower_boundary_mass_change":other[name]["lower_boundary_mass"]-base[name]["lower_boundary_mass"]})
    return rows


def spectral_radius_summary(component_chains,threshold=.98):
    radius=np.asarray(component_chains)[:,:,4].ravel();return {"median":float(np.median(radius)),"q95":float(np.quantile(radius,.95)),"q99":float(np.quantile(radius,.99)),"max":float(radius.max()),"near_instability_mass":float(np.mean(radius>threshold))}


def identification_classifications(summary,contraction,sensitivity_rows,low=.25,high=.5,prior_draws=None,fixed_rows=None):
    c={r["parameter"]:r["contraction_ratio"] for r in contraction};maxshift={n:0. for n in PARAMETER_ORDER};maxfixed={n:0. for n in PARAMETER_ORDER}
    for r in sensitivity_rows:maxshift[r["parameter"]]=max(maxshift[r["parameter"]],abs(r["standardized_posterior_shift"]))
    for r in fixed_rows or ():maxfixed[r["parameter"]]=max(maxfixed[r["parameter"]],abs(r["standardized_posterior_shift"]))
    prior_median={n:np.nan for n in PARAMETER_ORDER}
    if prior_draws is not None:
        values=np.asarray(prior_draws,float);prior_median={n:float(np.median(values[:,j])) for j,n in enumerate(PARAMETER_ORDER)}
    rows=[]
    for row in summary:
        name=row["parameter"];ratio=c[name];shift=maxshift[name];fixed=maxfixed[name];boundary=max(row["lower_boundary_mass"],row["upper_boundary_mass"])
        if shift>high or fixed>1 or boundary>.25:classification="WEAK_OR_PRIOR_SENSITIVE"
        elif ratio<.6 and shift<=low and fixed<=.5 and boundary<.10:classification="DATA_INFORMATIVE"
        else:classification="PARTIALLY_INFORMATIVE"
        rows.append({"parameter":name,"prior_median":prior_median[name],"posterior_median":row["median"],"posterior_sd":row["sd"],
                     "q025":row["q025"],"q975":row["q975"],"rhat":row["rhat"],"bulk_ess":row["bulk_ess"],"tail_ess":row["tail_ess"],
                     "contraction_ratio":ratio,"lower_boundary_mass":row["lower_boundary_mass"],"upper_boundary_mass":row["upper_boundary_mass"],
                     "max_prior_sensitivity_shift":shift,"max_fixed_assumption_shift":fixed,"classification":classification})
    return rows


def observable_moments(values):
    y=np.asarray(values,float);rows=[]
    for j in range(y.shape[1]):rows.append({"channel":j,"variance":float(np.var(y[:,j],ddof=1)),"lag1_autocorrelation":float(np.corrcoef(y[1:,j],y[:-1,j])[0,1])})
    corr=np.corrcoef(y,rowvar=False)
    return rows,{"corr_spot_cost":float(corr[0,1]),"corr_spot_output":float(corr[0,2]),"corr_spot_battery":float(corr[0,3]),
                 "lag1_spot_cost":float(np.corrcoef(y[1:,0],y[:-1,1])[0,1]),"lag1_spot_output":float(np.corrcoef(y[1:,0],y[:-1,2])[0,1]),
                 "lag1_spot_battery":float(np.corrcoef(y[1:,0],y[:-1,3])[0,1])}
