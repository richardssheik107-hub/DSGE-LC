"""Phase 2E-R posterior artifact persistence and recovery safety tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.structural.parameter_transform import PARAMETER_ORDER, load_phase2a_bounds
from src.structural.posterior_artifacts import (load_posterior_artifact,
    metadata_path, save_posterior_artifact)

ROOT = Path(__file__).resolve().parents[1]


def toy_results(draws=5):
    results = []
    for chain in range(4):
        theta = np.tile(np.array([.5] * 10 + [.3] * 4), (draws, 1))
        components = np.zeros((draws, 5)); components[:, 4] = .8
        results.append({"theta": theta, "z": np.zeros_like(theta),
                        "components": components, "accepted": np.ones(draws, bool)})
    return results


def test_saver_preserves_shape_and_metadata_roundtrip(tmp_path):
    path = tmp_path / "draws.npz"
    saved = save_posterior_artifact(path, toy_results(), specification="BATTERY_SD_050",
        rho_n=.8, battery_sd=.5, seed=20260915)
    arrays, loaded = load_posterior_artifact(path, expected_specification="BATTERY_SD_050",
        expected_rho_n=.8, expected_battery_sd=.5,
        bounds=load_phase2a_bounds(ROOT / "configs/phase2a.yaml"))
    assert arrays["theta"].shape == (4, 5, 14)
    assert tuple(loaded["parameter_order"]) == PARAMETER_ORDER
    assert loaded["production_draws_per_chain"] == 5
    assert loaded["artifact_sha256"] == saved["artifact_sha256"]
    assert json.loads(metadata_path(path).read_text())["seed"] == 20260915


def test_existing_artifact_not_overwritten_by_default(tmp_path):
    path = tmp_path / "draws.npz"
    save_posterior_artifact(path, toy_results(), specification="RHO_N_050",
        rho_n=.5, battery_sd=.25, seed=20260915)
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        save_posterior_artifact(path, toy_results(6), specification="RHO_N_050",
            rho_n=.5, battery_sd=.25, seed=20260915)
    assert path.read_bytes() == before


def test_parameter_order_and_assumption_metadata_are_exact(tmp_path):
    path = tmp_path / "draws.npz"
    save_posterior_artifact(path, toy_results(), specification="RHO_N_095",
        rho_n=.95, battery_sd=.25, seed=20260915)
    with pytest.raises(ValueError, match="rho_n"):
        load_posterior_artifact(path, expected_specification="RHO_N_095",
            expected_rho_n=.8, expected_battery_sd=.25)


def test_phase2d_future_runner_persists_every_sensitivity():
    source = (ROOT / "scripts/run_phase2d_bayesian_estimation.py").read_text()
    assert source.count("save_posterior_artifact") >= 3
    assert "label.lower()+\"_posterior_draws.npz\"" in source
    assert "item[\"name\"].lower()+\"_posterior_draws.npz\"" in source


def test_recovery_mode_never_calls_baseline_chain():
    source = (ROOT / "scripts/recover_phase2d_sensitivity_artifacts.py").read_text()
    assert "baseline_posterior_draws.npz" not in source
    assert "--all-missing" in source and "--force" in source
    assert "cfg[\"seed\"]" in source
