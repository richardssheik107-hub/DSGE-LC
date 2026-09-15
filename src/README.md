# Source Package Guide

`src/` contains reusable research code. Phase runners should orchestrate these modules rather than duplicate their logic.

## Packages

- `baselines/` — Random Walk, AR, VAR and BVAR forecast baselines.
- `data_audit/` — reusable source / workbook audit helpers.
- `diagnostics/` — transformations, descriptive statistics, stationarity, break and lag diagnostics.
- `evaluation/` — evaluation utilities used by forecast experiments.
- `structural/` — structural MVP, state-space, Kalman, likelihood and estimation diagnostics.

## Structural stack

Current `src/structural/` responsibilities progress roughly as:

```text
spec / equations
→ matrices / measurement
→ stability / observability / identification
→ simulation
→ state_space
→ kalman / kalman_diagnostics
→ likelihood
→ parameter_transform
→ estimation / profiles / curvature / optimization_diagnostics
```

The Phase 2A equations and Phase 2B canonical likelihood are frozen interfaces for Phase 2D unless a dedicated revision is explicitly approved.

## Next extension point

Bayesian estimation should add focused modules such as:

- `priors.py`
- `mcmc.py`
- `mcmc_diagnostics.py`
- `posterior_diagnostics.py`

Do not add IRF / FEVD or historical decomposition to the same implementation step before posterior convergence passes.

## Refactoring rule

During active Phase 2D work, prefer additive modules and small tested refactors. Avoid moving or renaming established Phase 2A—2C modules unless necessary, because existing tests and phase memos rely on those interfaces.
