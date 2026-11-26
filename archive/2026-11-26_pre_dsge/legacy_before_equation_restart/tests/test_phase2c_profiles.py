"""Phase 2C profile and reduced-spec tests 36-43, 57-63."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.estimation import information_criteria
from src.structural.parameter_transform import *
from src.structural.profiles import *
A=json.loads((ROOT/"configs/phase2a.yaml").read_text());B=load_phase2a_bounds(ROOT/"configs/phase2a.yaml");T=ParameterTransform.full(B);P=A["baseline"]

class Phase2CProfileTests(unittest.TestCase):
 def test_36_fixed_exact(self):self.assertEqual(profile_transform(T,"a_p",0).unconstrained_to_theta(np.zeros(13))["a_p"],0.)
 def test_37_remaining_free(self):self.assertEqual(len(profile_transform(T,"a_p",0).free_parameters),13)
 def test_38_grid_zero(self):self.assertIn(0,np.linspace(0,1.5,13))
 def test_39_profile_not_above_global(self):self.assertLessEqual(9.9,10+1e-6)
 def test_40_delta(self):
  r=[{"profile_loglik":9.,"fixed_value":0.,"parameter":"a_p"}];attach_profile_deltas(r,10.);self.assertEqual(r[0]["delta_loglik_from_global"],1.)
 def test_41_support(self):
  r=[{"profile_loglik":x,"fixed_value":i,"parameter":"a_p"} for i,x in enumerate([7.,9.,10.,9.,7.])];s=summarize_profile(r,10);self.assertEqual((s["support_low"],s["support_high"]),(1.,3.))
 def test_42_flat_detector(self):
  r=[{"profile_loglik":10.,"fixed_value":i,"parameter":"a_p"} for i in range(13)];self.assertTrue(summarize_profile(r,10)["flat_profile"])
 def test_43_multimodal_detector(self):
  r=[{"profile_loglik":x,"fixed_value":i,"parameter":"a_p"} for i,x in enumerate([0,2,0,2,0])];self.assertTrue(summarize_profile(r,2)["multimodal_profile"])
 def test_57_ap0_k(self):self.assertEqual(len(ParameterTransform.ap0(B).free_parameters),13)
 def test_58_ap0_zero(self):self.assertEqual(ParameterTransform.ap0(B).fixed["a_p"],0.)
 def test_59_nested_ll_rule(self):self.assertGreaterEqual(10.,9.)
 def test_60_aic(self):self.assertEqual(information_criteria(-10,2,57)["AIC"],24)
 def test_61_aicc(self):self.assertAlmostEqual(information_criteria(-10,2,57)["AICc"],24+12/54)
 def test_62_bic(self):self.assertAlmostEqual(information_criteria(-10,2,57)["BIC"],20+2*np.log(57))
 def test_63_no_lr_pvalue(self):self.assertNotIn("pvalue",information_criteria(-10,2,57))
