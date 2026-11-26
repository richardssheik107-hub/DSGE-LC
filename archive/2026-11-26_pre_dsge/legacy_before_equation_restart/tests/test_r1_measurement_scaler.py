"""R1-4 measurement-scaler reconstruction and leakage guards."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.structural.measurement import build_measurements, load_frozen_panel
from src.structural.r1_measurement_scaler import (
    COMMON_SCALER_ID,
    LEGACY_SCALER_ID,
    assert_legacy_measurements_match_original,
    assert_oos_training_scaler_future_invariant,
    assert_posterior_measurement_binding,
    build_measurement_scaler,
    build_measurement_versions,
    compare_measurement_versions,
)


PANEL = Path(__file__).resolve().parents[1] / "data/processed/phase1/monthly_structural_v1.csv"


@pytest.fixture
def frozen_panel() -> pd.DataFrame:
    if not PANEL.exists():
        pytest.skip("locally frozen Phase 1 panel is not available")
    return load_frozen_panel(PANEL)


def test_frozen_legacy_exactly_reconstructs_original(frozen_panel):
    panel_hash = hashlib.sha256(PANEL.read_bytes()).hexdigest()
    legacy, common = build_measurement_versions(
        frozen_panel, source_panel_sha256=panel_hash, code_version="test-r1-4"
    )
    assert_legacy_measurements_match_original(frozen_panel, legacy)
    original = build_measurements(frozen_panel, "OBS_MIXED4")
    assert legacy.measurements.equals(original)
    assert len(legacy.measurements) == len(common.measurements) == 57
    assert legacy.measurements.month.iloc[0] == "2021-01"
    assert legacy.measurements.month.iloc[-1] == "2025-09"
    assert legacy.scaler_table.fit_n.tolist() == [68, 68, 57, 57]
    assert common.scaler_table.fit_n.tolist() == [57] * 4
    assert legacy.scaler_table.fit_start_month.tolist() == ["2020-02", "2020-02", "2021-01", "2021-01"]
    assert legacy.scaler_table.fit_end_month.tolist() == ["2025-09"] * 4
    assert legacy.scaler_table.ddof.tolist() == [1] * 4
    assert legacy.scaler_table.source_panel_sha256.tolist() == [panel_hash] * 4
    assert legacy.scaler_sha256 != common.scaler_sha256
    assert len(legacy.scaler_sha256) == len(common.scaler_sha256) == 64


def test_common_support_is_a_distinct_unestimated_contrast(frozen_panel):
    legacy, common = build_measurement_versions(frozen_panel)
    comparison = compare_measurement_versions(legacy, common).set_index("label")
    assert comparison.loc["spot", "max_abs_measurement_difference"] > 0.2
    assert comparison.loc["ore_cost", "max_abs_measurement_difference"] > 0.2
    assert np.isclose(comparison.loc["output", "max_abs_measurement_difference"], 0.0)
    assert np.isclose(comparison.loc["battery", "max_abs_measurement_difference"], 0.0)
    for label in ("spot", "ore_cost", "output", "battery"):
        assert abs(comparison.loc[label, "common_model_z_mean"]) < 1e-13
        assert np.isclose(comparison.loc[label, "common_model_z_sample_variance"], 1.0)
    legacy_binding = {
        "measurement_scaler_id": LEGACY_SCALER_ID,
        "scaler_sha256": legacy.scaler_sha256,
    }
    assert_posterior_measurement_binding(legacy_binding, legacy)
    with pytest.raises(ValueError, match="ID mismatch"):
        assert_posterior_measurement_binding(legacy_binding, common)
    with pytest.raises(ValueError, match="missing binding"):
        assert_posterior_measurement_binding({}, legacy)
    with pytest.raises(ValueError, match="hash mismatch"):
        assert_posterior_measurement_binding(
            {"measurement_scaler_id": COMMON_SCALER_ID, "scaler_sha256": legacy.scaler_sha256}, common
        )


def test_oos_training_scaler_is_immune_to_future_values(frozen_panel):
    origin_index = frozen_panel.index[frozen_panel.month.eq("2023-12")][0]
    changed = frozen_panel.copy(deep=True)
    future = changed.index > origin_index
    for column in (
        "lc_spot_dlog", "spodumene_cny_dlog",
        "lc_output_yoy_log", "battery_install_yoy_log",
    ):
        changed.loc[future, column] = 1e6
    assert_oos_training_scaler_future_invariant(frozen_panel, changed, origin_index)
    changed.loc[origin_index, "lc_spot_dlog"] = 1e6
    with pytest.raises(ValueError, match="at/before origin"):
        assert_oos_training_scaler_future_invariant(frozen_panel, changed, origin_index)


def test_scaler_rejects_invalid_version_and_missing_fields(frozen_panel):
    with pytest.raises(ValueError, match="unknown measurement scaler"):
        build_measurement_scaler(frozen_panel, "UNREGISTERED")
    with pytest.raises(ValueError, match="missing OBS_MIXED4"):
        build_measurement_scaler(frozen_panel.drop(columns="lc_spot_dlog"), LEGACY_SCALER_ID)


def test_equal_fit_moments_do_not_make_different_measurement_path_posterior_compatible(frozen_panel):
    panel_hash = hashlib.sha256(PANEL.read_bytes()).hexdigest()
    original = build_measurement_scaler(
        frozen_panel, LEGACY_SCALER_ID,
        source_panel_sha256=panel_hash, code_version="same-code",
    )
    changed = frozen_panel.copy(deep=True)
    positions = changed.index[changed.month.isin(["2021-01", "2021-02"])]
    assert len(positions) == 2
    first, second = positions.tolist()
    changed.loc[[first, second], "lc_spot_dlog"] = changed.loc[
        [second, first], "lc_spot_dlog"].to_numpy()
    moved = build_measurement_scaler(
        changed, LEGACY_SCALER_ID,
        source_panel_sha256=panel_hash, code_version="same-code",
    )
    assert original.scaler_table.set_index("label").loc["spot", "mean"] == moved.scaler_table.set_index("label").loc["spot", "mean"]
    assert original.scaler_table.set_index("label").loc["spot", "sample_sd"] == moved.scaler_table.set_index("label").loc["spot", "sample_sd"]
    assert original.measurement_sha256 != moved.measurement_sha256
    assert original.scaler_sha256 != moved.scaler_sha256
    with pytest.raises(ValueError, match="hash mismatch"):
        assert_posterior_measurement_binding(
            {"measurement_scaler_id": LEGACY_SCALER_ID,
             "scaler_sha256": original.scaler_sha256}, moved)
    with pytest.raises(ValueError, match="exactly 57 joint months"):
        build_measurement_scaler(frozen_panel.iloc[:-1], COMMON_SCALER_ID)
