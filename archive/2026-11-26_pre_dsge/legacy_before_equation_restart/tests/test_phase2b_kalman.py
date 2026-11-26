"""Phase 2B acceptance tests 21-33 and 44-54: filter, smoother, missingness."""
from __future__ import annotations
import json,inspect,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.kalman import kalman_filter,rts_smoother
from src.structural.kalman_diagnostics import simulate_observations,state_rmse
from src.structural.spec import baseline_parameters
from src.structural.state_space import from_phase2a_parameters
A=json.loads((ROOT/"configs/phase2a.yaml").read_text());P={**baseline_parameters(),**A["baseline"]};M=from_phase2a_parameters("M0_CORE5",P,.25)
TRUTH,Y,_=simulate_observations(M,160,40,20260915);F=kalman_filter(M,Y);S=rts_smoother(M,F)

class Phase2BKalmanTests(unittest.TestCase):
 def test_21_filter_dimensions(self):self.assertEqual((F.filtered_mean.shape,F.filtered_cov.shape),((160,5),(160,5,5)))
 def test_22_baseline_arrays_finite(self):
  for x in (F.predicted_mean,F.predicted_cov,F.filtered_mean,F.filtered_cov,F.innovations,F.innovation_cov,F.standardized_innovations,F.kalman_gain,F.loglik_by_t):self.assertTrue(np.isfinite(x).all())
 def test_23_no_explicit_inverse(self):self.assertNotIn("np.linalg.inv",inspect.getsource(sys.modules["src.structural.kalman"]))
 def test_24_innovation_formula(self):self.assertTrue(np.allclose(F.innovations[0],Y[0]-M.H@F.predicted_mean[0]))
 def test_25_gain_dimensions(self):self.assertEqual(F.kalman_gain.shape,(160,5,4))
 def test_26_joseph_symmetric(self):self.assertLess(max(np.abs(x-x.T).max() for x in F.filtered_cov),1e-10)
 def test_27_filtered_psd(self):self.assertGreaterEqual(min(np.linalg.eigvalsh(x).min() for x in F.filtered_cov),-1e-9)
 def test_28_prediction_psd(self):self.assertGreaterEqual(min(np.linalg.eigvalsh(x).min() for x in F.predicted_cov),-1e-9)
 def test_29_innovation_pd(self):self.assertGreater(min(np.linalg.eigvalsh(x).min() for x in F.innovation_cov),0)
 def test_30_exact_p(self):self.assertTrue(np.allclose(F.filtered_mean[:,4],Y[:,0],atol=1e-10))
 def test_31_exact_c(self):self.assertTrue(np.allclose(F.filtered_mean[:,1],Y[:,1],atol=1e-10))
 def test_32_exact_q(self):self.assertTrue(np.allclose(F.filtered_mean[:,2],Y[:,2],atol=1e-10))
 def test_33_battery_not_forced(self):self.assertGreater(np.max(np.abs(F.filtered_mean[:,0]-Y[:,3])),1e-4)
 def test_44_last_smooth_mean(self):self.assertTrue(np.array_equal(S.smoothed_mean[-1],F.filtered_mean[-1]))
 def test_45_last_smooth_cov(self):self.assertTrue(np.array_equal(S.smoothed_cov[-1],F.filtered_cov[-1]))
 def test_46_smooth_symmetric(self):self.assertLess(max(np.abs(x-x.T).max() for x in S.smoothed_cov),1e-10)
 def test_47_smooth_psd(self):self.assertGreaterEqual(min(np.linalg.eigvalsh(x).min() for x in S.smoothed_cov),-1e-9)
 def test_48_smooth_latent_rmse(self):
  fr=np.sqrt(np.mean((TRUTH[:,[0,3]]-F.filtered_mean[:,[0,3]])**2));sr=np.sqrt(np.mean((TRUTH[:,[0,3]]-S.smoothed_mean[:,[0,3]])**2));self.assertLessEqual(sr,fr+1e-10)
 def _missing(self,col=None,index=20,all_missing=False):
  y=Y.copy();y[index,:]=np.nan if all_missing else y[index,:]
  if col is not None:y[::10,col]=np.nan
  return y,kalman_filter(M,y)
 def test_49_battery_missing(self):self.assertEqual(self._missing(3)[1].status,"OK")
 def test_50_output_missing(self):self.assertEqual(self._missing(2)[1].status,"OK")
 def test_51_only_spot(self):
  y=Y.copy();y[20,1:]=np.nan;r=kalman_filter(M,y);self.assertEqual((r.status,r.observed_mask[20].sum()),("OK",1))
 def test_52_all_missing(self):
  y,r=self._missing(index=20,all_missing=True);self.assertEqual(r.loglik_by_t[20],0);self.assertTrue(np.allclose(r.filtered_mean[20],r.predicted_mean[20]))
 def test_53_missing_not_zero(self):
  y,r=self._missing(3);self.assertTrue(np.isnan(r.innovations[0,3]));self.assertFalse(r.innovations[0,3]==0)
 def test_54_month_count(self):self.assertEqual(len(self._missing(3)[1].loglik_by_t),len(Y))
