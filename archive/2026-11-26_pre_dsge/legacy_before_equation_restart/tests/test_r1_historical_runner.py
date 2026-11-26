"""Counterexamples for R1 historical draw-first and signed graphics semantics."""
import numpy as np
import pytest

from scripts.run_r1_historical import posterior_cumulative_quantiles, split_signed_stack


def test_cumulative_quantile_is_not_cumsum_of_monthly_medians():
    draws = np.array([[0., 10.], [10., 0.], [10., 0.]])
    correct = posterior_cumulative_quantiles(draws)
    assert correct[2, 1] == 10.
    assert np.cumsum(np.median(draws, axis=0))[-1] == 10.
    # A sharp counterexample where median addition is visibly wrong.
    draws = np.array([[0., 10.], [10., 0.], [10., 10.]])
    assert posterior_cumulative_quantiles(draws)[2, 1] == 10.
    assert np.cumsum(np.median(draws, axis=0))[-1] == 20.


def test_signed_stack_keeps_negative_area_below_zero():
    values = np.array([[2., -3.], [-4., 5.]])
    positive, negative = split_signed_stack(values)
    np.testing.assert_array_equal(positive, [[2., 0.], [0., 5.]])
    np.testing.assert_array_equal(negative, [[0., -3.], [-4., 0.]])
    np.testing.assert_array_equal(positive + negative, values)


def test_cumulative_requires_finite_draw_matrix():
    with pytest.raises(ValueError):
        posterior_cumulative_quantiles(np.array([[1., np.nan]]))
