from pathlib import Path
import numpy as np
import pandas as pd
from src.structural.structural_forecasting import build_release_safe_training_measurements, structural_forecast
from src.structural.spec import baseline_parameters
ROOT=Path(__file__).resolve().parents[1]

def test_release_safe_origin_masks_output_and_battery():
    frame=pd.read_csv(ROOT/"data/processed/phase1/monthly_structural_v1.csv")
    origin=int(frame.index[frame.month.eq("2023-12")][0]); y,scaler,months=build_release_safe_training_measurements(frame,origin)
    assert months[-1]=="2023-12" and months[0]=="2021-01"
    assert np.isfinite(y[-1,0]) and np.isfinite(y[-1,1])
    assert np.isnan(y[-1,2]) and np.isnan(y[-1,3])
    assert abs(np.nanmean(y[:,0]))<1e-10

def test_scaling_uses_training_only():
    frame=pd.read_csv(ROOT/"data/processed/phase1/monthly_structural_v1.csv")
    origin=int(frame.index[frame.month.eq("2023-12")][0]); _,a,_=build_release_safe_training_measurements(frame,origin)
    changed=frame.copy(); changed.loc[origin+1:,"lc_spot_dlog"]=9999
    _,b,_=build_release_safe_training_measurements(changed,origin)
    assert a.mean==b.mean and a.sd==b.sd

def test_structural_forecast_finite_baseline():
    frame=pd.read_csv(ROOT/"data/processed/phase1/monthly_structural_v1.csv")
    origin=int(frame.index[frame.month.eq("2023-12")][0]); y,s,_=build_release_safe_training_measurements(frame,origin)
    p=baseline_parameters(); names=("rho_d","rho_c","rho_q","rho_p","a_p","a_c","b_d","b_c","b_q","b_n","sigma_d","sigma_c","sigma_q","sigma_p")
    theta={k:p[k] for k in names}
    _,lp,f=structural_forecast(theta,y,s,float(frame.lc_spot_log.iloc[origin]),[1,3,6],.8,.25)
    assert f.status=="OK" and np.isfinite(lp).all() and len(lp)==6
