"""Phase 2E sensitivity helper tests 41-46."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.structural.structural_results import *
CFG=json.loads((ROOT/"configs/phase2e.yaml").read_text())
class Phase2EConsistencyTests(unittest.TestCase):
 def test_41_specs_separate(self):self.assertEqual(len(CFG["sensitivity_artifacts"]),6)
 def test_42_no_pooling(self):self.assertEqual(CFG["posterior_source"],"PHASE2D_BASELINE")
 def test_43_irf_shift(self):self.assertAlmostEqual(irf_shift_sd(1,1.5,.5),1)
 def test_44_fevd_change(self):self.assertAlmostEqual(fevd_share_change(.25,.47),.22)
 def test_45_sign_flip(self):self.assertTrue(sign_flip(1,-1))
 def test_46_seed_fixed(self):self.assertEqual(CFG["seed"],20260915)
