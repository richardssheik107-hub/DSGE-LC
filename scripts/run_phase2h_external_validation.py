"""Validate latent inventory-pressure and cost states against independent SMM series."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.external_validation import rowwise_pearson,rowwise_spearman,correlation_summary,validation_strength
from src.structural.historical_decomposition import select_equal_per_chain
from src.structural.kalman import kalman_filter,rts_smoother
from src.structural.measurement import load_frozen_panel,build_measurements
from src.structural.parameter_transform import PARAMETER_ORDER,load_phase2a_bounds
from src.structural.posterior_artifacts import load_posterior_artifact
from src.structural.state_space import from_phase2a_parameters

OUT=ROOT/"outputs/phase2/phase2h";FREEZE=ROOT/"data/processed/core_monthly_panel.csv"
PANEL=ROOT/"data/processed/phase1/monthly_structural_v1.csv"
INV=ROOT/"data/processed/industry/lc_inventory_monthly.csv"
COST=ROOT/"data/processed/industry/lc_cost_margin_monthly.csv"
SPECS={"BASELINE":("outputs/phase2/phase2d/baseline_posterior_draws.npz",.80,1000),
       "RHO_N_050":("outputs/phase2/phase2d/rho_n_050_posterior_draws.npz",.50,250),
       "RHO_N_095":("outputs/phase2/phase2d/rho_n_095_posterior_draws.npz",.95,250)}

def load_theta(name,path,rho_n,bounds):
    if name=="BASELINE": return np.load(ROOT/path,allow_pickle=False)["theta"]
    arr,_=load_posterior_artifact(ROOT/path,expected_specification=name,expected_rho_n=rho_n,expected_battery_sd=.25,bounds=bounds)
    return arr["theta"]

def smooth_states(theta,rho_n,draws_per_chain,seed,y,months):
    subset,_=select_equal_per_chain(theta,draws_per_chain,seed);flat=subset.reshape(-1,14)
    states=np.empty((len(flat),len(months),2),np.float32);max_jitter=0.;min_cov=np.inf
    for i,row in enumerate(flat):
        p={k:float(row[j]) for j,k in enumerate(PARAMETER_ORDER)};p["rho_n"]=rho_n
        model=from_phase2a_parameters("M0_CORE5",p,.25);f=kalman_filter(model,y,time_index=months);s=rts_smoother(model,f)
        if f.status!="OK" or s.status!="OK" or not np.isfinite(s.smoothed_mean).all(): raise RuntimeError(f"smoother failed draw {i}")
        states[i,:,0]=s.smoothed_mean[:,3];states[i,:,1]=s.smoothed_mean[:,1]
        max_jitter=max(max_jitter,float(np.nanmax(f.jitter_used)));min_cov=min(min_cov,float(np.linalg.eigvalsh(s.smoothed_cov).min()))
    return states,{"draws":len(flat),"max_jitter":max_jitter,"min_smoothed_cov_eigenvalue":min_cov}

def append_corr(rows,spec,block,series,paths,target):
    for stat,vals in (("pearson",rowwise_pearson(paths,target)),("spearman",rowwise_spearman(paths,target))):
        s=correlation_summary(vals);rows.append({"specification":spec,"block":block,"validation_series":series,"statistic":stat,
            "n_months":len(target),**s,"classification":validation_strength(s)})

def lag_scan(state_df,val_df,state_col,val_col,max_lag,block):
    rows=[]
    for lag in range(-max_lag,max_lag+1):
        v=val_df[["month",val_col]].dropna().copy();v["state_month"]=(pd.PeriodIndex(v.month,freq="M")-lag).astype(str)
        m=state_df[["month",state_col]].merge(v,left_on="month",right_on="state_month")
        rows.append({"block":block,"state":state_col,"validation_series":val_col,"lag_validation_months":lag,
                     "n_months":len(m),"pearson":m[state_col].corr(m[val_col]),"spearman":m[state_col].corr(m[val_col],method="spearman")})
    return rows

def zscore(x):
    x=np.asarray(x,float);return (x-x.mean())/x.std(ddof=1)

def main():
    OUT.mkdir(parents=True,exist_ok=True);cfg=json.loads((ROOT/"configs/phase2h.yaml").read_text(encoding="utf-8-sig"));before=hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    p2a=json.loads((ROOT/"configs/phase2a.yaml").read_text());assert before.lower()==p2a["data_freeze_sha256"].lower();bounds=load_phase2a_bounds(ROOT/"configs/phase2a.yaml")
    frame=load_frozen_panel(PANEL,cfg["sample_end"]);measure=build_measurements(frame,cfg["measurement"]);months=measure.month.astype(str).to_numpy();y=measure[["spot","ore_cost","output","battery"]].to_numpy()
    if len(y)!=57 or months[0]!="2021-01" or months[-1]!="2025-09": raise RuntimeError("structural sample mismatch")
    results={};audit=[]
    for name,(path,rho_n,_) in SPECS.items():
        draws=cfg["baseline_draws_per_chain"] if name=="BASELINE" else cfg["sensitivity_draws_per_chain"]
        theta=load_theta(name,path,rho_n,bounds);states,a=smooth_states(theta,rho_n,draws,cfg["seed"],y,months);results[name]=states;a.update({"specification":name,"rho_n":rho_n,"draws_per_chain":draws});audit.append(a)
    inv=pd.read_csv(INV);inv=inv[(inv.month>=cfg["inventory_start"])&(inv.month<=cfg["inventory_end"])].copy();inv["log_inventory_mean"]=np.log(inv[cfg["inventory_primary"]]);inv["log_inventory_eom"]=np.log(inv[cfg["inventory_secondary"]])
    cost=pd.read_csv(COST);cost["spodumene_cost_dlog"]=np.log(cost[cfg["cost_primary"]]).diff();cost["lepidolite_cost_dlog"]=np.log(cost[cfg["cost_secondary"]]).diff();cost=cost[(cost.month>=cfg["cost_start"])&(cost.month<=cfg["cost_end"])].copy()
    pos={m:i for i,m in enumerate(months)};inv_idx=[pos[m] for m in inv.month];cost_idx=[pos[m] for m in cost.month if m in pos];cost=cost[cost.month.isin(pos)].reset_index(drop=True)
    rows=[]
    for name,states in results.items():
        append_corr(rows,name,"inventory","log_inventory_mean",states[:,inv_idx,0],inv.log_inventory_mean.to_numpy())
        append_corr(rows,name,"inventory","log_inventory_eom",states[:,inv_idx,0],inv.log_inventory_eom.to_numpy())
    base=results["BASELINE"];append_corr(rows,"BASELINE","cost","spodumene_route_cost_dlog",base[:,cost_idx,1],cost.spodumene_cost_dlog.to_numpy());append_corr(rows,"BASELINE","cost","lepidolite_route_cost_dlog",base[:,cost_idx,1],cost.lepidolite_cost_dlog.to_numpy())
    corr=pd.DataFrame(rows);corr.to_csv(OUT/"external_validation_correlations.csv",index=False);pd.DataFrame(audit).to_csv(OUT/"external_validation_smoother_audit.csv",index=False)
    q=np.quantile(base,[.05,.16,.50,.84,.95],axis=0);state_rows=[]
    for i,m in enumerate(months):
        state_rows.append({"month":m,"state":"inventory_pressure_n","q05":q[0,i,0],"q16":q[1,i,0],"median":q[2,i,0],"q84":q[3,i,0],"q95":q[4,i,0]})
        state_rows.append({"month":m,"state":"cost_c","q05":q[0,i,1],"q16":q[1,i,1],"median":q[2,i,1],"q84":q[3,i,1],"q95":q[4,i,1]})
    states_df=pd.DataFrame(state_rows);states_df.to_csv(OUT/"external_validation_state_paths.csv",index=False)
    med=states_df.pivot(index="month",columns="state",values="median").reset_index();lags=[]
    lags+=lag_scan(med,inv,"inventory_pressure_n","log_inventory_mean",cfg["lag_scan_months"],"inventory")
    lags+=lag_scan(med,cost,"cost_c","spodumene_cost_dlog",cfg["lag_scan_months"],"cost")
    pd.DataFrame(lags).to_csv(OUT/"external_validation_lag_scan.csv",index=False)
    m=med.merge(inv[["month","log_inventory_mean"]],on="month");fig,ax=plt.subplots(figsize=(9,4));ax.plot(m.month,zscore(m.inventory_pressure_n),label="latent inventory pressure n");ax.plot(m.month,zscore(m.log_inventory_mean),label="SMM total inventory log level");ax.legend();ax.tick_params(axis="x",rotation=45);fig.tight_layout();fig.savefig(OUT/"inventory_external_validation.png",dpi=180);plt.close(fig)
    m=med.merge(cost[["month","spodumene_cost_dlog"]],on="month");fig,ax=plt.subplots(figsize=(9,4));ax.plot(m.month,zscore(m.cost_c),label="latent cost state c");ax.plot(m.month,zscore(m.spodumene_cost_dlog),label="SMM spodumene-route cost dlog");ax.legend();ax.tick_params(axis="x",rotation=45);fig.tight_layout();fig.savefig(OUT/"cost_external_validation.png",dpi=180);plt.close(fig)
    def pick(spec,block,series): return corr[(corr.specification==spec)&(corr.block==block)&(corr.validation_series==series)&(corr.statistic=="pearson")].iloc[0]
    primary_inv=[pick(s,"inventory","log_inventory_mean") for s in SPECS];primary_cost=pick("BASELINE","cost","spodumene_route_cost_dlog")
    signs=all(r["median"]>0 for r in primary_inv) and primary_cost["median"]>0;finite=np.isfinite(corr[["q05","median","q95","p_positive"]].to_numpy()).all();freeze=hashlib.sha256(FREEZE.read_bytes()).hexdigest()==before
    warning=any(r["q05"]<=0 for r in primary_inv) or primary_cost["q05"]<=0;ready=bool(signs and finite and freeze)
    gates=[{"gate":"FREEZE_UNCHANGED","status":"PASS" if freeze else "FAIL"},{"gate":"SMOOTHER_FINITE","status":"PASS" if finite else "FAIL"},{"gate":"INVENTORY_EXTERNAL_SIGN","status":"PASS" if all(r["median"]>0 for r in primary_inv) else "REVIEW"},{"gate":"COST_EXTERNAL_SIGN","status":"PASS" if primary_cost["median"]>0 else "REVIEW"},{"gate":"EXTERNAL_VALIDATION_STRENGTH","status":"PASS_WITH_WARNING" if warning else "PASS"},{"gate":"PHASE_2H_READY","status":"YES" if ready else "NO"}]
    pd.DataFrame(gates).to_csv(OUT/"phase2h_gate_summary.csv",index=False)
    print(corr.to_string(index=False));print(pd.DataFrame(gates).to_string(index=False));print("inventory months",len(inv),"cost months",len(cost),"ready",ready)

if __name__=="__main__": main()
