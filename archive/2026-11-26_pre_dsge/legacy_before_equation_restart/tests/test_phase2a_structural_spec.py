"""Phase 2A acceptance tests 01-29: specification, equations and matrices."""
from __future__ import annotations
import json, sys, unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from src.structural.equations import transition
from src.structural.matrices import system_matrices
from src.structural.spec import MODEL_SPECS, baseline_parameters, parameter_names, parameter_registry

P = baseline_parameters(); CFG = json.loads((ROOT / "configs/phase2a.yaml").read_text())

class StructuralSpecTests(unittest.TestCase):
    def test_01_m0_state_order_exact(self): self.assertEqual(MODEL_SPECS["M0_CORE5"].states, ("d","c","q","n","p"))
    def test_02_m1_state_order_exact(self): self.assertEqual(MODEL_SPECS["M1_CAPACITY6"].states, ("d","c","k","q","n","p"))
    def test_03_observation_order_exact(self): self.assertTrue(all(s.observations == ("spot","ore_cost","output","battery") for s in MODEL_SPECS.values()))
    def test_04_shock_order_exact(self): self.assertTrue(all(s.shocks == ("demand","cost","supply","price") for s in MODEL_SPECS.values()))
    def test_05_m0_free_parameter_count(self): self.assertEqual(len(parameter_names("M0_CORE5")), 14)
    def test_06_m1_free_parameter_count(self): self.assertEqual(len(parameter_names("M1_CAPACITY6")), 15)
    def test_07_lambda_loadings_fixed_one(self):
        for model in MODEL_SPECS:
            H=system_matrices(model,P)[3]; self.assertTrue(np.allclose(H.sum(axis=1), 1))
    def test_08_inventory_loadings_fixed(self):
        A=system_matrices("M0_CORE5",P)[0]; self.assertEqual((A[3,2],A[3,0]), (1.,-1.))
    def test_09_capacity_loading_fixed_one(self):
        A=system_matrices("M1_CAPACITY6",P)[0]; self.assertEqual(A[3,2], P["rho_k"])
    def test_10_l_grid_exact(self): self.assertEqual(CFG["capacity_lag_grid"], [9,10,11])
    def test_11_demand_equation(self):
        x=np.zeros(5); x[0]=2; self.assertAlmostEqual(transition("M0_CORE5",x,np.zeros(4),P)[0],2*P["rho_d"])
    def test_12_cost_equation(self):
        x=np.zeros(5); x[1]=2; self.assertAlmostEqual(transition("M0_CORE5",x,np.zeros(4),P)[1],2*P["rho_c"])
    def test_13_supply_uses_lagged_price(self):
        x=np.zeros(5); x[4]=2; self.assertAlmostEqual(transition("M0_CORE5",x,np.zeros(4),P)[2],2*P["a_p"])
    def test_14_supply_uses_lagged_cost(self):
        x=np.zeros(5); x[1]=2; self.assertAlmostEqual(transition("M0_CORE5",x,np.zeros(4),P)[2],-2*P["a_c"])
    def test_15_inventory_uses_lagged_q_d(self):
        x=np.zeros(5); x[2]=3; x[0]=1; self.assertAlmostEqual(transition("M0_CORE5",x,np.zeros(4),P)[3],2)
    def test_16_price_uses_current_states(self):
        e=np.array([1.,1.,1.,0.]); y=transition("M0_CORE5",np.zeros(5),e,P); self.assertAlmostEqual(y[4],P["b_d"]*y[0]+P["b_c"]*y[1]-P["b_q"]*y[2])
    def test_17_no_contemporaneous_p_q_circle(self):
        x=np.zeros(5); x[4]=1; y=transition("M0_CORE5",x,np.zeros(4),P); self.assertAlmostEqual(y[2],P["a_p"])
    def test_18_positive_demand_raises_price(self): self.assertGreater(transition("M0_CORE5",np.zeros(5),np.array([1,0,0,0]),P)[4],0)
    def test_19_positive_cost_raises_price(self): self.assertGreater(transition("M0_CORE5",np.zeros(5),np.array([0,1,0,0]),P)[4],0)
    def test_20_positive_q_lowers_price(self):
        p=dict(P); p["rho_q"]=0; self.assertLess(transition("M0_CORE5",np.zeros(5),np.array([0,0,1,0]),p)[4],0)
    def test_21_positive_n_lowers_price(self):
        x=np.zeros(5); x[3]=1; self.assertLess(transition("M0_CORE5",x,np.zeros(4),P)[4],0)
    def test_22_a_dimensions_m0(self): self.assertEqual(system_matrices("M0_CORE5",P)[0].shape,(5,5))
    def test_23_a_dimensions_m1(self): self.assertEqual(system_matrices("M1_CAPACITY6",P)[0].shape,(6,6))
    def test_24_b_dimensions(self): self.assertEqual((system_matrices("M0_CORE5",P)[1].shape,system_matrices("M1_CAPACITY6",P)[1].shape),((5,4),(6,4)))
    def test_25_g_absent_m0(self): self.assertEqual(system_matrices("M0_CORE5",P)[2].shape,(5,0))
    def test_26_g_correct_m1(self):
        G=system_matrices("M1_CAPACITY6",P)[2][:,0]; self.assertTrue(np.allclose(G,[0,0,P["gamma_m"],P["gamma_m"],0,-P["b_q"]*P["gamma_m"]]))
    def test_27_h_mapping_correct(self):
        H=system_matrices("M1_CAPACITY6",P)[3]; self.assertEqual(tuple(np.argmax(H,axis=1)),(5,1,3,0))
    def test_28_equation_equals_matrix_transition(self):
        rng=np.random.default_rng(1); x=rng.normal(size=6); e=rng.normal(size=4); A,B,G,_=system_matrices("M1_CAPACITY6",P); self.assertTrue(np.allclose(transition("M1_CAPACITY6",x,e,P,.3),A@x+B@e+G[:,0]*.3))
    def test_29_shock_equals_b_mapping(self):
        e=np.array([.2,-.1,.3,.4]); B=system_matrices("M0_CORE5",P)[1]; self.assertTrue(np.allclose(transition("M0_CORE5",np.zeros(5),e,P),B@e))
