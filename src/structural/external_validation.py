"""External-validation helpers for latent structural states."""
from __future__ import annotations

import numpy as np
from scipy.stats import rankdata


def rowwise_pearson(paths: np.ndarray, target: np.ndarray) -> np.ndarray:
    x=np.asarray(paths,float); y=np.asarray(target,float)
    if x.ndim!=2 or y.ndim!=1 or x.shape[1]!=len(y):
        raise ValueError("shape mismatch")
    xc=x-x.mean(axis=1,keepdims=True); yc=y-y.mean()
    den=np.sqrt(np.sum(xc*xc,axis=1)*np.sum(yc*yc))
    if np.any(den<=0): raise ValueError("zero variance")
    return np.sum(xc*yc,axis=1)/den


def rowwise_spearman(paths: np.ndarray, target: np.ndarray) -> np.ndarray:
    x=np.asarray(paths,float); y=np.asarray(target,float)
    return rowwise_pearson(rankdata(x,axis=1),rankdata(y))


def correlation_summary(values: np.ndarray) -> dict[str,float]:
    v=np.asarray(values,float)
    if v.ndim!=1 or not np.isfinite(v).all(): raise ValueError("invalid correlations")
    q=np.quantile(v,[.05,.16,.50,.84,.95])
    return {"q05":float(q[0]),"q16":float(q[1]),"median":float(q[2]),
            "q84":float(q[3]),"q95":float(q[4]),"p_positive":float(np.mean(v>0))}


def validation_strength(summary: dict[str,float]) -> str:
    if summary["q05"]>0: return "STRONG_POSITIVE"
    if summary["median"]>0 and summary["p_positive"]>=.90: return "MODERATE_POSITIVE"
    if summary["median"]>0: return "WEAK_POSITIVE"
    return "CONTRADICTORY_OR_NULL"
