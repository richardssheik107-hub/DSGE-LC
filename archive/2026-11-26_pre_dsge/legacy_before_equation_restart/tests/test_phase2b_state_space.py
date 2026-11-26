"""Phase 2B acceptance tests 01-20: frozen matrices and initialization."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.matrices import system_matrices
from src.structural.spec import MODEL_SPECS,baseline_parameters
from src.structural.state_space import diffuse_initialization,from_phase2a_parameters,process_covariance,stationary_initialization
A_CFG=json.loads((ROOT/"configs/phase2a.yaml").read_text());B_CFG=json.loads((ROOT/"configs/phase2b.yaml").read_text());P={**baseline_parameters(),**A_CFG["baseline"]};M=from_phase2a_parameters("M0_CORE5",P,.25)

class Phase2BStateSpaceTests(unittest.TestCase):
 def test_01_state_order(self):self.assertEqual(M.state_names,("d","c","q","n","p"))
 def test_02_observation_order(self):self.assertEqual(M.observation_names,("spot","ore_cost","output","battery"))
 def test_03_shock_order(self):self.assertEqual(M.shock_names,("demand","cost","supply","price"))
 def test_04_a_matches_phase2a(self):self.assertTrue(np.array_equal(M.A,system_matrices("M0_CORE5",P)[0]))
 def test_05_b_matches_phase2a(self):self.assertTrue(np.array_equal(M.B,system_matrices("M0_CORE5",P)[1]))
 def test_06_h_matches_phase2a(self):self.assertTrue(np.array_equal(M.H,system_matrices("M0_CORE5",P)[3]))
 def test_07_w_equals_bbt(self):self.assertTrue(np.allclose(M.W,M.B@M.B.T))
 def test_08_sigma_not_double_counted(self):self.assertAlmostEqual(M.W[0,0],P["sigma_d"]**2)
 def test_09_w_symmetric(self):self.assertTrue(np.allclose(M.W,M.W.T))
 def test_10_w_psd(self):self.assertGreaterEqual(np.linalg.eigvalsh(M.W).min(),-1e-12)
 def test_11_r_diagonal(self):self.assertTrue(np.allclose(M.R,np.diag(np.diag(M.R))))
 def test_12_first_three_r_zero(self):self.assertTrue(np.array_equal(np.diag(M.R)[:3],np.zeros(3)))
 def test_13_battery_variance(self):self.assertEqual(M.R[3,3],.25**2)
 def test_14_dimensions(self):self.assertEqual((M.A.shape,M.B.shape,M.W.shape,M.H.shape,M.R.shape),((5,5),(5,4),(5,5),(4,5),(4,4)))
 def test_15_lyapunov_solution(self):
  _,Q,res=stationary_initialization(M);self.assertLess(res,1e-8);self.assertTrue(np.allclose(Q,M.A@Q@M.A.T+M.W))
 def test_16_stationary_symmetric(self):self.assertTrue(np.allclose(stationary_initialization(M)[1],stationary_initialization(M)[1].T))
 def test_17_stationary_psd(self):self.assertGreaterEqual(np.linalg.eigvalsh(stationary_initialization(M)[1]).min(),-1e-10)
 def test_18_zero_mean(self):self.assertTrue(np.array_equal(stationary_initialization(M)[0],np.zeros(5)))
 def test_19_unstable_rejected(self):
  p=dict(P);p["rho_d"]=1.01
  with self.assertRaisesRegex(ValueError,"UNSTABLE"):from_phase2a_parameters("M0_CORE5",p,.25)
 def test_20_diffuse_dimensions(self):
  m,Q=diffuse_initialization(M,10);self.assertEqual((m.shape,Q.shape),((5,),(5,5)));self.assertTrue(np.array_equal(Q,10*np.eye(5)))
