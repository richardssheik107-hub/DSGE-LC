# Test Suite Guide

The test suite is a research-safety layer, not only a software unit-test collection.

Current tests cover four broad areas:

1. **Data governance** — hashes, coverage, source reconciliation, candidate-vs-canonical separation.
2. **Phase 1 empirical code** — transformations, descriptive diagnostics, stationarity/break/lag logic, baseline forecasting.
3. **Structural numerics** — dimensions, stability, observability, Kalman covariance behavior, likelihood consistency.
4. **Estimation safety** — parameter transforms, multi-start optimization, profiles, curvature, weak-ID diagnostics and future-data protection.

The last completed Phase 2C run reported 401 passing tests in the configured Python 3.13 environment. A Python 3.12 collection attempt stopped because the environment lacked `statsmodels`; the repository dependency files now explicitly include the packages used by the test suite.

Before marking a new phase COMPLETE:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

A new phase should add tests for its own numerical gates and preserve all previous tests. Phase outputs and raw posterior chains should remain ignored rather than being used as committed golden files containing protected observations.
