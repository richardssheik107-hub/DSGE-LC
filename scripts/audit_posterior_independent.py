"""Read-only posterior re-audit with ArviZ; never resample or overwrite draws.

Run in a checkout with authorized artifacts and requirements-audit.txt installed.
Outputs are NEW audit reports, not replacements for historical phase results.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

PARAMETERS = ('rho_d','rho_c','rho_q','rho_p','a_p','a_c','b_d','b_c',
              'b_q','b_n','sigma_d','sigma_c','sigma_q','sigma_p')
DEFAULTS = dict(rhat_threshold=1.01, bulk_ess_threshold=400,
                tail_ess_threshold=400, mcse_sd_threshold=0.05)
ARTIFACTS = ('baseline', 'prior_flat_bounded', 'prior_moderate_shrink',
             'battery_sd_010', 'battery_sd_050', 'rho_n_050', 'rho_n_095')


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_draws(theta, names=PARAMETERS, thresholds=None):
    """Use reference diagnostics; flag stuck free-parameter chains separately."""
    import arviz as az
    x = np.asarray(theta, dtype=float)
    if x.ndim != 3 or x.shape[0] < 4 or x.shape[1] < 8 or x.shape[2] != len(names):
        raise ValueError('expected (at least 4 chains, at least 8 draws, parameters)')
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


def audit_file(path, thresholds=None):
    path = Path(path)
    before = sha256(path)
    sidecar = path.with_suffix('.metadata.json')
    metadata = json.loads(sidecar.read_text(encoding='utf-8-sig')) if sidecar.exists() else {}
    if metadata and metadata.get('artifact_sha256') != before:
        raise ValueError(f'artifact/sidecar hash mismatch: {path.name}')
    with np.load(path, allow_pickle=False) as data:
        theta = np.array(data['theta'], copy=True)
        embedded = tuple(data['parameter_order'].tolist()) if 'parameter_order' in data else ()
    order = tuple(metadata.get('parameter_order', embedded))
    if order and order != PARAMETERS:
        raise ValueError('parameter order differs from M0_FULL14')
    # Diagnostics can be inspected without legacy metadata, but cannot certify provenance.
    verified = bool(order == PARAMETERS and metadata.get('production_only') is True
                    and metadata.get('chains') == theta.shape[0]
                    and metadata.get('production_draws_per_chain') == theta.shape[1]
                    and {'specification', 'rho_n', 'battery_sd'}.issubset(metadata))
    result = check_draws(theta, thresholds=thresholds)
    unchanged = sha256(path) == before
    result.update(artifact=path.name, sha256=before, unchanged=unchanged,
                  metadata_verified=verified,
                  artifact_gate=bool(result['passed'] and unchanged and verified),
                  scope='CONVERGENCE_ONLY; support/stability/likelihood require separate audit')
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
    for name in ARTIFACTS:
        path = args.artifact_dir / f'{name}_posterior_draws.npz'
        try:
            results.append(audit_file(path, limits))
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
