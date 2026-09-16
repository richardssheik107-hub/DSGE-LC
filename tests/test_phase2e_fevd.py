"""Phase 2E FEVD tests 27-40."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.fevd import *
from src.structural.matrices import system_matrices
from src.structural.spec import baseline_parameters
C=json.loads((ROOT/"configs/phase2a.yaml").read_text());P={**baseline_parameters(),**C["baseline"]};A,B,_,_=system_matrices("M0_CORE5",P);S,K=structural_fevd(A,B,(1,3,6,12,24))
class Phase2EFEVDTests(unittest.TestCase):
 def test_27_dimension(self):self.assertEqual(S.shape,(5,5,4))
 def test_28_nonnegative(self):self.assertTrue(np.all(K>=0))
 def test_29_share_range(self):
  defined=np.isfinite(S)
  self.assertTrue(np.all((S[defined]>=0)&(S[defined]<=1)))
 def test_30_positive_totals_sum_one(self):
  total=K.sum(2);self.assertTrue(np.allclose(np.nansum(S,axis=2)[total>0],1))
 def test_31_h1_impact_only(self):self.assertTrue(np.allclose(K[0],B**2))
 def test_32_h3_exact(self):self.assertTrue(np.allclose(K[1],B**2+(A@B)**2+(A@A@B)**2))
 def test_33_column_formula(self):self.assertAlmostEqual(K[0,4,0],B[4,0]**2)
 def test_34_covariance_identity(self):self.assertLess(forecast_variance_identity_check(A,B,24),1e-10)
 def test_35_no_cholesky(self):self.assertNotIn("cholesky",(ROOT/"src/structural/fevd.py").read_text().lower())
 def test_36_no_double_scale(self):self.assertAlmostEqual(K[0,0,0],P["sigma_d"]**2)
 def test_37_summary_quantiles(self):
  r=posterior_fevd_summary(np.stack([S,S]),(1,3,6,12,24),("d","c","q","n","p"),("demand","cost","supply","price"));self.assertTrue(all(x["q05"]<=x["q16"]<=x["median"]<=x["q84"]<=x["q95"] for x in r if x["status"]=="DEFINED"))
 def test_38_summary_range(self):self.assertTrue(all(0<=x["median"]<=1 for x in posterior_fevd_summary(np.stack([S,S]),(1,3,6,12,24),("d","c","q","n","p"),("demand","cost","supply","price")) if x["status"]=="DEFINED"))
 def test_39_price_denominator_positive(self):self.assertTrue(np.all(K[:,4].sum(1)>0))
 def test_40_four_structural_shocks(self):self.assertEqual(S.shape[-1],4)

 def test_h1_inventory_zero_variance_is_undefined_not_zero(self):
  self.assertTrue(np.array_equal(K[0,3],np.zeros(4)))
  self.assertTrue(np.isnan(S[0,3]).all())
  rows=posterior_fevd_summary(np.stack([S,S]),(1,3,6,12,24),("d","c","q","n","p"),("demand","cost","supply","price"))
  inventory=[row for row in rows if row["state"]=="n" and row["horizon"]==1]
  self.assertEqual(len(inventory),4)
  self.assertTrue(all(row["status"]=="NOT_DEFINED" and row["valid_draws"]==0 and np.isnan(row["mean"]) and np.isnan(row["q16"]) and np.isnan(row["q84"]) for row in inventory))

 def test_h1_price_denominator_and_draw_additivity(self):
  self.assertGreater(K[0,4].sum(),0)
  audit=fevd_additivity_audit(S,K)
  self.assertEqual(audit["status"],"PASS")
  self.assertEqual(audit["zero_forecast_variance_count"],1)
  self.assertLess(audit["max_draw_share_sum_error"],1e-12)
  self.assertLess(audit["max_mean_share_sum_error"],1e-12)

 def test_zero_price_variance_fails_audit(self):
  a=np.eye(5)*.5;b=np.zeros((5,4));b[0,0]=2.
  shares,contrib=structural_fevd(a,b,(1,))
  self.assertEqual(fevd_additivity_audit(shares,contrib)["status"],"FAIL")
  self.assertTrue(np.isnan(shares[0,4]).all())

 def test_mean_of_shares_adds_but_marginal_medians_need_not(self):
  x=np.zeros((3,1,1,4))
  x[0,0,0,0]=1.;x[1,0,0,1]=1.;x[2,0,0,2]=1.
  rows=posterior_fevd_summary(x,(12,),("p",),("demand","cost","supply","price"))
  self.assertAlmostEqual(sum(row["mean"] for row in rows),1.)
  self.assertEqual(sum(row["median"] for row in rows),0.)
  self.assertTrue(all(row["status"]=="DEFINED" for row in rows))

 def test_per_draw_share_uses_b_once_with_no_extra_sigma(self):
  a=np.zeros((5,5));b=np.zeros((5,4));b[0,0]=2.;b[4,0]=3.;b[4,1]=4.
  shares,contrib=structural_fevd(a,b,(1,))
  self.assertAlmostEqual(contrib[0,4,0],9.)
  self.assertAlmostEqual(contrib[0,4,1],16.)
  self.assertAlmostEqual(shares[0,4,0],9./25.)

 def test_corrupt_share_or_zero_share_vector_fails_audit(self):
  corrupt=S.copy();corrupt[0,4,0]+=.1
  self.assertEqual(fevd_additivity_audit(corrupt,K)["status"],"FAIL")
  corrupt=S.copy();corrupt[0,3]=0.
  self.assertEqual(fevd_additivity_audit(corrupt,K)["status"],"FAIL")
