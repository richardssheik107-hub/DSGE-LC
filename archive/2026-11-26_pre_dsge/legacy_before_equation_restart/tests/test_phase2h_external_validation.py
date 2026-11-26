from pathlib import Path
import numpy as np
import pandas as pd
from src.structural.external_validation import rowwise_pearson,rowwise_spearman,correlation_summary,validation_strength
ROOT=Path(__file__).resolve().parents[1]

def test_rowwise_correlations_known_signs():
    x=np.array([[1.,2.,3.,4.],[4.,3.,2.,1.]])
    y=np.array([2.,4.,6.,8.])
    assert np.allclose(rowwise_pearson(x,y),[1.,-1.])
    assert np.allclose(rowwise_spearman(x,y),[1.,-1.])

def test_correlation_summary_and_classification():
    s=correlation_summary(np.array([.2,.3,.4,.5,.6]))
    assert 0<s["q05"]<s["median"]<s["q95"]
    assert s["p_positive"]==1.0
    assert validation_strength(s)=="STRONG_POSITIVE"

def test_validation_series_cover_frozen_overlap():
    inv=pd.read_csv(ROOT/"data/processed/industry/lc_inventory_monthly.csv")
    inv=inv[(inv.month>="2023-06")&(inv.month<="2025-09")]
    assert len(inv)==28 and inv.lc_inventory_total_mean.notna().all() and inv.lc_inventory_total_eom.notna().all()
    cost=pd.read_csv(ROOT/"data/processed/industry/lc_cost_margin_monthly.csv")
    cost["dlog"]=np.log(cost.lc_cost_spodumene).diff();cost=cost[(cost.month>="2022-11")&(cost.month<="2025-09")]
    assert len(cost)==35 and cost.dlog.notna().all()

def test_freeze_validation_sources_are_not_core_splices():
    core=pd.read_csv(ROOT/"data/processed/core_monthly_panel.csv")
    assert "lc_inventory_total_mean" not in core.columns
    assert "lc_cost_spodumene" not in core.columns
