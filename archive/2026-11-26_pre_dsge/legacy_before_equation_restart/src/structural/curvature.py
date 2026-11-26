"""Finite-difference Hessian, per-period score, OPG and local geometry."""
from __future__ import annotations
import numpy as np


def finite_difference_hessian(function,x,step=1e-4):
    x=np.asarray(x,float);n=len(x);H=np.empty((n,n));f0=float(function(x))
    for i in range(n):
        ei=np.zeros(n);ei[i]=step
        H[i,i]=(function(x+ei)-2*f0+function(x-ei))/(step*step)
        for j in range(i+1,n):
            ej=np.zeros(n);ej[j]=step
            H[i,j]=H[j,i]=(function(x+ei+ej)-function(x+ei-ej)-function(x-ei+ej)+function(x-ei-ej))/(4*step*step)
    return .5*(H+H.T)


def matrix_diagnostics(matrix,names,near_zero_relative=1e-8,condition_review=1e4):
    matrix=.5*(np.asarray(matrix,float)+np.asarray(matrix,float).T)
    eigval,eigvec=np.linalg.eigh(matrix);order=np.argsort(eigval);eigval=eigval[order];eigvec=eigvec[:,order]
    scale=max(1.,float(np.max(np.abs(eigval))));tol=max(matrix.shape)*np.finfo(float).eps*scale
    rank=int(np.sum(np.abs(eigval)>tol));positive=bool(np.all(eigval>tol))
    positive_values=eigval[eigval>tol];condition=float(positive_values.max()/positive_values.min()) if positive and len(positive_values) else np.inf
    weak=[]
    for k in range(min(3,len(names))):
        idx=np.argsort(np.abs(eigvec[:,k]))[-3:][::-1]
        weak.append({"direction":k+1,"eigenvalue":float(eigval[k]),"largest_loadings":";".join(f"{names[j]}:{eigvec[j,k]:.6g}" for j in idx)})
    classification="INDEFINITE_CURVATURE" if eigval[0]<-tol else "WEAK_CURVATURE" if (not positive or condition>condition_review or eigval[0]<near_zero_relative*scale) else "CURVATURE_OK"
    return {"min_eigenvalue":float(eigval[0]),"max_eigenvalue":float(eigval[-1]),"rank":rank,"dimension":len(names),
            "condition_number":condition,"positive_definite":positive,"near_zero_eigenvalues":int(np.sum(np.abs(eigval)<near_zero_relative*scale)),
            "classification":classification,"eigenvalues":eigval,"eigenvectors":eigvec,"weak_directions":weak}


def hessian_step_robustness(function,x,steps,names):
    rows=[];matrices=[]
    for step in steps:
        H=finite_difference_hessian(function,x,float(step));d=matrix_diagnostics(H,names);matrices.append(H)
        rows.append({"step":step,**{k:v for k,v in d.items() if k not in ("eigenvalues","eigenvectors","weak_directions")}})
    sign_consistent=len({r["positive_definite"] for r in rows})==1
    rank_consistent=len({r["rank"] for r in rows})==1
    for row in rows:row["step_sign_consistent"]=sign_consistent;row["step_rank_consistent"]=rank_consistent;row["numerically_unstable"]=not(sign_consistent and rank_consistent)
    return rows,matrices


def per_time_score(contribution_function,x,step=1e-4):
    x=np.asarray(x,float);base=np.asarray(contribution_function(x),float);scores=np.empty((len(base),len(x)))
    for j in range(len(x)):
        delta=np.zeros(len(x));delta[j]=step
        scores[:,j]=(np.asarray(contribution_function(x+delta))-np.asarray(contribution_function(x-delta)))/(2*step)
    return scores


def opg_diagnostics(scores,names):
    opg=np.asarray(scores,float).T@np.asarray(scores,float);return opg,matrix_diagnostics(opg,names)


def native_covariance(hessian,transform,z,max_condition=1e4):
    d=matrix_diagnostics(hessian,transform.free_parameters)
    if not d["positive_definite"] or d["condition_number"]>max_condition:return None,None
    cov_z=np.linalg.inv(hessian);J=np.diag(transform.jacobian_diagonal(z));cov_native=J@cov_z@J.T
    return cov_native,cov_z


def high_correlation_pairs(cov,names,threshold=.9):
    if cov is None:return []
    sd=np.sqrt(np.diag(cov));corr=np.divide(cov,np.outer(sd,sd),out=np.zeros_like(cov),where=np.outer(sd,sd)>0)
    return [{"parameter_1":names[i],"parameter_2":names[j],"correlation":float(corr[i,j]),"absolute_correlation":float(abs(corr[i,j]))}
            for i in range(len(names)) for j in range(i+1,len(names)) if abs(corr[i,j])>threshold]
