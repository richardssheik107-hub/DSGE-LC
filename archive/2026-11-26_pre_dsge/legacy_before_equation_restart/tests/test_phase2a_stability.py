"""Phase 2A acceptance tests 30-34 and 47-53."""
from __future__ import annotations
import sys, unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.structural.equations import transition, zero_steady_state
from src.structural.matrices import system_matrices
from src.structural.simulation import lagged_value
from src.structural.spec import baseline_parameters, validate_design
from src.structural.stability import stability_metrics
P=baseline_parameters()

class StabilityAndCapacityTests(unittest.TestCase):
    def test_30_known_stable(self): self.assertTrue(stability_metrics(system_matrices("M0_CORE5",P)[0])["stable"])
    def test_31_constructed_unstable(self):
        A=np.diag([1.01,.5]); self.assertFalse(stability_metrics(A)["stable"])
    def test_32_spectral_radius_correct(self): self.assertAlmostEqual(stability_metrics(np.diag([-.8,.2]))["spectral_radius"],.8)
    def test_33_zero_state_zero_shock(self): self.assertTrue(np.allclose(transition("M0_CORE5",zero_steady_state("M0_CORE5"),np.zeros(4),P),0))
    def test_34_m1_zero_margin_steady_state(self): self.assertTrue(np.allclose(transition("M1_CAPACITY6",zero_steady_state("M1_CAPACITY6"),np.zeros(4),P,0),0))
    def test_47_lag_9_index(self): self.assertEqual(lagged_value(np.arange(20),12,9),3)
    def test_48_lag_10_index(self): self.assertEqual(lagged_value(np.arange(20),12,10),2)
    def test_49_lag_11_index(self): self.assertEqual(lagged_value(np.arange(20),12,11),1)
    def test_50_no_future_margin(self): self.assertEqual(lagged_value(np.arange(20),5,11),0)
    def test_51_gamma_nonnegative(self):
        p=dict(P); p["gamma_m"]=-.1
        with self.assertRaises(ValueError): validate_design("M1_CAPACITY6",p,10)
    def test_52_rho_k_sensitivity_only(self):
        for rho in (.8,.9,.97): p=dict(P); p["rho_k"]=rho; validate_design("M1_CAPACITY6",p,10)
    def test_53_capacity_has_no_independent_shock(self): self.assertTrue(np.allclose(system_matrices("M1_CAPACITY6",P)[1][2],0))
