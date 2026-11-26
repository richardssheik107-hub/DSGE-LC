import hashlib
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from src.futures.spot_futures import (
    basis_inventory_summary,
    build_monthly_spot_futures,
    lead_lag_correlations,
    reconcile_canonical_daily_spot,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE_HASH = "9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5"


def test_canonical_daily_spot_reconciles_exactly_and_is_not_modified():
    daily_path = ROOT / "data/interim/industry/lc_spot_daily.csv"
    before = hashlib.sha256(daily_path.read_bytes()).hexdigest()
    _, reconciliation, audit = reconcile_canonical_daily_spot(
        daily_path,
        ROOT / "data/processed/core_monthly_panel.csv",
        sample_end="2025-09",
        absolute_tolerance=1e-6,
    )
    after = hashlib.sha256(daily_path.read_bytes()).hexdigest()
    assert before == after
    assert audit["status"] == "PASS"
    assert len(reconciliation) == 69
    assert reconciliation.absolute_difference.max() <= 1e-6


def test_monthly_basis_formula_and_roll_safe_return_passthrough(tmp_path):
    freeze = tmp_path / "freeze.csv"
    pd.DataFrame({"month": ["2023-07", "2023-08"], "lc_spot": [100.0, 110.0]}).to_csv(freeze, index=False)
    futures = pd.DataFrame({
        "month": ["2023-07", "2023-08"],
        "mean_main_close": [105.0, 99.0],
        "month_end_main_close": [106.0, 100.0],
        "monthly_roll_safe_log_return": [0.01, -0.02],
        "monthly_volume": [10.0, 11.0],
        "main_contract_at_month_end": ["LC2401", "LC2402"],
        "switch_count": [0, 1],
    })
    daily = pd.DataFrame({
        "date": pd.to_datetime(["2023-07-31", "2023-08-31"]),
        "lc_spot": [102.0, 100.0],
    })
    aligned = build_monthly_spot_futures(freeze, futures, start_month="2023-07", end_month="2023-08", canonical_daily_spot=daily)
    assert np.allclose(aligned.basis_mean_pct, [0.05, -0.10])
    assert np.allclose(aligned.basis_month_end_pct, [106 / 102 - 1, 0.0])
    assert np.allclose(aligned.futures_monthly_return, [0.01, -0.02])


def test_lead_lag_positive_convention_detects_futures_lead():
    futures = pd.Series([1.0, -1.0, 2.0, -2.0, 3.0, -3.0, 4.0])
    spot = futures.shift(1)
    table = lead_lag_correlations(futures, spot, [-1, 0, 1], frequency="synthetic")
    best = table.loc[table.pearson.idxmax()]
    assert best.lag_spot_periods == 1
    assert np.isclose(best.pearson, 1.0)


def test_basis_inventory_lag_convention_and_sensitivity_shape():
    months = ["2023-01", "2023-02", "2023-03", "2023-04", "2023-05"]
    paths = np.array([[1, 2, 3, 4, 5], [2, 4, 6, 8, 10]], dtype=float)
    monthly = pd.DataFrame({"month": months, "basis_mean_pct": [0.0, 1, 2, 3, 4]})
    table = basis_inventory_summary({"BASELINE": (paths, months)}, monthly, lags=[0])
    assert set(table.statistic) == {"pearson", "spearman"}
    assert np.allclose(table["median"], 1.0)
    assert set(table.lag_convention) == {"positive=inventory_state_t_vs_basis_t_plus_lag"}


def test_freeze_hash_and_no_futures_raw_are_tracked():
    actual = hashlib.sha256((ROOT / "data/processed/core_monthly_panel.csv").read_bytes()).hexdigest()
    assert actual == FREEZE_HASH
    tracked = subprocess.run(
        ["git", "ls-files", "--", "*LC[0-9][0-9][0-9][0-9].csv"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tracked == ""
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert not any(Path(name).name.upper().startswith("LC") and Path(name).suffix.lower() == ".csv" for name in staged)
