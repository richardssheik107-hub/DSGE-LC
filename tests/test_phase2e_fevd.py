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
 def test_29_share_range(self):self.assertTrue(np.all((S>=0)&(S<=1)))
 def test_30_positive_totals_sum_one(self):
  total=K.sum(2);self.assertTrue(np.allclose(S.sum(2)[total>0],1))
 def test_31_h1_impact_only(self):self.assertTrue(np.allclose(K[0],B**2))
 def test_32_h3_exact(self):self.assertTrue(np.allclose(K[1],B**2+(A@B)**2+(A@A@B)**2))
 def test_33_column_formula(self):self.assertAlmostEqual(K[0,4,0],B[4,0]**2)
 def test_34_covariance_identity(self):self.assertLess(forecast_variance_identity_check(A,B,24),1e-10)
 def test_35_no_cholesky(self):self.assertNotIn("cholesky",(ROOT/"src/structural/fevd.py").read_text().lower())
 def test_36_no_double_scale(self):self.assertAlmostEqual(K[0,0,0],P["sigma_d"]**2)
 def test_37_summary_quantiles(self):
  r=posterior_fevd_summary(np.stack([S,S]),(1,3,6,12,24),("d","c","q","n","p"),("demand","cost","supply","price"));self.assertTrue(all(x["q05"]<=x["median"]<=x["q95"] for x in r))
 def test_38_summary_range(self):self.assertTrue(all(0<=x["median"]<=1 for x in posterior_fevd_summary(np.stack([S,S]),(1,3,6,12,24),("d","c","q","n","p"),("demand","cost","supply","price"))))
 def test_39_price_denominator_positive(self):self.assertTrue(np.all(K[:,4].sum(1)>0))
 def test_40_four_structural_shocks(self):self.assertEqual(S.shape[-1],4)
