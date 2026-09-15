# Configuration Guide

`configs/` stores phase-specific operational settings. Config files should define reproducible choices, not duplicate result tables or mutate earlier source-of-truth ranges.

## Current files

- `data_sources.yaml` — data-source configuration used by acquisition/build scripts.
- `phase1.yaml` — Phase 1 diagnostics / baseline settings.
- `phase2a.yaml` — **structural design source of truth**, including canonical parameter ranges and model-design choices.
- `phase2b.yaml` — Kalman / likelihood validation settings.
- `phase2c.yaml` — constrained optimization, synthetic recovery, profile and curvature settings.

## Rules

1. Later phases should read structural parameter bounds from `phase2a.yaml` rather than copy them into new configs.
2. A phase config may define additional sensitivity ranges, but those must be named as sensitivity-only.
3. Result values such as MLE estimates, posterior medians or IRF peaks do not belong in config files.
4. Fixed research assumptions (`rho_n`, `battery_sd`) should be explicit and traceable when they enter a phase.
5. Seeds, chain counts, optimizer budgets and diagnostic thresholds belong in the phase that uses them.
6. Updating a config after seeing results must be documented as a new planned robustness / revision rather than silently replacing the original gate.

## Next expected config

Phase 2D may add `phase2d.yaml` for prior hyperparameters, chain schedule and convergence thresholds **when the Phase 2D implementation is created**. It should not redefine Phase 2A structural equations or canonical parameter bounds.
