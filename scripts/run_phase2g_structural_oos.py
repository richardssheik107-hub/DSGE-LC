"""Run strict expanding-window structural OOS and compare with frozen Phase 1B baselines."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.structural.parameter_transform import ParameterTransform,load_phase2a_bounds,PARAMETER_ORDER
from src.structural.priors import prior_specs,draw_stable_prior,theta_from_array
from src.structural.spec import baseline_parameters
from src.structural.structural_forecasting import build_release_safe_training_measurements,fit_map_multistart,structural_forecast
from src.evaluation.metrics import direction_metrics

OUT=ROOT/"outputs/phase2/phase2g"; FREEZE=ROOT/"data/processed/core_monthly_panel.csv"; DATA=ROOT/"data/processed/phase1/monthly_structural_v1.csv"


def metrics(frame):
    rows=[]
    for model,g in frame.groupby("model",sort=False):
        for h,x in g.groupby("horizon"):
            e=x.forecast_spot.to_numpy()-x.actual_spot.to_numpy(); ce=x.forecast_log_change.to_numpy()-x.actual_log_change.to_numpy()
            rw=frame[(frame.model=="RW_NO_DRIFT")&(frame.horizon==h)]
            re=rw.forecast_spot.to_numpy()-rw.actual_spot.to_numpy(); rrmse=np.sqrt(np.mean(re**2))
            rows.append({"model":model,"horizon":int(h),"n":len(x),"rmse_level":np.sqrt(np.mean(e**2)),
                         "mae_level":np.mean(np.abs(e)),"theil_u2":np.sqrt(np.mean(e**2))/rrmse,
                         "rmse_change":np.sqrt(np.mean(ce**2)),**direction_metrics(x.actual_log_change.to_numpy(),x.forecast_log_change.to_numpy())})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=json.loads((ROOT/"configs/phase2g.yaml").read_text(encoding="utf-8-sig")); p2a=json.loads((ROOT/"configs/phase2a.yaml").read_text()); p2d=json.loads((ROOT/"configs/phase2d.yaml").read_text())
    before=hashlib.sha256(FREEZE.read_bytes()).hexdigest(); assert before.lower()==p2a["data_freeze_sha256"].lower()
    data=pd.read_csv(DATA); assert (len(data),data.month.iloc[0],data.month.iloc[-1])==(69,"2020-01","2025-09")
    bounds=load_phase2a_bounds(ROOT/"configs/phase2a.yaml"); transform=ParameterTransform.full(bounds); prior=prior_specs(p2d)[cfg["prior"]]
    stable,_=draw_stable_prior(prior,bounds,10,cfg["seed"]+700,cfg["rho_n"]); prior_starts=[theta_from_array(x) for x in stable]
    theory={k:v for k,v in baseline_parameters().items() if k in PARAMETER_ORDER}; horizons=cfg["horizons"]
    first=int(data.index[data.month.eq(cfg["first_origin"])][0]); predictions=[]; fits=[]; previous=None
    for origin in range(first,len(data)-1):
        observable=[h for h in horizons if origin+h<len(data)]
        if not observable: continue
        y,scaler,months=build_release_safe_training_measurements(data,origin)
        starts=[theory]
        if previous is not None: starts.insert(0,previous)
        need=(cfg["starts_later_origin"] if previous is not None else cfg["starts_first_origin"])-len(starts)
        starts.extend(prior_starts[:max(0,need)])
        best,allrows=fit_map_multistart(transform,y,bounds,prior,starts,cfg["rho_n"],cfg["battery_sd"],cfg["maxiter"],cfg["ftol"],cfg["z_bound"])
        previous=best["theta"]
        _,logpath,_=structural_forecast(previous,y,scaler,float(data.lc_spot_log.iloc[origin]),observable,cfg["rho_n"],cfg["battery_sd"])
        fits.append({"origin":data.month.iloc[origin],"train_start":months[0],"train_end":months[-1],"n_measurements":len(months),
                     "objective":best["objective"],"spectral_radius":best["spectral_radius"],"successful_starts":sum(r["success"] for r in allrows),
                     "valid_starts":sum(r["objective"]<1e11 for r in allrows),**{f"theta_{k}":v for k,v in previous.items()}})
        for h in observable:
            target=origin+h
            predictions.append({"model":"STRUCTURAL_MAP_M0","forecast_origin":data.month.iloc[origin],"target_month":data.month.iloc[target],"horizon":h,
                                "actual_spot":float(data.lc_spot.iloc[target]),"forecast_spot":float(np.exp(logpath[h-1])),
                                "actual_log_change":float(data.lc_spot_log.iloc[target]-data.lc_spot_log.iloc[origin]),
                                "forecast_log_change":float(logpath[h-1]-data.lc_spot_log.iloc[origin]),"train_end":data.month.iloc[origin],"n_train":len(months),
                                "notes":"STRICT_TEMPORAL_OOS; training-only scaling; release-safe output/battery at origin; native-theta MAP prior"})
    structural=pd.DataFrame(predictions); fits=pd.DataFrame(fits)
    structural.to_csv(OUT/"structural_oos_predictions.csv",index=False); fits.to_csv(OUT/"structural_oos_fit_diagnostics.csv",index=False)
    base=pd.read_csv(ROOT/"outputs/phase1/baseline_results/forecast_predictions.csv")
    base=base[(base.information_set=="RELEASE_SAFE_APPROXIMATION")&(base.window_variant=="PRIMARY_48")&base.model.isin(["RW_NO_DRIFT","AR_BIC","VAR_SPEC_B","BVAR_SPEC_B"])].copy()
    common=base[["model","forecast_origin","target_month","horizon","actual_spot","forecast_spot","actual_log_change","forecast_log_change"]]
    common=pd.concat([common,structural[["model","forecast_origin","target_month","horizon","actual_spot","forecast_spot","actual_log_change","forecast_log_change"]]],ignore_index=True)
    targets=None
    for _,g in common.groupby("model"):
        cell=set(zip(g.target_month,g.horizon)); targets=cell if targets is None else targets & cell
    common=common[[(m,h) in targets for m,h in zip(common.target_month,common.horizon)]].copy()
    common.to_csv(OUT/"structural_vs_baseline_common_predictions.csv",index=False)
    summary=metrics(common); summary.to_csv(OUT/"structural_oos_metrics.csv",index=False)
    summary.pivot(index="horizon",columns="model",values="theil_u2").to_csv(OUT/"structural_oos_u2_table.csv")
    drift=[]
    for p in PARAMETER_ORDER:
        s=fits[f"theta_{p}"]; drift.append({"parameter":p,"min":s.min(),"max":s.max(),"sd":s.std(ddof=1),"first":s.iloc[0],"last":s.iloc[-1]})
    pd.DataFrame(drift).to_csv(OUT/"structural_oos_parameter_path.csv",index=False)
    gate=np.isfinite(structural.forecast_spot).all() and (fits.spectral_radius<1).all() and len(structural)>0
    pd.DataFrame([{"gate":"STRICT_TEMPORAL_OOS","status":"PASS" if gate else "FAIL"},
                  {"gate":"FREEZE_UNCHANGED","status":"PASS" if hashlib.sha256(FREEZE.read_bytes()).hexdigest()==before else "FAIL"},
                  {"gate":"PHASE_2G_READY","status":"YES" if gate else "NO"}]).to_csv(OUT/"phase2g_gate_summary.csv",index=False)
    print(summary.to_string(index=False)); print("origins",len(fits),"forecasts",len(structural),"gate",gate)

if __name__=="__main__": main()
