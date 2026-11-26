"""Phase 2F frozen-data, scope and Git safety gates."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
P2A=json.loads((ROOT/"configs/phase2a.yaml").read_text())
P2F=json.loads((ROOT/"configs/phase2f.yaml").read_text())


def tracked_files():
    return subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True).splitlines()


def test_37_freeze_sha_unchanged():
    assert hashlib.sha256((ROOT/"data/processed/core_monthly_panel.csv").read_bytes()).hexdigest()==P2A["data_freeze_sha256"]


def test_38_measurement_sample_has_57_rows():
    panel=pd.read_csv(ROOT/"data/processed/phase1/monthly_structural_v1.csv")
    assert len(panel.loc[panel.month.between("2021-01","2025-09")])==57


def test_39_sample_end_is_2025_09():
    assert P2F["sample_end"]=="2025-09"


def test_40_no_data_freeze_v2_in_runner():
    source=(ROOT/"scripts/run_phase2f_historical_decomposition.py").read_text().lower()
    assert "core_monthly_panel_v2" not in source


def test_41_no_future_observations():
    assert P2F["sample_start"]=="2021-01" and max(end for _,end in P2F["historical_windows"].values())=="2025-09"


def test_42_no_commercial_raw_files_committed():
    assert not any(path.lower().endswith((".xlsx",".xls")) for path in tracked_files())


def test_43_no_raw_posterior_artifacts_committed():
    assert not any(path.lower().endswith((".npz",".npy",".pkl",".pickle")) for path in tracked_files())


def test_44_no_monthly_posterior_cube_committed():
    forbidden=("posterior_state_cube","posterior_shock_cube","posterior_contribution_cube")
    assert not any(any(token in path.lower() for token in forbidden) for path in tracked_files())


def test_windows_are_predeclared_exactly():
    assert P2F["historical_windows"]=={"RISE_2021_2022":["2021-02","2022-12"],"DECLINE_2023":["2023-01","2023-12"],"LATER_2024_2025":["2024-01","2025-09"]}


def test_no_new_estimation_calls_in_phase2f():
    source=(ROOT/"scripts/run_phase2f_historical_decomposition.py").read_text().lower()
    assert "posteriortarget" not in source and "run_adaptive_chain" not in source and "minimize(" not in source
