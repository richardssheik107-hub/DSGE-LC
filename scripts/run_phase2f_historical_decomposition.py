"""Run posterior historical decomposition without new parameter estimation."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.historical_decomposition import (activity_shares,
    decomposition_identity_error,episode_contributions,historical_contributions,
    reconstruct_smoothed_shocks,select_equal_per_chain,subset_representativeness)
from src.structural.kalman import kalman_filter,rts_smoother
from src.structural.measurement import build_measurements,load_frozen_panel
from src.structural.parameter_transform import PARAMETER_ORDER,load_phase2a_bounds
from src.structural.posterior_artifacts import load_posterior_artifact
from src.structural.state_space import from_phase2a_parameters

OUT=ROOT/"outputs/phase2/phase2f";FREEZE=ROOT/"data/processed/core_monthly_panel.csv";PANEL=ROOT/"data/processed/phase1/monthly_structural_v1.csv"
SHOCKS=("demand","cost","supply","price")
QUANTILES=(.05,.16,.50,.84,.95)
SPECIFICATIONS={
 "BASELINE":("outputs/phase2/phase2d/baseline_posterior_draws.npz",.80,.25),
 "PRIOR_FLAT_BOUNDED":("outputs/phase2/phase2d/prior_flat_bounded_posterior_draws.npz",.80,.25),
 "PRIOR_MODERATE_SHRINK":("outputs/phase2/phase2d/prior_moderate_shrink_posterior_draws.npz",.80,.25),
 "BATTERY_SD_010":("outputs/phase2/phase2d/battery_sd_010_posterior_draws.npz",.80,.10),
 "BATTERY_SD_050":("outputs/phase2/phase2d/battery_sd_050_posterior_draws.npz",.80,.50),
 "RHO_N_050":("outputs/phase2/phase2d/rho_n_050_posterior_draws.npz",.50,.25),
 "RHO_N_095":("outputs/phase2/phase2d/rho_n_095_posterior_draws.npz",.95,.25),
}

def qrow(values):
    q=np.quantile(np.asarray(values,float),QUANTILES)
    return {"q05":q[0],"q16":q[1],"median":q[2],"q84":q[3],"q95":q[4]}

def classify_residual(value,cfg):
    return "HIGH" if value>cfg["residual_activity_high"] else "MODERATE" if value>=cfg["residual_activity_moderate"] else "LOW"

def load_draws(name,path,rho_n,battery_sd,bounds):
    if name=="BASELINE":
        with np.load(ROOT/path,allow_pickle=False) as raw:return np.asarray(raw["theta"],float)
    arrays,_=load_posterior_artifact(ROOT/path,expected_specification=name,expected_rho_n=rho_n,expected_battery_sd=battery_sd,bounds=bounds)
    return arrays["theta"]

def run_specification(name,theta,rho_n,battery_sd,draws_per_chain,seed,y,months,cfg):
    subset,indices=select_equal_per_chain(theta,draws_per_chain,seed);flat=subset.reshape(-1,14);T=len(y)
    shocks=np.empty((len(flat),T-1,4),np.float32);price=np.empty((len(flat),T,4),np.float32);initial=np.empty((len(flat),T),np.float32);smoothed_p=np.empty((len(flat),T),np.float32)
    max_reconstruction=0.;max_identity=0.;max_jitter=0.;minimum_covariance=np.inf;rank_min=4
    for draw,row in enumerate(flat):
        pars={parameter:float(row[j]) for j,parameter in enumerate(PARAMETER_ORDER)};pars["rho_n"]=rho_n
        model=from_phase2a_parameters("M0_CORE5",pars,battery_sd);filtered=kalman_filter(model,y,time_index=months);smoothed=rts_smoother(model,filtered)
        if filtered.status!="OK" or smoothed.status!="OK" or not np.isfinite(smoothed.smoothed_mean).all():raise RuntimeError(f"smoother failure: {name} draw {draw}")
        minimum_covariance=min(minimum_covariance,float(np.linalg.eigvalsh(smoothed.smoothed_cov).min()));max_jitter=max(max_jitter,float(np.nanmax(filtered.jitter_used)))
        epsilon,_,error,rank=reconstruct_smoothed_shocks(smoothed.smoothed_mean,model.A,model.B);ic,contribution=historical_contributions(model.A,model.B,smoothed.smoothed_mean[0],epsilon);identity=decomposition_identity_error(smoothed.smoothed_mean,ic,contribution)
        max_reconstruction=max(max_reconstruction,error);max_identity=max(max_identity,identity);rank_min=min(rank_min,rank)
        shocks[draw]=epsilon;price[draw]=contribution[:,:,4];initial[draw]=ic[:,4];smoothed_p[draw]=smoothed.smoothed_mean[:,4]
    standardized=subset_representativeness(theta,subset)
    subset_row={"specification":name,"chains":theta.shape[0],"draws_per_chain":draws_per_chain,"total_draws":len(flat),"seed":seed,"selection":"FIXED_SEED_EQUAL_PER_CHAIN_POSTERIOR_INTEGRATION","max_abs_median_shift_sd":float(np.max(np.abs(standardized))),"representative":bool(np.max(np.abs(standardized))<=cfg["subset_median_sd_tolerance"]),"indices_sha256":hashlib.sha256(indices.tobytes()).hexdigest()}
    audit={"specification":name,"draws":len(flat),"filter_status":"PASS","smoother_status":"PASS","max_jitter":max_jitter,"minimum_smoothed_covariance_eigenvalue":minimum_covariance}
    reconstruction={"specification":name,"B_rank_min":rank_min,"max_absolute_reconstruction_residual":max_reconstruction,"tolerance":cfg["shock_reconstruction_tolerance"],"status":"PASS" if rank_min==4 and max_reconstruction<=cfg["shock_reconstruction_tolerance"] else "FAIL"}
    identity={"specification":name,"max_absolute_decomposition_error":max_identity,"tolerance":cfg["decomposition_identity_tolerance"],"status":"PASS" if max_identity<=cfg["decomposition_identity_tolerance"] else "FAIL"}
    return {"subset":subset_row,"audit":audit,"reconstruction":reconstruction,"identity":identity,"shocks":shocks,"price":price,"initial":initial,"smoothed_p":smoothed_p}

def monthly_outputs(result,months,observed):
    shock_rows=[]
    for t,month in enumerate(months):
        for j,shock in enumerate(SHOCKS):
            if t==0:shock_rows.append({"month":month,"shock":shock,"timing":"INITIAL_CONDITION_MONTH","q05":np.nan,"q16":np.nan,"median":np.nan,"q84":np.nan,"q95":np.nan})
            else:shock_rows.append({"month":month,"shock":shock,"timing":"TRANSITION_FROM_PREVIOUS_MONTH",**qrow(result["shocks"][:,t-1,j])})
    contribution_rows=[]
    components={"initial_condition":result["initial"],**{shock:result["price"][:,:,j] for j,shock in enumerate(SHOCKS)},"smoothed_p":result["smoothed_p"]}
    for component,values in components.items():
        for t,month in enumerate(months):contribution_rows.append({"month":month,"component":component,"observed_standardized_spot_dlog":observed[t],**qrow(values[:,t])})
    return shock_rows,contribution_rows

def episode_outputs(name,result,months,observed,cfg):
    net_rows=[];activity_rows=[];summary=[]
    for window,(start,end) in cfg["historical_windows"].items():
        idx=np.where((months>=start)&(months<=end))[0];net=episode_contributions(result["price"],idx);activity,shares=activity_shares(result["price"],idx);ic=result["initial"][:,idx].sum(1)
        for j,shock in enumerate(SHOCKS):
            values=net[:,j];net_rows.append({"specification":name,"window":window,"start":start,"end":end,"component":shock,**qrow(values),"p_positive":np.mean(values>0),"p_negative":np.mean(values<0)})
            activity_rows.append({"specification":name,"window":window,"shock":shock,**qrow(shares[:,j]),"absolute_activity_median":np.median(activity[:,j])})
        net_rows.append({"specification":name,"window":window,"start":start,"end":end,"component":"initial_condition",**qrow(ic),"p_positive":np.mean(ic>0),"p_negative":np.mean(ic<0)})
        med=np.median(net,axis=0);share_med=np.median(shares,axis=0);positive=np.where(med>0,med,-np.inf);negative=np.where(med<0,med,np.inf)
        dominant_positive=SHOCKS[int(np.argmax(positive))] if np.isfinite(positive).any() else "NONE";dominant_negative=SHOCKS[int(np.argmin(negative))] if np.isfinite(negative).any() else "NONE";largest_activity=SHOCKS[int(np.argmax(share_med))]
        residual=float(share_med[3]);summary.append({"specification":name,"window":window,"observed_cumulative_standardized_price_pressure":float(observed[idx].sum()),"smoothed_cumulative_median":float(np.median(result["smoothed_p"][:,idx].sum(1))),"initial_condition_net_median":float(np.median(ic)),"dominant_positive_shock":dominant_positive,"dominant_negative_shock":dominant_negative,"largest_absolute_activity_shock":largest_activity,"price_residual_activity_share_median":residual,"fundamental_activity_share_median":1-residual,"residual_classification":classify_residual(residual,cfg)})
    return net_rows,activity_rows,summary

def make_figures(months,observed,baseline,episode_net,episode_activity,sensitivity):
    x=np.arange(len(months));median_price=np.median(baseline["price"],axis=0);median_ic=np.median(baseline["initial"],axis=0)
    fig,ax=plt.subplots(figsize=(11,5));ax.plot(x,observed,color="black",lw=1.5,label="observed standardized spot dlog");ax.plot(x,np.median(baseline["smoothed_p"],axis=0),color="black",ls="--",label="smoothed p")
    ax.stackplot(x,median_ic,*[median_price[:,j] for j in range(4)],labels=("initial",)+SHOCKS,alpha=.65);ax.legend(ncol=3,fontsize=8);ax.set_xticks(x[::6],months[::6],rotation=45);ax.set_ylabel("standardized price-change pressure");fig.tight_layout();fig.savefig(OUT/"historical_price_decomposition.png",dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4));
    for j,shock in enumerate(SHOCKS):ax.plot(x,np.cumsum(median_price[:,j]),label=shock)
    ax.plot(x,np.cumsum(median_ic),label="initial",ls="--");ax.legend();ax.set_xticks(x[::6],months[::6],rotation=45);ax.set_ylabel("cumulative standardized price-change pressure");fig.tight_layout();fig.savefig(OUT/"historical_cumulative_contributions.png",dpi=180);plt.close(fig)
    fig,axes=plt.subplots(4,1,figsize=(11,8),sharex=True)
    for j,(ax,shock) in enumerate(zip(axes,SHOCKS)):
        values=baseline["shocks"][:,:,j];q=np.quantile(values,[.05,.5,.95],axis=0);ax.fill_between(x[1:],q[0],q[2],alpha=.2);ax.plot(x[1:],q[1]);ax.axhline(0,color="black",lw=.5);ax.set_ylabel(shock)
    axes[-1].set_xticks(x[::6],months[::6],rotation=45);fig.tight_layout();fig.savefig(OUT/"structural_shocks_over_time.png",dpi=180);plt.close(fig)
    base_net=episode_net[(episode_net.specification=="BASELINE")&(episode_net.component.isin(SHOCKS))].pivot(index="window",columns="component",values="median");base_net.plot(kind="bar",figsize=(8,4));plt.axhline(0,color="black",lw=.6);plt.ylabel("net standardized pressure");plt.tight_layout();plt.savefig(OUT/"episode_contribution_bars.png",dpi=180);plt.close()
    residual=episode_activity[(episode_activity.specification=="BASELINE")&(episode_activity.shock=="price")];plt.figure(figsize=(7,4));plt.bar(residual.window,residual["median"]);plt.axhline(.5,color="orange");plt.axhline(.7,color="red");plt.ylabel("price-residual activity share");plt.xticks(rotation=20);plt.tight_layout();plt.savefig(OUT/"historical_residual_share.png",dpi=180);plt.close()
    pivot=sensitivity.pivot(index="specification",columns="window",values="price_residual_activity_share_median");pivot.plot(kind="bar",figsize=(10,4));plt.ylabel("residual activity share");plt.tight_layout();plt.savefig(OUT/"historical_sensitivity_comparison.png",dpi=180);plt.close()

def main():
    OUT.mkdir(parents=True,exist_ok=True);cfg=json.loads((ROOT/"configs/phase2f.yaml").read_text());p2a=json.loads((ROOT/"configs/phase2a.yaml").read_text());bounds=load_phase2a_bounds(ROOT/"configs/phase2a.yaml");before=hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    if before!=p2a["data_freeze_sha256"]:raise RuntimeError("Data Freeze mismatch")
    frame=load_frozen_panel(PANEL,cfg["sample_end"]);measure=build_measurements(frame,cfg["measurement"]);months=measure.month.to_numpy();y=measure[["spot","ore_cost","output","battery"]].to_numpy();observed=y[:,0]
    if len(y)!=57 or months[0]!=cfg["sample_start"] or months[-1]!=cfg["sample_end"]:raise RuntimeError("sample mismatch")
    results={};subset_rows=[];smoother_rows=[];reconstruction_rows=[];identity_rows=[]
    for name,(path,rho_n,battery_sd) in SPECIFICATIONS.items():
        theta=load_draws(name,path,rho_n,battery_sd,bounds);draws=cfg["baseline_draws_per_chain"] if name=="BASELINE" else cfg["sensitivity_draws_per_chain"]
        result=run_specification(name,theta,rho_n,battery_sd,draws,cfg["seed"],y,months,cfg)
        if name=="BASELINE" and not result["subset"]["representative"]:
            result=run_specification(name,theta,rho_n,battery_sd,cfg["fallback_draws_per_chain"],cfg["seed"],y,months,cfg)
        results[name]=result;subset_rows.append(result["subset"]);smoother_rows.append(result["audit"]);reconstruction_rows.append(result["reconstruction"]);identity_rows.append(result["identity"]);print(name,result["subset"],result["reconstruction"],result["identity"],flush=True)
        if result["reconstruction"]["status"]!="PASS" or result["identity"]["status"]!="PASS":raise SystemExit("PHASE2F_NUMERICAL_FAILURE")
    pd.DataFrame(subset_rows).to_csv(OUT/"posterior_subset_audit.csv",index=False);pd.DataFrame(smoother_rows).to_csv(OUT/"smoother_audit.csv",index=False);pd.DataFrame(reconstruction_rows).to_csv(OUT/"shock_reconstruction_audit.csv",index=False);pd.DataFrame(identity_rows).to_csv(OUT/"decomposition_identity_audit.csv",index=False)
    shock_rows,monthly_rows=monthly_outputs(results["BASELINE"],months,observed);pd.DataFrame(shock_rows).to_csv(OUT/"monthly_structural_shocks.csv",index=False);pd.DataFrame(monthly_rows).to_csv(OUT/"monthly_price_contributions.csv",index=False)
    net_rows=[];activity_rows=[];summaries=[]
    for name,result in results.items():
        nrows,arows,srows=episode_outputs(name,result,months,observed,cfg);net_rows.extend(nrows);activity_rows.extend(arows);summaries.extend(srows)
    net=pd.DataFrame(net_rows);activity=pd.DataFrame(activity_rows);summary=pd.DataFrame(summaries);net.to_csv(OUT/"episode_net_contributions.csv",index=False);activity.to_csv(OUT/"episode_activity_shares.csv",index=False)
    initial_rows=[]
    for horizon in (3,6,12):
        values=results["BASELINE"]["initial"][:,horizon-1];initial_rows.append({"month_number":horizon,"month":months[horizon-1],**qrow(values),"absolute_median":float(np.median(np.abs(values))),"warning":bool(np.median(np.abs(values))>cfg["initial_condition_warning_absolute"] and horizon==12)})
    pd.DataFrame(initial_rows).to_csv(OUT/"initial_condition_diagnostic.csv",index=False)
    baseline_summary=summary[summary.specification=="BASELINE"].set_index("window");sensitivity_rows=[]
    for _,row in summary.iterrows():
        if row.specification=="BASELINE":continue
        base=baseline_summary.loc[row.window];stable=row.dominant_positive_shock==base.dominant_positive_shock and row.dominant_negative_shock==base.dominant_negative_shock and row.largest_absolute_activity_shock==base.largest_absolute_activity_shock
        classification="STABLE" if stable else "MODERATE"
        detail={}
        for shock in SHOCKS:
            alternative_net=net[(net.specification==row.specification)&(net.window==row.window)&(net.component==shock)].iloc[0]["median"]
            baseline_net=net[(net.specification=="BASELINE")&(net.window==row.window)&(net.component==shock)].iloc[0]["median"]
            alternative_share=activity[(activity.specification==row.specification)&(activity.window==row.window)&(activity.shock==shock)].iloc[0]["median"]
            baseline_share=activity[(activity.specification=="BASELINE")&(activity.window==row.window)&(activity.shock==shock)].iloc[0]["median"]
            detail.update({f"{shock}_net_median":alternative_net,f"baseline_{shock}_net_median":baseline_net,f"{shock}_activity_share_median":alternative_share,f"baseline_{shock}_activity_share_median":baseline_share})
        sensitivity_rows.append({**row.to_dict(),**detail,"baseline_dominant_positive":base.dominant_positive_shock,"baseline_dominant_negative":base.dominant_negative_shock,"baseline_largest_activity":base.largest_absolute_activity_shock,"story_stability":classification})
    sensitivity=pd.DataFrame(sensitivity_rows);sensitivity.to_csv(OUT/"historical_sensitivity_summary.csv",index=False)
    spot_error=float(np.max(np.abs(results["BASELINE"]["smoothed_p"]-observed[None,:])));severe_windows=int((baseline_summary.price_residual_activity_share_median>.70).sum());critical_complete=all(name in set(sensitivity.specification) for name in cfg["critical_sensitivity"]);numerical=all(x["status"]=="PASS" for x in reconstruction_rows+identity_rows);spot_pass=spot_error<=cfg["spot_state_identity_tolerance"];ready=numerical and spot_pass and critical_complete
    gates=[{"gate":"POSTERIOR_SUBSET","status":"PASS" if subset_rows[0]["representative"] else "FAIL"},{"gate":"KALMAN_RTS","status":"PASS"},{"gate":"SHOCK_RECONSTRUCTION","status":"PASS" if numerical else "FAIL"},{"gate":"DECOMPOSITION_IDENTITY","status":"PASS" if numerical else "FAIL"},{"gate":"SPOT_STATE_IDENTITY","status":"PASS" if spot_pass else "FAIL","value":spot_error,"tolerance":cfg["spot_state_identity_tolerance"]},{"gate":"CRITICAL_SENSITIVITY","status":"PASS" if critical_complete else "FAIL"},{"gate":"HISTORICAL_RESIDUAL_DOMINANCE","status":"PASS_WITH_WARNING" if severe_windows==3 else "PASS","value":severe_windows},{"gate":"PHASE_2F_READY","status":"YES" if ready else "NO"}];pd.DataFrame(gates).to_csv(OUT/"phase2f_gate_summary.csv",index=False)
    make_figures(months,observed,results["BASELINE"],net,activity,sensitivity)
    if hashlib.sha256(FREEZE.read_bytes()).hexdigest()!=before:raise RuntimeError("Freeze changed")
    print(json.dumps({"phase2f_ready":ready,"spot_state_error":spot_error,"max_reconstruction_error":max(x["max_absolute_reconstruction_residual"] for x in reconstruction_rows),"max_identity_error":max(x["max_absolute_decomposition_error"] for x in identity_rows),"severe_residual_windows":severe_windows},indent=2))

if __name__=="__main__":main()
