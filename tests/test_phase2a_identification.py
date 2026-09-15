"""Phase 2A acceptance tests 35-46 and 54-60."""
from __future__ import annotations
import hashlib, json, subprocess, sys, unittest
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.structural.identification import jacobian_metrics, moment_vector, numerical_jacobian, stationary_covariance, weak_pairs
from src.structural.matrices import system_matrices
from src.structural.measurement import build_measurements, load_frozen_panel
from src.structural.observability import block_matrix, observability_metrics
from src.structural.spec import baseline_parameters, parameter_registry
P=baseline_parameters(); CFG=json.loads((ROOT/"configs/phase2a.yaml").read_text()); PANEL=ROOT/"data/processed/phase1/monthly_structural_v1.csv"; FREEZE=ROOT/"data/processed/core_monthly_panel.csv"

class IdentificationAndSafetyTests(unittest.TestCase):
    def test_35_m0_observability_dimensions(self):
        A,_,_,H=system_matrices("M0_CORE5",P); self.assertEqual(block_matrix(A,H).shape,(20,5))
    def test_36_m1_observability_dimensions(self):
        A,_,_,H=system_matrices("M1_CAPACITY6",P); self.assertEqual(block_matrix(A,H).shape,(24,6))
    def test_37_rank_deterministic(self):
        A,_,_,H=system_matrices("M0_CORE5",P); self.assertEqual(observability_metrics(A,H),observability_metrics(A,H))
    def test_38_inventory_rank_falls_b_n_zero(self):
        p=dict(P); p["b_n"]=0; A,_,_,H=system_matrices("M0_CORE5",p); self.assertEqual(observability_metrics(A,H)["rank"],4)
    def test_39_demand_scale_fixed(self):
        H=system_matrices("M0_CORE5",P)[3]; self.assertEqual(H[3,0],1)
    def test_40_capacity_scale_fixed(self): self.assertTrue(any(r["parameter"]=="capacity_output_loading" and r["status"]=="fixed:+1" for r in parameter_registry()))
    def test_41_moment_vector_finite(self): self.assertTrue(np.isfinite(moment_vector("M0_CORE5",P)).all())
    def test_42_lyapunov_symmetric(self):
        A,B,_,_=system_matrices("M0_CORE5",P); Q=stationary_covariance(A,B); self.assertTrue(np.allclose(Q,Q.T))
    def test_43_lyapunov_psd(self):
        A,B,_,_=system_matrices("M0_CORE5",P); self.assertGreaterEqual(np.linalg.eigvalsh(stationary_covariance(A,B)).min(),-1e-10)
    def test_44_jacobian_dimensions(self):
        J,n=numerical_jacobian("M0_CORE5",P); self.assertEqual(J.shape,(58,len(n)))
    def test_45_rank_duplicate_sensitivity(self):
        J=np.column_stack([np.arange(4),np.arange(4)]); self.assertEqual(jacobian_metrics(J)["rank"],1)
    def test_46_weak_pair_detector(self):
        J=np.column_stack([np.arange(1,5),2*np.arange(1,5)]); self.assertEqual(len(weak_pairs(J,("a","b"))),1)
    def test_54_freeze_hash(self): self.assertEqual(hashlib.sha256(FREEZE.read_bytes()).hexdigest(),CFG["data_freeze_sha256"])
    def test_55_no_future_empirical_transform(self):
        frame=load_frozen_panel(PANEL); self.assertLessEqual(frame.month.max(),"2025-09")
    def test_56_no_v2_candidates_used(self):
        frame=load_frozen_panel(PANEL); self.assertFalse(any("v2" in c.lower() or "candidate" in c.lower() for c in frame))
    def test_57_commercial_histories_not_committed(self):
        tracked=subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True).splitlines(); self.assertFalse(any("data/raw/commercial" in p or p.lower().endswith(".xlsx") for p in tracked))
    def test_58_phase2_outputs_ignored(self):
        result=subprocess.run(["git","check-ignore","outputs/phase2/phase2a/model_spec_summary.csv"],cwd=ROOT,capture_output=True,text=True); self.assertEqual(result.returncode,0)
    def test_59_original_excel_hashes(self):
        expected={"动力电池行业数据库-20260819.xlsx":"e00614c96c88d3426ffe89fe75de60124d3efcec8430de06ed8d011a62c7aff9","【东吴电新数据库】锂电池材料价格周报-20260612.xlsx":"5dfd059c9224cf735bef5a4b544b43c560a756220fbf7ddaf42a17a4d38966a2"}
        for name,digest in expected.items(): self.assertEqual(hashlib.sha256((ROOT/"data"/name).read_bytes()).hexdigest(),digest)
    def test_60_phase1_assets_remain(self): self.assertTrue((ROOT/"tests/test_phase1b_baselines.py").exists() and (ROOT/"outputs/phase1/baseline_results/baseline_metrics.csv").exists())
