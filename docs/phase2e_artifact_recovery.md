# Phase 2E-R Sensitivity Posterior Artifact Recovery

## Root cause

Phase 2D successfully ran and summarized all six sensitivity posteriors, but `run_phase2d_bayesian_estimation.py` persisted raw production draws only for the baseline. The sensitivity loops retained `res` long enough to write convergence, posterior-shift and correlation summaries, then discarded it without creating posterior artifacts. This is a `POSTERIOR_ARTIFACT_PERSISTENCE_GAP`, not an MCMC convergence, model, IRF, FEVD or Data Freeze failure.

## Search and recovery rule

The complete `outputs/phase2/phase2d/` subtree was searched for NPZ, NPY, pickle, checkpoint, chain, posterior and sensitivity artifacts. Only `baseline_posterior_draws.npz` existed. The missing specifications were therefore reconstructed by explicit targeted deterministic replay using the frozen Phase 2D transform, target, priors, starts, seeds, adaptive warmup, frozen 90/10 production kernel, convergence diagnostics and extension rules. Baseline MCMC was not rerun.

## Recovery audit

| Specification | Draws/chain | Max R-hat | Min bulk ESS | Min tail ESS | Replay shift error | Result |
|---|---:|---:|---:|---:|---:|---|
| PRIOR_FLAT_BOUNDED | 48,000 | 1.00796 | 892.95 | 428.01 | 1.35e-15 | PASS |
| PRIOR_MODERATE_SHRINK | 18,000 | 1.00994 | 609.34 | 476.02 | 1.43e-15 | PASS |
| BATTERY_SD_010 | 42,000 | 1.00512 | 790.94 | 450.99 | 2.96e-15 | PASS |
| BATTERY_SD_050 | 18,000 | 1.00830 | 429.18 | 577.75 | 2.42e-15 | PASS |
| RHO_N_050 | 24,000 | 1.00817 | 608.12 | 447.00 | 1.61e-15 | PASS |
| RHO_N_095 | 36,000 | 1.00486 | 874.59 | 427.47 | 9.55e-16 | PASS |

Every stopping count exactly matches the original Phase 2D record. All artifacts contain four production-only chains, 14 parameters in canonical order, finite arrays, in-support native parameters, stable transition radii, exact assumption metadata and SHA256 sidecars. The replayed posterior medians reproduce the original summaries to floating-point precision, far inside the 0.10 baseline-posterior-SD mismatch threshold.

## Future persistence

`posterior_artifacts.py` now provides reusable save/load, metadata, SHA256 and integrity validation. The Phase 2D runner now persists baseline and every sensitivity posterior during any future full run. `recover_phase2d_sensitivity_artifacts.py` supports one specification or all missing specifications, skips valid existing artifacts by default and requires explicit `--force` before overwrite.

All posterior NPZ and metadata artifacts remain local and gitignored.
