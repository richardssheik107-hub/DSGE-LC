"""Deterministically replay only missing Phase 2D sensitivity posterior artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_phase2d_bayesian_estimation import (initial_points, load_phase2c_modes,
    proposal_preconditioner, run_chains, spec_outputs)
from src.structural.mcmc import PosteriorTarget
from src.structural.measurement import build_measurements, load_frozen_panel
from src.structural.parameter_transform import PARAMETER_ORDER, ParameterTransform, load_phase2a_bounds
from src.structural.posterior_artifacts import load_posterior_artifact, save_posterior_artifact
from src.structural.priors import prior_specs

OUT = ROOT / "outputs/phase2/phase2d"
FREEZE = ROOT / "data/processed/core_monthly_panel.csv"
PANEL = ROOT / "data/processed/phase1/monthly_structural_v1.csv"
EXPECTED_DRAWS = {
    "PRIOR_FLAT_BOUNDED": 48000,
    "PRIOR_MODERATE_SHRINK": 18000,
    "BATTERY_SD_010": 42000,
    "BATTERY_SD_050": 18000,
    "RHO_N_050": 24000,
    "RHO_N_095": 36000,
}
FILENAMES = {name: name.lower() + "_posterior_draws.npz" for name in EXPECTED_DRAWS}


def specification_table(cfg):
    rows = {
        "PRIOR_FLAT_BOUNDED": ("PRIOR_FLAT_BOUNDED", cfg["rho_n_fixed"], cfg["battery_sd_fixed"]),
        "PRIOR_MODERATE_SHRINK": ("PRIOR_MODERATE_SHRINK", cfg["rho_n_fixed"], cfg["battery_sd_fixed"]),
    }
    for item in cfg["fixed_sensitivity"]:
        rows[item["name"]] = (cfg["baseline_prior"], item["rho_n"], item["battery_sd"])
    return rows


def recorded_summary(name):
    filename = "prior_sensitivity_summary.csv" if name.startswith("PRIOR_") else "fixed_assumption_sensitivity.csv"
    frame = pd.read_csv(OUT / filename)
    return frame.loc[frame.specification.eq(name)].set_index("parameter")


def replay_one(name, cfg, workers, force=False):
    p2a = json.loads((ROOT / "configs/phase2a.yaml").read_text())
    bounds = load_phase2a_bounds(ROOT / "configs/phase2a.yaml")
    transform = ParameterTransform.full(bounds)
    specs = prior_specs(cfg)
    prior_name, rho_n, battery_sd = specification_table(cfg)[name]
    path = OUT / FILENAMES[name]
    if path.exists() and not force:
        arrays, metadata = load_posterior_artifact(path, expected_specification=name,
            expected_rho_n=rho_n, expected_battery_sd=battery_sd, bounds=bounds)
        return {"specification": name, "source": "EXISTING", "chains": 4,
                "draws_per_chain": arrays["theta"].shape[1], "max_rhat": np.nan,
                "min_bulk_ess": np.nan, "min_tail_ess": np.nan,
                "replay_shift_error": np.nan, "artifact_sha256": metadata["artifact_sha256"],
                "status": "PASS"}
    frame = load_frozen_panel(PANEL, p2a["sample_end"])
    measure = build_measurements(frame, cfg["measurement"])
    if len(measure) != 57 or measure.month.iloc[0] != "2021-01" or measure.month.iloc[-1] != "2025-09":
        raise RuntimeError("sample mismatch")
    y = measure[["spot", "ore_cost", "output", "battery"]].to_numpy()
    mle, map_theta = load_phase2c_modes()
    starts = initial_points(transform, mle["theta"], map_theta, specs[cfg["baseline_prior"]], bounds, cfg)
    target = PosteriorTarget(transform, y, specs[prior_name], rho_n, battery_sd, cfg["numerical_guard_abs_z"])
    results, diagnostics, passed = run_chains(target, starts, cfg, workers, label=name,
        initial_chol=proposal_preconditioner(target, starts[0]))
    theta, _, summary, _, _ = spec_outputs(results, diagnostics, bounds, cfg)
    recorded = recorded_summary(name)
    baseline = pd.read_csv(OUT / "baseline_posterior_summary.csv").set_index("parameter")
    replay_error = max(abs((row["median"] - recorded.loc[row["parameter"], "sensitivity_median"])
                           / baseline.loc[row["parameter"], "sd"]) for row in summary)
    stopping_match = theta.shape[1] == EXPECTED_DRAWS[name]
    status = "PASS" if passed and replay_error <= .10 else "FAIL"
    metadata = save_posterior_artifact(path, results, specification=name, rho_n=rho_n,
        battery_sd=battery_sd, seed=cfg["seed"], force=force)
    load_posterior_artifact(path, expected_specification=name, expected_rho_n=rho_n,
        expected_battery_sd=battery_sd, bounds=bounds)
    return {"specification": name, "source": "DETERMINISTIC_REPLAY", "chains": 4,
            "draws_per_chain": theta.shape[1], "expected_draws_per_chain": EXPECTED_DRAWS[name],
            "stopping_count_match": stopping_match,
            "max_rhat": max(x["rhat"] for x in diagnostics),
            "min_bulk_ess": min(x["bulk_ess"] for x in diagnostics),
            "min_tail_ess": min(x["tail_ess"] for x in diagnostics),
            "replay_shift_error": replay_error, "artifact_sha256": metadata["artifact_sha256"],
            "status": status}


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--specification", choices=tuple(EXPECTED_DRAWS))
    group.add_argument("--all-missing", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    cfg = json.loads((ROOT / "configs/phase2d.yaml").read_text())
    expected = json.loads((ROOT / "configs/phase2a.yaml").read_text())["data_freeze_sha256"]
    before = hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    if before != expected:
        raise RuntimeError("Data Freeze mismatch")
    names = list(EXPECTED_DRAWS) if args.all_missing else [args.specification]
    rows = []
    audit_path = OUT / "sensitivity_artifact_recovery_audit.csv"
    if audit_path.exists():
        rows = pd.read_csv(audit_path).to_dict("records")
    for name in names:
        rows = [row for row in rows if row["specification"] != name]
        row = replay_one(name, cfg, args.workers, args.force)
        rows.append(row)
        pd.DataFrame(rows).sort_values("specification").to_csv(audit_path, index=False)
        print(json.dumps(row, indent=2), flush=True)
        if row["status"] != "PASS":
            raise SystemExit(f"SENSITIVITY_REPLAY_MISMATCH: {name}")
    if hashlib.sha256(FREEZE.read_bytes()).hexdigest() != before:
        raise RuntimeError("Data Freeze changed")


if __name__ == "__main__":
    main()
