"""Phase 2B acceptance tests 61-85: frozen data, M1 smoke and safety."""
from __future__ import annotations
import hashlib,inspect,json,subprocess,sys,unittest
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.kalman import kalman_filter,rts_smoother
from src.structural.measurement import build_measurements,load_frozen_panel
from src.structural.spec import baseline_parameters
from src.structural.state_space import diffuse_initialization,from_phase2a_parameters
A=json.loads((ROOT/"configs/phase2a.yaml").read_text());B=json.loads((ROOT/"configs/phase2b.yaml").read_text());P={**baseline_parameters(),**A["baseline"]};FRAME=load_frozen_panel(ROOT/"data/processed/phase1/monthly_structural_v1.csv");D=build_measurements(FRAME,"OBS_MIXED4");Y=D[["spot","ore_cost","output","battery"]].to_numpy();M=from_phase2a_parameters("M0_CORE5",P,.25);F=kalman_filter(M,Y);S=rts_smoother(M,F);OUT=ROOT/"outputs/phase2/phase2b"

class Phase2BRealDataTests(unittest.TestCase):
 def test_61_primary_n(self):self.assertEqual(len(D),57)
 def test_62_primary_start(self):self.assertEqual(D.month.iloc[0],"2021-01")
 def test_63_primary_end(self):self.assertEqual(D.month.iloc[-1],"2025-09")
 def test_64_no_future(self):self.assertFalse(D.month.gt("2025-09").any())
 def test_65_real_likelihood_finite(self):self.assertTrue(np.isfinite(F.loglik))
 def test_66_contribution_count(self):self.assertEqual(len(F.loglik_by_t),57)
 def test_67_real_filter_finite(self):self.assertTrue(np.isfinite(F.filtered_mean).all())
 def test_68_real_smoother_finite(self):self.assertTrue(np.isfinite(S.smoothed_mean).all())
 def test_69_rho_n_grid(self):
  self.assertTrue(all(kalman_filter(from_phase2a_parameters("M0_CORE5",{**P,"rho_n":v},.25),Y).status=="OK" for v in B["rho_n_grid"]))
 def test_70_battery_sd_grid(self):self.assertTrue(all(kalman_filter(from_phase2a_parameters("M0_CORE5",P,v),Y).status=="OK" for v in B["battery_sd_grid"]))
 def test_71_secondary_smoke(self):
  d=build_measurements(FRAME,"OBS_DLOG_MOY4");r=kalman_filter(M,d[["spot","ore_cost","output","battery"]].to_numpy());self.assertEqual((len(d),r.status),(68,"OK"))
 def test_72_m1_control_dimensions(self):self.assertEqual(from_phase2a_parameters("M1_CAPACITY6",P,.25).G.shape,(6,1))
 def test_73_control_enters_current_state(self):
  m=from_phase2a_parameters("M1_CAPACITY6",P,.25);y=np.full((1,4),np.nan);r=kalman_filter(m,y,initial_mean=np.zeros(6),initial_cov=np.eye(6),controls=np.array([[2.]]));self.assertTrue(np.allclose(r.predicted_mean[0],m.G[:,0]*2))
 def test_74_no_future_control(self):
  m=from_phase2a_parameters("M1_CAPACITY6",P,.25);u=np.zeros((2,1));u[1]=2;r=kalman_filter(m,np.full((2,4),np.nan),initial_mean=np.zeros(6),initial_cov=np.eye(6),controls=u);self.assertTrue(np.allclose(r.predicted_mean[0],0))
 def test_75_lag_not_applied_twice(self):
  m=from_phase2a_parameters("M1_CAPACITY6",P,.25);u=np.array([[1.]]);r=kalman_filter(m,np.full((1,4),np.nan),initial_mean=np.zeros(6),initial_cov=np.eye(6),controls=u);self.assertTrue(np.allclose(r.predicted_mean[0],m.G[:,0]))
 def test_76_m1_synthetic_finite(self):self.assertEqual(pd.read_csv(OUT/"m1_compatibility_smoke.csv").iloc[0].filter_status,"OK")
 def test_77_freeze_hash(self):self.assertEqual(hashlib.sha256((ROOT/"data/processed/core_monthly_panel.csv").read_bytes()).hexdigest(),A["data_freeze_sha256"])
 def test_78_excel_hashes(self):
  files={"动力电池行业数据库-20260819.xlsx":"e00614c96c88d3426ffe89fe75de60124d3efcec8430de06ed8d011a62c7aff9","【东吴电新数据库】锂电池材料价格周报-20260612.xlsx":"5dfd059c9224cf735bef5a4b544b43c560a756220fbf7ddaf42a17a4d38966a2"}
  for f,h in files.items():self.assertEqual(hashlib.sha256((ROOT/"data"/f).read_bytes()).hexdigest(),h)
 def test_79_no_v2_candidates(self):self.assertFalse(any("v2" in c.lower() or "candidate" in c.lower() for c in FRAME))
 def test_80_outputs_ignored(self):self.assertEqual(subprocess.run(["git","check-ignore","outputs/phase2/phase2b/kalman_realdata_summary.csv"],cwd=ROOT).returncode,0)
 def test_81_latent_states_not_committed(self):self.assertEqual(subprocess.check_output(["git","ls-files","outputs/phase2"],cwd=ROOT,text=True).strip(),"")
 def test_82_no_mcmc_package(self):
  config=(ROOT/"configs/phase2b.yaml").read_text().lower();self.assertNotIn("pymc",config);self.assertNotIn("stan",config)
  keys=set(B);self.assertTrue(keys.isdisjoint({"rho_d","rho_c","rho_q","rho_p","a_p","a_c","b_d","b_c","b_q","b_n","sigma_d","sigma_c","sigma_q","sigma_p"}))
 def test_83_no_optimizer_invoked(self):
  code="".join((ROOT/p).read_text() for p in ["src/structural/kalman.py","src/structural/likelihood.py","scripts/run_phase2b_kalman_validation.py"]);self.assertNotIn("minimize(",code);self.assertNotIn("optimize.",code)
 def test_84_phase2a_tests_present(self):self.assertEqual(len(list((ROOT/"tests").glob("test_phase2a_*.py"))),3)
 def test_85_phase1_tests_present(self):self.assertGreaterEqual(len(list((ROOT/"tests").glob("test_phase1*.py"))),3)
