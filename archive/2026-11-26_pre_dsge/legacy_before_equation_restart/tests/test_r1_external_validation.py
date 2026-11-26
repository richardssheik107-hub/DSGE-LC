import numpy as np
import pytest

from src.structural.r1_external_validation import (
    comparison_series,
    linear_detrend,
    paired_block_bootstrap_correlation,
    paired_moving_block_indices,
    state_information_comparison,
)


def test_paired_moving_blocks_keep_time_order_and_seed():
    a = paired_moving_block_indices(11, 3, 20, 20260915)
    assert a.shape == (20, 11)
    assert np.array_equal(a, paired_moving_block_indices(11, 3, 20, 20260915))
    assert np.all((a >= 0) & (a < 11))
    for row in a:
        assert np.array_equal(np.diff(row[:3]), [1, 1])
        assert np.array_equal(np.diff(row[3:6]), [1, 1])
        assert np.array_equal(np.diff(row[6:9]), [1, 1])


def test_paired_bootstrap_preserves_matching_series_and_is_reproducible():
    x = np.array([2., 4., 3., 9., 5., 10., 8., 12., 7., 16.])
    a = paired_block_bootstrap_correlation(x, 3 * x + 2, block_length=3, n_rep=2000, seed=20260915)
    b = paired_block_bootstrap_correlation(x, 3 * x + 2, block_length=3, n_rep=2000, seed=20260915)
    assert a["point_correlation"] == pytest.approx(1.)
    assert a["valid_replicates"] == 2000
    assert a["invalid_replicates"] == 0
    assert a["ci025"] == pytest.approx(1.)
    assert a["ci975"] == pytest.approx(1.)
    assert np.array_equal(a["replicate_correlations"], b["replicate_correlations"])


def test_constant_bootstrap_replicates_reported_not_zero_filled():
    x = np.array([0., 0., 0., 1., 1., 1.])
    a = paired_block_bootstrap_correlation(x, x, block_length=2, n_rep=2000, seed=24)
    assert a["both_constant_count"] > 0
    assert a["invalid_replicates"] == a["both_constant_count"]
    assert a["valid_replicates"] + a["invalid_replicates"] == 2000
    assert np.isnan(a["replicate_correlations"]).sum() == a["invalid_replicates"]
    assert a["ci025"] == pytest.approx(1.)


def test_transformations_align_months_without_padding_and_detrend_both():
    state = np.array([1., 2., 4., 7.])
    external = np.exp(np.array([1., 2., 3., 5.]))
    sx, sy = comparison_series(state, external, "log_change")
    assert np.array_equal(sx, state[1:])
    assert np.allclose(sy, [1., 1., 2.])
    sx, sy = comparison_series(state, external, "state_change_vs_log_change")
    assert np.allclose(sx, [1., 2., 3.])
    assert np.allclose(sy, [1., 1., 2.])
    sx, sy = comparison_series(state, external, "detrended_log_level")
    assert sx.sum() == pytest.approx(0., abs=1e-14)
    assert sy.sum() == pytest.approx(0., abs=1e-14)
    assert abs(np.dot(np.arange(4), sx)) < 1e-14
    assert abs(np.dot(np.arange(4), sy)) < 1e-14
    assert np.allclose(linear_detrend([1., 2., 3., 4.]), 0.)


def test_invalid_shapes_logs_and_constant_original_explicit():
    with pytest.raises(ValueError):
        comparison_series([1., 2., 3.], [1., 0., 2.], "log_level")
    with pytest.raises(ValueError):
        comparison_series([1., 2., 3.], [1., 2., 3.], "not_a_transform")
    with pytest.raises(ValueError):
        paired_moving_block_indices(5, 6, 2000, 1)
    with pytest.raises(ValueError):
        paired_block_bootstrap_correlation([1., 2., 3.], [1., 2., 3., 4.], block_length=2, seed=1)
    result = paired_block_bootstrap_correlation(np.ones(6), np.arange(6), block_length=3, n_rep=100, seed=1)
    assert result["point_status"] == "STATE_CONSTANT"
    assert result["interval_status"] == "NO_VALID_REPLICATES"
    assert result["state_constant_count"] + result["both_constant_count"] == 100
    assert np.isnan(result["ci025"])


def test_information_comparison_uses_same_target_and_reports_invalid_draws():
    target = np.exp(np.array([1., 2., 4., 3., 6.]))
    filtered = np.array([[1., 2., 3., 4., 5.], [5., 4., 3., 2., 1.]])
    smoothed = np.array([[1., 2., 4., 3., 6.], [6., 3., 4., 2., 1.]])
    result = state_information_comparison(filtered, smoothed, target, transformation="log_level")
    assert result["n_draws"] == 2
    assert result["filtered_valid_draws"] == result["smoothed_valid_draws"] == 2
    assert result["smoothed_correlations"][0] == pytest.approx(1.)
    with pytest.raises(ValueError):
        state_information_comparison(filtered, smoothed[:, :-1], target, transformation="log_level")
