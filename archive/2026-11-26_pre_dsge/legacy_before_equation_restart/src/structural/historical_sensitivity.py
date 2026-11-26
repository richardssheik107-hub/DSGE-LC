"""R1 historical-story sensitivity and three separate downstream gates.

Classification operates on *draw-level* window net contributions and absolute
activity shares.  It never infers sign certainty or dominant-driver probability
from marginal medians.  The thresholds are supplied by the pre-registered R1
configuration; this module neither changes the structural model nor reads data.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

import numpy as np


CLASSES = frozenset({"STABLE", "MODERATE", "HIGH", "AMBIGUOUS", "NOT_EVALUATED"})
REQUIRED_TECHNICAL_CHECKS = (
    "ARTIFACT_PROVENANCE",
    "REFERENCE_CONVERGENCE",
    "POSTERIOR_SUBSET",
    "KALMAN_RTS",
    "COVARIANCE_NUMERICS",
    "B_RANK",
    "SHOCK_RECONSTRUCTION",
    "DECOMPOSITION_IDENTITY",
    "SPOT_STATE_IDENTITY",
)


def _settings(config: Mapping) -> Mapping:
    settings = config.get("historical", config)
    required = (
        "dominant_driver_posterior_probability",
        "high_activity_share_change",
        "sign_interval_low",
        "sign_interval_high",
        "identity_absolute_tolerance",
    )
    absent = [key for key in required if key not in settings]
    if absent:
        raise ValueError(f"R1 historical thresholds missing: {absent}")
    probability = float(settings["dominant_driver_posterior_probability"])
    change = float(settings["high_activity_share_change"])
    low = float(settings["sign_interval_low"])
    high = float(settings["sign_interval_high"])
    tolerance = float(settings["identity_absolute_tolerance"])
    if not (0.5 < probability <= 1 and 0 < change < 1
            and 0 < low < 0.5 < high < 1 and tolerance >= 0
            and np.isfinite([probability, change, low, high, tolerance]).all()):
        raise ValueError("invalid R1 historical sensitivity thresholds")
    return settings


def _draw_matrix(value, shock_count: int) -> np.ndarray | None:
    if value is None:
        return None
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        return None
    if (array.ndim != 2 or array.shape[0] == 0 or array.shape[1] != shock_count
            or not np.isfinite(array).all()):
        return None
    return array


def _driver_probabilities(shares: np.ndarray, shocks: Sequence[str]) -> dict[str, float]:
    """Tied draws have no unique driver, so they add no label probability."""
    maxima = shares.max(axis=1, keepdims=True)
    leaders = shares == maxima
    unique = leaders.sum(axis=1) == 1
    indexes = np.argmax(shares[unique], axis=1)
    counts = np.bincount(indexes, minlength=len(shocks))
    return {name: float(counts[i] / len(shares)) for i, name in enumerate(shocks)}


def classify_historical_window(
    baseline_net,
    alternative_net,
    baseline_activity,
    alternative_activity,
    shocks: Sequence[str],
    config: Mapping,
    *,
    core_shocks: Sequence[str] | None = None,
) -> dict:
    """Classify one fixed window and return the evidence behind its label.

    Arrays are ``(draw, shock)`` and need not have equal draw counts across
    specifications.  ``core_shocks`` restricts the interval-reversal test to
    predeclared important shocks; when omitted all modeled shocks are in scope.
    """
    settings = _settings(config)
    shocks = tuple(shocks)
    if not shocks or len(set(shocks)) != len(shocks):
        raise ValueError("shock names must be nonempty and unique")
    core = tuple(shocks if core_shocks is None else core_shocks)
    if not core or not set(core).issubset(shocks):
        raise ValueError("core_shocks must be a nonempty subset of shocks")
    matrices = tuple(_draw_matrix(array, len(shocks)) for array in
                     (baseline_net, alternative_net, baseline_activity, alternative_activity))
    if any(array is None for array in matrices):
        return {"classification": "NOT_EVALUATED", "reason": "MISSING_OR_NONFINITE_DRAW_MATRIX",
                "evidence": []}
    base_net, alt_net, base_share, alt_share = matrices
    tolerance = float(settings["identity_absolute_tolerance"])
    for shares in (base_share, alt_share):
        if (np.any(shares < -tolerance) or np.any(shares > 1 + tolerance)
                or not np.allclose(shares.sum(axis=1), 1., rtol=0, atol=tolerance)):
            return {"classification": "NOT_EVALUATED", "reason": "INVALID_ACTIVITY_SHARE",
                    "evidence": []}

    low = float(settings["sign_interval_low"])
    high = float(settings["sign_interval_high"])
    base_q = np.quantile(base_net, [low, .5, high], axis=0)
    alt_q = np.quantile(alt_net, [low, .5, high], axis=0)
    base_mean_share = base_share.mean(axis=0)
    alt_mean_share = alt_share.mean(axis=0)
    share_change = np.abs(alt_mean_share - base_mean_share)
    base_prob = _driver_probabilities(base_share, shocks)
    alt_prob = _driver_probabilities(alt_share, shocks)
    base_driver = max(base_prob, key=base_prob.get)
    alt_driver = max(alt_prob, key=alt_prob.get)
    base_driver_prob = base_prob[base_driver]
    alt_driver_prob = alt_prob[alt_driver]
    concentration = float(settings["dominant_driver_posterior_probability"])
    large_share_change = float(settings["high_activity_share_change"])

    evidence = []
    opposite_interval_shocks = []
    uncertain_sign_flips = []
    for j, shock in enumerate(shocks):
        base_positive = base_q[0, j] > 0
        base_negative = base_q[2, j] < 0
        alt_positive = alt_q[0, j] > 0
        alt_negative = alt_q[2, j] < 0
        opposite = bool((base_positive and alt_negative) or (base_negative and alt_positive))
        base_median = float(base_q[1, j])
        alt_median = float(alt_q[1, j])
        sign_flip = bool(np.sign(base_median) != np.sign(alt_median))
        if opposite and shock in core:
            opposite_interval_shocks.append(shock)
        if sign_flip and not opposite:
            uncertain_sign_flips.append(shock)
        evidence.append({
            "shock": shock,
            "baseline_q_low": float(base_q[0, j]),
            "baseline_median": base_median,
            "baseline_q_high": float(base_q[2, j]),
            "alternative_q_low": float(alt_q[0, j]),
            "alternative_median": alt_median,
            "alternative_q_high": float(alt_q[2, j]),
            "baseline_mean_activity_share": float(base_mean_share[j]),
            "alternative_mean_activity_share": float(alt_mean_share[j]),
            "absolute_activity_share_change": float(share_change[j]),
            "opposite_sign_disjoint_intervals": opposite,
            "median_sign_flip": sign_flip,
            "baseline_driver_probability": base_prob[shock],
            "alternative_driver_probability": alt_prob[shock],
        })

    driver_replacement = bool(
        base_driver != alt_driver
        and base_driver_prob >= concentration
        and alt_driver_prob >= concentration
        and float(share_change.max()) > large_share_change
    )
    same_rank = tuple(np.argsort(-base_mean_share)) == tuple(np.argsort(-alt_mean_share))
    same_median_signs = not any(item["median_sign_flip"] for item in evidence)
    no_clear_driver = base_driver_prob < concentration and alt_driver_prob < concentration
    both_intervals_cross_zero = all(
        item["baseline_q_low"] <= 0 <= item["baseline_q_high"]
        and item["alternative_q_low"] <= 0 <= item["alternative_q_high"]
        for item in evidence
    )
    if opposite_interval_shocks or driver_replacement:
        classification = "HIGH"
    elif uncertain_sign_flips or no_clear_driver or both_intervals_cross_zero:
        classification = "AMBIGUOUS"
    elif same_rank and same_median_signs and float(share_change.max()) <= large_share_change:
        classification = "STABLE"
    else:
        classification = "MODERATE"
    return {
        "classification": classification,
        "reason": "EVALUATED",
        "evidence": evidence,
        "opposite_interval_shocks": opposite_interval_shocks,
        "dominant_driver_replacement_trigger": driver_replacement,
        "baseline_dominant_driver": base_driver,
        "baseline_dominant_driver_probability": base_driver_prob,
        "alternative_dominant_driver": alt_driver,
        "alternative_dominant_driver_probability": alt_driver_prob,
        "max_absolute_activity_share_change": float(share_change.max()),
        "unchanged_mean_activity_rank": bool(same_rank),
        "uncertain_median_sign_flips": uncertain_sign_flips,
        "baseline_draws": len(base_net),
        "alternative_draws": len(alt_net),
        "thresholds": {
            "dominant_driver_posterior_probability": concentration,
            "high_activity_share_change": large_share_change,
            "sign_interval_low": low,
            "sign_interval_high": high,
        },
    }


def evaluate_historical_gates(
    required_specifications: Sequence[str],
    required_windows: Sequence[str],
    checks_by_spec: Mapping[str, Mapping[str, object]],
    sensitivity_rows: Sequence[Mapping[str, object]],
    *,
    input_hashes_unchanged: bool,
) -> dict:
    """Do not promote incomplete calculations to ``READY``.

    All technical checks must be explicitly True or ``PASS`` for each required
    specification.  HIGH sensitivity is a valid result, not a numerical error;
    it blocks only an unqualified historical-stability interpretation.
    """
    specs = tuple(required_specifications)
    windows = tuple(required_windows)
    if (not specs or not windows or len(set(specs)) != len(specs)
            or len(set(windows)) != len(windows) or "BASELINE" not in specs):
        raise ValueError("required specifications/windows must be nonempty and unique")
    failures = []
    if input_hashes_unchanged is not True:
        failures.append("INPUT_HASH_CHANGED_OR_UNVERIFIED")
    for specification in specs:
        checks = checks_by_spec.get(specification, {})
        for name in REQUIRED_TECHNICAL_CHECKS:
            if checks.get(name) is not True and checks.get(name) != "PASS":
                failures.append(f"{specification}:{name}")

    expected_pairs = {(specification, window) for specification in specs
                      if specification != "BASELINE" for window in windows}
    counts = Counter()
    classes = []
    for row in sensitivity_rows:
        key = (row.get("specification"), row.get("window"))
        counts[key] += 1
        label = row.get("classification")
        if key not in expected_pairs or label not in CLASSES:
            failures.append(f"INVALID_SENSITIVITY_ROW:{key}")
        elif label == "NOT_EVALUATED":
            failures.append(f"SENSITIVITY_NOT_EVALUATED:{key}")
        else:
            classes.append(label)
    for key in sorted(expected_pairs):
        if counts[key] != 1:
            failures.append(f"SENSITIVITY_MISSING_OR_DUPLICATE:{key}:{counts[key]}")
    implementation_pass = not failures
    if not implementation_pass:
        sensitivity_status = "NOT_EVALUATED"
        interpretation = "BLOCKED"
    elif "HIGH" in classes:
        sensitivity_status = "HIGH"
        interpretation = "INTERPRETATION_REVIEW_REQUIRED"
    elif "AMBIGUOUS" in classes:
        sensitivity_status = "AMBIGUOUS"
        interpretation = "INTERPRETATION_REVIEW_REQUIRED"
    elif "MODERATE" in classes:
        sensitivity_status = "MODERATE"
        interpretation = "QUALIFIED_INTERPRETATION_ONLY"
    else:
        sensitivity_status = "STABLE"
        interpretation = "READY_FOR_STABILITY_CLAIM"
    return {
        "IMPLEMENTATION_VALIDITY": "PASS" if implementation_pass else "FAIL",
        "STATISTICAL_OR_ECONOMIC_SENSITIVITY": sensitivity_status,
        "DOWNSTREAM_INTERPRETATION_GATE": interpretation,
        "technical_ready": implementation_pass,
        "unqualified_stability_claim_ready": interpretation == "READY_FOR_STABILITY_CLAIM",
        "required_specifications": list(specs),
        "required_windows": list(windows),
        "failures": failures,
    }
