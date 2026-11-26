"""Run the frozen Phase 2C constrained estimation and identification preflight."""
from __future__ import annotations
import argparse,hashlib,json,sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.curvature import (hessian_step_robustness,high_correlation_pairs,
    matrix_diagnostics,native_covariance,opg_diagnostics,per_time_score)
from src.structural.estimation import EstimationObjective,information_criteria,optimize_start
from src.structural.kalman_diagnostics import innovation_summary,simulate_observations
from src.structural.likelihood import evaluate_m0_likelihood
from src.structural.matrices import system_matrices
from src.structural.measurement import build_measurements,load_frozen_panel
from src.structural.optimization_diagnostics import (cluster_solutions,detect_ridge,
    generate_stable_starts,normalized_parameter_distance)
from src.structural.parameter_transform import (PARAMETER_ORDER,ParameterTransform,
    boundary_diagnostics,load_phase2a_bounds,parameter_bounds,parameter_category)
from src.structural.profiles import attach_profile_deltas,run_profile,summarize_profile
from src.structural.spec import baseline_parameters
from src.structural.stability import stability_metrics
from src.structural.state_space import from_phase2a_parameters

OUT=ROOT/"outputs/phase2/phase2c";FREEZE=ROOT/"data/processed/core_monthly_panel.csv"
PANEL=ROOT/"data/processed/phase1/monthly_structural_v1.csv"


def _worker(payload):
    transform,y,start,settings=payload
    objective=EstimationObjective(transform,y,settings["rho_n"],settings["battery_sd"],settings["kind"],settings["penalty"])
    return optimize_start(objective,start["theta"],start["start_id"],start["source"],"L-BFGS-B",
                          settings["maxiter"],settings["ftol"],settings["z_bound"])


def _profile_worker(payload):
    transform,y,name,grid,best,cfg,maxiter,rho_n,battery_sd=payload
    rows=run_profile(transform,y,name,grid,best["theta"],rho_n=rho_n,battery_sd=battery_sd,
                     penalty=cfg["large_penalty"],maxiter=maxiter,ftol=cfg["optimizer_ftol"],z_bound=cfg["optimizer_z_bound"])
    attach_profile_deltas(rows,best["loglik"])
    return rows,summarize_profile(rows,best["loglik"],cfg["profile_support_delta_loglik"])


def parallel_multistart(transform,y,starts,cfg,kind="mle",rho_n=None,battery_sd=None,maxiter=None,workers=8):
    settings={"rho_n":cfg["rho_n_fixed"] if rho_n is None else rho_n,"battery_sd":cfg["battery_sd_fixed"] if battery_sd is None else battery_sd,
              "kind":kind,"penalty":cfg["large_penalty"],"maxiter":cfg["optimizer_maxiter"] if maxiter is None else maxiter,
              "ftol":cfg["optimizer_ftol"],"z_bound":cfg["optimizer_z_bound"]}
    tagged=[{**s,"start_id":i} for i,s in enumerate(starts)]
    payload=[(transform,y,s,settings) for s in tagged]
    with ProcessPoolExecutor(max_workers=min(workers,len(payload))) as pool:return list(pool.map(_worker,payload))


def flatten_solution(row):
    out={k:v for k,v in row.items() if k not in ("theta","audit")}
    out.update({f"theta_{n}":row["theta"][n] for n in PARAMETER_ORDER})
    audit=row["audit"]
    for key in ("evaluations","valid_evaluations","unstable_evaluations","invalid_evaluations","kalman_failures","nonfinite_evaluations"):
        out[f"audit_{key}"]=getattr(audit,key)
    return out


def best_valid(rows):
    valid=[r for r in rows if r["valid"] and np.isfinite(r["loglik"])]
    if not valid:raise RuntimeError("no valid finite optimization solution")
    return max(valid,key=lambda r:r["loglik"])


def profile_tables(transform,y,best,cfg,parameters=None,maxiter=160,rho_n=None,battery_sd=None,workers=6):
    parameters=parameters or cfg["profile_parameters"];all_rows=[];summaries=[]
    payload=[]
    for name in parameters:
        lo,hi=transform.bounds[name];grid=np.linspace(lo,hi,cfg["profile_points"])
        payload.append((transform,y,name,grid,best,cfg,maxiter,cfg["rho_n_fixed"] if rho_n is None else rho_n,cfg["battery_sd_fixed"] if battery_sd is None else battery_sd))
    with ProcessPoolExecutor(max_workers=min(workers,len(payload))) as pool:results=list(pool.map(_profile_worker,payload))
    for rows,summary in results:all_rows.extend(rows);summaries.append(summary)
    return all_rows,summaries


def load_solution_rows(path):
    table=pd.read_csv(path);rows=[]
    for record in table.to_dict("records"):
        theta={n:float(record[f"theta_{n}"]) for n in PARAMETER_ORDER}
        row={k:v for k,v in record.items() if not k.startswith("theta_") and not k.startswith("audit_")}
        row["theta"]=theta;row["valid"]=bool(row["valid"]);row["success"]=bool(row["success"]);rows.append(row)
    return rows


def curvature_bundle(transform,y,best,cfg,rho_n=None,battery_sd=None):
    rho_n=cfg["rho_n_fixed"] if rho_n is None else rho_n;battery_sd=cfg["battery_sd_fixed"] if battery_sd is None else battery_sd
    objective=EstimationObjective(transform,y,rho_n,battery_sd,"mle",cfg["large_penalty"]);z=transform.theta_to_unconstrained(best["theta"])
    rows,mats=hessian_step_robustness(objective,z,cfg["hessian_steps"],transform.free_parameters);H=mats[0];diag=matrix_diagnostics(H,transform.free_parameters)
    def contributions(zz):
        theta=transform.unconstrained_to_theta(zz);p={**theta,"rho_n":rho_n};result=evaluate_m0_likelihood(p,battery_sd,y)
        if result.status!="OK":return np.full(len(y),-cfg["large_penalty"]/len(y))
        return result.filter_result.loglik_by_t
    scores=per_time_score(contributions,z,cfg["hessian_steps"][0]);opg,opgd=opg_diagnostics(scores,transform.free_parameters)
    cov,_=native_covariance(H,transform,z);pairs=high_correlation_pairs(cov,transform.free_parameters)
    return rows,H,diag,scores,opg,opgd,cov,pairs


def write_profile(rows,summaries,prefix=""):
    clean=[]
    for r in rows:
        x={k:v for k,v in r.items() if k!="theta"}
        if r.get("theta"):x.update({f"theta_{n}":r["theta"][n] for n in PARAMETER_ORDER})
        clean.append(x)
    pd.DataFrame(clean).to_csv(OUT/f"{prefix}profile_likelihood.csv",index=False)
    pd.DataFrame(summaries).to_csv(OUT/f"{prefix}profile_summary.csv",index=False)


def synthetic_stage(a,cfg,bounds,baseline):
    transform=ParameterTransform.full(bounds);model=from_phase2a_parameters("M0_CORE5",baseline,cfg["battery_sd_fixed"])
    _,y,_=simulate_observations(model,cfg["synthetic_T"],cfg["synthetic_burn"],cfg["random_seed"])
    base_z=transform.theta_to_unconstrained(baseline);starts=[]
    for i in range(cfg["synthetic_starts"]):
        if i==0:z=base_z
        else:z=np.clip(base_z+.08*np.sin((i+1)*(np.arange(len(base_z))+1)),-5,5)
        theta=transform.unconstrained_to_theta(z);starts.append({"theta":theta,"source":"truth" if i==0 else "truth_neighborhood"})
    rows=parallel_multistart(transform,y,starts,cfg,maxiter=cfg["synthetic_optimizer_maxiter"],workers=8);best=best_valid(rows)
    for row in rows:
        row["normalized_recovery_rmse"]=float(np.sqrt(np.mean([((row["theta"][n]-baseline[n])/(bounds[n][1]-bounds[n][0]))**2 for n in PARAMETER_ORDER])))
        row["boundary_count"]=sum(bool(x["boundary_flag"]) for x in boundary_diagnostics(row["theta"],bounds,cfg["boundary_fraction"]))
    errors=np.array([abs(best["theta"][n]-baseline[n])/(bounds[n][1]-bounds[n][0]) for n in PARAMETER_ORDER]);truth=evaluate_m0_likelihood(baseline,cfg["battery_sd_fixed"],y)
    clusters=cluster_solutions(rows,bounds,cfg["mode_same_loglik_tol"],cfg["mode_same_distance_tol"])
    top=sum(r["valid"] and best["loglik"]-r["loglik"]<=cfg["synthetic_top_basin_loglik_tol"] for r in rows);successful=sum(r["valid"] for r in rows)
    boundary=sum(bool(r["boundary_flag"]) for r in boundary_diagnostics(best["theta"],bounds,cfg["boundary_fraction"]))
    review=float(np.sqrt(np.mean(errors**2)))>cfg["synthetic_recovery_rmse_review"]
    for row in rows:
        row["strict_converged"]=bool(row["success"] and row["valid"] and row["spectral_radius"]<1)
        row["practically_converged"]=bool(row["valid"] and row["spectral_radius"]<1 and row["terminated_at_iteration_cap"]
            and row["projected_gradient_norm"]<=cfg["synthetic_practical_gradient_norm"]
            and row["recent_objective_improvement"]<=cfg["synthetic_practical_objective_improvement"]
            and best["loglik"]-row["loglik"]<=cfg["synthetic_top_basin_loglik_tol"])
        row["convergence_classification"]="STRICT_CONVERGED" if row["strict_converged"] else "PRACTICALLY_CONVERGED" if row["practically_converged"] else "NOT_CONVERGED"
    converged=sum(r["strict_converged"] or r["practically_converged"] for r in rows)
    gate=bool(np.isfinite(best["loglik"]) and best["spectral_radius"]<1 and best["max_jitter"]<=0 and successful>0
              and converged/max(1,successful)>=cfg["synthetic_converged_majority_fraction"]
              and top/max(1,successful)>=cfg["synthetic_converged_majority_fraction"] and boundary<=4 and not review)
    summary={"retained_T":len(y),"seed":cfg["random_seed"],"truth_loglik":truth.loglik,"mle_loglik":best["loglik"],
             "normalized_rmse":float(np.sqrt(np.mean(errors**2))),"max_normalized_error":float(errors.max()),"valid_starts":successful,
             "optimizer_success_starts":sum(r["success"] for r in rows),"strict_converged_starts":sum(r["strict_converged"] for r in rows),
             "practically_converged_starts":sum(r["practically_converged"] for r in rows),"accepted_converged_starts":converged,
             "top_basin_within_tolerance":top,"cluster_count":len(clusters),"boundary_count":boundary,
             "spectral_radius":best["spectral_radius"],"max_jitter":best["max_jitter"],"recovery_review":review,"gate":"PASS" if gate else "FAIL"}
    detail=pd.DataFrame({"parameter":PARAMETER_ORDER,"truth":[baseline[n] for n in PARAMETER_ORDER],"mle":[best["theta"][n] for n in PARAMETER_ORDER],"normalized_absolute_error":errors})
    detail.to_csv(OUT/"synthetic_recovery_parameters.csv",index=False);pd.DataFrame([summary]).to_csv(OUT/"synthetic_recovery_summary.csv",index=False)
    pd.DataFrame([flatten_solution(r) for r in rows]).to_csv(OUT/"synthetic_multistart_results.csv",index=False)
    return gate,summary,best


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--workers",type=int,default=8);parser.add_argument("--resume-after-mle",action="store_true");args=parser.parse_args()
    a=json.loads((ROOT/"configs/phase2a.yaml").read_text());cfg=json.loads((ROOT/"configs/phase2c.yaml").read_text());bounds=load_phase2a_bounds(ROOT/"configs/phase2a.yaml")
    before=hashlib.sha256(FREEZE.read_bytes()).hexdigest();expected=a["data_freeze_sha256"].lower()
    if before.lower()!=expected:raise RuntimeError("Data Freeze v1 hash mismatch")
    OUT.mkdir(parents=True,exist_ok=True);baseline={**baseline_parameters(),**a["baseline"]};baseline["rho_n"]=cfg["rho_n_fixed"]
    if args.resume_after_mle:
        synthetic_summary=pd.read_csv(OUT/"synthetic_recovery_summary.csv").iloc[0].to_dict();synthetic_gate=synthetic_summary["gate"]=="PASS"
        if not synthetic_gate:raise RuntimeError("saved synthetic gate is not PASS")
        print("Resuming after accepted synthetic and real MLE checkpoints",flush=True)
    else:
        synthetic_gate,synthetic_summary,_=synthetic_stage(a,cfg,bounds,baseline)
        print("Synthetic gate",synthetic_summary,flush=True)
        if not synthetic_gate:
            pd.DataFrame([{"gate":"SYNTHETIC_RECOVERY","status":"FAIL"},{"gate":"PHASE_2C_READY","status":"NO"}]).to_csv(OUT/"phase2c_gate_summary.csv",index=False)
            raise SystemExit("STOP REAL ESTIMATION: synthetic recovery gate failed")
    frame=load_frozen_panel(PANEL,a["sample_end"]);measurements=build_measurements(frame,cfg["primary_measurement"]);y=measurements[["spot","ore_cost","output","battery"]].to_numpy()
    if len(y)!=57 or measurements.month.max()>"2025-09":raise RuntimeError("frozen measurement sample mismatch")
    transform=ParameterTransform.full(bounds);starts,start_audit=generate_stable_starts(transform,baseline,cfg["mle_starts"],cfg["random_seed"],cfg["rho_n_fixed"])
    if args.resume_after_mle:mle_rows=load_solution_rows(OUT/"multistart_mle_results.csv");best=best_valid(mle_rows)
    else:
        mle_rows=parallel_multistart(transform,y,starts,cfg,maxiter=260,workers=args.workers);best=best_valid(mle_rows)
        pd.DataFrame([flatten_solution(r) for r in mle_rows]).to_csv(OUT/"multistart_mle_results.csv",index=False)
    clusters=cluster_solutions(mle_rows,bounds,cfg["mode_same_loglik_tol"],cfg["mode_same_distance_tol"]);pd.DataFrame(clusters).to_csv(OUT/"solution_clusters.csv",index=False)
    ridge,ridge_rows=detect_ridge(mle_rows,bounds,cfg["ridge_loglik_tol"],cfg["ridge_distance_threshold"])
    bd=boundary_diagnostics(best["theta"],bounds,cfg["boundary_fraction"]);pd.DataFrame(bd).to_csv(OUT/"boundary_diagnostics.csv",index=False)
    phase1={"a_p":"WEAK","b_n":"WEAK_STATE","b_q":"WEAK","rho_p":"STRUCTURAL_PERSISTENCE","rho_q":"STRUCTURAL_PERSISTENCE","b_c":"STRONG_COST_CHANNEL"}
    roles={"rho_d":"demand persistence","rho_c":"cost persistence","rho_q":"supply persistence","rho_p":"price persistence","a_p":"lagged price to supply","a_c":"cost pressure on supply","b_d":"demand loading","b_c":"cost loading","b_q":"supply loading","b_n":"inventory loading","sigma_d":"demand shock scale","sigma_c":"cost shock scale","sigma_q":"supply shock scale","sigma_p":"price shock scale"}
    params=pd.DataFrame([{**r,"phase1_evidence":phase1.get(r["parameter"],"PRE-SPECIFIED SIGN"),"structural_role":roles[r["parameter"]]} for r in bd]);params.to_csv(OUT/"mle_mode_parameters.csv",index=False)
    print(f"Real MLE {best['loglik']:.6f}; valid {sum(r['valid'] for r in mle_rows)}/{len(mle_rows)}",flush=True)
    cross_obj=EstimationObjective(transform,y,cfg["rho_n_fixed"],cfg["battery_sd_fixed"],"mle",cfg["large_penalty"])
    powell=optimize_start(cross_obj,best["theta"],0,"best_mle","Powell",500,cfg["optimizer_ftol"],cfg["optimizer_z_bound"])
    powell_delta=powell["loglik"]-best["loglik"];powell_distance=normalized_parameter_distance(powell["theta"],best["theta"],bounds)
    optimizer_flag=abs(powell_delta)>1e-3 or powell_distance>.05
    powell_row={k:v for k,v in powell.items() if k not in ("theta","audit")};powell_row.update({"delta_loglik_from_lbfgsb":powell_delta,"normalized_parameter_distance":powell_distance})
    pd.DataFrame([powell_row]).to_csv(OUT/"optimizer_crosscheck.csv",index=False)
    profile_rows,profile_summary=profile_tables(transform,y,best,cfg,maxiter=180,workers=min(6,args.workers));write_profile(profile_rows,profile_summary)
    hrows,H,hdiag,scores,opg,opgd,cov,corrpairs=curvature_bundle(transform,y,best,cfg)
    pd.DataFrame(hrows).to_csv(OUT/"hessian_diagnostics.csv",index=False)
    eig_rows=[]
    for d in hdiag["weak_directions"]:eig_rows.append(d)
    pd.DataFrame(eig_rows).to_csv(OUT/"hessian_eigenvectors.csv",index=False)
    pd.DataFrame([{k:v for k,v in opgd.items() if k not in ("eigenvalues","eigenvectors","weak_directions")}]).to_csv(OUT/"opg_diagnostics.csv",index=False)
    weak_rows=[]
    for x in hdiag["weak_directions"]:weak_rows.append({"source":"HESSIAN",**x})
    for x in opgd["weak_directions"]:weak_rows.append({"source":"OPG",**x})
    for x in corrpairs:weak_rows.append({"source":"LOCAL_COVARIANCE",**x})
    pd.DataFrame(weak_rows).to_csv(OUT/"weak_parameter_pairs.csv",index=False)
    triggered_categories=sorted({parameter_category(r["parameter"]) for r in bd if r["boundary_flag"]})
    extended=[]
    for category in triggered_categories:
        ebounds=parameter_bounds(a["parameter_ranges"],[category]);etrans=ParameterTransform.full(ebounds)
        estarts,_=generate_stable_starts(etrans,best["theta"],8,cfg["random_seed"]+100+len(extended),cfg["rho_n_fixed"])
        erows=parallel_multistart(etrans,y,estarts,cfg,maxiter=180,workers=args.workers);ebest=best_valid(erows)
        extended.append({"category":category,"primary_loglik":best["loglik"],"extended_loglik":ebest["loglik"],"delta_loglik":ebest["loglik"]-best["loglik"],
                         "normalized_distance_primary_scale":normalized_parameter_distance(best["theta"],ebest["theta"],bounds),"extended_boundary_count":sum(bool(r["boundary_flag"]) for r in boundary_diagnostics(ebest["theta"],ebounds,cfg["boundary_fraction"])),"replaces_primary":False})
    pd.DataFrame(extended,columns=["category","primary_loglik","extended_loglik","delta_loglik","normalized_distance_primary_scale","extended_boundary_count","replaces_primary"]).to_csv(OUT/"extended_range_checks.csv",index=False)
    sensitivity=[]
    for rn in (.5,.8,.95):
        for sd in (.1,.25,.5):
            if rn==.8 and sd==.25:sbest=best;srows=mle_rows
            else:
                ss,_=generate_stable_starts(transform,best["theta"],cfg["sensitivity_starts"],cfg["random_seed"]+int(rn*1000)+int(sd*100),rn)
                srows=parallel_multistart(transform,y,ss,cfg,rho_n=rn,battery_sd=sd,maxiter=180,workers=args.workers);sbest=best_valid(srows)
            sensitivity.append({"rho_n":rn,"battery_sd":sd,"loglik":sbest["loglik"],"delta_loglik_from_primary":sbest["loglik"]-best["loglik"],
                                "normalized_parameter_distance":normalized_parameter_distance(sbest["theta"],best["theta"],bounds),"boundary_count":sum(bool(r["boundary_flag"]) for r in boundary_diagnostics(sbest["theta"],bounds,cfg["boundary_fraction"])),
                                "spectral_radius":sbest["spectral_radius"],"hessian_condition":"NOT_RUN_COMPUTATION_CONTROL","selects_new_baseline":False})
    pd.DataFrame(sensitivity).to_csv(OUT/"fixed_assumption_sensitivity.csv",index=False)
    map_starts,_=generate_stable_starts(transform,best["theta"],cfg["map_starts"],cfg["random_seed"]+500,cfg["rho_n_fixed"])
    map_rows=parallel_multistart(transform,y,map_starts,cfg,kind="map",maxiter=220,workers=args.workers)
    map_best=min((r for r in map_rows if r["valid"] and np.isfinite(r["objective"])),key=lambda r:r["objective"])
    map_table=[flatten_solution(r) for r in map_rows]
    for r in map_table:r["posterior_objective_label"]="WEAK_DIAGNOSTIC_MODE_NOT_POSTERIOR_ESTIMATE"
    pd.DataFrame(map_table).to_csv(OUT/"map_diagnostic_results.csv",index=False)
    fitted=evaluate_m0_likelihood({**best["theta"],"rho_n":cfg["rho_n_fixed"]},cfg["battery_sd_fixed"],y)
    pd.DataFrame(innovation_summary(fitted.filter_result.standardized_innovations)).to_csv(OUT/"innovation_mode_diagnostics.csv",index=False)
    ap_profile=next(s for s in profile_summary if s["parameter"]=="a_p");ap_zero=next(r for r in profile_rows if r["parameter"]=="a_p" and r["fixed_value"]==0.)
    ap_row=next(r for r in bd if r["parameter"]=="a_p");ap_trigger=bool(ap_row["normalized_position"]<.02 and ap_profile["flat_profile"] and ap_zero["delta_loglik_from_global"]<1.)
    selection=[{"model":"M0_FULL14","k":14,"loglik":best["loglik"],**information_criteria(best["loglik"],14,len(y)),"mode_stability":"RIDGE" if ridge else "MULTISTART_AUDITED","curvature":hdiag["classification"]}]
    ap_best=None;ap_status="NOT_TRIGGERED"
    if ap_trigger:
        aptrans=ParameterTransform.ap0(bounds);apstarts,_=generate_stable_starts(aptrans,{**best["theta"],"a_p":0.},16,cfg["random_seed"]+700,cfg["rho_n_fixed"])
        aprows=parallel_multistart(aptrans,y,apstarts,cfg,maxiter=240,workers=args.workers);ap_best=best_valid(aprows)
        apclusters=cluster_solutions(aprows,bounds,cfg["mode_same_loglik_tol"],cfg["mode_same_distance_tol"])
        aphrows,apH,apdiag,_,_,apopgd,_,_=curvature_bundle(aptrans,y,ap_best,cfg)
        aprofile,apsummary=profile_tables(aptrans,y,ap_best,cfg,parameters=["b_n","b_q","rho_p"],maxiter=160,workers=min(3,args.workers));write_profile(aprofile,apsummary,"ap0_")
        ap_boundary=sum(bool(r["boundary_flag"]) for r in boundary_diagnostics(ap_best["theta"],bounds,cfg["boundary_fraction"]))
        severe=any(s["flat_profile"] and s["support_boundary_open"] for s in apsummary)
        ap_status="AP0_NOT_READY" if severe or apdiag["rank"]<10 or apopgd["rank"]<10 else "AP0_WEAK" if apdiag["classification"]!="CURVATURE_OK" or ap_boundary>2 else "AP0_READY"
        selection.append({"model":"M0_AP0_13","k":13,"loglik":ap_best["loglik"],**information_criteria(ap_best["loglik"],13,len(y)),"mode_stability":f"{len(apclusters)} clusters","curvature":apdiag["classification"]})
    pd.DataFrame(selection).to_csv(OUT/"model_selection_preflight.csv",index=False)
    severe_profile=sum(s["multimodal_profile"] or (s["flat_profile"] and s["support_boundary_open"]) for s in profile_summary)
    full_status="FULL14_NOT_READY" if ridge or severe_profile>=2 or hdiag["rank"]<11 or opgd["rank"]<11 or hdiag["classification"]=="INDEFINITE_CURVATURE" else "FULL14_READY"
    if ap_trigger and ap_status=="AP0_READY":selected="M0_AP0_13";ready="YES"
    elif full_status=="FULL14_READY":selected="M0_FULL14";ready="YES"
    else:selected="NO ESTIMATION SPEC READY";ready="NO"
    sensitive_cells=sum(r["normalized_parameter_distance"]>.2 and abs(r["delta_loglik_from_primary"])<=5. for r in sensitivity)
    sensitivity_class="FIXED_ASSUMPTION_SENSITIVE_RIDGE" if sensitive_cells>=2 else "ROBUST_TO_FIXED_ASSUMPTIONS"
    gate_rows=[{"gate":"SYNTHETIC_RECOVERY","status":"PASS"},{"gate":"FULL14","status":full_status},{"gate":"AP0","status":ap_status},
               {"gate":"OPTIMIZER_CROSSCHECK","status":"OPTIMIZER_SENSITIVITY_FLAG" if optimizer_flag else "PASS"},{"gate":"FIXED_ASSUMPTIONS","status":sensitivity_class},
               {"gate":"PHASE_2C_READY","status":ready,"selected_specification":selected}]
    pd.DataFrame(gate_rows).to_csv(OUT/"phase2c_gate_summary.csv",index=False)
    after=hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    if after!=before:raise RuntimeError("Data Freeze changed during estimation")
    run_summary={"sample_start":measurements.month.iloc[0],"sample_end":measurements.month.iloc[-1],"N":len(y),"freeze_sha256":after,
                 "design_loglik":-513.9047,"mle_loglik":best["loglik"],"valid_starts":sum(r["valid"] for r in mle_rows),"optimizer_success_starts":sum(r["success"] for r in mle_rows),
                 "cluster_count":len(clusters),"top_cluster_size":clusters[0]["size"] if clusters else 0,"ridge_flag":ridge,"boundary_count":sum(bool(r["boundary_flag"]) for r in bd),
                 "hessian_classification":hdiag["classification"],"hessian_rank":hdiag["rank"],"hessian_condition":hdiag["condition_number"],"opg_rank":opgd["rank"],"opg_condition":opgd["condition_number"],
                 "map_mle_distance":normalized_parameter_distance(map_best["theta"],best["theta"],bounds),"map_loglik":map_best["loglik"],"map_prior":map_best["prior"],
                 "a_p_trigger":ap_trigger,"full14_status":full_status,"ap0_status":ap_status,"selected_specification":selected,"phase2c_ready":ready,
                 "start_generated":start_audit["generated"],"start_stable":start_audit["stable"],"start_rejected_unstable":start_audit["rejected_unstable"]}
    pd.DataFrame([run_summary]).to_csv(OUT/"phase2c_run_summary.csv",index=False)
    print(json.dumps(run_summary,ensure_ascii=False,indent=2),flush=True)


if __name__=="__main__":main()
