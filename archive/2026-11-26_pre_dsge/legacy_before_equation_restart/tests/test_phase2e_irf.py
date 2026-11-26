"""Phase 2E IRF tests 1-26."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.irf import *
from src.structural.matrices import system_matrices
from src.structural.spec import baseline_parameters
A0=json.loads((ROOT/"configs/phase2a.yaml").read_text());P={**baseline_parameters(),**A0["baseline"]};A,B,_,H=system_matrices("M0_CORE5",P);R=impulse_response(A,B,24)
class Phase2EIRFTests(unittest.TestCase):
 def test_01_dimensions(self):self.assertEqual(R.shape,(25,5,4))
 def test_02_h0_B(self):self.assertTrue(np.array_equal(R[0],B))
 def test_03_h1_AB(self):self.assertTrue(np.allclose(R[1],A@B))
 def test_04_recursive_power(self):self.assertTrue(np.allclose(R[7],np.linalg.matrix_power(A,7)@B))
 def test_05_shock_order(self):self.assertEqual(SHOCK_ORDER,("demand","cost","supply","price"))
 def test_06_state_order(self):self.assertEqual(STATE_ORDER,("d","c","q","n","p"))
 def test_07_no_double_sigma(self):self.assertAlmostEqual(R[0,0,0],P["sigma_d"])
 def test_08_finite(self):self.assertTrue(np.isfinite(R).all())
 def test_09_stable_decay(self):self.assertLess(np.abs(R[-1]).max(),np.abs(R).max())
 def test_10_observation_mapping(self):self.assertTrue(np.allclose(observation_response(R[:,:,0],H)[3],H@R[3,:,0]))
 def test_11_demand_d_positive(self):self.assertGreater(R[0,0,0],0)
 def test_12_demand_p_positive(self):self.assertGreater(R[0,4,0],0)
 def test_13_demand_h1_n_negative(self):self.assertLess(R[1,3,0],0)
 def test_14_cost_c_positive(self):self.assertGreater(R[0,1,1],0)
 def test_15_cost_p_positive(self):self.assertGreater(R[0,4,1],0)
 def test_16_cost_h1_q_formula(self):self.assertAlmostEqual(R[1,2,1],P["a_p"]*R[0,4,1]-P["a_c"]*R[0,1,1])
 def test_17_supply_q_positive(self):self.assertGreater(R[0,2,2],0)
 def test_18_supply_p_negative(self):self.assertLess(R[0,4,2],0)
 def test_19_supply_h1_n_positive(self):self.assertGreater(R[1,3,2],0)
 def test_20_price_p_positive(self):self.assertGreater(R[0,4,3],0)
 def test_21_price_h1_q_nonnegative(self):self.assertGreaterEqual(R[1,2,3],0)
 def test_22_quantiles_ordered(self):
  rows=posterior_irf_summary(np.stack([R[:,:,:1],R[:,:,:1]*1.1]),"demand");self.assertTrue(all(x["q05"]<=x["q16"]<=x["median"]<=x["q84"]<=x["q95"] for x in rows))
 def test_23_sign_probability_bounds(self):self.assertTrue(all(0<=x<=1 for x in sign_probability([-1,1,1])))
 def test_24_peak_horizon_valid(self):self.assertTrue(np.all((peak_timing(np.stack([R[:,4,0]]))[0]>=0)&(peak_timing(np.stack([R[:,4,0]]))[0]<=24)))
 def test_25_terminal_ratio_finite(self):self.assertTrue(np.isfinite(persistence_metric(np.stack([R[:,4,0]]))).all())
 def test_26_stability(self):self.assertLess(max(abs(np.linalg.eigvals(A))),1)
