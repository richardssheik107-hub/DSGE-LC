# Configuration Guide

`configs/` stores phase-specific operational settings. Config files should define reproducible choices, not duplicate result tables or mutate earlier source-of-truth ranges.

## Current files

- `data_sources.yaml` — data-source configuration used by acquisition/build scripts.
- `phase1.yaml` — Phase 1 diagnostics / baseline settings.
- `phase2a.yaml` — **structural design source of truth**, including canonical parameter ranges and model-design choices.
- `phase2b.yaml` — Kalman / likelihood validation settings.
- `phase2c.yaml` — constrained optimization, synthetic recovery, profile and curvature settings.
- `phase2d.yaml` — proper prior hyperparameters, MCMC schedule, convergence thresholds and fixed-assumption sensitivity specs.

## Rules

1. Later phases should read structural parameter bounds from `phase2a.yaml` rather than copy them into new configs.
2. A phase config may define additional sensitivity ranges, but those must be named as sensitivity-only.
3. Result values such as MLE estimates, posterior medians or IRF peaks do not belong in config files.
4. Fixed research assumptions (`rho_n`, `battery_sd`) should be explicit and traceable when they enter a phase.
5. Seeds, chain counts, optimizer budgets and diagnostic thresholds belong in the phase that uses them.
6. Updating a config after seeing results must be documented as a new planned robustness / revision rather than silently replacing the original gate.
7. Phase 2D is now frozen as the posterior-estimation configuration; future IRF/FEVD settings should live in a separate new config rather than being appended to `phase2d.yaml`.

## Next expected config

The next structural-results stage may add a dedicated config (for example `phase2e.yaml`) containing only posterior IRF / FEVD horizons, draw-selection rules, uncertainty summaries and structural-consistency thresholds. It must reuse the Phase 2D posterior and the Phase 2A structural definitions rather than redefining either.
