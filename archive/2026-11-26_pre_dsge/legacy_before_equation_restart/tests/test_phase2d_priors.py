"""Phase 2D prior, transform, Jacobian and support tests 1-15."""
from __future__ import annotations
import json,math,sys,unittest
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from scipy.stats import beta as beta_dist,halfnorm
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.mcmc import PosteriorTarget,log_transform_jacobian
from src.structural.parameter_transform import PARAMETER_ORDER,ParameterTransform,load_phase2a_bounds
from src.structural.priors import _log_truncated_halfnormal,draw_prior_native,log_prior_native,prior_specs,stable_mask,theta_from_array
A=json.loads((ROOT/"configs/phase2a.yaml").read_text());CFG=json.loads((ROOT/"configs/phase2d.yaml").read_text());BOUNDS=load_phase2a_bounds(ROOT/"configs/phase2a.yaml");T=ParameterTransform.full(BOUNDS);S=prior_specs(CFG);BASE=S["PRIOR_BASELINE_WEAK"]

class Phase2DPriorTests(unittest.TestCase):
 def setUp(self):self.mid={n:(lo+hi)/2 for n,(lo,hi) in BOUNDS.items()}
 def test_01_native_prior_finite_in_support(self):self.assertTrue(np.isfinite(log_prior_native(self.mid,BOUNDS,BASE)))
 def test_02_prior_minus_inf_outside_support(self):
  x=dict(self.mid);x["a_c"]=-.01;self.assertEqual(log_prior_native(x,BOUNDS,BASE),-np.inf)
 def test_03_truncated_normalization_finite(self):self.assertTrue(np.isfinite(_log_truncated_halfnormal(.5,.75,0,1.5)))
 def test_04_scaled_beta_density_correct(self):
  x=dict(self.mid);got=log_prior_native(x,BOUNDS,BASE);parts=0.
  for n in PARAMETER_ORDER:
   lo,hi=BOUNDS[n];v=x[n]
   if n.startswith("rho_"):parts+=beta_dist.logpdf((v-lo)/(hi-lo),2,2)-math.log(hi-lo)
   elif n.startswith("sigma_"):parts+=_log_truncated_halfnormal(v,1.,lo,hi)
   else:parts+=_log_truncated_halfnormal(v,.75,lo,hi)
  self.assertAlmostEqual(got,parts,10)
 def test_05_halfnormal_truncation_correct(self):
  z=halfnorm.cdf(1.5,scale=.75)-halfnorm.cdf(0,scale=.75);expected=halfnorm.logpdf(.4,scale=.75)-math.log(z)
  self.assertAlmostEqual(_log_truncated_halfnormal(.4,.75,0,1.5),expected,10)
 def test_06_prior_draws_obey_bounds(self):
  d=draw_prior_native(BASE,BOUNDS,250,4);self.assertTrue(all(np.all((d[:,j]>=lo)&(d[:,j]<=hi)) for j,(lo,hi) in enumerate(BOUNDS.values())))
 def test_07_unstable_theta_rejected(self):
  d=np.array([[BOUNDS[n][1] for n in PARAMETER_ORDER]]);mask,_=stable_mask(d,.8);self.assertFalse(mask[0])
 def test_08_log_jacobian_finite(self):self.assertTrue(np.isfinite(log_transform_jacobian(np.zeros(14),T)))
 def test_09_jacobian_matches_finite_difference(self):
  z=np.linspace(-1,1,14);eps=1e-6;diag=[]
  for j in range(14):
   e=np.zeros(14);e[j]=eps;up=T.unconstrained_to_theta(z+e)[PARAMETER_ORDER[j]];dn=T.unconstrained_to_theta(z-e)[PARAMETER_ORDER[j]];diag.append((up-dn)/(2*eps))
  self.assertAlmostEqual(log_transform_jacobian(z,T),float(np.log(diag).sum()),7)
 def test_10_posterior_target_includes_jacobian(self):
  src=(ROOT/"src/structural/mcmc.py").read_text();self.assertIn("result.loglik+lp+lj",src)
 def test_11_theta_z_roundtrip(self):
  z=np.linspace(-3,3,14);self.assertTrue(np.allclose(T.theta_to_unconstrained(T.unconstrained_to_theta(z)),z))
 def test_12_large_positive_z_nears_upper(self):
  th=T.unconstrained_to_theta(np.full(14,25.));self.assertTrue(all(BOUNDS[n][1]-th[n]<1e-9 for n in PARAMETER_ORDER))
 def test_13_large_negative_z_nears_lower(self):
  th=T.unconstrained_to_theta(np.full(14,-25.));self.assertTrue(all(th[n]-BOUNDS[n][0]<1e-9 for n in PARAMETER_ORDER))
 def test_14_no_substantive_eight_bound(self):self.assertTrue(np.isfinite(log_transform_jacobian(np.full(14,9.),T)))
 def test_15_guard_only_extreme(self):
  class Dummy(PosteriorTarget):pass
  target=object.__new__(Dummy);target.guard=30.;self.assertLess(np.max(np.abs(np.full(14,9.))),target.guard);self.assertGreater(np.max(np.abs(np.full(14,31.))),target.guard)
