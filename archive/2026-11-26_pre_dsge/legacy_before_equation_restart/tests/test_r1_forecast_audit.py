"""R1-5 complete-key and order-independent forecast audits."""
import numpy as np
import pandas as pd
import pytest

from scripts.run_r1_forecast_audit import (
    MODELS, expected_grid, independent_metrics, key_audit,
    selected_histories_are_admissible,
)
from scripts.run_r1_external_validation import require_contiguous_months
from src.structural.parameter_transform import PARAMETER_ORDER


def _example():
    rows = []
    for origin, target, h, actual in (
        ("2023-12", "2024-01", 1, 100.),
        ("2024-01", "2024-02", 1, 120.),
        ("2024-01", "2024-04", 3, 130.),
    ):
        for i, model in enumerate(MODELS):
            rows.append({"model": model, "forecast_origin": origin,
                         "target_month": target, "horizon": h,
                         "actual_spot": actual, "forecast_spot": actual + i + 1,
                         "actual_log_change": .2,
                         "forecast_log_change": .1 + i / 100})
    return pd.DataFrame(rows)


def test_full_key_unique_actual_consistent_and_order_independent():
    frame = _example()
    audit, common = key_audit(frame, 1e-6)
    assert len(audit) == len(frame) == 15
    assert audit.status.eq("PASS").all()
    result = independent_metrics(common).sort_values(["model", "horizon"]).reset_index(drop=True)
    _, shuffled = key_audit(frame.sample(frac=1, random_state=9), 1e-6)
    changed_order = independent_metrics(shuffled).sort_values(["model", "horizon"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(result, changed_order)


def test_missing_duplicate_and_actual_mismatch_are_visible_not_silently_scored():
    frame = _example()
    key = frame.forecast_origin.eq("2023-12")
    missing = frame.drop(frame.index[key & frame.model.eq("STRUCTURAL_MAP_M0")])
    audit, common = key_audit(missing, 1e-6)
    assert (audit.status == "MISSING").sum() == 1
    assert len(common) == 10  # entire incomplete key excluded for every model

    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    audit, common = key_audit(duplicate, 1e-6)
    assert (audit.status == "DUPLICATE").sum() == 1
    assert len(common) == 10

    altered = frame.copy()
    altered.loc[altered.index[0], "actual_spot"] += .1
    audit, common = key_audit(altered, 1e-6)
    assert (audit.status == "ACTUAL_MISMATCH").sum() == len(MODELS)
    assert len(common) == 10


def test_same_target_and_horizon_different_origin_is_not_same_key():
    frame = _example()
    same_target = frame.iloc[:len(MODELS)].copy()
    same_target["forecast_origin"] = "2023-11"
    same_target["horizon"] = 2
    combined = pd.concat([frame, same_target], ignore_index=True)
    audit, common = key_audit(combined, 1e-6)
    assert len(audit) == 4 * len(MODELS)
    assert len(common) == len(combined)
    assert audit.status.eq("PASS").all()


def test_external_window_rejects_missing_or_duplicate_months():
    require_contiguous_months(["2022-10", "2022-11", "2022-12"], "2022-10", "2022-12", "cost")
    with pytest.raises(RuntimeError, match="unique contiguous"):
        require_contiguous_months(["2022-10", "2022-12", "2022-12"], "2022-10", "2022-12", "cost")


def test_entire_missing_key_and_common_wrong_actual_fail_expected_grid():
    frame = _example()
    expected = frame.drop_duplicates(["forecast_origin", "target_month", "horizon"])[
        ["forecast_origin", "target_month", "horizon", "actual_spot", "actual_log_change"]
    ].rename(columns={"actual_spot": "true_actual_spot",
                      "actual_log_change": "true_actual_log_change"})
    dropped = frame.loc[~frame.forecast_origin.eq("2023-12")]
    audit, common = key_audit(dropped, 1e-6, expected)
    assert (audit.status == "MISSING").sum() == len(MODELS)
    assert len(common) == 10

    wrong = frame.copy()
    wrong.loc[wrong.forecast_origin.eq("2023-12"), "actual_spot"] += 1.0
    audit, common = key_audit(wrong, 1e-6, expected)
    assert (audit.status == "PANEL_TRUTH_MISMATCH").sum() == len(MODELS)
    assert len(common) == 10


def test_configured_grid_detects_origin_missing_from_fit_and_all_forecasts():
    months = ["2023-12", "2024-01", "2024-02", "2024-03"]
    panel = pd.DataFrame({"month": months, "lc_spot": [10., 11., 12., 13.],
                          "lc_spot_log": np.log([10., 11., 12., 13.])})
    planned = expected_grid(panel, [1, 2], "2023-12")
    assert len(planned) == 5
    assert planned.forecast_origin.drop_duplicates().tolist() == months[:-1]
    fits = pd.DataFrame({"origin": ["2023-12"], "successful_starts": [2],
                         "valid_starts": [2], "objective": [1.],
                         "spectral_radius": [.5],
                         **{f"theta_{name}": [.5] for name in PARAMETER_ORDER}})
    origin = selected_histories_are_admissible(
        fits, 2, 2, {name: (0., 1.) for name in PARAMETER_ORDER}, months[:-1])
    assert origin.status.tolist() == ["PASS_ALL_STARTS_SUCCESS",
                                      "MISSING_FIT_DIAGNOSTIC", "MISSING_FIT_DIAGNOSTIC"]
    audit, common = key_audit(_example().iloc[0:0], 1e-6, planned)
    assert (audit.status == "MISSING").sum() == len(planned) * len(MODELS)
    assert common.empty
