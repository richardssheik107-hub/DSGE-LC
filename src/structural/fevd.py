"""Structural-column FEVD without secondary orthogonalization."""
from __future__ import annotations
import numpy as np

def structural_fevd(A,B,horizons=(1,3,6,12,24)):
    A=np.asarray(A,float);B=np.asarray(B,float);horizons=tuple(horizons);responses=B.copy();cumulative=np.zeros((A.shape[0],B.shape[1]));shares=[];contrib=[]
    for h in range(max(horizons)):
        cumulative+=responses**2
        if h+1 in horizons:
            total=cumulative.sum(1);shares.append(np.divide(cumulative,total[:,None],out=np.zeros_like(cumulative),where=total[:,None]>0));contrib.append(cumulative.copy())
        responses=A@responses
    return np.stack(shares,axis=0),np.stack(contrib,axis=0)

def posterior_fevd_summary(values,horizons,state_names,shock_names):
    x=np.asarray(values,float);q=np.quantile(x,[.05,.5,.95],axis=0);rows=[]
    for k,H in enumerate(horizons):
        for i,state in enumerate(state_names):
            for j,shock in enumerate(shock_names):rows.append({"state":state,"shock":shock,"horizon":H,"q05":q[0,k,i,j],"median":q[1,k,i,j],"q95":q[2,k,i,j],"mean":x[:,k,i,j].mean(),"sd":x[:,k,i,j].std(ddof=1)})
    return rows

def forecast_variance_identity_check(A,B,horizon):
    A=np.asarray(A,float);B=np.asarray(B,float);W=B@B.T;power=np.eye(A.shape[0]);cov=np.zeros_like(W);columns=np.zeros(A.shape[0])
    for _ in range(horizon):cov+=power@W@power.T;columns+=np.sum((power@B)**2,axis=1);power=A@power
    return float(np.max(np.abs(np.diag(cov)-columns)))

def residual_dominance(price_shares,moderate=.5,high=.7):
    value=float(np.median(np.asarray(price_shares)));return "HIGH_RESIDUAL_DOMINANCE" if value>high else "MODERATE_RESIDUAL_DOMINANCE" if value>=moderate else "LOW_RESIDUAL_DOMINANCE"
