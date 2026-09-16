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
    np.savez_compressed(p, theta=np.random.default_rng(4).normal(size=(4, 1000, 14)))
    before = audit.sha256(p)
    r = audit.audit_file(p)
    assert r['unchanged'] and audit.sha256(p) == before
    assert not r['metadata_verified'] and not r['artifact_gate']


def test_sidecar_hash_mismatch_fails(tmp_path):
    p = tmp_path / 'posterior.npz'
    np.savez_compressed(p, theta=np.ones((4, 100, 14)))
    p.with_suffix('.metadata.json').write_text(json.dumps({'artifact_sha256': 'wrong'}))
    with pytest.raises(ValueError): audit.audit_file(p)
