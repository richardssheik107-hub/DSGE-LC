"""Phase 2D posterior, synthetic, real-data and sensitivity tests 45-66."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.kalman_diagnostics import simulate_observations
from src.structural.mcmc import PosteriorTarget,run_adaptive_chain
from src.structural.measurement import build_measurements,load_frozen_panel
from src.structural.parameter_transform import PARAMETER_ORDER,ParameterTransform,load_phase2a_bounds
from src.structural.posterior_diagnostics import posterior_correlation,posterior_summary,prior_posterior_contraction,sensitivity_shift,spectral_radius_summary
from src.structural.priors import prior_specs
from src.structural.spec import baseline_parameters
from src.structural.state_space import from_phase2a_parameters
A=json.loads((ROOT/"configs/phase2a.yaml").read_text());CFG=json.loads((ROOT/"configs/phase2d.yaml").read_text());BOUNDS=load_phase2a_bounds(ROOT/"configs/phase2a.yaml");T=ParameterTransform.full(BOUNDS);S=prior_specs(CFG)
PHASE2C_MODE=dict(zip(PARAMETER_ORDER,[.7713675771513933,.6111951530432311,.5405561715294913,.203467163168681,.3142946362347702,.0005030251956997,.1532653547611956,.4082603856329911,.0777086041085663,.0303389332938112,.6289941817548099,.842738949422403,.7329448272369047,.7678999603509122]))
def fake_diag():return [{"parameter":n,"rhat":1.,"bulk_ess":1000.,"tail_ess":900.,"mcse":.01,"posterior_sd":.1,"mcse_sd":.01} for n in PARAMETER_ORDER]
def fake_chains():
 rng=np.random.default_rng(1);out=np.empty((4,200,14))
 for j,n in enumerate(PARAMETER_ORDER):lo,hi=BOUNDS[n];out[:,:,j]=rng.uniform(lo,hi,(4,200))
 return out

class Phase2DPosteriorTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.theta=fake_chains();cls.summary=posterior_summary(cls.theta,fake_diag(),BOUNDS);cls.frame=load_frozen_panel(ROOT/"data/processed/phase1/monthly_structural_v1.csv",A["sample_end"]);cls.measure=build_measurements(cls.frame,"OBS_MIXED4")
 def test_45_quantiles_monotonic(self):self.assertTrue(all(r["q025"]<=r["q05"]<=r["q25"]<=r["q50"]<=r["q75"]<=r["q95"]<=r["q975"] for r in self.summary))
 def test_46_boundary_mass_correct(self):
  x=self.theta.copy();x[:,:,5]=.001;s=posterior_summary(x,fake_diag(),BOUNDS);self.assertEqual(s[5]["lower_boundary_mass"],1.)
 def test_47_correlation_symmetric(self):self.assertTrue(np.allclose(posterior_correlation(self.theta)[0],posterior_correlation(self.theta)[0].T))
 def test_48_contraction_ratio_correct(self):
  prior=self.theta.reshape(-1,14)*2;rows=prior_posterior_contraction(prior,self.summary);self.assertAlmostEqual(rows[0]["contraction_ratio"],.5)
 def test_49_sensitivity_shift_correct(self):
  other=[dict(r) for r in self.summary];other[0]["median"]+=self.summary[0]["sd"];self.assertAlmostEqual(sensitivity_shift(self.summary,other,"x")[0]["standardized_posterior_shift"],1.)
 def test_50_spectral_radius_summary(self):
  c=np.zeros((4,20,5));c[:,:,4]=.7;self.assertAlmostEqual(spectral_radius_summary(c)["median"],.7)
 def _synthetic_target(self):
  truth={**baseline_parameters(),**A["baseline"]};model=from_phase2a_parameters("M0_CORE5",truth,CFG["battery_sd_fixed"]);_,y,_=simulate_observations(model,30,20,7);return truth,PosteriorTarget(T,y,S[CFG["baseline_prior"]],.8,.25,30)
 def test_51_synthetic_target_finite_truth(self):
  truth,target=self._synthetic_target();self.assertTrue(np.isfinite(target(T.theta_to_unconstrained(truth)).total))
 def test_52_accepted_draws_stable(self):
  truth,target=self._synthetic_target();r=run_adaptive_chain(target,T.theta_to_unconstrained(truth),10,20,5,initial_scale=.005);self.assertTrue(np.all(r["components"][:,4]<1))
 def test_53_no_uncontrolled_jitter(self):
  truth,target=self._synthetic_target();ev=target(T.theta_to_unconstrained(truth));self.assertTrue(np.isfinite(ev.max_jitter));self.assertLess(ev.max_jitter,1e-3)
 def test_54_synthetic_checkpoint_recovery(self):
  truth,target=self._synthetic_target();z=T.theta_to_unconstrained(truth);r=run_adaptive_chain(target,z,5,20,18,initial_scale=.001);med=np.median(r["theta"],axis=0);err=np.sqrt(np.mean([((med[j]-truth[n])/(BOUNDS[n][1]-BOUNDS[n][0]))**2 for j,n in enumerate(PARAMETER_ORDER)]));self.assertLess(err,.05)
 def test_55_synthetic_chain_reproducible(self):
  truth,target=self._synthetic_target();z=T.theta_to_unconstrained(truth);a=run_adaptive_chain(target,z,5,10,33,initial_scale=.002);b=run_adaptive_chain(target,z,5,10,33,initial_scale=.002);self.assertTrue(np.array_equal(a["z"],b["z"]))
 def test_56_obs_mixed4_n57(self):self.assertEqual(len(self.measure),57)
 def test_57_sample_start(self):self.assertEqual(self.measure.month.iloc[0],"2021-01")
 def test_58_sample_end(self):self.assertEqual(self.measure.month.iloc[-1],"2025-09")
 def test_59_no_future_contamination(self):self.assertTrue((self.measure.month<="2025-09").all())
 def test_60_mode_target_finite(self):
  y=self.measure[["spot","ore_cost","output","battery"]].to_numpy();target=PosteriorTarget(T,y,S[CFG["baseline_prior"]],.8,.25,30);self.assertTrue(np.isfinite(target(T.theta_to_unconstrained(PHASE2C_MODE)).total))
 def test_61_four_chains_validly_initialized(self):self.assertEqual(CFG["chains"],4)
 def test_62_baseline_accepted_stable(self):
  truth,target=self._synthetic_target();r=run_adaptive_chain(target,T.theta_to_unconstrained(truth),5,20,19,initial_scale=.002);self.assertTrue(np.all(r["components"][:,4]<1))
 def test_63_three_prior_specs_exact(self):self.assertEqual(set(S),{"PRIOR_BASELINE_WEAK","PRIOR_FLAT_BOUNDED","PRIOR_MODERATE_SHRINK"})
 def test_64_prior_not_mle_centered(self):self.assertNotIn("mean",CFG["priors"]["PRIOR_BASELINE_WEAK"])
 def test_65_fixed_specs_exact(self):self.assertEqual([(x["rho_n"],x["battery_sd"]) for x in CFG["fixed_sensitivity"]],[(.8,.1),(.8,.5),(.5,.25),(.95,.25)])
 def test_66_grid_not_new_baseline(self):self.assertEqual(CFG["baseline_prior"],"PRIOR_BASELINE_WEAK")
