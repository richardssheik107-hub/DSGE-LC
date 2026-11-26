"""R1-4 audit of the frozen OBS_MIXED4 measurement scalers.

The common-support version is a *constructed, unestimated contrast*.  It must
not be combined with draws fitted to the legacy measurements.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

import numpy as np
import pandas as pd


LEGACY_SCALER_ID = "LEGACY_V1_PER_SERIES_SCALER"
COMMON_SCALER_ID = "COMMON_SUPPORT_57_SCALER"
MEASUREMENT_FIELDS = (
    ("spot", "lc_spot_dlog", "monthly_log_difference"),
    ("ore_cost", "spodumene_cny_dlog", "monthly_log_difference"),
    ("output", "lc_output_yoy_log", "year_on_year_log_difference"),
    ("battery", "battery_install_yoy_log", "year_on_year_log_difference"),
)
_LABELS = tuple(item[0] for item in MEASUREMENT_FIELDS)
_SOURCE_FIELDS = tuple(item[1] for item in MEASUREMENT_FIELDS)


@dataclass(frozen=True)
class MeasurementBuild:
    scaler_id: str
    measurements: pd.DataFrame
    scaler_table: pd.DataFrame
    scaler_sha256: str
    measurement_sha256: str


def _validate_panel(frame: pd.DataFrame) -> None:
    required = ("month", *_SOURCE_FIELDS)
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"missing OBS_MIXED4 fields: {missing}")
    if frame.empty or frame["month"].isna().any():
        raise ValueError("panel months must be nonempty and nonmissing")
    months = frame["month"].astype(str)
    if months.duplicated().any() or not months.is_monotonic_increasing:
        raise ValueError("panel months must be unique and increasing")
    if not months.str.fullmatch(r"\d{4}-(0[1-9]|1[0-2])").all():
        raise ValueError("panel months must use YYYY-MM")


def build_measurement_scaler(
    frame: pd.DataFrame,
    scaler_id: str,
    *,
    source_panel_sha256: str | None = None,
    code_version: str | None = None,
) -> MeasurementBuild:
    """Build a versioned scaler without changing the source frame.

    LEGACY fits each available raw series before complete-case intersection;
    COMMON first intersects the four raw series, then fits each one there.
    Input fields already contain the named log transforms; no new transform is
    applied here.  The sample standard deviation always has ``ddof=1``.
    """
    _validate_panel(frame)
    if scaler_id not in (LEGACY_SCALER_ID, COMMON_SCALER_ID):
        raise ValueError(f"unknown measurement scaler: {scaler_id}")
    if source_panel_sha256 is not None and (
        len(source_panel_sha256) != 64
        or any(c not in "0123456789abcdef" for c in source_panel_sha256.lower())
    ):
        raise ValueError("source_panel_sha256 must be a 64-digit hex digest")

    # Keep the original row index for precise parity with build_measurements.
    raw = {label: frame[column].astype(float) for label, column, _ in MEASUREMENT_FIELDS}
    common_mask = pd.concat(raw.values(), axis=1).notna().all(axis=1)
    model_months = frame.loc[common_mask, "month"].tolist()
    if len(model_months) < 2:
        raise ValueError("common support must contain at least two months")
    if scaler_id == COMMON_SCALER_ID and len(model_months) != 57:
        raise ValueError("COMMON_SUPPORT_57_SCALER requires exactly 57 joint months")

    result = pd.DataFrame({"month": frame["month"]})
    stats = []
    for label, column, transform in MEASUREMENT_FIELDS:
        fitting = raw[label] if scaler_id == LEGACY_SCALER_ID else raw[label].loc[common_mask]
        nonmissing = fitting.dropna()
        mu = float(fitting.mean())
        sd = float(fitting.std(ddof=1))
        if not np.isfinite(mu) or not np.isfinite(sd) or sd <= 0:
            raise ValueError(f"nonfinite or zero-variance scaler for {label}")
        result[label] = (raw[label] - mu) / sd
        fit_months = frame.loc[nonmissing.index, "month"]
        stats.append({
            "scaler_id": scaler_id,
            "label": label,
            "source_field": column,
            "source_transform": transform,
            "fit_start_month": str(fit_months.iloc[0]),
            "fit_end_month": str(fit_months.iloc[-1]),
            "fit_n": int(len(nonmissing)),
            "fit_missing_n": int(len(fitting) - len(nonmissing)),
            "mean": mu,
            "sample_sd": sd,
            "ddof": 1,
            "missing_handling": "skip_na_per_series_then_complete_case" if scaler_id == LEGACY_SCALER_ID else "complete_case_before_fitting",
            "model_start_month": str(model_months[0]),
            "model_end_month": str(model_months[-1]),
            "model_n": int(len(model_months)),
            "source_panel_sha256": source_panel_sha256,
            "code_version": code_version,
        })
    measurements = result.dropna().reset_index(drop=True)
    if measurements["month"].tolist() != model_months:
        raise AssertionError("model sample differs from the four-field intersection")
    values = np.asarray(measurements[list(_LABELS)].to_numpy(float), dtype="<f8")
    measurement_digest = hashlib.sha256(
        json.dumps(measurements["month"].astype(str).tolist(), separators=(",", ":")).encode("utf-8")
        + values.tobytes(order="C")
    ).hexdigest()
    table = pd.DataFrame(stats)
    table["measurement_sha256"] = measurement_digest
    hash_fields = (
        "scaler_id", "label", "source_field", "source_transform",
        "fit_start_month", "fit_end_month", "fit_n", "mean", "sample_sd",
        "ddof", "model_start_month", "model_end_month", "model_n",
    )
    payload = {
        "scaler_statistics": [{key: row[key] for key in hash_fields} for row in stats],
        "source_panel_sha256": source_panel_sha256,
        "code_version": code_version,
        "measurement_sha256": measurement_digest,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    return MeasurementBuild(scaler_id, measurements, table, digest, measurement_digest)


def build_measurement_versions(
    frame: pd.DataFrame, *, source_panel_sha256: str | None = None,
    code_version: str | None = None,
) -> tuple[MeasurementBuild, MeasurementBuild]:
    """Return (legacy, common-support) builds from the same frozen panel."""
    kwargs = {"source_panel_sha256": source_panel_sha256, "code_version": code_version}
    legacy = build_measurement_scaler(frame, LEGACY_SCALER_ID, **kwargs)
    common = build_measurement_scaler(frame, COMMON_SCALER_ID, **kwargs)
    if legacy.measurements["month"].tolist() != common.measurements["month"].tolist():
        raise AssertionError("scaler versions must have the same model months")
    if legacy.scaler_sha256 == common.scaler_sha256:
        raise AssertionError("distinct scaler versions unexpectedly share a digest")
    return legacy, common


def compare_measurement_versions(
    legacy: MeasurementBuild, common: MeasurementBuild,
) -> pd.DataFrame:
    """Compare fit statistics and standardized observations by series."""
    if legacy.scaler_id != LEGACY_SCALER_ID or common.scaler_id != COMMON_SCALER_ID:
        raise ValueError("expected legacy and common-support versions, respectively")
    if legacy.measurements["month"].tolist() != common.measurements["month"].tolist():
        raise ValueError("measurement versions have different model months")
    rows = []
    for label in _LABELS:
        a = legacy.scaler_table.set_index("label").loc[label]
        b = common.scaler_table.set_index("label").loc[label]
        x = legacy.measurements[label].to_numpy(float)
        y = common.measurements[label].to_numpy(float)
        rows.append({
            "label": label,
            "legacy_fit_n": int(a.fit_n), "common_fit_n": int(b.fit_n),
            "legacy_mean": float(a["mean"]), "common_mean": float(b["mean"]),
            "mean_change_common_minus_legacy": float(b["mean"] - a["mean"]),
            "legacy_sample_sd": float(a.sample_sd),
            "common_sample_sd": float(b.sample_sd),
            "sd_relative_change": float(b.sample_sd / a.sample_sd - 1.0),
            "legacy_model_z_mean": float(x.mean()),
            "common_model_z_mean": float(y.mean()),
            "legacy_model_z_sample_variance": float(x.var(ddof=1)),
            "common_model_z_sample_variance": float(y.var(ddof=1)),
            "max_abs_measurement_difference": float(np.max(np.abs(y - x))),
        })
    return pd.DataFrame(rows)


def assert_legacy_measurements_match_original(
    frame: pd.DataFrame, legacy: MeasurementBuild,
) -> None:
    """Require bit-exact parity with the original OBS_MIXED4 builder."""
    from .measurement import build_measurements

    if legacy.scaler_id != LEGACY_SCALER_ID:
        raise ValueError("only legacy measurements may be compared to original input")
    original = build_measurements(frame, "OBS_MIXED4")
    if original["month"].tolist() != legacy.measurements["month"].tolist():
        raise AssertionError("legacy model months do not match the original builder")
    if not np.array_equal(
        original[list(_LABELS)].to_numpy(float),
        legacy.measurements[list(_LABELS)].to_numpy(float),
    ):
        raise AssertionError("legacy measurement values do not match original builder")


def assert_posterior_measurement_binding(
    posterior_binding: Mapping[str, str], measurement: MeasurementBuild,
) -> None:
    """Reject an unbound posterior or any measurement version/hash mismatch.

    A legacy posterior requires an independently recorded binding containing
    both ``measurement_scaler_id`` and ``scaler_sha256``.  Merely relabelling
    common-support observations as legacy cannot pass this guard.
    """
    if posterior_binding.get("measurement_scaler_id") != measurement.scaler_id:
        raise ValueError("posterior/measurement scaler ID mismatch or missing binding")
    if posterior_binding.get("scaler_sha256") != measurement.scaler_sha256:
        raise ValueError("posterior/measurement scaler hash mismatch or missing binding")


def assert_oos_training_scaler_future_invariant(
    frame: pd.DataFrame, future_modified_frame: pd.DataFrame, origin_index: int,
) -> None:
    """Check that changes strictly after an OOS origin do not alter its scaler."""
    from .structural_forecasting import build_release_safe_training_measurements

    if len(frame) != len(future_modified_frame) or not 0 <= origin_index < len(frame):
        raise ValueError("frames must have equal length and a valid origin index")
    if not frame.iloc[:origin_index + 1].equals(future_modified_frame.iloc[:origin_index + 1]):
        raise ValueError("future_modified_frame changed observations at/before origin")
    y1, scaler1, months1 = build_release_safe_training_measurements(frame, origin_index)
    y2, scaler2, months2 = build_release_safe_training_measurements(future_modified_frame, origin_index)
    if months1 != months2 or not np.array_equal(y1, y2, equal_nan=True):
        raise AssertionError("OOS training measurements depend on future rows")
    if scaler1.mean != scaler2.mean or scaler1.sd != scaler2.sd:
        raise AssertionError("OOS training scaler depends on future rows")
