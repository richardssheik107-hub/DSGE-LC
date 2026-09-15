"""Rank-normalized split R-hat, Geyer ESS, MCSE and chain audits."""
from __future__ import annotations
import numpy as np
from scipy.stats import norm,rankdata


def split_chains(chains):
    x=np.asarray(chains,float);m,n=x.shape[:2];half=n//2
    if half<2:raise ValueError("chains too short to split")
    return np.concatenate([x[:,:half],x[:,n-half:]],axis=0)


def _basic_rhat(chains):
    x=np.asarray(chains,float);m,n=x.shape;chain_mean=x.mean(1);W=np.mean(x.var(1,ddof=1));B=n*np.var(chain_mean,ddof=1)
    if W==0:return 1. if B==0 else np.inf
    var_plus=(n-1)/n*W+B/n;return float(np.sqrt(var_plus/W))


def _rank_normalize(x):
    ranks=rankdata(np.asarray(x).ravel(),method="average");z=norm.ppf((ranks-3/8)/(len(ranks)+1/4));return z.reshape(np.asarray(x).shape)


def rank_normalized_split_rhat(chains):
    split=split_chains(chains);rank_rhat=_basic_rhat(_rank_normalize(split));median=np.median(split);folded=_basic_rhat(_rank_normalize(np.abs(split-median)))
    return float(max(rank_rhat,folded))


def _autocovariance(x):
    x=np.asarray(x,float)-np.mean(x);n=len(x);fft=np.fft.rfft(np.concatenate([x,np.zeros_like(x)]));ac=np.fft.irfft(fft*np.conjugate(fft))[:n]
    return ac/np.arange(n,0,-1)


def effective_sample_size(chains):
    x=np.asarray(chains,float);m,n=x.shape
    if np.all(x==x.flat[0]):return float(m*n)
    acov=np.array([_autocovariance(c) for c in x]);W=np.mean(acov[:,0]);B=n*np.var(x.mean(1),ddof=1);var_plus=(n-1)/n*W+B/n
    if not np.isfinite(var_plus) or var_plus<=0:return 1.
    rho=np.ones(n);rho[1:]=1-(W-np.mean(acov[:,1:],axis=0))/var_plus
    pairs=[]
    for t in range(1,n-1,2):
        pair=rho[t]+rho[t+1]
        if pair<0:break
        pairs.append(pair)
    if pairs:
        pairs=np.minimum.accumulate(pairs);tau=-1+2*np.sum(pairs)
    else:tau=1.
    return float(min(m*n,max(1.,m*n/max(1.,tau))))


def bulk_ess(chains):return effective_sample_size(_rank_normalize(split_chains(chains)))


def tail_ess(chains):
    x=np.asarray(chains,float);flat=x.ravel();lo,hi=np.quantile(flat,[.05,.95])
    return float(min(effective_sample_size((x<=lo).astype(float)),effective_sample_size((x>=hi).astype(float))))


def diagnostic_table(theta_chains,names):
    rows=[]
    for j,name in enumerate(names):
        x=theta_chains[:,:,j];bulk=bulk_ess(x);tail=tail_ess(x);sd=float(np.std(x,ddof=1));mcse=sd/np.sqrt(bulk)
        rows.append({"parameter":name,"rhat":rank_normalized_split_rhat(x),"bulk_ess":bulk,"tail_ess":tail,"mcse":mcse,"posterior_sd":sd,"mcse_sd":mcse/sd if sd>0 else 0.})
    return rows


def acceptance_summary(results):
    rows=[]
    for i,r in enumerate(results):
        audit=r["audit"];n=len(r["accepted"]);unique=len(np.unique(r["z"],axis=0))/n
        rows.append({"chain":i+1,"production_draws":n,"warmup_acceptance":r["warmup_acceptance"],"production_acceptance":float(r["accepted"].mean()),
                     "max_rejection_streak":r["max_rejection_streak"],"unique_state_fraction":unique,"unstable_rejection_fraction":audit.unstable/max(1,audit.proposals),
                     "invalid_rejection_fraction":audit.invalid/max(1,audit.proposals),"guard_rejections":audit.guard,"kalman_failures":audit.kalman_failures,
                     "nonfinite":audit.nonfinite,"nonzero_jitter_states":audit.nonzero_jitter})
    return rows


def convergence_pass(rows,config):
    return bool(all(r["rhat"]<=config["rhat_threshold"] and r["bulk_ess"]>=config["bulk_ess_threshold"] and r["tail_ess"]>=config["tail_ess_threshold"] and r["mcse_sd"]<=config["mcse_sd_threshold"] for r in rows))
