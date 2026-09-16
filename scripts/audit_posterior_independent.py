"""Read-only posterior re-audit with ArviZ; never resample or overwrite draws.

Run in a checkout with authorized artifacts and requirements-audit.txt installed.
Outputs are NEW audit reports, not replacements for historical phase results.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.structural.parameter_transform import load_phase2a_bounds

PARAMETERS = ('rho_d','rho_c','rho_q','rho_p','a_p','a_c','b_d','b_c',
              'b_q','b_n','sigma_d','sigma_c','sigma_q','sigma_p')
DEFAULTS = dict(rhat_threshold=1.01, bulk_ess_threshold=400,
                tail_ess_threshold=400, mcse_sd_threshold=0.05)
ARTIFACTS = ('baseline', 'prior_flat_bounded', 'prior_moderate_shrink',
             'battery_sd_010', 'battery_sd_050', 'rho_n_050', 'rho_n_095')
REQUIRED_ARRAYS = ('theta', 'z', 'components', 'accepted')


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_draws(theta, names=PARAMETERS, thresholds=None):
    """Use reference diagnostics; flag stuck free-parameter chains separately."""
    import arviz as az
    x = np.asarray(theta, dtype=float)
    if not names or len(set(names)) != len(names):
        raise ValueError('parameter names must be nonempty and unique')
    if x.ndim != 3 or x.shape[0] != 4 or x.shape[1] < 8 or x.shape[2] != len(names):
        raise ValueError('expected (exactly 4 chains, at least 8 draws, parameters)')
    if not np.isfinite(x).all():
        raise ValueError('non-finite posterior draws')
    limits = dict(DEFAULTS if thresholds is None else thresholds)
    rows = []
    for j, name in enumerate(names):
        v = x[:, :, j]
        stuck = bool(np.any(np.ptp(v, axis=1) == 0))
        if stuck:
            rows.append(dict(parameter=name, status='STUCK_FREE_PARAMETER', passed=False))
            continue
        sd = float(np.std(v, ddof=1))
        row = dict(parameter=name, rhat=float(az.rhat(v, method='rank')),
                   bulk_ess=float(az.ess(v, method='bulk')),
                   tail_ess=float(az.ess(v, method='tail', prob=(.05, .95))),
                   mean_ess=float(az.ess(v, method='mean')),
                   mcse_mean=float(az.mcse(v, method='mean')), posterior_sd=sd)
        row['mcse_sd'] = row['mcse_mean'] / sd
        if not all(np.isfinite(value) for key, value in row.items() if key != 'parameter'):
            raise ValueError(f'non-finite reference diagnostic: {name}')
        row['passed'] = bool(row['rhat'] <= limits['rhat_threshold']
                             and row['bulk_ess'] >= limits['bulk_ess_threshold']
                             and row['tail_ess'] >= limits['tail_ess_threshold']
                             and row['mcse_sd'] <= limits['mcse_sd_threshold'])
        row['status'] = 'PASS' if row['passed'] else 'REVIEW'
        rows.append(row)
    return dict(reference='ArviZ', version=az.__version__, thresholds=limits,
                chains=x.shape[0], draws_per_chain=x.shape[1],
                passed=bool(rows) and all(r['passed'] for r in rows), parameters=rows)


def _embedded_metadata(raw):
    fields = ('parameter_order', 'specification', 'rho_n', 'battery_sd',
              'production_draws_per_chain', 'chains', 'seed')
    result = {}
    for field in fields:
        if field in raw:
            value = raw[field].tolist()
            result[field] = value
    return result


def _radii_from_theta(theta, rho_n, batch_size=8192):
    """Rebuild M0 A, independently of the NPZ's stored radius column."""
    flat = np.asarray(theta, dtype=float).reshape(-1, len(PARAMETERS))
    out = np.empty(len(flat), dtype=float)
    for start in range(0, len(flat), batch_size):
        t = flat[start:start + batch_size]
        A = np.zeros((len(t), 5, 5), dtype=float)
        rd, rc, rq, rp, ap, ac, bd, bc, bq, bn = (t[:, j] for j in range(10))
        A[:, 0, 0] = rd
        A[:, 1, 1] = rc
        A[:, 2, 1] = -ac
        A[:, 2, 2] = rq
        A[:, 2, 4] = ap
        A[:, 3, 0] = -1.
        A[:, 3, 2] = 1.
        A[:, 3, 3] = rho_n
        A[:, 4, 0] = bd * rd + bn
        A[:, 4, 1] = bc * rc + bq * ac
        A[:, 4, 2] = -bq * rq - bn
        A[:, 4, 3] = -bn * rho_n
        A[:, 4, 4] = rp - bq * ap
        out[start:start + len(t)] = np.abs(np.linalg.eigvals(A)).max(axis=1)
    return out.reshape(theta.shape[:2])


def audit_file(path, thresholds=None, *, expected_specification=None,
               expected_rho_n=None, expected_battery_sd=None, bounds=None):
    path = Path(path)
    before = sha256(path)
    sidecar = path.with_suffix('.metadata.json')
    metadata = json.loads(sidecar.read_text(encoding='utf-8-sig')) if sidecar.exists() else {}
    if metadata and metadata.get('artifact_sha256') != before:
        raise ValueError(f'artifact/sidecar hash mismatch: {path.name}')
    with np.load(path, allow_pickle=False) as data:
        missing = [name for name in REQUIRED_ARRAYS if name not in data]
        if missing:
            raise ValueError(f'missing artifact arrays: {missing}')
        arrays = {name: np.array(data[name], copy=True) for name in REQUIRED_ARRAYS}
        embedded = _embedded_metadata(data)
    theta, z, components, accepted = (arrays[name] for name in REQUIRED_ARRAYS)
    if theta.ndim != 3 or theta.shape[0] != 4 or theta.shape[2] != len(PARAMETERS):
        raise ValueError('theta shape must be (4, production draws, 14)')
    if z.shape != theta.shape or components.shape != theta.shape[:2] + (5,) or accepted.shape != theta.shape[:2]:
        raise ValueError('theta/z/components/accepted dimensions conflict')
    if accepted.dtype != np.dtype('bool'):
        raise ValueError('accepted must be a boolean production indicator')
    if any(not np.isfinite(arrays[key]).all() for key in ('theta', 'z', 'components')):
        raise ValueError('non-finite artifact array')
    for field in ('parameter_order', 'specification', 'rho_n', 'battery_sd',
                  'production_draws_per_chain', 'chains', 'seed'):
        if field in metadata and field in embedded and metadata[field] != embedded[field]:
            raise ValueError(f'embedded/sidecar conflict: {field}')
    merged = {**embedded, **{k: v for k, v in metadata.items() if k != 'artifact_sha256'}}
    issues = []
    if tuple(merged.get('parameter_order', ())) != PARAMETERS:
        issues.append('PARAMETER_ORDER_UNVERIFIED')
    if metadata.get('production_only') is not True:
        issues.append('PRODUCTION_ONLY_UNVERIFIED')
    if merged.get('chains') != 4 or merged.get('production_draws_per_chain') != theta.shape[1]:
        issues.append('CHAIN_DRAW_METADATA_UNVERIFIED')
    for field, expected in (('specification', expected_specification),
                            ('rho_n', expected_rho_n), ('battery_sd', expected_battery_sd)):
        if expected is not None and merged.get(field) != expected:
            issues.append(f'{field.upper()}_MISMATCH_OR_MISSING')
    if not metadata:
        issues.append('SIDECAR_MISSING')
    if bounds is None:
        bounds = load_phase2a_bounds(Path(__file__).resolve().parents[1] / 'configs/phase2a.yaml')
    low = np.array([bounds[name][0] for name in PARAMETERS])
    high = np.array([bounds[name][1] for name in PARAMETERS])
    support_ok = bool(np.all((theta >= low) & (theta <= high)))
    transformed = low + (high - low) * expit(z)
    transform_error = float(np.max(np.abs(theta - transformed)))
    transform_ok = bool(transform_error <= 1e-10)
    rho_for_stability = expected_rho_n if expected_rho_n is not None else merged.get('rho_n')
    if rho_for_stability is None:
        stable = False
        max_radius = None
        radius_error = None
    else:
        radii = _radii_from_theta(theta, float(rho_for_stability))
        stable = bool(np.isfinite(radii).all() and np.all(radii < 1.))
        max_radius = float(np.max(radii))
        radius_error = float(np.max(np.abs(radii - components[:, :, 4])))
        if radius_error > 1e-10:
            issues.append('STORED_RADIUS_CONFLICT')
    verified = not issues
    result = check_draws(theta, thresholds=thresholds)
    unchanged = sha256(path) == before
    result.update(artifact=path.name, sha256=before, unchanged=unchanged,
                  metadata_verified=verified, provenance_issues=issues,
                  parameter_support_gate=support_ok,
                  transform_gate=transform_ok, max_transform_error=transform_error,
                  stability_gate=stable, max_recomputed_radius=max_radius,
                  max_stored_radius_error=radius_error,
                  artifact_gate=bool(result['passed'] and unchanged and verified and support_ok and transform_ok and stable),
                  scope='ARTIFACT_AND_CONVERGENCE; target-density component replay is separate')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-dir', type=Path, default=Path('outputs/phase2/phase2d'))
    parser.add_argument('--config', type=Path, default=Path('configs/phase2d.yaml'))
    parser.add_argument('--output', type=Path,
                        default=Path('outputs/repository_audit/independent_posterior_audit.json'))
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Output exists: choose a new report filename; nothing overwritten.')
    cfg = json.loads(args.config.read_text(encoding='utf-8-sig'))
    limits = {key: cfg[key] for key in DEFAULTS}
    results, errors = [], []
    expected = {'baseline': (cfg['baseline_prior'], cfg['rho_n_fixed'], cfg['battery_sd_fixed']),
                'prior_flat_bounded': ('PRIOR_FLAT_BOUNDED', cfg['rho_n_fixed'], cfg['battery_sd_fixed']),
                'prior_moderate_shrink': ('PRIOR_MODERATE_SHRINK', cfg['rho_n_fixed'], cfg['battery_sd_fixed'])}
    expected.update({item['name'].lower(): (item['name'], item['rho_n'], item['battery_sd'])
                     for item in cfg['fixed_sensitivity']})
    for name in ARTIFACTS:
        path = args.artifact_dir / f'{name}_posterior_draws.npz'
        try:
            spec, rho_n, battery_sd = expected[name]
            results.append(audit_file(path, limits, expected_specification=spec,
                                      expected_rho_n=rho_n, expected_battery_sd=battery_sd))
        except (FileNotFoundError, KeyError, ValueError) as exc:
            errors.append(dict(artifact=path.name, error=str(exc)))
    ready = len(results) == len(ARTIFACTS) and not errors and all(r['artifact_gate'] for r in results)
    report = dict(status='PASS' if ready else 'REVIEW_REQUIRED', results=results, errors=errors,
                  note='No MCMC, no local state correction, no historical output replacement.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(dict(status=report['status'], audited=len(results), errors=len(errors))))
    raise SystemExit(0 if ready else 2)


if __name__ == '__main__':
    main()
