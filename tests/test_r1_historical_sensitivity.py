"""Prespecified R1 story-classification and downstream-gate counterexamples."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.structural.historical_sensitivity import (
    REQUIRED_TECHNICAL_CHECKS,
    classify_historical_window,
    evaluate_historical_gates,
)


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = json.loads((ROOT / "configs/r1_revision.json").read_text())['historical']
SHOCKS = ('demand', 'cost', 'supply', 'price')
WINDOWS = ('RISE_2021_2022', 'DECLINE_2023', 'LATER_2024_2025')
SPECS = tuple(HISTORICAL['required_specifications'])


def _net(seed=1, draws=1000):
    rng = np.random.default_rng(seed)
    return rng.normal(loc=[1., -.8, .6, .4], scale=.05, size=(draws, 4))


def _shares(values, draws=1000):
    return np.tile(np.asarray(values, dtype=float), (draws, 1))


def _complete_gate_inputs():
    checks = {spec: {key: True for key in REQUIRED_TECHNICAL_CHECKS}
              for spec in SPECS}
    rows = [{'specification': spec, 'window': window, 'classification': 'STABLE'}
            for spec in SPECS if spec != 'BASELINE' for window in WINDOWS]
    return checks, rows


def test_disjoint_opposite_sign_90pct_intervals_trigger_high():
    baseline = _net()
    alternative = _net(2)
    alternative[:, 0] *= -1
    share = _shares([.5, .2, .2, .1])
    result = classify_historical_window(baseline, alternative, share, share,
                                        SHOCKS, HISTORICAL)
    assert result['classification'] == 'HIGH'
    assert result['opposite_interval_shocks'] == ['demand']
    item = result['evidence'][0]
    assert item['baseline_q_low'] > 0 > item['alternative_q_high']
    assert item['opposite_sign_disjoint_intervals']


def test_dominant_driver_replacement_with_large_share_change_triggers_high():
    net = _net()
    baseline = _shares([.7, .1, .1, .1])
    alternative = _shares([.1, .7, .1, .1])
    result = classify_historical_window(net, net, baseline, alternative,
                                        SHOCKS, HISTORICAL)
    assert result['classification'] == 'HIGH'
    assert result['dominant_driver_replacement_trigger']
    assert result['baseline_dominant_driver_probability'] == 1.
    assert result['alternative_dominant_driver_probability'] == 1.
    assert result['max_absolute_activity_share_change'] > HISTORICAL['high_activity_share_change']


def test_near_zero_median_sign_flip_without_interval_separation_is_not_high():
    rng = np.random.default_rng(41)
    baseline = _net()
    alternative = baseline.copy()
    baseline[:, 0] = rng.normal(loc=.01, scale=.2, size=len(baseline))
    alternative[:, 0] = rng.normal(loc=-.01, scale=.2, size=len(alternative))
    share = _shares([.5, .2, .2, .1])
    result = classify_historical_window(baseline, alternative, share, share,
                                        SHOCKS, HISTORICAL)
    assert result['classification'] == 'AMBIGUOUS'
    assert result['evidence'][0]['median_sign_flip']
    assert not result['evidence'][0]['opposite_sign_disjoint_intervals']
    assert not result['dominant_driver_replacement_trigger']


def test_stable_and_moderate_are_distinct_from_high():
    net = _net()
    stable_share = _shares([.4, .3, .2, .1])
    stable = classify_historical_window(net, net + .01, stable_share, stable_share,
                                        SHOCKS, HISTORICAL)
    assert stable['classification'] == 'STABLE'
    alternate_share = _shares([.3, .4, .2, .1])
    moderate = classify_historical_window(net, net + .01, stable_share,
                                          alternate_share, SHOCKS, HISTORICAL)
    assert moderate['classification'] == 'MODERATE'
    assert not moderate['dominant_driver_replacement_trigger']


def test_missing_or_invalid_draws_are_not_evaluated():
    net = _net()
    share = _shares([.4, .3, .2, .1])
    missing = classify_historical_window(net, None, share, share, SHOCKS, HISTORICAL)
    assert missing['classification'] == 'NOT_EVALUATED'
    invalid_share = share.copy()
    invalid_share[0] = 0
    invalid = classify_historical_window(net, net, share, invalid_share,
                                         SHOCKS, HISTORICAL)
    assert invalid['classification'] == 'NOT_EVALUATED'


def test_core_shock_scope_is_explicit():
    net = _net()
    other = net.copy()
    other[:, 0] *= -1
    share = _shares([.4, .3, .2, .1])
    result = classify_historical_window(net, other, share, share, SHOCKS,
                                        HISTORICAL, core_shocks=('cost',))
    assert result['classification'] != 'HIGH'
    assert result['opposite_interval_shocks'] == []
    with pytest.raises(ValueError):
        classify_historical_window(net, other, share, share, SHOCKS,
                                   HISTORICAL, core_shocks=('unmodeled',))


def test_all_complete_stable_is_ready():
    checks, rows = _complete_gate_inputs()
    result = evaluate_historical_gates(SPECS, WINDOWS, checks, rows,
                                       input_hashes_unchanged=True)
    assert result['IMPLEMENTATION_VALIDITY'] == 'PASS'
    assert result['STATISTICAL_OR_ECONOMIC_SENSITIVITY'] == 'STABLE'
    assert result['DOWNSTREAM_INTERPRETATION_GATE'] == 'READY_FOR_STABILITY_CLAIM'
    assert result['technical_ready'] and result['unqualified_stability_claim_ready']


def test_high_sensitivity_preserves_technical_pass_but_requires_review():
    checks, rows = _complete_gate_inputs()
    rows[0]['classification'] = 'HIGH'
    result = evaluate_historical_gates(SPECS, WINDOWS, checks, rows,
                                       input_hashes_unchanged=True)
    assert result['IMPLEMENTATION_VALIDITY'] == 'PASS'
    assert result['STATISTICAL_OR_ECONOMIC_SENSITIVITY'] == 'HIGH'
    assert result['DOWNSTREAM_INTERPRETATION_GATE'] == 'INTERPRETATION_REVIEW_REQUIRED'
    assert result['technical_ready'] and not result['unqualified_stability_claim_ready']


def test_missing_specification_or_window_and_empty_table_cannot_ready():
    checks, rows = _complete_gate_inputs()
    checks.pop('RHO_N_095')
    result = evaluate_historical_gates(SPECS, WINDOWS, checks, rows,
                                       input_hashes_unchanged=True)
    assert result['IMPLEMENTATION_VALIDITY'] == 'FAIL'
    assert not result['technical_ready']
    checks, rows = _complete_gate_inputs()
    rows.pop()
    result = evaluate_historical_gates(SPECS, WINDOWS, checks, rows,
                                       input_hashes_unchanged=True)
    assert result['IMPLEMENTATION_VALIDITY'] == 'FAIL'
    checks, _ = _complete_gate_inputs()
    result = evaluate_historical_gates(SPECS, WINDOWS, checks, [],
                                       input_hashes_unchanged=True)
    assert result['IMPLEMENTATION_VALIDITY'] == 'FAIL'


def test_any_failed_subset_or_input_hash_blocks_readiness():
    checks, rows = _complete_gate_inputs()
    checks['BATTERY_SD_050']['POSTERIOR_SUBSET'] = False
    result = evaluate_historical_gates(SPECS, WINDOWS, checks, rows,
                                       input_hashes_unchanged=True)
    assert result['IMPLEMENTATION_VALIDITY'] == 'FAIL'
    assert 'BATTERY_SD_050:POSTERIOR_SUBSET' in result['failures']
    checks, rows = _complete_gate_inputs()
    result = evaluate_historical_gates(SPECS, WINDOWS, checks, rows,
                                       input_hashes_unchanged=False)
    assert result['IMPLEMENTATION_VALIDITY'] == 'FAIL'


def test_not_evaluated_and_duplicate_sensitivity_rows_block_readiness():
    checks, rows = _complete_gate_inputs()
    rows[0]['classification'] = 'NOT_EVALUATED'
    result = evaluate_historical_gates(SPECS, WINDOWS, checks, rows,
                                       input_hashes_unchanged=True)
    assert result['STATISTICAL_OR_ECONOMIC_SENSITIVITY'] == 'NOT_EVALUATED'
    assert result['DOWNSTREAM_INTERPRETATION_GATE'] == 'BLOCKED'
    checks, rows = _complete_gate_inputs()
    rows.append(rows[0].copy())
    result = evaluate_historical_gates(SPECS, WINDOWS, checks, rows,
                                       input_hashes_unchanged=True)
    assert result['IMPLEMENTATION_VALIDITY'] == 'FAIL'
