# Test Suite Guide

The test suite is a research-safety layer, not only a software unit-test collection.

Current tests cover five broad areas:

1. **Data governance** — hashes, coverage, source reconciliation, candidate-vs-canonical separation.
2. **Phase 1 empirical code** — transformations, descriptive diagnostics, stationarity/break/lag logic, baseline forecasting.
3. **Structural numerics** — dimensions, stability, observability, Kalman covariance behavior, likelihood consistency.
4. **Deterministic estimation safety** — parameter transforms, multi-start optimization, profiles, curvature, weak-ID diagnostics and future-data protection.
5. **Bayesian estimation safety** — proper priors, Jacobian-correct transformed targets, MCMC state handling, chain extension, R-hat/ESS/MCSE, posterior summaries and Phase 2D safety gates.

The completed Phase 2D run reported **479 passing tests, 0 failures and 0 warnings** in the configured Python 3.13 environment. Python compilation and `git diff --check` also passed. Raw posterior chains and Phase outputs remain ignored rather than being committed as golden files.

Before marking a new phase COMPLETE:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

A new posterior structural-results phase should add tests for IRF dimensions/sign conventions, posterior-draw propagation, FEVD add-up/normalization, horizon handling, deterministic reproducibility and future-data safety while preserving all Phase 1—2D tests.
