"""Portable synthetic tests. No proprietary observations or posterior artifacts."""
from pathlib import Path
import importlib.util
import json
import numpy as np
import pytest
pytest.importorskip('arviz', reason='install requirements-audit.txt for independent audit tests')
path = Path(__file__).resolve().parents[1] / 'scripts/audit_posterior_independent.py'
spec = importlib.util.spec_from_file_location('independent_audit', path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_iid_reference_diagnostics():
    x = np.random.default_rng(1).normal(size=(4, 5000, 2))
    result = audit.check_draws(x, ('a', 'b'))
    assert result['passed']


def test_stuck_chain_never_certifies_convergence():
    x = np.ones((4, 5000, 1))
    result = audit.check_draws(x, ('a',))
    assert not result['passed']
    assert result['parameters'][0]['status'] == 'STUCK_FREE_PARAMETER'


def test_shifted_chains_fail():
    x = np.random.default_rng(2).normal(size=(4, 5000, 1))
    x[0] += 3
    assert not audit.check_draws(x, ('a',))['passed']


def test_mean_mcse_uses_reference_mean_estimand():
    import arviz as az
    v = np.exp(np.random.default_rng(3).normal(size=(4, 2000)))
    r = audit.check_draws(v[:, :, None], ('a',))['parameters'][0]
    assert np.isclose(r['mcse_mean'], float(az.mcse(v, method='mean')))


@pytest.mark.parametrize('kind', ['nonfinite', 'dimension'])
def test_bad_arrays_fail(kind):
    x = np.ones((4, 100, 1)) if kind == 'nonfinite' else np.ones((4, 100))
    if kind == 'nonfinite': x[0, 0, 0] = np.nan
    with pytest.raises(ValueError): audit.check_draws(x, ('a',))


def test_file_audit_is_readonly_and_missing_metadata_not_certified(tmp_path):
    p = tmp_path / 'posterior.npz'
    theta = np.random.default_rng(4).normal(size=(4, 1000, 14))
    np.savez_compressed(p, theta=theta, z=theta,
                        components=np.zeros((4, 1000, 5)),
                        accepted=np.ones((4, 1000), dtype=bool))
    before = audit.sha256(p)
    r = audit.audit_file(p)
    assert r['unchanged'] and audit.sha256(p) == before
    assert not r['metadata_verified'] and not r['artifact_gate']
    assert 'SIDECAR_MISSING' in r['provenance_issues']


def test_sidecar_hash_mismatch_fails(tmp_path):
    p = tmp_path / 'posterior.npz'
    np.savez_compressed(p, theta=np.ones((4, 100, 14)))
    p.with_suffix('.metadata.json').write_text(json.dumps({'artifact_sha256': 'wrong'}))
    with pytest.raises(ValueError): audit.audit_file(p)


def test_missing_auxiliary_arrays_fail(tmp_path):
    p = tmp_path / 'posterior.npz'
    np.savez_compressed(p, theta=np.zeros((4, 100, 14)))
    with pytest.raises(ValueError, match='missing artifact arrays'):
        audit.audit_file(p)


def test_sidecar_and_embedded_spec_conflict_fail(tmp_path):
    p = tmp_path / 'posterior.npz'
    theta = np.random.default_rng(8).normal(size=(4, 100, 14))
    np.savez_compressed(p, theta=theta, z=theta,
                        components=np.zeros((4, 100, 5)),
                        accepted=np.ones((4, 100), dtype=bool),
                        specification=np.asarray('PRIOR_FLAT_BOUNDED'))
    sidecar = {'artifact_sha256': audit.sha256(p),
               'specification': 'PRIOR_MODERATE_SHRINK'}
    p.with_suffix('.metadata.json').write_text(json.dumps(sidecar))
    with pytest.raises(ValueError, match='embedded/sidecar conflict'):
        audit.audit_file(p)


def test_sidecar_and_embedded_parameter_order_conflict_fail(tmp_path):
    p = tmp_path / 'posterior.npz'
    theta = np.random.default_rng(10).normal(size=(4, 100, 14))
    np.savez_compressed(p, theta=theta, z=theta,
                        components=np.zeros((4, 100, 5)),
                        accepted=np.ones((4, 100), dtype=bool),
                        parameter_order=np.asarray(audit.PARAMETERS))
    sidecar = {'artifact_sha256': audit.sha256(p),
               'parameter_order': list(reversed(audit.PARAMETERS))}
    p.with_suffix('.metadata.json').write_text(json.dumps(sidecar))
    with pytest.raises(ValueError, match='embedded/sidecar conflict: parameter_order'):
        audit.audit_file(p)


def test_batched_recomputed_radius_matches_structural_matrix():
    from src.structural.matrices import system_matrices
    params = {'rho_d': .65, 'rho_c': .60, 'rho_q': .55, 'rho_p': .45,
              'a_p': .10, 'a_c': .20, 'b_d': .35, 'b_c': .45,
              'b_q': .25, 'b_n': .20, 'sigma_d': .40, 'sigma_c': .35,
              'sigma_q': .40, 'sigma_p': .50}
    theta = np.array([[params[name] for name in audit.PARAMETERS]])[None, :, :]
    actual = audit._radii_from_theta(theta, .8)[0, 0]
    A = system_matrices('M0_CORE5', {**params, 'rho_n': .8})[0]
    expected = np.max(np.abs(np.linalg.eigvals(A)))
    assert np.isclose(actual, expected, rtol=0, atol=1e-12)


def test_expected_specification_is_not_inferred_from_filename(tmp_path):
    p = tmp_path / 'prior_flat_bounded_posterior_draws.npz'
    theta = np.random.default_rng(9).normal(size=(4, 100, 14))
    np.savez_compressed(p, theta=theta, z=theta,
                        components=np.zeros((4, 100, 5)),
                        accepted=np.ones((4, 100), dtype=bool),
                        parameter_order=np.asarray(audit.PARAMETERS),
                        specification=np.asarray('PRIOR_MODERATE_SHRINK'),
                        rho_n=np.asarray(.8), battery_sd=np.asarray(.25),
                        chains=np.asarray(4), production_draws_per_chain=np.asarray(100))
    sidecar = {'artifact_sha256': audit.sha256(p),
               'parameter_order': list(audit.PARAMETERS),
               'specification': 'PRIOR_MODERATE_SHRINK',
               'rho_n': .8, 'battery_sd': .25,
               'chains': 4, 'production_draws_per_chain': 100,
               'production_only': True}
    p.with_suffix('.metadata.json').write_text(json.dumps(sidecar))
    result = audit.audit_file(p, expected_specification='PRIOR_FLAT_BOUNDED',
                              expected_rho_n=.8, expected_battery_sd=.25)
    assert not result['metadata_verified']
    assert 'SPECIFICATION_MISMATCH_OR_MISSING' in result['provenance_issues']
