"""Run Phase 2E posterior IRF/FEVD diagnostics without re-estimation."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.fevd import forecast_variance_identity_check,posterior_fevd_summary,residual_dominance,structural_fevd
from src.structural.irf import SHOCK_ORDER,STATE_ORDER,impulse_response,observation_response,peak_timing,persistence_metric,posterior_irf_summary
from src.structural.matrices import system_matrices
from src.structural.parameter_transform import PARAMETER_ORDER,load_phase2a_bounds
from src.structural.posterior_artifacts import load_posterior_artifact
from src.structural.structural_results import economic_sign_checks,sensitivity_classification

OUT=ROOT/"outputs/phase2/phase2e";FREEZE=ROOT/"data/processed/core_monthly_panel.csv"
OBS_ORDER=("spot","ore_cost","output","battery")
SENSITIVITY_TARGETS=(("demand","p"),("cost","p"),("supply","p"),("demand","n"),("supply","n"),("cost","q"),("price","q"))

def _sensitivity_results(theta,rho_n,cfg,baseline_state,baseline_fevd):
    flat=np.asarray(theta,float).reshape(-1,14);n=len(flat);hmax=cfg["irf_max_horizon"]
    irf_values={target:np.empty((n,hmax+1),np.float32) for target in SENSITIVITY_TARGETS}
    price_fevd=np.empty((n,len(cfg["fevd_horizons"]),4),np.float32);identity=0.
    state_index={name:i for i,name in enumerate(STATE_ORDER)};shock_index={name:i for i,name in enumerate(SHOCK_ORDER)}
    for s,row in enumerate(flat):
        pars={name:float(row[j]) for j,name in enumerate(PARAMETER_ORDER)};pars["rho_n"]=rho_n;A,B,_,_=system_matrices(cfg["primary_model"],pars)
        response=impulse_response(A,B,hmax);shares,_=structural_fevd(A,B,cfg["fevd_horizons"]);price_fevd[s]=shares[:,state_index["p"],:]
        for target in SENSITIVITY_TARGETS:
            shock,state=target;irf_values[target][s]=response[:,state_index[state],shock_index[shock]]
        for horizon in cfg["fevd_horizons"]:identity=max(identity,forecast_variance_identity_check(A,B,horizon))
    irf_rows=[];sign_rows=[]
    for shock,state in SENSITIVITY_TARGETS:
        values=irf_values[(shock,state)];base=baseline_state[(baseline_state.shock==shock)&(baseline_state.state==state)].set_index("horizon")
        for horizon in cfg["irf_report_horizons"]:
            x=values[:,horizon].astype(float);median=float(np.median(x));base_sd=float(base.loc[horizon,"sd"]);shift=(median-float(base.loc[horizon,"median"]))/base_sd if base_sd>0 else np.nan
            irf_rows.append({"shock":shock,"state":state,"horizon":horizon,"q05":np.quantile(x,.05),"median":median,"q95":np.quantile(x,.95),"baseline_median":base.loc[horizon,"median"],"baseline_sd":base_sd,"shift_sd":shift,"classification":sensitivity_classification(shift,cfg["irf_sensitivity_moderate_sd"],cfg["irf_sensitivity_high_sd"])})
        for horizon in (0,1):
            x=values[:,horizon].astype(float);sign_rows.append({"shock":shock,"state":state,"horizon":horizon,"median":np.median(x),"p_plus":np.mean(x>0),"p_minus":np.mean(x<0)})
    fevd_rows=[]
    for k,horizon in enumerate(cfg["fevd_horizons"]):
        for j,shock in enumerate(SHOCK_ORDER):
            x=price_fevd[:,k,j].astype(float);base=baseline_fevd[(baseline_fevd.horizon==horizon)&(baseline_fevd.shock==shock)].iloc[0];change=float(np.median(x)-base["median"])
            fevd_rows.append({"horizon":horizon,"shock":shock,"q05":np.quantile(x,.05),"median":np.median(x),"q95":np.quantile(x,.95),"baseline_median":base["median"],"absolute_share_change":abs(change),"signed_share_change":change,"classification":sensitivity_classification(change,cfg["fevd_sensitivity_moderate"],cfg["fevd_sensitivity_high"])})
    return irf_rows,sign_rows,fevd_rows,identity,irf_values

def _summary_plot(frame,path,title,states=None):
    fig,axes=plt.subplots(1,4,figsize=(14,3),sharex=True);states=states or ["p"]*4
    for ax,shock,state in zip(axes,SHOCK_ORDER,states):
        x=frame[(frame.shock==shock)&(frame.state==state)];h=x.horizon.to_numpy(float);ax.axhline(0,color="black",lw=.7);ax.fill_between(h,x.q05.astype(float),x.q95.astype(float),alpha=.15);ax.fill_between(h,x.q16.astype(float),x.q84.astype(float),alpha=.25);ax.plot(h,x["median"].astype(float));ax.set_title(f"{shock} → {state}");ax.set_xlabel("month")
    fig.suptitle(title);fig.tight_layout();fig.savefig(path,dpi=180);plt.close(fig)

def main():
    OUT.mkdir(parents=True,exist_ok=True);cfg=json.loads((ROOT/"configs/phase2e.yaml").read_text());p2a=json.loads((ROOT/"configs/phase2a.yaml").read_text());before=hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    if before!=p2a["data_freeze_sha256"]:raise RuntimeError("Data Freeze mismatch")
    artifact=ROOT/cfg["baseline_artifact"]
    if not artifact.exists():raise SystemExit("MISSING_PHASE2D_POSTERIOR_ARTIFACT: "+str(artifact))
    raw=np.load(artifact);theta=np.asarray(raw["theta"],float)
    if theta.shape!=(4,18000,14) or not np.isfinite(theta).all():raise RuntimeError("baseline posterior integrity failure")
    bounds=load_phase2a_bounds(ROOT/"configs/phase2a.yaml")
    for j,name in enumerate(PARAMETER_ORDER):
        lo,hi=bounds[name]
        if np.any((theta[:,:,j]<lo)|(theta[:,:,j]>hi)):raise RuntimeError("posterior support failure: "+name)
    flat=theta.reshape(-1,14);n=len(flat);Hmax=cfg["irf_max_horizon"];irfs=np.empty((n,Hmax+1,5,4),np.float32);fevds=np.empty((n,len(cfg["fevd_horizons"]),5,4),np.float32);radii=np.empty(n);identity=0.;Hmat=None
    for s,row in enumerate(flat):
        pars={name:float(row[j]) for j,name in enumerate(PARAMETER_ORDER)};pars["rho_n"]=cfg["rho_n"];A,B,_,Hmat=system_matrices(cfg["primary_model"],pars);radii[s]=max(abs(np.linalg.eigvals(A)))
        if radii[s]>=1:raise RuntimeError("unstable baseline posterior draw")
        irfs[s]=impulse_response(A,B,Hmax);shares,_=structural_fevd(A,B,cfg["fevd_horizons"]);fevds[s]=shares
        for horizon in cfg["fevd_horizons"]:identity=max(identity,forecast_variance_identity_check(A,B,horizon))
    state_rows=[];obs_rows=[]
    for j,shock in enumerate(SHOCK_ORDER):
        state_rows.extend(posterior_irf_summary(irfs[:,:,:,j],shock,STATE_ORDER,cfg["credible_quantiles"]));obs=observation_response(irfs[:,:,:,j],Hmat);obs_rows.extend(posterior_irf_summary(obs,shock,OBS_ORDER,cfg["credible_quantiles"]))
    state=pd.DataFrame(state_rows);observed=pd.DataFrame(obs_rows);state.to_csv(OUT/"irf_baseline_state_summary.csv",index=False);observed.to_csv(OUT/"irf_baseline_observation_summary.csv",index=False)
    price=state[state.state=="p"].copy();price.to_csv(OUT/"irf_price_summary.csv",index=False);state[["shock","state","horizon","p_plus","p_minus"]].to_csv(OUT/"irf_sign_probabilities.csv",index=False)
    peak_rows=[];persist_rows=[]
    for j,shock in enumerate(SHOCK_ORDER):
        x=irfs[:,:,4,j].astype(float);idx,peak=peak_timing(x);ratio=persistence_metric(x);peak_rows.append({"shock":shock,"peak_horizon_median":np.median(idx),"peak_horizon_q05":np.quantile(idx,.05),"peak_horizon_q95":np.quantile(idx,.95),"peak_response_median":np.median(peak),"sign_reversal_median":bool(np.any(np.sign(np.median(x,0)[1:])!=np.sign(np.median(x,0)[0])))})
        persist_rows.append({"shock":shock,"terminal_ratio_median":np.median(ratio),"terminal_ratio_q05":np.quantile(ratio,.05),"terminal_ratio_q95":np.quantile(ratio,.95),"long_persistence_review":np.median(ratio)>cfg["terminal_persistence_review"]})
    pd.DataFrame(peak_rows).to_csv(OUT/"irf_peak_timing.csv",index=False);pd.DataFrame(persist_rows).to_csv(OUT/"irf_persistence_summary.csv",index=False)
    fevd_rows=posterior_fevd_summary(fevds,cfg["fevd_horizons"],STATE_ORDER,SHOCK_ORDER);fevd_frame=pd.DataFrame(fevd_rows);fevd_frame.to_csv(OUT/"fevd_state_summary.csv",index=False);fevd_price=fevd_frame[fevd_frame.state=="p"].copy();fevd_price.to_csv(OUT/"fevd_price_summary.csv",index=False)
    pd.DataFrame([{"draws":n,"horizons":";".join(map(str,cfg["fevd_horizons"])),"max_absolute_identity_error":identity,"tolerance":1e-10,"status":"PASS" if identity<=1e-10 else "FAIL"}]).to_csv(OUT/"fevd_identity_audit.csv",index=False)
    residual=fevds[:,cfg["fevd_horizons"].index(12),4,3].astype(float);fundamental=1-residual;resrow={"horizon":12,"price_residual_median":np.median(residual),"q05":np.quantile(residual,.05),"q95":np.quantile(residual,.95),"fundamental_median":np.median(fundamental),"classification":residual_dominance(residual,cfg["residual_dominance_moderate"],cfg["residual_dominance_high"]),"severe_warning":bool(np.median(residual)>cfg["residual_dominance_severe"] and np.quantile(residual,.05)>.70)};pd.DataFrame([resrow]).to_csv(OUT/"fevd_residual_dominance.csv",index=False)
    irf_by_shock={shock:irfs[:,:,:,j] for j,shock in enumerate(SHOCK_ORDER)};checks=economic_sign_checks(irf_by_shock,{n:i for i,n in enumerate(STATE_ORDER)},{n:i for i,n in enumerate(SHOCK_ORDER)});pd.DataFrame(checks).to_csv(OUT/"structural_consistency_table.csv",index=False)
    specs={"PRIOR_FLAT_BOUNDED":(.8,.25),"PRIOR_MODERATE_SHRINK":(.8,.25),"BATTERY_SD_010":(.8,.10),"BATTERY_SD_050":(.8,.50),"RHO_N_050":(.50,.25),"RHO_N_095":(.95,.25)}
    sensitivity_irf=[];sensitivity_sign=[];sensitivity_fevd=[];artifact_rows=[{"artifact":"baseline","path":str(artifact.relative_to(ROOT)),"chains":4,"draws_per_chain":18000,"total_draws":n,"finite":True,"stable":True,"status":"PASS"}];sensitivity_identity=0.;plot_data={}
    for name,path in cfg["sensitivity_artifacts"].items():
        rho_n,battery_sd=specs[name];arrays,metadata=load_posterior_artifact(ROOT/path,expected_specification=name,expected_rho_n=rho_n,expected_battery_sd=battery_sd,bounds=bounds)
        irows,srows,frows,sidentity,values=_sensitivity_results(arrays["theta"],rho_n,cfg,state,fevd_price)
        sensitivity_irf.extend({"specification":name,**row} for row in irows);sensitivity_sign.extend({"specification":name,**row} for row in srows);sensitivity_fevd.extend({"specification":name,**row} for row in frows);sensitivity_identity=max(sensitivity_identity,sidentity);plot_data[name]=values
        artifact_rows.append({"artifact":name,"path":path,"chains":metadata["chains"],"draws_per_chain":metadata["production_draws_per_chain"],"total_draws":metadata["chains"]*metadata["production_draws_per_chain"],"finite":True,"stable":True,"sha256":metadata["artifact_sha256"],"status":"PASS"})
    pd.DataFrame(sensitivity_irf).to_csv(OUT/"irf_sensitivity_summary.csv",index=False);pd.DataFrame(sensitivity_sign).to_csv(OUT/"irf_sign_sensitivity.csv",index=False);pd.DataFrame(sensitivity_fevd).to_csv(OUT/"fevd_sensitivity_summary.csv",index=False);pd.DataFrame(artifact_rows).to_csv(OUT/"posterior_artifact_audit.csv",index=False)
    numerical_pass=identity<=1e-10 and sensitivity_identity<=1e-10 and np.isfinite(irfs).all() and np.isfinite(fevds).all();core_sign_pass=all(x["status"]!="FAIL" for x in checks);sign_frame=pd.DataFrame(sensitivity_sign);core=sign_frame[(sign_frame.horizon==0)&(sign_frame.state=="p")&sign_frame.shock.isin(["demand","cost","supply"])]
    reversals=core[((core.shock.isin(["demand","cost"]))&(core["median"]<=0))|((core.shock=="supply")&(core["median"]>=0))];sensitivity_pass=len(reversals)==0
    baseline_pass=numerical_pass and core_sign_pass;ready=baseline_pass and sensitivity_pass
    gates=[{"gate":"BASELINE_POSTERIOR_INTEGRITY","status":"PASS"},{"gate":"IRF_NUMERICAL","status":"PASS" if numerical_pass else "FAIL"},{"gate":"FEVD_IDENTITY","status":"PASS" if identity<=1e-10 and sensitivity_identity<=1e-10 else "FAIL"},{"gate":"STRUCTURAL_SIGNS","status":"PASS_WITH_WEAK_AC_WARNING" if core_sign_pass else "FAIL"},{"gate":"SENSITIVITY_ARTIFACTS","status":"PASS"},{"gate":"SENSITIVITY_PROPAGATION","status":"PASS_WITH_WARNING" if sensitivity_pass else "FAIL","reason":"AMPLITUDE_AND_INVENTORY_SENSITIVITY" if sensitivity_pass else "STRUCTURAL_RESULTS_ASSUMPTION_SENSITIVE"},{"gate":"PHASE_2E_READY","status":"YES" if ready else "NO","reason":"PASS_WITH_WARNING" if ready else "STRUCTURAL_RESULTS_ASSUMPTION_SENSITIVE"}];pd.DataFrame(gates).to_csv(OUT/"phase2e_gate_summary.csv",index=False)
    _summary_plot(state,OUT/"irf_price_4shocks.png","Posterior price-state IRFs")
    targets={"demand":["d","q","n","p"],"cost":["c","q","n","p"],"supply":["q","n","p","d"],"price":["p","q","n","d"]}
    for shock,names in targets.items():_summary_plot(pd.concat([state[state.shock==shock].assign(shock=s) for s in SHOCK_ORDER]),OUT/f"irf_{shock}_shock_states.png",f"{shock.title()} shock state responses",names)
    pivot=fevd_price.pivot(index="horizon",columns="shock",values="median");pivot.plot(kind="bar",stacked=True,figsize=(7,4));plt.ylabel("share");plt.tight_layout();plt.savefig(OUT/"fevd_price_horizons.png",dpi=180);plt.close()
    fig,ax=plt.subplots(figsize=(7,4))
    for shock in SHOCK_ORDER:
        x=fevd_price[fevd_price.shock==shock];ax.plot(x.horizon,x["median"],label=shock);ax.fill_between(x.horizon.astype(float),x.q05.astype(float),x.q95.astype(float),alpha=.12)
    ax.legend();ax.set_ylabel("price FEVD share");fig.tight_layout();fig.savefig(OUT/"fevd_price_posterior_bands.png",dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,4,figsize=(14,3),sharex=True);plot_targets=(("demand","p"),("cost","p"),("supply","p"),("price","q"))
    for ax,(shock,target_state) in zip(axes,plot_targets):
        base=state[(state.shock==shock)&(state.state==target_state)];ax.plot(base.horizon,base["median"],color="black",lw=2,label="baseline")
        for name,values in plot_data.items():ax.plot(np.arange(Hmax+1),np.median(values[(shock,target_state)],axis=0),lw=.8,alpha=.8,label=name)
        ax.axhline(0,color="grey",lw=.5);ax.set_title(f"{shock} → {target_state}");ax.set_xlabel("month")
    axes[0].legend(fontsize=6);fig.tight_layout();fig.savefig(OUT/"sensitivity_irf_price.png",dpi=180);plt.close(fig)
    if hashlib.sha256(FREEZE.read_bytes()).hexdigest()!=before:raise RuntimeError("Freeze changed")
    print(json.dumps({"baseline_pass":baseline_pass,"phase2e_ready":ready,"sensitivity_artifacts":len(cfg["sensitivity_artifacts"]),"max_identity_error":max(identity,sensitivity_identity),"core_sign_reversals":len(reversals),"residual":resrow},indent=2))
if __name__=="__main__":main()
