# Source Package Guide

`src/` contains reusable research code. Phase runners should orchestrate these modules rather than duplicate their logic.

## Packages

- `baselines/` — Random Walk, AR, VAR and BVAR forecast baselines.
- `data_audit/` — reusable source / workbook audit helpers.
- `diagnostics/` — transformations, descriptive statistics, stationarity, break and lag diagnostics.
- `evaluation/` — evaluation utilities used by forecast experiments.
- `structural/` — structural MVP, state-space, Kalman, likelihood, deterministic estimation and Bayesian posterior diagnostics.

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
→ priors
→ mcmc / mcmc_diagnostics
→ posterior_diagnostics
```

The Phase 2A equations and Phase 2B canonical likelihood remain frozen interfaces unless a dedicated model-revision phase is explicitly approved.

## Phase 2D modules

Phase 2D added focused Bayesian modules:

- `priors.py` — proper native-space priors and stable-prior audit;
- `mcmc.py` — Jacobian-correct z-space adaptive random-walk Metropolis;
- `mcmc_diagnostics.py` — rank-normalized split R-hat, bulk/tail ESS, MCSE and chain diagnostics;
- `posterior_diagnostics.py` — posterior summaries, boundary mass, contraction, sensitivity and PPC summaries.

Phase 2D is complete; these modules are now reusable infrastructure rather than an active extension point.

## Next extension point

The next structural-results layer should add focused, testable modules for:

- posterior IRF generation;
- posterior FEVD;
- sign / timing / economic-consistency audits;
- posterior uncertainty propagation。

Do not combine historical decomposition or structural OOS into the same implementation before the IRF/FEVD consistency gate passes.

## Refactoring rule

Prefer additive modules and small tested refactors. Avoid moving or renaming established Phase 2A—2D modules unless necessary, because tests and phase memos rely on those interfaces.
