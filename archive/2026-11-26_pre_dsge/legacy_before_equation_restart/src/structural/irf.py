"""Posterior impulse responses for the frozen structural A/B convention."""
from __future__ import annotations
import numpy as np

STATE_ORDER=("d","c","q","n","p")
SHOCK_ORDER=("demand","cost","supply","price")

def impulse_response(A,B,max_horizon=24):
    A=np.asarray(A,float);B=np.asarray(B,float);out=np.empty((max_horizon+1,A.shape[0],B.shape[1]));out[0]=B
    for h in range(1,max_horizon+1):out[h]=A@out[h-1]
    return out

def observation_response(state_irf,H):return np.einsum("...s,os->...o",np.asarray(state_irf,float),np.asarray(H,float))

def posterior_irf_summary(values,shock,state_names=STATE_ORDER,quantiles=(.05,.16,.5,.84,.95)):
    x=np.asarray(values,float);q=np.quantile(x,quantiles,axis=0);rows=[]
    for h in range(x.shape[1]):
        for i,state in enumerate(state_names):rows.append({"shock":shock,"state":state,"horizon":h,"q05":q[0,h,i],"q16":q[1,h,i],"median":q[2,h,i],"q84":q[3,h,i],"q95":q[4,h,i],"mean":x[:,h,i].mean(),"sd":x[:,h,i].std(ddof=1),"p_plus":np.mean(x[:,h,i]>0),"p_minus":np.mean(x[:,h,i]<0)})
    return rows

def sign_probability(values):
    x=np.asarray(values,float);return float(np.mean(x>0)),float(np.mean(x<0))

def peak_timing(price_irfs):
    x=np.asarray(price_irfs,float);idx=np.argmax(np.abs(x),axis=1);peak=x[np.arange(len(x)),idx]
    return idx,peak

def persistence_metric(price_irfs):
    x=np.asarray(price_irfs,float);den=np.max(np.abs(x),axis=1);return np.divide(np.abs(x[:,-1]),den,out=np.zeros_like(den),where=den>0)
