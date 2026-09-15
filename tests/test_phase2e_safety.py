"""Phase 2E data and scope safety tests 47-60."""
from __future__ import annotations
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));A=json.loads((ROOT/"configs/phase2a.yaml").read_text());FILES=[ROOT/"scripts/run_phase2e_irf_fevd.py",ROOT/"src/structural/irf.py",ROOT/"src/structural/fevd.py",ROOT/"src/structural/structural_results.py"]
class Phase2ESafetyTests(unittest.TestCase):
 def _code(self):return "\n".join(x.read_text(encoding="utf-8").lower() for x in FILES)
 def test_47_freeze(self):self.assertEqual(hashlib.sha256((ROOT/"data/processed/core_monthly_panel.csv").read_bytes()).hexdigest(),A["data_freeze_sha256"])
 def test_48_obs_spec(self):self.assertEqual(A["primary_measurement"],"OBS_MIXED4")
 def test_49_n57(self):self.assertIn("(4,18000,14)",self._code().replace(" ",""))
 def test_50_end_month(self):self.assertEqual(A["sample_end"],"2025-09")
 def test_51_no_v2(self):self.assertNotIn("core_monthly_panel_v2",self._code())
 def test_52_no_future(self):self.assertNotIn("2025-10",self._code())
 def test_53_no_commercial_tracked(self):self.assertFalse(any(x.endswith(".xlsx") for x in subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True).splitlines()))
 def test_54_raw_posterior_ignored(self):self.assertEqual(subprocess.run(["git","check-ignore","outputs/phase2/phase2d/baseline_posterior_draws.npz"],cwd=ROOT).returncode,0)
 def test_55_no_monthly_state_commit(self):self.assertNotIn("monthly_state",self._code())
 def test_56_no_hd(self):self.assertNotIn("historical_decomposition(",self._code())
 def test_57_no_smoother(self):self.assertNotIn("smoother",self._code())
 def test_58_no_forecast(self):self.assertNotIn("structural_forecast(",self._code())
 def test_59_no_m1(self):self.assertNotIn("m1_capacity6",self._code())
 def test_60_no_futures(self):self.assertNotIn("futures_estimation",self._code())
