"""Run Phase 2D prior, adaptive-RWM, convergence and posterior-ID diagnostics."""
from __future__ import annotations
import argparse,hashlib,json,sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.kalman_diagnostics import simulate_observations
from src.structural.curvature import finite_difference_hessian
from src.structural.mcmc import PosteriorEvaluation,PosteriorTarget,extend_chain,run_adaptive_chain
from src.structural.mcmc_diagnostics import acceptance_summary,convergence_pass,diagnostic_table
from src.structural.measurement import build_measurements,load_frozen_panel
from src.structural.parameter_transform import PARAMETER_ORDER,ParameterTransform,load_phase2a_bounds
from src.structural.posterior_artifacts import save_posterior_artifact
from src.structural.posterior_diagnostics import (covariance_weak_directions,identification_classifications,observable_moments,
    posterior_correlation,posterior_summary,prior_posterior_contraction,sensitivity_shift,spectral_radius_summary)
from src.structural.priors import draw_stable_prior,effective_prior_audit,prior_specs,theta_from_array
from src.structural.profiles import attach_profile_deltas,run_profile
from src.structural.spec import baseline_parameters
from src.structural.state_space import from_phase2a_parameters

OUT=ROOT/"outputs/phase2/phase2d";FREEZE=ROOT/"data/processed/core_monthly_panel.csv";PANEL=ROOT/"data/processed/phase1/monthly_structural_v1.csv"


class IdentityTransform:
    def __init__(self,d):self.d=d
    def unconstrained_to_theta(self,z):return {f"x{i}":float(v) for i,v in enumerate(z)}


class GaussianTarget:
    def __init__(self,mean,cov):self.mean=np.asarray(mean);self.precision=np.linalg.inv(cov);self.transform=IdentityTransform(len(mean))
    def __call__(self,z):
        d=np.asarray(z)-self.mean;v=float(-.5*d@self.precision@d);return PosteriorEvaluation(v,v,0.,0.,"OK",0.,0.)


class BetaZTarget:
    def __init__(self,a=2.,b=3.,jacobian=True):self.a=a;self.b=b;self.jacobian=jacobian;self.transform=IdentityTransform(1)
    def __call__(self,z):
        z=float(np.asarray(z)[0]);theta=1/(1+np.exp(-z));lp=(self.a-1)*np.log(theta)+(self.b-1)*np.log1p(-theta);lj=np.log(theta)+np.log1p(-theta) if self.jacobian else 0.;return PosteriorEvaluation(float(lp+lj),float(lp),0.,float(lj),"OK",0.,0.)


def _chain_worker(payload):
    target,start,warmup,production,seed,settings=payload
    return run_adaptive_chain(target,start,warmup,production,seed,target_accept=settings["warmup_acceptance_target"],mixture_probability=settings["proposal_mixture_probability"],ridge=settings["proposal_ridge"],small_scale=settings["small_proposal_scale"],initial_chol=settings.get("initial_chol"),initial_scale=settings.get("initial_scale"))


def _extend_worker(payload):return extend_chain(*payload)


def _fine_profile_worker(payload):
    transform,y,name,grid,best,cfg=payload
    rows=run_profile(transform,y,name,grid,best["theta"],rho_n=cfg["rho_n_fixed"],battery_sd=cfg["battery_sd_fixed"],maxiter=cfg["fine_profile_maxiter"],ftol=1e-8,z_bound=8.)
    return attach_profile_deltas(rows,best["loglik"])


def load_phase2c_modes():
    mle=pd.read_csv(ROOT/"outputs/phase2/phase2c/mle_mode_parameters.csv");mle_theta=dict(zip(mle.parameter,mle.estimate));run=pd.read_csv(ROOT/"outputs/phase2/phase2c/phase2c_run_summary.csv").iloc[0]
    maps=pd.read_csv(ROOT/"outputs/phase2/phase2c/map_diagnostic_results.csv").sort_values("objective");row=maps.iloc[0];map_theta={n:float(row[f"theta_{n}"]) for n in PARAMETER_ORDER}
    return {"theta":mle_theta,"loglik":float(run.mle_loglik)},map_theta


def run_fine_profiles(transform,y,mle,cfg,workers):
    grids={"a_c":[0,.001,.0025,.005,.01,.025,.05,.10,.20],"b_n":[0,.005,.01,.02,.03,.05,.075,.10,.15]}
    payload=[(transform,y,n,np.array(g),mle,cfg) for n,g in grids.items()]
    with ProcessPoolExecutor(max_workers=min(workers,2)) as pool:results=list(pool.map(_fine_profile_worker,payload))
    for name,rows in zip(grids,results):
        clean=[]
        for r in rows:clean.append({k:v for k,v in r.items() if k!="theta"})
        pd.DataFrame(clean).to_csv(OUT/f"fine_profile_{'ac' if name=='a_c' else 'bn'}.csv",index=False)
    return dict(zip(grids,results))


def initial_points(transform,mle,map_theta,prior,bounds,cfg):
    stable,_=draw_stable_prior(prior,bounds,200,cfg["seed"]+900,cfg["rho_n_fixed"]);candidates=[]
    for row in stable:
        theta=theta_from_array(row);distance=np.linalg.norm([(theta[n]-mle[n])/(bounds[n][1]-bounds[n][0]) for n in PARAMETER_ORDER])
        if distance>=.15:candidates.append((distance,theta))
    candidates.sort(reverse=True,key=lambda x:x[0]);points=[mle,map_theta,candidates[0][1],candidates[len(candidates)//2][1]]
    return [transform.theta_to_unconstrained(p) for p in points]


def proposal_preconditioner(target,z):
    H=finite_difference_hessian(lambda x:-target(x).total,np.asarray(z,float),1e-4);value,vector=np.linalg.eigh(.5*(H+H.T));floor=max(1e-4,float(np.max(np.abs(value)))*1e-5);safe=np.maximum(value,floor);cov=vector@np.diag(1/safe)@vector.T
    return np.linalg.cholesky(.5*(cov+cov.T)+np.eye(len(z))*1e-10)


def run_chains(target,starts,cfg,workers,warmup=None,production=None,label="posterior",extend_to_gate=True,initial_chol=None):
    warmup=cfg["warmup_draws"] if warmup is None else warmup;production=cfg["initial_production_draws"] if production is None else production
    seeds=[cfg["seed"]+i+1 for i in range(cfg["chains"])];settings={k:cfg[k] for k in ("warmup_acceptance_target","proposal_mixture_probability","proposal_ridge","small_proposal_scale")}
    if initial_chol is not None:settings.update(initial_chol=initial_chol,initial_scale=2.38/np.sqrt(len(starts[0])))
    payload=[(target,starts[i],warmup,production,seeds[i],settings) for i in range(cfg["chains"])]
    if workers==1:results=[_chain_worker(x) for x in payload]
    else:
        with ProcessPoolExecutor(max_workers=min(workers,cfg["chains"])) as pool:results=list(pool.map(_chain_worker,payload))
    while True:
        theta=np.stack([r["theta"] for r in results]);names=PARAMETER_ORDER if theta.shape[2]==14 else tuple(f"x{i}" for i in range(theta.shape[2]));diagnostics=diagnostic_table(theta,names)
        print(label,"draws",theta.shape[1],"max_rhat",max(x["rhat"] for x in diagnostics),"min_bulk",min(x["bulk_ess"] for x in diagnostics),"min_tail",min(x["tail_ess"] for x in diagnostics),flush=True)
        if not extend_to_gate or convergence_pass(diagnostics,cfg) or theta.shape[1]>=cfg["max_production_draws"]:break
        block=min(cfg["extension_block_draws"],cfg["max_production_draws"]-theta.shape[1])
        if workers==1:results=[_extend_worker((target,r,block,None)) for r in results]
        else:
            with ProcessPoolExecutor(max_workers=min(workers,cfg["chains"])) as pool:results=list(pool.map(_extend_worker,[(target,r,block,None) for r in results]))
    return results,diagnostics,convergence_pass(diagnostics,cfg)


def save_raw_baseline(results):
    return save_posterior_artifact(OUT/"baseline_posterior_draws.npz",results,specification="PRIOR_BASELINE_WEAK",rho_n=.80,battery_sd=.25,seed=20260915,force=True)


def spec_outputs(results,diagnostics,bounds,cfg):
    theta=np.stack([r["theta"] for r in results]);components=np.stack([r["components"] for r in results]);summary=posterior_summary(theta,diagnostics,bounds,cfg["boundary_fraction"])
    return theta,components,summary,spectral_radius_summary(components,cfg["near_instability_radius"]),acceptance_summary(results)


def sampler_validation(cfg,workers):
    mean=np.array([.3,-.2,.5,0.,.8]);cov=np.diag([.5,.8,.3,.6,.4]);starts=[mean+np.array([i*.2,-i*.1,0,0,0]) for i in range(4)]
    gresults,_gdiag,_=run_chains(GaussianTarget(mean,cov),starts,cfg,workers,warmup=1000,production=3000,label="analytic_gaussian",extend_to_gate=False)
    g=np.stack([r["z"] for r in gresults]);mean_error=float(np.max(np.abs(g.reshape(-1,5).mean(0)-mean)));cov_error=float(np.max(np.abs(np.cov(g.reshape(-1,5),rowvar=False)-cov)))
    bresults,_bdiag,_=run_chains(BetaZTarget(),[np.array([-2.]),np.array([0.]),np.array([1.]),np.array([2.])],cfg,workers,warmup=800,production=3000,label="beta_jacobian",extend_to_gate=False)
    btheta=1/(1+np.exp(-np.stack([r["z"] for r in bresults]).ravel()));beta_mean=float(btheta.mean())
    nresults,_ndiag,_=run_chains(BetaZTarget(jacobian=False),[np.array([-2.]),np.array([0.]),np.array([1.]),np.array([2.])],cfg,workers,warmup=500,production=1500,label="beta_no_jacobian_negative_control",extend_to_gate=False)
    ntheta=1/(1+np.exp(-np.stack([r["z"] for r in nresults]).ravel()));negative_mean=float(ntheta.mean())
    rows=[{"test":"5D_GAUSSIAN","mean_max_error":mean_error,"cov_max_error":cov_error,"status":"PASS" if mean_error<.08 and cov_error<.12 else "FAIL"},
          {"test":"BETA_2_3_WITH_JACOBIAN","sample_mean":beta_mean,"target_mean":.4,"status":"PASS" if abs(beta_mean-.4)<.03 else "FAIL"},
          {"test":"JACOBIAN_NEGATIVE_CONTROL","sample_mean":negative_mean,"distance_from_target":abs(negative_mean-.4),"status":"PASS" if abs(negative_mean-.4)>.04 else "FAIL"}]
    pd.DataFrame(rows).to_csv(OUT/"sampler_validation.csv",index=False);return all(r["status"]=="PASS" for r in rows)


def structural_synthetic_validation(transform,prior,bounds,cfg,workers):
    a=json.loads((ROOT/"configs/phase2a.yaml").read_text());truth={**baseline_parameters(),**a["baseline"]};model=from_phase2a_parameters("M0_CORE5",truth,cfg["battery_sd_fixed"]);_,y,_=simulate_observations(model,cfg["synthetic_T"],cfg["synthetic_burn"],cfg["seed"])
    truth_z=transform.theta_to_unconstrained(truth);starts=[truth_z]
    for i in range(1,4):starts.append(truth_z+.15*np.sin(i*(np.arange(len(truth_z))+1)))
    target=PosteriorTarget(transform,y,prior,cfg["rho_n_fixed"],cfg["battery_sd_fixed"],cfg["numerical_guard_abs_z"])
    preconditioner=proposal_preconditioner(target,truth_z)
    results,diag,_=run_chains(target,starts,cfg,workers,cfg["synthetic_warmup_draws"],cfg["synthetic_production_draws"],"structural_synthetic",extend_to_gate=False,initial_chol=preconditioner)
    theta=np.stack([r["theta"] for r in results]);median=np.median(theta.reshape(-1,14),axis=0);error=np.sqrt(np.mean([((median[i]-truth[n])/(bounds[n][1]-bounds[n][0]))**2 for i,n in enumerate(PARAMETER_ORDER)]))
    status="PASS" if np.isfinite(theta).all() and max(r["rhat"] for r in diag)<1.15 and error<.30 and all((r["components"][:,4]<1).all() for r in results) else "FAIL"
    row={"T":cfg["synthetic_T"],"chains":4,"warmup":cfg["synthetic_warmup_draws"],"production":cfg["synthetic_production_draws"],"max_rhat":max(r["rhat"] for r in diag),"normalized_median_rmse":error,"status":status}
    pd.DataFrame([row]).to_csv(OUT/"structural_synthetic_posterior.csv",index=False);pd.DataFrame(diag).to_csv(OUT/"structural_synthetic_diagnostics.csv",index=False);pd.DataFrame(acceptance_summary(results)).to_csv(OUT/"structural_synthetic_acceptance.csv",index=False);return status=="PASS"


def prior_audits(specs,bounds,cfg):
    rows=[];stable_draws={}
    for i,(name,spec) in enumerate(specs.items()):
        draws,mask,radii=effective_prior_audit(spec,bounds,cfg["prior_audit_candidates"],cfg["seed"]+100*i,cfg["rho_n_fixed"]);stable=draws[mask];stable_draws[name]=stable
        rows.append({"prior":name,"record":"overall","candidates":len(draws),"stable":len(stable),"stable_share":float(mask.mean()),"spectral_radius_median":float(np.median(radii[mask])),"spectral_radius_q95":float(np.quantile(radii[mask],.95))})
        for j,p in enumerate(PARAMETER_ORDER):rows.append({"prior":name,"record":p,"mean":float(stable[:,j].mean()),"sd":float(stable[:,j].std(ddof=1)),"median":float(np.median(stable[:,j]))})
    pd.DataFrame(rows).to_csv(OUT/"prior_audit.csv",index=False);return stable_draws


def predictive_audit(draws,cfg,label,observed=None):
    rows=[];cor=[]
    for i,row in enumerate(draws):
        theta=theta_from_array(row);theta["rho_n"]=cfg["rho_n_fixed"];model=from_phase2a_parameters("M0_CORE5",theta,cfg["battery_sd_fixed"]);_,y,_=simulate_observations(model,57,50,cfg["seed"]+3000+i);mom,c=observable_moments(y);rows.extend({"draw":i,**x} for x in mom);cor.append(c)
    frame=pd.DataFrame(rows);summary_rows=[]
    for channel,group in frame.groupby("channel"):
        summary_rows.append({"sample":label,"channel":channel,"variance_median":group.variance.median(),"variance_q05":group.variance.quantile(.05),"variance_q95":group.variance.quantile(.95),
                             "lag1_autocorrelation_median":group.lag1_autocorrelation.median(),"lag1_autocorrelation_q05":group.lag1_autocorrelation.quantile(.05),"lag1_autocorrelation_q95":group.lag1_autocorrelation.quantile(.95)})
    summary=pd.DataFrame(summary_rows)
    output=[summary,pd.DataFrame([{"sample":label,"channel":"correlations",**pd.DataFrame(cor).median().to_dict()}])]
    if observed is not None:
        observed_moments,observed_correlations=observable_moments(observed);output.append(pd.DataFrame([{"sample":"observed","channel":x["channel"],"variance_median":x["variance"],"lag1_autocorrelation_median":x["lag1_autocorrelation"]} for x in observed_moments]));output.append(pd.DataFrame([{"sample":"observed","channel":"correlations",**observed_correlations}]))
    pd.concat(output,ignore_index=True,sort=False).to_csv(OUT/("prior_predictive_summary.csv" if label=="prior" else "posterior_predictive_summary.csv"),index=False)


def replay_fixed_correlations(transform,y,mle,map_theta,baseline_prior,bounds,cfg,workers):
    """Reproduce only fixed-assumption chains when the correlation audit needs rebuilding."""
    raw=np.load(OUT/"baseline_posterior_draws.npz");base_theta=raw["theta"];base_corr,_=posterior_correlation(base_theta,PARAMETER_ORDER,cfg["posterior_correlation_flag"])
    starts=initial_points(transform,mle,map_theta,baseline_prior,bounds,cfg);weak_pairs=(("b_n","b_q"),("b_n","rho_p"),("b_q","rho_p"));rows=[]
    for item in cfg["fixed_sensitivity"]:
        target=PosteriorTarget(transform,y,baseline_prior,item["rho_n"],item["battery_sd"],cfg["numerical_guard_abs_z"]);results,_,passed=run_chains(target,starts,cfg,workers,label=f"{item['name']}_CORRELATION_REPLAY",initial_chol=proposal_preconditioner(target,starts[0]))
        if not passed:raise RuntimeError(f"fixed correlation replay failed convergence: {item['name']}")
        corr,_=posterior_correlation(np.stack([r["theta"] for r in results]),PARAMETER_ORDER,cfg["posterior_correlation_flag"])
        for left,right in weak_pairs:
            i,j=PARAMETER_ORDER.index(left),PARAMETER_ORDER.index(right);rows.append({"specification":item["name"],"parameter_1":left,"parameter_2":right,"baseline_correlation":base_corr[i,j],"sensitivity_correlation":corr[i,j],"correlation_change":corr[i,j]-base_corr[i,j]})
        pd.DataFrame(rows).to_csv(OUT/"fixed_assumption_correlation_change.csv",index=False)
    pd.DataFrame(rows).to_csv(OUT/"fixed_assumption_correlation_change.csv",index=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--workers",type=int,default=4);parser.add_argument("--skip-fine-profiles",action="store_true");parser.add_argument("--skip-sampler-validations",action="store_true");parser.add_argument("--fixed-correlation-replay",action="store_true");args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    a=json.loads((ROOT/"configs/phase2a.yaml").read_text());cfg=json.loads((ROOT/"configs/phase2d.yaml").read_text());bounds=load_phase2a_bounds(ROOT/"configs/phase2a.yaml");transform=ParameterTransform.full(bounds);specs=prior_specs(cfg)
    before=hashlib.sha256(FREEZE.read_bytes()).hexdigest();
    if before.lower()!=a["data_freeze_sha256"].lower():raise RuntimeError("Data Freeze mismatch")
    frame=load_frozen_panel(PANEL,a["sample_end"]);measure=build_measurements(frame,cfg["measurement"]);y=measure[["spot","ore_cost","output","battery"]].to_numpy()
    if len(y)!=57 or measure.month.iloc[0]!="2021-01" or measure.month.iloc[-1]!="2025-09":raise RuntimeError("sample mismatch")
    mle,map_theta=load_phase2c_modes()
    if args.fixed_correlation_replay:
        replay_fixed_correlations(transform,y,mle["theta"],map_theta,specs[cfg["baseline_prior"]],bounds,cfg,args.workers);print("fixed-assumption correlation audit complete",flush=True);return
    if not args.skip_fine_profiles:run_fine_profiles(transform,y,mle,cfg,args.workers);print("fine profiles complete",flush=True)
    else:print("using completed fine-profile checkpoints",flush=True)
    stable_prior=prior_audits(specs,bounds,cfg);predictive_audit(stable_prior[cfg["baseline_prior"]][:cfg["prior_predictive_stable_draws"]],cfg,"prior")
    if not args.skip_sampler_validations:
        if not sampler_validation(cfg,args.workers):raise SystemExit("sampler analytic validation failed")
    elif not (OUT/"sampler_validation.csv").exists():raise RuntimeError("sampler validation checkpoint missing")
    baseline_prior=specs[cfg["baseline_prior"]]
    if not args.skip_sampler_validations:
        if not structural_synthetic_validation(transform,baseline_prior,bounds,cfg,args.workers):raise SystemExit("structural synthetic posterior validation failed")
    else:
        checkpoint=pd.read_csv(OUT/"structural_synthetic_posterior.csv").iloc[0]
        if checkpoint.status!="PASS":raise RuntimeError("structural synthetic checkpoint is not PASS")
        print("using completed sampler-validation checkpoints",flush=True)
    starts=initial_points(transform,mle["theta"],map_theta,baseline_prior,bounds,cfg);target=PosteriorTarget(transform,y,baseline_prior,cfg["rho_n_fixed"],cfg["battery_sd_fixed"],cfg["numerical_guard_abs_z"])
    real_preconditioner=proposal_preconditioner(target,starts[0])
    base_results,base_diag,base_pass=run_chains(target,starts,cfg,args.workers,label="baseline",initial_chol=real_preconditioner);theta,components,base_summary,radius,accept=spec_outputs(base_results,base_diag,bounds,cfg)
    save_raw_baseline(base_results);pd.DataFrame(base_diag).to_csv(OUT/"rhat_ess_diagnostics.csv",index=False);pd.DataFrame(base_diag)[["parameter","rhat"]].to_csv(OUT/"rhat_diagnostics.csv",index=False);pd.DataFrame(base_diag)[["parameter","bulk_ess","tail_ess"]].to_csv(OUT/"ess_diagnostics.csv",index=False);pd.DataFrame(accept).to_csv(OUT/"mcmc_acceptance_summary.csv",index=False);pd.DataFrame(base_summary).to_csv(OUT/"baseline_posterior_summary.csv",index=False)
    pd.DataFrame([{"chains":4,"warmup":cfg["warmup_draws"],"production_per_chain":theta.shape[1],"extensions":max(0,(theta.shape[1]-cfg["initial_production_draws"])//cfg["extension_block_draws"]),"convergence_pass":base_pass,**radius}]).to_csv(OUT/"baseline_chain_summary.csv",index=False)
    if not base_pass:
        pd.DataFrame([{"gate":"BASELINE_POSTERIOR","status":"FAIL"},{"gate":"PHASE_2D_READY","status":"NO","reason":"MCMC_MIXING_FAILURE"}]).to_csv(OUT/"phase2d_gate_summary.csv",index=False);raise SystemExit("baseline convergence gate failed")
    corr,pairs=posterior_correlation(theta,PARAMETER_ORDER,cfg["posterior_correlation_flag"]);pd.DataFrame(corr,index=PARAMETER_ORDER,columns=PARAMETER_ORDER).to_csv(OUT/"posterior_correlation.csv");weak=covariance_weak_directions(theta);pd.DataFrame(weak).to_csv(OUT/"posterior_weak_directions.csv",index=False)
    contraction=prior_posterior_contraction(stable_prior[cfg["baseline_prior"]],base_summary);pd.DataFrame(contraction).to_csv(OUT/"prior_posterior_contraction.csv",index=False)
    sens_rows=[];sens_convergence=[]
    for label in ("PRIOR_FLAT_BOUNDED","PRIOR_MODERATE_SHRINK"):
        pt=PosteriorTarget(transform,y,specs[label],cfg["rho_n_fixed"],cfg["battery_sd_fixed"],cfg["numerical_guard_abs_z"]);res,diag,passed=run_chains(pt,starts,cfg,args.workers,label=label,initial_chol=proposal_preconditioner(pt,starts[0]));_,_,summary,sradius,_=spec_outputs(res,diag,bounds,cfg);sens_rows.extend(sensitivity_shift(base_summary,summary,label));sens_convergence.append({"specification":label,"converged":passed,"max_rhat":max(r["rhat"] for r in diag),"min_bulk_ess":min(r["bulk_ess"] for r in diag),"min_tail_ess":min(r["tail_ess"] for r in diag),**sradius})
        save_posterior_artifact(OUT/(label.lower()+"_posterior_draws.npz"),res,specification=label,rho_n=cfg["rho_n_fixed"],battery_sd=cfg["battery_sd_fixed"],seed=cfg["seed"],force=True)
    pd.DataFrame(sens_rows).to_csv(OUT/"prior_sensitivity_summary.csv",index=False)
    fixed_rows=[];fixed_convergence=[];fixed_correlation_rows=[];weak_pairs=(("b_n","b_q"),("b_n","rho_p"),("b_q","rho_p"))
    for item in cfg["fixed_sensitivity"]:
        ft=PosteriorTarget(transform,y,baseline_prior,item["rho_n"],item["battery_sd"],cfg["numerical_guard_abs_z"]);res,diag,passed=run_chains(ft,starts,cfg,args.workers,label=item["name"],initial_chol=proposal_preconditioner(ft,starts[0]));ftheta,_,summary,sradius,_=spec_outputs(res,diag,bounds,cfg);fixed_rows.extend({**r,"rho_n":item["rho_n"],"battery_sd":item["battery_sd"]} for r in sensitivity_shift(base_summary,summary,item["name"]));fixed_convergence.append({"specification":item["name"],"converged":passed,"max_rhat":max(r["rhat"] for r in diag),"min_bulk_ess":min(r["bulk_ess"] for r in diag),"min_tail_ess":min(r["tail_ess"] for r in diag),**sradius})
        save_posterior_artifact(OUT/(item["name"].lower()+"_posterior_draws.npz"),res,specification=item["name"],rho_n=item["rho_n"],battery_sd=item["battery_sd"],seed=cfg["seed"],force=True)
        fcorr,_=posterior_correlation(ftheta,PARAMETER_ORDER,cfg["posterior_correlation_flag"])
        for left,right in weak_pairs:
            i,j=PARAMETER_ORDER.index(left),PARAMETER_ORDER.index(right);fixed_correlation_rows.append({"specification":item["name"],"parameter_1":left,"parameter_2":right,"baseline_correlation":corr[i,j],"sensitivity_correlation":fcorr[i,j],"correlation_change":fcorr[i,j]-corr[i,j]})
    pd.DataFrame(fixed_rows).to_csv(OUT/"fixed_assumption_sensitivity.csv",index=False);pd.DataFrame(fixed_correlation_rows).to_csv(OUT/"fixed_assumption_correlation_change.csv",index=False);pd.DataFrame(sens_convergence+fixed_convergence).to_csv(OUT/"sensitivity_convergence.csv",index=False)
    rng=np.random.default_rng(cfg["seed"]+5000);pooled=theta.reshape(-1,14);chosen=pooled[rng.choice(len(pooled),cfg["posterior_predictive_draws"],replace=False)];predictive_audit(chosen,cfg,"posterior",y)
    identity=identification_classifications(base_summary,contraction,sens_rows,cfg["prior_sensitivity_shift_low"],cfg["prior_sensitivity_shift_high"],stable_prior[cfg["baseline_prior"]],fixed_rows);pd.DataFrame(identity).to_csv(OUT/"posterior_identification.csv",index=False)
    prior_pass=all(x["converged"] for x in sens_convergence);fixed_pass=all(x["converged"] for x in fixed_convergence);max_core=max(abs(r["standardized_posterior_shift"]) for r in sens_rows if r["parameter"] in ("b_c","b_d","rho_d","rho_c","rho_q","sigma_c","sigma_p"));prior_dominated=max_core>1
    fixed_high=sum(abs(r["standardized_posterior_shift"])>1 for r in fixed_rows if r["specification"]=="BATTERY_SD_050" and r["parameter"] in ("b_c","b_d","rho_d","rho_c","rho_q","sigma_c","sigma_p"))>=2
    ready=prior_pass and fixed_pass and not prior_dominated and not fixed_high
    gates=[{"gate":"SAMPLER_VALIDATION","status":"PASS"},{"gate":"STRUCTURAL_SYNTHETIC","status":"PASS"},{"gate":"BASELINE_POSTERIOR","status":"PASS"},{"gate":"PRIOR_SENSITIVITY","status":"PASS" if prior_pass and not prior_dominated else "FAIL"},{"gate":"FIXED_ASSUMPTIONS","status":"PASS_WITH_WARNING" if fixed_pass and not fixed_high else "FAIL"},{"gate":"PHASE_2D_READY","status":"YES" if ready else "NO"}]
    pd.DataFrame(gates).to_csv(OUT/"phase2d_gate_summary.csv",index=False)
    if hashlib.sha256(FREEZE.read_bytes()).hexdigest()!=before:raise RuntimeError("Data Freeze changed")
    print(json.dumps({"ready":ready,"draws_per_chain":theta.shape[1],"max_rhat":max(r["rhat"] for r in base_diag),"min_bulk":min(r["bulk_ess"] for r in base_diag),"min_tail":min(r["tail_ess"] for r in base_diag),"max_mcse_sd":max(r["mcse_sd"] for r in base_diag),"prior_dominated":prior_dominated,"fixed_high":fixed_high},indent=2),flush=True)


if __name__=="__main__":main()
