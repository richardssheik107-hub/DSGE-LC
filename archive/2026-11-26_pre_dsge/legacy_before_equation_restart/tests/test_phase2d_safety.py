"""Phase 2D repository, freeze and scope-safety tests 67-78."""
from __future__ import annotations
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));A=json.loads((ROOT/"configs/phase2a.yaml").read_text())
FILES=[ROOT/"src/structural/priors.py",ROOT/"src/structural/mcmc.py",ROOT/"src/structural/mcmc_diagnostics.py",ROOT/"src/structural/posterior_diagnostics.py",ROOT/"scripts/run_phase2d_bayesian_estimation.py"]
class Phase2DSafetyTests(unittest.TestCase):
 def _code(self):return "\n".join(p.read_text(encoding="utf-8") for p in FILES).lower()
 def test_67_freeze_hash(self):self.assertEqual(hashlib.sha256((ROOT/"data/processed/core_monthly_panel.csv").read_bytes()).hexdigest(),A["data_freeze_sha256"])
 def test_68_excel_hashes(self):
  expected={"动力电池行业数据库-20260819.xlsx":"e00614c96c88d3426ffe89fe75de60124d3efcec8430de06ed8d011a62c7aff9","【东吴电新数据库】锂电池材料价格周报-20260612.xlsx":"5dfd059c9224cf735bef5a4b544b43c560a756220fbf7ddaf42a17a4d38966a2"}
  for f,h in expected.items():self.assertEqual(hashlib.sha256((ROOT/"data"/f).read_bytes()).hexdigest(),h)
 def test_69_no_future_observation(self):self.assertNotIn("2025-10",self._code())
 def test_70_no_freeze_v2(self):self.assertNotIn("freeze v2",self._code())
 def test_71_no_m1_real_estimation(self):self.assertNotIn('"m1_capacity6"',self._code())
 def test_72_no_irf_invoked(self):self.assertNotIn("run_irf",self._code())
 def test_73_no_fevd_invoked(self):self.assertNotIn("run_fevd",self._code())
 def test_74_no_historical_decomposition(self):self.assertNotIn("historical_decomposition",self._code())
 def test_75_raw_draws_ignored(self):self.assertEqual(subprocess.run(["git","check-ignore","outputs/phase2/phase2d/baseline_posterior_draws.npz"],cwd=ROOT).returncode,0)
 def test_76_states_not_committed(self):self.assertFalse(any("phase2d" in p and "state" in p for p in subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True).splitlines()))
 def test_77_phase2c_test_suite_present(self):self.assertGreaterEqual(len(list((ROOT/"tests").glob("test_phase2c_*.py"))),5)
 def test_78_previous_suite_preserved(self):self.assertGreaterEqual(len(list((ROOT/"tests").glob("test_*.py"))),25)
