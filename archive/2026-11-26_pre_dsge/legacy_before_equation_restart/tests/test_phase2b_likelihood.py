"""Phase 2B acceptance tests 34-43 and 55-60: likelihood validation."""
from __future__ import annotations
import inspect,json,sys,unittest
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.kalman import kalman_filter
from src.structural.kalman_diagnostics import innovation_summary,simulate_observations
from src.structural.likelihood import evaluate_m0_likelihood,gaussian_loglikelihood
from src.structural.spec import baseline_parameters
from src.structural.state_space import StateSpaceModel,from_phase2a_parameters,stationary_initialization
A=json.loads((ROOT/"configs/phase2a.yaml").read_text());P={**baseline_parameters(),**A["baseline"]};M=from_phase2a_parameters("M0_CORE5",P,.25);TRUTH,Y,_=simulate_observations(M,200,50,20260915);F=kalman_filter(M,Y)

class Phase2BLikelihoodTests(unittest.TestCase):
 def test_34_manual_one_step(self):
  y=Y[:1];_,Q,_=stationary_initialization(M);e=y[0]-M.H@np.zeros(5);S=M.H@Q@M.H.T+M.R;sign,ld=np.linalg.slogdet(S);expected=-.5*(4*np.log(2*np.pi)+ld+e@np.linalg.solve(S,e));self.assertAlmostEqual(kalman_filter(M,y).loglik,expected,places=10)
 def test_35_scalar_ar_reference(self):
  model=StateSpaceModel("AR1",np.array([[.5]]),np.array([[.3]]),np.array([[.09]]),np.zeros((1,0)),np.array([[1.]]),np.array([[.04]]),("x",),("y",),("e",),{});y=np.array([[.7]]);S=.09/(1-.25)+.04;expected=-.5*(np.log(2*np.pi)+np.log(S)+.7**2/S);self.assertAlmostEqual(kalman_filter(model,y).loglik,expected)
 def test_36_stable_logdet_path(self):
  code=inspect.getsource(sys.modules["src.structural.kalman"]);self.assertIn("cho_factor",code);self.assertNotIn("np.linalg.det",code)
 def test_37_sum_contributions(self):self.assertAlmostEqual(F.loglik,F.loglik_by_t.sum())
 def test_38_all_missing_contribution(self):
  y=Y.copy();y[4]=np.nan;self.assertEqual(kalman_filter(M,y).loglik_by_t[4],0)
 def test_39_partial_reduced_dimension(self):
  y=Y[:1].copy();y[0,3]=np.nan;r=kalman_filter(M,y);Q=stationary_initialization(M)[1];H=M.H[:3];e=y[0,:3]-H@np.zeros(5);S=H@Q@H.T;expected=-.5*(3*np.log(2*np.pi)+np.linalg.slogdet(S)[1]+e@np.linalg.solve(S,e));self.assertAlmostEqual(r.loglik,expected)
 def test_40_unstable_minus_inf(self):
  p=dict(P);p.update({"a_p":1.5,"b_q":1.5,"b_n":1.5});r=evaluate_m0_likelihood(p,.25,Y);self.assertEqual((r.status,r.loglik),("UNSTABLE_PARAMETERS",float("-inf")))
 def test_41_invalid_sigma(self):
  p=dict(P);p["sigma_p"]=0;r=evaluate_m0_likelihood(p,.25,Y);self.assertEqual((r.status,r.loglik),("INVALID_PARAMETERS",float("-inf")))
 def test_42_small_perturbation_finite(self):
  p=dict(P);p["rho_p"]+=1e-5;self.assertTrue(np.isfinite(evaluate_m0_likelihood(p,.25,Y).loglik))
 def test_43_deterministic(self):self.assertEqual(evaluate_m0_likelihood(P,.25,Y).loglik,evaluate_m0_likelihood(P,.25,Y).loglik)
 def test_55_truth_finite(self):self.assertTrue(np.isfinite(F.loglik))
 def test_56_gross_wrong_finite(self):
  p=dict(P);p["b_c"]*=.5;self.assertTrue(np.isfinite(evaluate_m0_likelihood(p,.25,Y).loglik))
 def test_57_truth_beats_majority(self):
  table=pd.read_csv(ROOT/"outputs/phase2/phase2b/synthetic_likelihood_profiles.csv");gross=table[table.profile.eq("gross_perturbation")];self.assertGreater((gross.loglik<F.loglik).mean(),.5)
 def test_58_profiles_finite(self):self.assertTrue(np.isfinite(pd.read_csv(ROOT/"outputs/phase2/phase2b/synthetic_likelihood_profiles.csv").loglik).all())
 def test_59_profile_continuity(self):
  table=pd.read_csv(ROOT/"outputs/phase2/phase2b/synthetic_likelihood_profiles.csv");profile=table[(table.profile=="one_dimensional")&(table.parameter=="rho_d")].sort_values("parameter_value");self.assertLess(np.abs(np.diff(profile.loglik)).max(),1e6)
 def test_60_whitened_finite(self):self.assertTrue(np.isfinite(F.standardized_innovations).all())
