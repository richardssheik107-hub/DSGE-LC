"""Synthetic tests for the isolated R1 FEVD revision runner."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts.run_r1_fevd import (ROOT, covariance_identity_errors, draw_audit,
                                load_specs, validate_a01_tables)
from src.structural.fevd import structural_fevd
from src.structural.matrices import system_matrices
from src.structural.spec import baseline_parameters


def test_r1_specs_match_seven_frozen_posterior_targets():
    p2e = json.loads((ROOT / "configs/phase2e.yaml").read_text())
    p2d = json.loads((ROOT / "configs/phase2d.yaml").read_text())
    r1 = json.loads((ROOT / "configs/r1_revision.json").read_text())
    required = r1["historical"]["required_specifications"]
    specs = load_specs(p2e, p2d, required)
    assert list(specs) == required
    assert specs["BASELINE"]["rho_n"] == .8
    assert specs["BATTERY_SD_050"]["battery_sd"] == .5
    assert specs["RHO_N_095"]["rho_n"] == .95
    with pytest.raises(ValueError, match="do not match"):
        load_specs(p2e, p2d, required[:-1])


def test_r1_draw_audit_distinguishes_zero_variance_from_failure():
    parameters = baseline_parameters()
    A, B, _, _ = system_matrices("M0_CORE5", parameters)
    horizons = (1, 3, 6, 12, 24)
    shares, contributions = structural_fevd(A, B, horizons)
    covariance_errors = covariance_identity_errors(A, B, contributions, horizons)
    audit = draw_audit(shares, contributions, covariance_errors, 1e-10)
    assert audit["valid"]
    assert not audit["defined"][0, 3]
    assert audit["total"][0, 3] == 0
    assert audit["defined"][0, 4]
    assert np.max(covariance_errors) < 1e-10
    assert np.max(audit["sum_error"]) < 1e-10


def test_r1_draw_audit_rejects_false_zero_share_vector():
    parameters = baseline_parameters()
    A, B, _, _ = system_matrices("M0_CORE5", parameters)
    shares, contributions = structural_fevd(A, B, (1,))
    shares[0, 3] = 0
    covariance_errors = covariance_identity_errors(A, B, contributions, (1,))
    assert not draw_audit(shares, contributions, covariance_errors, 1e-10)["valid"]


def test_r1_a01_tables_reject_duplicate_specification():
    required = ["BASELINE", "RHO_N_050"]
    gate = pd.DataFrame({"specification": required, "A01_GATE": ["PASS", "PASS"]}).set_index("specification")
    integrity = pd.DataFrame({"specification": required}).set_index("specification")
    validate_a01_tables(gate, integrity, required)
    duplicated = pd.concat([gate, gate.iloc[[0]]])
    with pytest.raises(RuntimeError, match="duplicated"):
        validate_a01_tables(duplicated, integrity, required)
    with pytest.raises(RuntimeError, match="duplicated"):
        validate_a01_tables(gate, pd.concat([integrity, integrity.iloc[[0]]]), required)
