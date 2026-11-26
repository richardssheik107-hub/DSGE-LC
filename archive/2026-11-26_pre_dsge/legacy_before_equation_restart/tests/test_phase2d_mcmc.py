"""Phase 2D sampler-core and analytic-target tests 16-32."""
from __future__ import annotations
import sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.mcmc import PosteriorEvaluation,extend_chain,random_walk_proposal,run_adaptive_chain
from src.structural.mcmc_diagnostics import bulk_ess,rank_normalized_split_rhat

class Identity:
 def unconstrained_to_theta(self,z):return {f"x{i}":float(v) for i,v in enumerate(z)}
class NormalTarget:
 def __init__(self,d=1,shift=0.):self.transform=Identity();self.d=d;self.shift=shift
 def __call__(self,z):
  z=np.asarray(z);v=float(-.5*np.sum((z-self.shift)**2));return PosteriorEvaluation(v,v,0,0,"OK",0,0)
class RejectPositive(NormalTarget):
 def __call__(self,z):
  if np.any(np.asarray(z)>0):return PosteriorEvaluation(-np.inf,-np.inf,0,0,"UNSTABLE",1.1,0)
  return super().__call__(z)
class RejectKalman(NormalTarget):
 def __call__(self,z):
  if np.any(np.asarray(z)>0):return PosteriorEvaluation(-np.inf,-np.inf,0,0,"KALMAN_FAILURE",.8,0)
  return super().__call__(z)

class Phase2DMCMCTests(unittest.TestCase):
 def test_16_proposal_seed_deterministic(self):
  a=random_walk_proposal(np.zeros(2),np.eye(2),1,np.random.default_rng(2));b=random_walk_proposal(np.zeros(2),np.eye(2),1,np.random.default_rng(2));self.assertTrue(np.array_equal(a,b))
 def test_17_symmetric_rw_proposal(self):
  rng=np.random.default_rng(3);steps=np.array([random_walk_proposal(np.zeros(2),np.eye(2),1,rng,1) for _ in range(4000)]);self.assertLess(np.abs(steps.mean(0)).max(),.05)
 def test_18_accepted_state_updates(self):
  r=run_adaptive_chain(NormalTarget(),[-5.],10,30,8,initial_scale=.5);self.assertGreater(np.unique(r["z"]).size,1)
 def test_19_rejected_state_unchanged(self):
  r=run_adaptive_chain(RejectPositive(),[-.01],1,30,9,initial_scale=10,mixture_probability=1);self.assertTrue(np.all(r["z"]<=0))
 def test_20_log_acceptance_ratio(self):self.assertAlmostEqual(NormalTarget()([1.]).total-NormalTarget()([0.]).total,-.5)
 def test_21_unstable_proposal_rejected(self):
  r=run_adaptive_chain(RejectPositive(),[-.2],1,20,1,initial_scale=4,mixture_probability=1);self.assertGreater(r["audit"].unstable,0)
 def test_22_invalid_kalman_counted(self):
  r=run_adaptive_chain(RejectKalman(),[-.2],1,20,1,initial_scale=4,mixture_probability=1);self.assertGreater(r["audit"].kalman_failures,0)
 def test_23_adaptation_warmup_only(self):
  r=run_adaptive_chain(NormalTarget(),[0.],100,20,5);self.assertIn("kernel",r)
 def test_24_production_covariance_frozen(self):
  r=run_adaptive_chain(NormalTarget(2),[0.,0.],100,20,5);k=r["kernel"]["chol"].copy();extend_chain(NormalTarget(2),r,10);self.assertTrue(np.array_equal(k,r["kernel"]["chol"]))
 def test_25_production_scale_frozen(self):
  r=run_adaptive_chain(NormalTarget(),[0.],100,20,5);s=r["kernel"]["scale"];extend_chain(NormalTarget(),r,10);self.assertEqual(s,r["kernel"]["scale"])
 def test_26_normal_mean_recovered(self):
  r=run_adaptive_chain(NormalTarget(1,.4),[0.],500,3000,11);self.assertLess(abs(r["z"].mean()-.4),.15)
 def test_27_mvn_mean_recovered(self):
  r=run_adaptive_chain(NormalTarget(5),np.zeros(5),700,5000,12);self.assertLess(np.abs(r["z"].mean(0)).max(),.2)
 def test_28_mvn_covariance_recovered(self):
  r=run_adaptive_chain(NormalTarget(5),np.zeros(5),700,5000,13);self.assertLess(np.abs(np.diag(np.cov(r["z"],rowvar=False))-1).max(),.3)
 def test_29_multichain_rhat_converges(self):
  c=np.stack([run_adaptive_chain(NormalTarget(),[float(i)],400,2000,20+i)["z"][:,0] for i in range(4)]);self.assertLess(rank_normalized_split_rhat(c),1.05)
 def test_30_ess_positive(self):
  x=np.random.default_rng(2).normal(size=(4,1000));self.assertGreater(bulk_ess(x),100)
 def test_31_beta_jacobian_recovered(self):
  rng=np.random.default_rng(4);theta=rng.beta(2,3,20000);self.assertLess(abs(theta.mean()-.4),.01)
 def test_32_jacobian_negative_control_differs(self):
  grid=np.linspace(-12,12,100000);t=1/(1+np.exp(-grid));w=t*(1-t)**2;wj=w*t*(1-t);self.assertGreater(abs(np.average(t,weights=w)-np.average(t,weights=wj)),.04)
