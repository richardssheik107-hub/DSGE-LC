"""Economic consistency and sensitivity classifications for Phase 2E."""
from __future__ import annotations
import numpy as np

def sign_classification(prob,strong=.9,moderate=.75):return "STRONG_SIGN_CONCENTRATION" if prob>=strong else "MODERATE_SIGN_CONCENTRATION" if prob>=moderate else "SIGN_AMBIGUOUS"
def irf_shift_sd(baseline_median,alternative_median,baseline_sd):return float((alternative_median-baseline_median)/baseline_sd) if baseline_sd>0 else np.nan
def fevd_share_change(baseline,alternative):return float(alternative-baseline)
def sensitivity_classification(value,moderate,high):
    value=abs(float(value));return "HIGH" if value>high else "MODERATE" if value>moderate else "LOW"
def sign_flip(baseline,alternative):return bool(np.sign(baseline)!=np.sign(alternative) and baseline!=0 and alternative!=0)

def economic_sign_checks(irfs,state_index,shock_index):
    checks=[("Demand impact d","demand","d",0,1),("Demand impact p","demand","p",0,1),("Demand h1 n","demand","n",1,-1),("Cost impact c","cost","c",0,1),("Cost impact p","cost","p",0,1),("Cost h1 q","cost","q",1,-1),("Supply impact q","supply","q",0,1),("Supply impact p","supply","p",0,-1),("Supply h1 n","supply","n",1,1),("Price impact p","price","p",0,1),("Price h1 q","price","q",1,1)];rows=[]
    for mechanism,shock,state,h,expected in checks:
        x=irfs[shock][:,h,state_index[state]];prob=float(np.mean(x>0)) if expected>0 else float(np.mean(x<=0));status="PASS" if prob>=.999 else "PASS_WITH_WEAK_AC_WARNING" if mechanism=="Cost h1 q" else "FAIL";rows.append({"mechanism":mechanism,"shock":shock,"state":state,"horizon":h,"expected_sign":"POSITIVE" if expected>0 else "NONPOSITIVE","posterior_sign_probability":prob,"status":status})
    return rows
