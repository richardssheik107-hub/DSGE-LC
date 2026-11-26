"""Run fixed-design Phase 2B Kalman, smoother and likelihood validation."""
from __future__ import annotations

import hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.structural.kalman import kalman_filter, rts_smoother
from src.structural.kalman_diagnostics import (covariance_audit, initialization_comparison,
    innovation_summary, simulate_observations, state_rmse)
from src.structural.likelihood import evaluate_m0_likelihood, gaussian_loglikelihood
from src.structural.measurement import build_measurements, load_frozen_panel
from src.structural.spec import baseline_parameters
from src.structural.state_space import (diffuse_initialization, from_phase2a_parameters,
    stationary_initialization)

PHASE2A=ROOT/"configs/phase2a.yaml"; PHASE2B=ROOT/"configs/phase2b.yaml"
FREEZE=ROOT/"data/processed/core_monthly_panel.csv"; PANEL=ROOT/"data/processed/phase1/monthly_structural_v1.csv"
OUT=ROOT/"outputs/phase2/phase2b"

def write_states(path,months,names,values):
    frame=pd.DataFrame(values,columns=names); frame.insert(0,"month",months); frame.to_csv(path,index=False)

def main():
    a=json.loads(PHASE2A.read_text(encoding="utf-8")); cfg=json.loads(PHASE2B.read_text(encoding="utf-8"))
    if hashlib.sha256(FREEZE.read_bytes()).hexdigest().lower()!=a["data_freeze_sha256"].lower(): raise RuntimeError("Data Freeze v1 hash mismatch")
    OUT.mkdir(parents=True,exist_ok=True)
    p={**baseline_parameters(),**a["baseline"]}; battery_sd=float(a["baseline"]["battery_measurement_sd"])
    panel=load_frozen_panel(PANEL,a["sample_end"]); primary=build_measurements(panel,cfg["primary_measurement"]); secondary=build_measurements(panel,cfg["secondary_measurement"])
    y=primary[["spot","ore_cost","output","battery"]].to_numpy(); months=primary.month.to_numpy()
    model=from_phase2a_parameters("M0_CORE5",p,battery_sd); mean0,P0,lyap=stationary_initialization(model)
    options={"jitter_ladder":tuple(cfg["jitter_ladder"]),"psd_tolerance":cfg["psd_tolerance"],"maximum_jitter_multiplier":cfg["maximum_allowed_jitter_scale"]}
    real=kalman_filter(model,y,time_index=months,initial_mean=mean0,initial_cov=P0,**options); smooth=rts_smoother(model,real,cfg["psd_tolerance"])
    pred_audit=covariance_audit(real.predicted_cov,cfg["psd_tolerance"]); filt_audit=covariance_audit(real.filtered_cov,cfg["psd_tolerance"]); smooth_audit=covariance_audit(smooth.smoothed_cov,cfg["psd_tolerance"])
    real_summary=[{"model":"M0_CORE5","measurement":cfg["primary_measurement"],"start":months[0],"end":months[-1],"n":len(y),"fixed_design_loglik":real.loglik,"average_loglik":real.loglik/len(y),"filter_status":real.status,"smoother_status":smooth.status,"lyapunov_residual":lyap,"W_rank":np.linalg.matrix_rank(model.W),"max_jitter":np.nanmax(real.jitter_used),"prediction_psd_violations":pred_audit["violations"],"filter_psd_violations":filt_audit["violations"],"smoother_psd_violations":smooth_audit["violations"]}]
    pd.DataFrame(real_summary).to_csv(OUT/"kalman_realdata_summary.csv",index=False)
    pd.DataFrame({"month":months,"loglik_contribution":real.loglik_by_t,"observed_dimensions":real.observed_mask.sum(axis=1),"jitter":real.jitter_used}).to_csv(OUT/"kalman_loglik_contributions.csv",index=False)
    write_states(OUT/"filtered_states_baseline.csv",months,model.state_names,real.filtered_mean)
    write_states(OUT/"smoothed_states_baseline.csv",months,model.state_names,smooth.smoothed_mean)

    init={"stationary":(mean0,P0)}
    for scale in cfg["diffuse_scales"]: init[f"diffuse_{int(scale)}"]=diffuse_initialization(model,scale)
    pd.DataFrame(initialization_comparison(model,y,init,time_index=months,**options)).to_csv(OUT/"initialization_sensitivity.csv",index=False)

    fixed=[]
    for rn in cfg["rho_n_grid"]:
        for sd in cfg["battery_sd_grid"]:
            pp=dict(p); pp["rho_n"]=rn; mm=from_phase2a_parameters("M0_CORE5",pp,sd); rr=kalman_filter(mm,y,**options)
            observed_eigs=[np.linalg.eigvalsh(rr.innovation_cov[t][np.ix_(rr.observed_mask[t],rr.observed_mask[t])]).min() for t in range(len(y))]
            fixed.append({"configuration_type":"rho_n_battery_sd_grid","parameter":"grid","direction":"fixed","rho_n":rn,"battery_sd":sd,"fraction":0.,"status":"NUMERICALLY_VALID" if rr.status=="OK" else "REVIEW","loglik":rr.loglik,"average_loglik":rr.loglik/len(y),"max_jitter":np.nanmax(rr.jitter_used),"min_innovation_eigenvalue":min(observed_eigs),"terminal_covariance_trace":np.trace(rr.filtered_cov[-1])})
    frac=cfg["likelihood_perturbation_fraction"]
    for name in ("rho_p","b_c","b_n","sigma_p"):
        for direction in (-1,1):
            pp=dict(p); pp[name]*=1+direction*frac; rr=evaluate_m0_likelihood(pp,battery_sd,y,**options)
            fixed.append({"configuration_type":"predefined_parameter_perturbation","parameter":name,"direction":"minus" if direction<0 else "plus","rho_n":pp["rho_n"],"battery_sd":battery_sd,"fraction":direction*frac,"status":"NUMERICALLY_VALID" if rr.status=="OK" else "REVIEW","loglik":rr.loglik,"average_loglik":rr.loglik/len(y),"max_jitter":np.nanmax(rr.filter_result.jitter_used) if rr.filter_result else np.nan,"min_innovation_eigenvalue":np.nan,"terminal_covariance_trace":np.trace(rr.filter_result.filtered_cov[-1]) if rr.filter_result else np.nan})
    pd.DataFrame(fixed).to_csv(OUT/"fixed_parameter_sensitivity.csv",index=False)

    sy_states,sy_obs,_=simulate_observations(model,cfg["synthetic_T"]-cfg["synthetic_burn"],cfg["synthetic_burn"],cfg["synthetic_seed"])
    sy_filter=kalman_filter(model,sy_obs,**options); sy_smooth=rts_smoother(model,sy_filter,cfg["psd_tolerance"])
    f_rmse=state_rmse(sy_states,sy_filter.filtered_mean); s_rmse=state_rmse(sy_states,sy_smooth.smoothed_mean)
    pd.DataFrame([{"state":name,"filtered_rmse":f_rmse[i],"smoothed_rmse":s_rmse[i],"smoother_not_worse":s_rmse[i]<=f_rmse[i]+1e-10} for i,name in enumerate(model.state_names)]).to_csv(OUT/"synthetic_state_rmse.csv",index=False)
    synth_innov=innovation_summary(sy_filter.standardized_innovations)
    pd.DataFrame([{"sample":"synthetic",**r} for r in synth_innov]+[{"sample":"real_fixed_design",**r} for r in innovation_summary(real.standardized_innovations)]).to_csv(OUT/"innovation_diagnostics.csv",index=False)
    sy_cov=covariance_audit(sy_filter.filtered_cov,cfg["psd_tolerance"]); sy_s_cov=covariance_audit(sy_smooth.smoothed_cov,cfg["psd_tolerance"])
    pd.DataFrame([{"retained_T":len(sy_obs),"seed":cfg["synthetic_seed"],"filter_status":sy_filter.status,"smoother_status":sy_smooth.status,"loglik":sy_filter.loglik,"max_jitter":np.nanmax(sy_filter.jitter_used),"filtered_covariance_violations":sy_cov["violations"],"smoothed_covariance_violations":sy_s_cov["violations"],"latent_filtered_rmse":float(np.sqrt(np.mean((sy_states[:,[0,3]]-sy_filter.filtered_mean[:,[0,3]])**2))),"latent_smoothed_rmse":float(np.sqrt(np.mean((sy_states[:,[0,3]]-sy_smooth.smoothed_mean[:,[0,3]])**2)))}]).to_csv(OUT/"synthetic_validation_summary.csv",index=False)

    gross=[]
    truth_ll=sy_filter.loglik
    specs=[]
    for name in ("rho_d","rho_c","rho_q","rho_p"):
        for delta in (-.2,.2): specs.append((name,"add",delta))
    for name in ("b_c","b_n","sigma_p"):
        for factor in (.5,1.5): specs.append((name,"multiply",factor))
    for name,operation,value in specs:
        pp=dict(p); pp[name]=pp[name]+value if operation=="add" else pp[name]*value
        rr=evaluate_m0_likelihood(pp,battery_sd,sy_obs,**options)
        gross.append({"profile":"gross_perturbation","parameter":name,"operation":operation,"grid_value":value,"parameter_value":pp[name],"loglik":rr.loglik,"status":rr.status,"is_truth":False})
    profiles=[]
    for name in ("rho_d","b_c","b_n","sigma_p"):
        for factor in (.7,.85,1.,1.15,1.3):
            pp=dict(p); pp[name]=min(.999,pp[name]*factor) if name.startswith("rho_") else pp[name]*factor
            rr=evaluate_m0_likelihood(pp,battery_sd,sy_obs,**options)
            profiles.append({"profile":"one_dimensional","parameter":name,"operation":"multiply","grid_value":factor,"parameter_value":pp[name],"loglik":rr.loglik,"status":rr.status,"is_truth":factor==1.})
    all_profile=[{"profile":"truth","parameter":"all","operation":"fixed","grid_value":1.,"parameter_value":np.nan,"loglik":truth_ll,"status":sy_filter.status,"is_truth":True}]+gross+profiles
    pd.DataFrame(all_profile).to_csv(OUT/"synthetic_likelihood_profiles.csv",index=False)

    miss=[]; pattern=cfg["missing_test_pattern"]
    variants={"battery_every_10":sy_obs.copy(),"output_every_12":sy_obs.copy(),"spot_only_month":sy_obs.copy(),"all_missing_month":sy_obs.copy()}
    variants["battery_every_10"][::pattern["battery_every"],3]=np.nan
    variants["output_every_12"][::pattern["output_every"],2]=np.nan
    variants["spot_only_month"][pattern["spot_only_index"],1:]=np.nan
    variants["all_missing_month"][pattern["all_missing_index"],:]=np.nan
    for name,values in variants.items():
        rr=kalman_filter(model,values,**options)
        target=pattern["all_missing_index"] if name=="all_missing_month" else pattern["spot_only_index"] if name=="spot_only_month" else 0
        miss.append({"pattern":name,"status":rr.status,"month_count":len(rr.loglik_by_t),"missing_cells":np.isnan(values).sum(),"target_index":target,"target_observed_dimensions":rr.observed_mask[target].sum(),"target_loglik":rr.loglik_by_t[target],"all_finite_filter":np.isfinite(rr.filtered_mean).all(),"max_jitter":np.nanmax(rr.jitter_used)})
    pd.DataFrame(miss).to_csv(OUT/"missing_observation_validation.csv",index=False)

    m1p=dict(p); m1p.update(a["baseline"]); m1=from_phase2a_parameters("M1_CAPACITY6",m1p,battery_sd); periods=cfg["m1_smoke"]["periods"]
    rng=np.random.default_rng(cfg["synthetic_seed"]); raw=np.zeros(periods+cfg["synthetic_burn"])
    for t in range(1,len(raw)): raw[t]=np.clip(.7*raw[t-1]+rng.normal(scale=.35),-2,2)
    lag=cfg["m1_smoke"]["capacity_lag"]; already=np.zeros_like(raw); already[lag:]=raw[:-lag]
    m1_states,m1_obs,m1_controls=simulate_observations(m1,periods,cfg["synthetic_burn"],cfg["synthetic_seed"]+1,already.reshape(-1,1))
    m1_filter=kalman_filter(m1,m1_obs,controls=m1_controls,**options)
    pd.DataFrame([{"model":"M1_CAPACITY6","periods":periods,"lag":lag,"control_dim":m1.control_dim,"filter_status":m1_filter.status,"smoother_status":"NOT_RUN_NOT_REQUIRED","finite":np.isfinite(m1_filter.filtered_mean).all(),"control_already_lagged":True,"engine_applied_additional_lag":False,"future_control_used":False,"max_jitter":np.nanmax(m1_filter.jitter_used),"note":"capacity has no independent shock; compatibility gate covers control-aligned filtering only"}]).to_csv(OUT/"m1_compatibility_smoke.csv",index=False)

    sec_y=secondary[["spot","ore_cost","output","battery"]].to_numpy(); sec=kalman_filter(model,sec_y,**options); sec_s=rts_smoother(model,sec,cfg["psd_tolerance"])
    lower_share=float(np.mean([row["loglik"]<truth_ll for row in gross if np.isfinite(row["loglik"])])); truth_rank=1+sum(row["loglik"]>truth_ll for row in gross)
    synth_reasonable=all(abs(r["mean"])<.15 and .7<r["variance"]<1.3 and abs(r["lag1_autocorrelation"])<.15 for r in synth_innov)
    synthetic_pass=sy_filter.status==sy_smooth.status=="OK" and sy_cov["violations"]==sy_s_cov["violations"]==0 and lower_share>.5 and synth_reasonable and all(x.status=="OK" for x in [kalman_filter(model,v,**options) for v in variants.values()])
    real_pass=real.status==smooth.status=="OK" and len(y)==57 and np.isfinite(real.loglik_by_t).all() and pred_audit["violations"]==filt_audit["violations"]==smooth_audit["violations"]==0 and all(row["status"]=="NUMERICALLY_VALID" for row in fixed) and sec.status==sec_s.status=="OK"
    gate=[{"gate":"SYNTHETIC","status":"PASS" if synthetic_pass else "FAIL","truth_loglik":truth_ll,"truth_rank":truth_rank,"gross_lower_share":lower_share,"detail":"fixed-seed filter/smoother/likelihood/missingness validation"},{"gate":"REAL_DATA_PLUMBING","status":"PASS" if real_pass else "FAIL","truth_loglik":np.nan,"truth_rank":np.nan,"gross_lower_share":np.nan,"detail":"fixed design point; no parameters estimated"},{"gate":"SECONDARY_SMOKE","status":"PASS" if sec.status==sec_s.status=="OK" else "FAIL","truth_loglik":sec.loglik,"truth_rank":np.nan,"gross_lower_share":np.nan,"detail":f"{cfg['secondary_measurement']} N={len(sec_y)}; raw likelihood not compared"},{"gate":"M1_COMPATIBILITY","status":"PASS" if m1_filter.status=="OK" else "FAIL","truth_loglik":m1_filter.loglik,"truth_rank":np.nan,"gross_lower_share":np.nan,"detail":"synthetic already-lagged control filter only; M1 remains extension"}]
    pd.DataFrame(gate).to_csv(OUT/"phase2b_gate_summary.csv",index=False)
    print(pd.DataFrame(gate).to_string(index=False)); print(f"Real fixed-design loglik: {real.loglik:.6f}; outputs: {OUT}")

if __name__=="__main__": main()
