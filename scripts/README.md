# Script Entry Points

`scripts/` contains executable orchestration. Reusable model logic belongs in `src/`; scripts should mainly load configuration/data, call library functions, write ignored outputs and enforce stage gates.

## Data scripts

`scripts/data/` contains acquisition, ingestion, audit, reconciliation and panel-building utilities. Important examples include:

- `audit_industry_data.py`
- `audit_new_secondary_excel.py`
- `audit_public_completion.py`
- `build_core_monthly_panel.py`
- `build_high_value_industry_update.py`
- `build_industry_monthly.py`
- `build_public_gap_closure.py`
- `build_public_phase1_dataset.py`

Commercial raw workbooks remain local and ignored. Data scripts must not silently overwrite Data Freeze v1.

## Phase runners

Current main runners:

```text
run_phase1a1_descriptives.py
run_phase1a2_diagnostics.py
run_phase1b_baselines.py
run_phase2a_structural_design.py
run_phase2b_kalman_validation.py
run_phase2c_estimation_preflight.py
```

Execution order matches the research pipeline; do not skip phase gates just because later code exists.

## Runner design rule

A runner may:

- load config;
- verify data hashes / sample boundaries;
- assemble inputs;
- call `src/` functions;
- generate ignored CSV/figures;
- write concise aggregate diagnostics.

A runner should not:

- contain a second copy of the Kalman likelihood;
- redefine structural equations;
- embed commercial observations in source code;
- silently change earlier-phase parameter ranges;
- automatically launch the next research phase after a gate failure.

## Next runner

When Phase 2D implementation begins, use a new explicit entry point such as:

`run_phase2d_bayesian_estimation.py`

and keep MCMC / diagnostics logic in reusable `src/structural/` modules.
