"""Prespecified synthetic counterexamples for the Phase 2D diagnostics.

AR(1) theory tolerance is fixed at +/-20% for 80,000 retained draws.
ArviZ parity tolerances are fixed at 0.5% for ESS/MCSE and 1e-10 for R-hat;
the optional parity test runs when the separately installed audit dependency is
available.  These values are not selected from the posterior audit results.
"""
import numpy as np
import pytest
from src.structural.mcmc_diagnostics import (
    bulk_ess, convergence_pass, diagnostic_table, effective_sample_size,
    mean_ess, rank_normalized_split_rhat, tail_ess,
)

CFG = dict(rhat_threshold=1.01, bulk_ess_threshold=400,
           tail_ess_threshold=400, mcse_sd_threshold=0.05)
AR1_RATIO_BOUNDS = (.80, 1.20)
REFERENCE_REL_TOL = .005
REFERENCE_RHAT_ABS_TOL = 1e-10

@pytest.mark.parametrize("rho", [0., .5, .9, -.5])
def test_ar1_ess_matches_known_long_run_variance(rho):
    rng = np.random.default_rng(20260916)
    e = rng.normal(size=(4, 21000))
    x = np.zeros_like(e)
    for t in range(1, x.shape[1]):
        x[:, t] = rho*x[:, t-1] + e[:, t]
    x = x[:, 1000:]
    theoretical = x.size*(1-rho)/(1+rho)
    assert AR1_RATIO_BOUNDS[0] < mean_ess(x)/theoretical < AR1_RATIO_BOUNDS[1]
    if rho < 0:
        assert mean_ess(x) > x.size  # antithetic ESS must not be capped at N


def test_iid_normal_rhat_and_ess_scale():
    x = np.random.default_rng(42).normal(size=(4, 4000))
    assert rank_normalized_split_rhat(x) < 1.01
    assert .70 * x.size < bulk_ess(x) < 1.40 * x.size


def test_stuck_constant_free_parameter_fails_gate():
    x = np.ones((4, 1000, 1))
    rows = diagnostic_table(x, ['x'])
    assert rows[0]['diagnostic_status'] == 'FROZEN_FREE_PARAMETER'
    assert not convergence_pass(rows, CFG)
    assert effective_sample_size(x[:, :, 0]) == 0
    assert np.isinf(rank_normalized_split_rhat(x[:, :, 0]))


def test_one_stuck_chain_fails_gate():
    x = np.random.default_rng(4).normal(size=(4, 2000, 1))
    x[0] = 1
    rows = diagnostic_table(x, ['x'])
    assert rows[0]['diagnostic_status'] == 'FROZEN_FREE_PARAMETER'
    assert not convergence_pass(rows, CFG)


def test_chain_mean_and_scale_disagreement_detected():
    rng = np.random.default_rng(120)
    mean_shift = rng.normal(size=(4, 2000))
    mean_shift[0] += 2
    scale_shift = rng.normal(size=(4, 2000))
    scale_shift[0] *= 3
    assert rank_normalized_split_rhat(mean_shift) > 1.10
    assert rank_normalized_split_rhat(scale_shift) > 1.10


def test_split_detects_within_chain_half_drift():
    rng = np.random.default_rng(121)
    x = rng.normal(size=(4, 2000))
    x[:, 1000:] += 1.5
    assert rank_normalized_split_rhat(x) > 1.10


def test_empty_diagnostic_list_cannot_pass():
    assert not convergence_pass([], CFG)
    assert not convergence_pass([dict(rhat=np.nan, bulk_ess=1000,
                                      tail_ess=1000, mcse_sd=.01)], CFG)
    assert not convergence_pass([dict(rhat=1., bulk_ess=np.inf,
                                      tail_ess=1000, mcse_sd=.01)], CFG)
    assert not convergence_pass([dict(rhat=1., bulk_ess=1000,
                                      tail_ess=1000)], CFG)


def test_mcse_uses_raw_mean_ess_not_rank_bulk():
    x = np.exp(np.random.default_rng(7).normal(size=(4, 2000)))
    r = diagnostic_table(x[:, :, None], ['x'])[0]
    assert np.isclose(r['mcse_sd'], 1/np.sqrt(mean_ess(x)))


def test_nonfinite_input_rejected():
    x = np.zeros((4, 100)); x[0, 0] = np.nan
    with pytest.raises(ValueError):
        bulk_ess(x)
    with pytest.raises(ValueError):
        diagnostic_table(x[:, :, None], ['x'])
    x[0, 0] = np.inf
    with pytest.raises(ValueError):
        diagnostic_table(x[:, :, None], ['x'])


def test_empty_wrong_dimension_and_duplicate_parameters_rejected():
    with pytest.raises(ValueError):
        diagnostic_table(np.empty((4, 100, 0)), [])
    with pytest.raises(ValueError):
        diagnostic_table(np.zeros((4, 100)), ['x'])
    with pytest.raises(ValueError):
        diagnostic_table(np.zeros((4, 100, 2)), ['x'])
    with pytest.raises(ValueError):
        diagnostic_table(np.zeros((4, 100, 2)), ['x', 'x'])


def test_tail_ess_preserves_chain_split_information():
    rng = np.random.default_rng(1)
    x = rng.normal(size=(4, 2000))
    assert 1000 < tail_ess(x) < 20000


def test_constant_tail_indicator_in_one_chain_is_not_frozen_parameter():
    rng = np.random.default_rng(2)
    x = rng.normal(size=(4, 200))
    x[0] += 4  # lower-tail indicator is all zero in this source chain
    assert not np.any(x[0] <= np.quantile(x, .05))
    assert np.ptp(x[0]) > 0  # the free parameter itself is not frozen
    assert np.isfinite(tail_ess(x)) and tail_ess(x) > 0


def test_rejection_repeats_odd_draw_count_and_heavy_tails_are_valid():
    rng = np.random.default_rng(11)
    x = np.repeat(rng.standard_t(3, size=(4, 751)), 2, axis=1)[:, :-1]
    assert x.shape == (4, 1501)
    assert np.isfinite(rank_normalized_split_rhat(x))
    assert 0 < bulk_ess(x) < x.size * np.log10(x.size)
    assert 0 < tail_ess(x) < x.size * np.log10(x.size)


@pytest.mark.parametrize('case', ['normal', 'heavy_repeated_odd', 'tail_indicator_constant'])
def test_parity_with_independent_arviz_reference_when_available(case):
    az = pytest.importorskip('arviz')
    rng = np.random.default_rng(20260916)
    if case == 'normal':
        x = rng.normal(size=(4, 1001))
    elif case == 'heavy_repeated_odd':
        x = np.repeat(rng.standard_t(3, size=(4, 501)), 2, axis=1)[:, :-1]
    else:
        x = rng.normal(size=(4, 400))
        x[0] += 4
    row = diagnostic_table(x[:, :, None], ['x'])[0]
    assert np.isclose(row['rhat'], float(az.rhat(x, method='rank')),
                      rtol=0, atol=REFERENCE_RHAT_ABS_TOL)
    for field, method in [('bulk_ess', 'bulk'), ('tail_ess', 'tail'),
                          ('mean_ess', 'mean')]:
        options = {'prob': (.05, .95)} if method == 'tail' else {}
        assert np.isclose(row[field], float(az.ess(x, method=method, **options)),
                          rtol=REFERENCE_REL_TOL, atol=0)
    assert np.isclose(row['mcse'], float(az.mcse(x, method='mean')),
                      rtol=REFERENCE_REL_TOL, atol=0)
