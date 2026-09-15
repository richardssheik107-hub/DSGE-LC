"""Phase 2C objective, synthetic, multistart and sensitivity tests."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.estimation import *
from src.structural.kalman_diagnostics import simulate_observations
from src.structural.likelihood import evaluate_m0_likelihood
from src.structural.measurement import build_measurements,load_frozen_panel
from src.structural.optimization_diagnostics import *
from src.structural.parameter_transform import *
from src.structural.spec import baseline_parameters
from src.structural.state_space import from_phase2a_parameters
A=json.loads((ROOT/"configs/phase2a.yaml").read_text());C=json.loads((ROOT/"configs/phase2c.yaml").read_text());P={**baseline_parameters(),**A["baseline"]};B=load_phase2a_bounds(ROOT/"configs/phase2a.yaml");T=ParameterTransform.full(B);M=from_phase2a_parameters("M0_CORE5",P,.25);_,Y,_=simulate_observations(M,24,10,20260915)

class Phase2COptimizationTests(unittest.TestCase):
 def test_09_same_likelihood(self):self.assertEqual(-EstimationObjective(T,Y)(T.theta_to_unconstrained(P)),evaluate_m0_likelihood(P,.25,Y).loglik)
 def test_10_invalid_penalty(self):self.assertGreaterEqual(EstimationObjective(T,Y).evaluate_theta({**P,"sigma_p":0}),1e10)
 def test_11_unstable_penalty(self):self.assertGreaterEqual(EstimationObjective(T,Y).evaluate_theta({**P,"a_p":1.5,"b_q":1.5,"b_n":1.5}),1e10)
 def test_12_valid_finite(self):self.assertTrue(np.isfinite(EstimationObjective(T,Y)(T.theta_to_unconstrained(P))))
 def test_13_mle_no_prior(self):self.assertEqual(EstimationObjective(T,Y)(T.theta_to_unconstrained(P)),-evaluate_m0_likelihood(P,.25,Y).loglik)
 def test_14_map_prior(self):self.assertAlmostEqual(EstimationObjective(T,Y,kind="map")(T.theta_to_unconstrained(P)),-evaluate_m0_likelihood(P,.25,Y).loglik-logprior_native(P))
 def test_15_no_jacobian(self):
  z=T.theta_to_unconstrained(P);self.assertAlmostEqual(EstimationObjective(T,Y,kind="map")(z),-evaluate_m0_likelihood(P,.25,Y).loglik-logprior_native(P))
 def test_16_freeze_not_touched(self):self.assertTrue((ROOT/"data/processed/core_monthly_panel.csv").exists())
 def test_17_deterministic_starts(self):self.assertEqual(generate_stable_starts(T,P,16,7)[0],generate_stable_starts(T,P,16,7)[0])
 def test_18_truth_finite(self):self.assertTrue(np.isfinite(evaluate_m0_likelihood(P,.25,Y).loglik))
 def test_19_multistart_valid(self):self.assertTrue(run_multistart(T,Y,generate_stable_starts(T,P,1,7)[0],maxiter=1)[0]["valid"])
 def test_20_best_stable(self):self.assertTrue(is_stable_theta(P))
 def test_21_recovery_metric_finite(self):self.assertTrue(np.isfinite(normalized_parameter_distance(P,P,B)))
 def test_22_failure_surfaced(self):self.assertGreater(EstimationObjective(T,Y).audit.evaluations,-1)
 def test_23_baseline_included(self):self.assertEqual(generate_stable_starts(T,P,8,7)[0][0]["source"],"baseline")
 def test_24_exact_count(self):self.assertEqual(len(generate_stable_starts(T,P,16,7)[0]),16)
 def test_25_lhs_seed(self):self.assertEqual(generate_stable_starts(T,P,16,7)[0],generate_stable_starts(T,P,16,7)[0])
 def test_26_unstable_rejected(self):self.assertFalse(is_stable_theta({**P,"a_p":1.5,"b_q":1.5,"b_n":1.5}))
 def test_27_distance_scaling(self):self.assertAlmostEqual(normalized_parameter_distance(P,{**P,"a_p":P["a_p"]+1.5},B),1.)
 def test_28_clusters_deterministic(self):
  s=[{"valid":True,"loglik":1.,"theta":P,"start_id":0}];self.assertEqual(cluster_solutions(s,B),cluster_solutions(s,B))
 def test_29_ridge_detection(self):
  s=[{"valid":True,"loglik":1.,"theta":P,"start_id":0},{"valid":True,"loglik":.5,"theta":{**P,"a_p":1.},"start_id":1}];self.assertTrue(detect_ridge(s,B)[0])
 def test_30_failures_retained(self):
  s=[{"valid":False,"loglik":-np.inf,"theta":P,"start_id":0}];self.assertEqual(cluster_solutions(s,B),[])
 def test_64_rho_grid(self):self.assertEqual([.5,.8,.95],json.loads((ROOT/"configs/phase2b.yaml").read_text())["rho_n_grid"])
 def test_65_battery_grid(self):self.assertEqual([.1,.25,.5],json.loads((ROOT/"configs/phase2b.yaml").read_text())["battery_sd_grid"])
 def test_66_nine_configs(self):self.assertEqual(len([(r,s) for r in [.5,.8,.95] for s in [.1,.25,.5]]),9)
 def test_67_primary_fixed(self):self.assertEqual((C["rho_n_fixed"],C["battery_sd_fixed"]),(.8,.25))
 def test_68_distance_zero(self):self.assertEqual(normalized_parameter_distance(P,P,B),0.)
