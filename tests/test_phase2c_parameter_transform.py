"""Phase 2C transform and boundary acceptance tests 1-8, 31-35."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.parameter_transform import *
A=json.loads((ROOT/"configs/phase2a.yaml").read_text());BOUNDS=load_phase2a_bounds(ROOT/"configs/phase2a.yaml");T=ParameterTransform.full(BOUNDS)

class Phase2CTransformTests(unittest.TestCase):
 def test_01_order_exact(self):self.assertEqual(PARAMETER_ORDER,("rho_d","rho_c","rho_q","rho_p","a_p","a_c","b_d","b_c","b_q","b_n","sigma_d","sigma_c","sigma_q","sigma_p"))
 def test_02_round_trip(self):
  x={n:(lo+hi)/2.7 for n,(lo,hi) in BOUNDS.items()};self.assertTrue(all(abs(T.unconstrained_to_theta(T.theta_to_unconstrained(x))[n]-x[n])<1e-10 for n in x))
 def test_03_rho_bounds(self):self.assertTrue(all(BOUNDS[n][0]<T.unconstrained_to_theta(np.full(14,8.))[n]<BOUNDS[n][1] for n in PERSISTENCE))
 def test_04_effect_bounds(self):self.assertTrue(all(BOUNDS[n][0]<T.unconstrained_to_theta(np.full(14,-8.))[n]<BOUNDS[n][1] for n in EFFECT))
 def test_05_sigma_bounds(self):self.assertTrue(all(BOUNDS[n][0]<T.unconstrained_to_theta(np.zeros(14))[n]<BOUNDS[n][1] for n in SHOCK_SD))
 def test_06_boundary_metric(self):self.assertAlmostEqual(boundary_distance("a_p",.15,BOUNDS),.1)
 def test_07_ap0_exact(self):self.assertEqual(ParameterTransform.ap0(BOUNDS).unconstrained_to_theta(np.zeros(13))["a_p"],0.)
 def test_08_loaded_bounds(self):self.assertEqual(BOUNDS["rho_d"],tuple(A["parameter_ranges"]["persistence"]))
 def test_31_lower_flag(self):self.assertEqual(boundary_diagnostics({n:BOUNDS[n][0] for n in PARAMETER_ORDER},BOUNDS)[0]["boundary_flag"],"LOWER")
 def test_32_upper_flag(self):self.assertEqual(boundary_diagnostics({n:BOUNDS[n][1] for n in PARAMETER_ORDER},BOUNDS)[0]["boundary_flag"],"UPPER")
 def test_33_interior_unflagged(self):self.assertFalse(boundary_diagnostics({n:sum(BOUNDS[n])/2 for n in PARAMETER_ORDER},BOUNDS)[0]["boundary_flag"])
 def test_34_extended_deterministic(self):self.assertEqual(parameter_bounds(A["parameter_ranges"],["effect"])["b_c"],(0.,3.))
 def test_35_primary_not_replaced(self):self.assertEqual(BOUNDS["b_c"],(0.,1.5))
