"""Phase 2C curvature and OPG tests 44-56."""
from __future__ import annotations
import sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.curvature import *
from src.structural.parameter_transform import *
B=parameter_bounds();T=ParameterTransform.full(B)

class Phase2CCurvatureTests(unittest.TestCase):
 def test_44_symmetric(self):self.assertTrue(np.allclose(finite_difference_hessian(lambda x:x@x,np.ones(2)),finite_difference_hessian(lambda x:x@x,np.ones(2)).T))
 def test_45_quadratic(self):self.assertTrue(np.allclose(finite_difference_hessian(lambda x:x@x,np.ones(2),1e-3),2*np.eye(2),atol=1e-5))
 def test_46_step_rows(self):self.assertEqual(len(hessian_step_robustness(lambda x:x@x,np.ones(2),[1e-4,2e-4],("a","b"))[0]),2)
 def test_47_sorted(self):self.assertTrue(np.all(np.diff(matrix_diagnostics(np.diag([2.,1.]),("a","b"))["eigenvalues"])>=0))
 def test_48_condition(self):self.assertEqual(matrix_diagnostics(np.diag([2.,1.]),("a","b"))["condition_number"],2.)
 def test_49_indefinite_blocks(self):self.assertIsNone(native_covariance(np.diag([1.]*13+[-1.]),T,np.zeros(14))[0])
 def test_50_delta_mapping(self):self.assertEqual(native_covariance(np.eye(14),T,np.zeros(14))[0].shape,(14,14))
 def test_51_score_shape(self):self.assertEqual(per_time_score(lambda x:np.tile(x.sum(),57),np.ones(14)).shape,(57,14))
 def test_52_score_finite(self):self.assertTrue(np.isfinite(per_time_score(lambda x:np.tile(x.sum(),3),np.ones(2))).all())
 def test_53_opg_symmetric(self):self.assertTrue(np.allclose(opg_diagnostics(np.ones((3,2)),("a","b"))[0],opg_diagnostics(np.ones((3,2)),("a","b"))[0].T))
 def test_54_opg_psd(self):self.assertGreaterEqual(np.linalg.eigvalsh(opg_diagnostics(np.ones((3,2)),("a","b"))[0]).min(),-1e-12)
 def test_55_opg_rank(self):self.assertEqual(opg_diagnostics(np.eye(2),("a","b"))[1]["rank"],2)
 def test_56_weak_pair(self):self.assertTrue(high_correlation_pairs(np.array([[1,.95],[.95,1.]]),("a","b")))
