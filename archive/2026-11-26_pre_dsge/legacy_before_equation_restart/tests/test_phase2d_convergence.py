"""Phase 2D convergence and extension tests 33-44."""
from __future__ import annotations
import sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.mcmc import PosteriorEvaluation,extend_chain,run_adaptive_chain
from src.structural.mcmc_diagnostics import bulk_ess,convergence_pass,diagnostic_table,effective_sample_size,rank_normalized_split_rhat,split_chains,tail_ess
class Identity:
 def unconstrained_to_theta(self,z):return {"x0":float(z[0])}
class Target:
 transform=Identity()
 def __call__(self,z):v=-.5*float(z[0])**2;return PosteriorEvaluation(v,v,0,0,"OK",0,0)

class Phase2DConvergenceTests(unittest.TestCase):
 def setUp(self):self.rng=np.random.default_rng(9)
 def test_33_iid_rhat_near_one(self):self.assertLess(rank_normalized_split_rhat(self.rng.normal(size=(4,2000))),1.01)
 def test_34_shifted_rhat_above_one(self):
  x=self.rng.normal(size=(4,1000));x[0]+=2;self.assertGreater(rank_normalized_split_rhat(x),1.1)
 def test_35_rank_rhat_finite(self):self.assertTrue(np.isfinite(rank_normalized_split_rhat(self.rng.standard_t(3,size=(4,500)))))
 def test_36_split_dimensions(self):self.assertEqual(split_chains(np.zeros((4,101))).shape,(8,50))
 def test_37_iid_ess_near_raw(self):self.assertGreater(effective_sample_size(self.rng.normal(size=(4,2000))),4000)
 def test_38_ar_ess_lower(self):
  e=self.rng.normal(size=(4,2000));x=np.zeros_like(e)
  for t in range(1,2000):x[:,t]=.95*x[:,t-1]+e[:,t]
  self.assertLess(effective_sample_size(x),2000)
 def test_39_tail_ess_finite(self):self.assertTrue(np.isfinite(tail_ess(self.rng.normal(size=(4,500)))))
 def test_40_constant_chain_safe(self):self.assertEqual(effective_sample_size(np.ones((4,100))),0)
 def test_41_failed_diagnostics_detected(self):
  rows=[{"rhat":1.02,"bulk_ess":500,"tail_ess":500,"mcse_sd":.01}];cfg={"rhat_threshold":1.01,"bulk_ess_threshold":400,"tail_ess_threshold":400,"mcse_sd_threshold":.05};self.assertFalse(convergence_pass(rows,cfg))
 def test_42_all_chains_extended_equal(self):
  rs=[run_adaptive_chain(Target(),[0.],10,20,i) for i in range(4)];rs=[extend_chain(Target(),r,7) for r in rs];self.assertEqual({len(r["z"]) for r in rs},{27})
 def test_43_kernel_unchanged_after_warmup(self):
  r=run_adaptive_chain(Target(),[0.],50,20,3);k=(r["kernel"]["chol"].copy(),r["kernel"]["scale"]);extend_chain(Target(),r,8);self.assertTrue(np.array_equal(k[0],r["kernel"]["chol"]));self.assertEqual(k[1],r["kernel"]["scale"])
 def test_44_max_production_config_exact(self):
  import json;cfg=json.loads((ROOT/"configs/phase2d.yaml").read_text());self.assertEqual(cfg["max_production_draws"],60000);self.assertEqual(cfg["extension_block_draws"],6000)
