"""Phase 2C safety acceptance tests 69-81."""
from __future__ import annotations
import hashlib,inspect,json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
A=json.loads((ROOT/"configs/phase2a.yaml").read_text());FILES=[ROOT/"src/structural/estimation.py",ROOT/"src/structural/profiles.py",ROOT/"scripts/run_phase2c_estimation_preflight.py"]

class Phase2CSafetyTests(unittest.TestCase):
 def test_69_freeze_hash(self):self.assertEqual(hashlib.sha256((ROOT/"data/processed/core_monthly_panel.csv").read_bytes()).hexdigest(),A["data_freeze_sha256"])
 def test_70_excel_hashes(self):
  expected={"动力电池行业数据库-20260819.xlsx":"e00614c96c88d3426ffe89fe75de60124d3efcec8430de06ed8d011a62c7aff9","【东吴电新数据库】锂电池材料价格周报-20260612.xlsx":"5dfd059c9224cf735bef5a4b544b43c560a756220fbf7ddaf42a17a4d38966a2"}
  for f,h in expected.items():self.assertEqual(hashlib.sha256((ROOT/"data"/f).read_bytes()).hexdigest(),h)
 def _code(self):return "\n".join(p.read_text(encoding="utf-8") for p in FILES if p.exists()).lower()
 def test_71_no_future(self):self.assertNotIn("2025-10",self._code())
 def test_72_no_v2(self):self.assertNotIn("freeze v2",self._code())
 def test_73_no_m1_estimation(self):self.assertNotIn("m1_capacity6",self._code())
 def test_74_no_mcmc(self):self.assertNotIn("mcmc",self._code())
 def test_75_no_irf(self):self.assertNotIn("run_irf",self._code())
 def test_76_no_fevd(self):self.assertNotIn("run_fevd",self._code())
 def test_77_no_hd(self):self.assertNotIn("historical_decomposition",self._code())
 def test_78_outputs_ignored(self):self.assertEqual(subprocess.run(["git","check-ignore","outputs/phase2/phase2c/x.csv"],cwd=ROOT).returncode,0)
 def test_79_states_not_tracked(self):self.assertFalse(any("phase2c" in p and "state" in p for p in subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True).splitlines()))
 def test_80_phase2b_tests(self):self.assertGreaterEqual(len(list((ROOT/"tests").glob("test_phase2b_*.py"))),4)
 def test_81_prior_tests(self):self.assertGreaterEqual(len(list((ROOT/"tests").glob("test_phase1*.py"))),3)
