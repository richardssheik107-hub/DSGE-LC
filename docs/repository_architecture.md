# Repository Architecture

本页描述仓库的**运行结构和 source-of-truth 关系**。目标是减少“文档写了一套、脚本读另一套、配置又复制一套”的漂移风险。

## 1. Top-level layout

```text
DSGE-LC/
├─ configs/        phase-specific operational settings
├─ data/           public raw, processed public/auxiliary data, metadata
├─ docs/           plans, current status, phase memos, data audits
├─ scripts/        executable entry points
├─ src/            reusable library code
├─ tests/          regression, numerical and safety tests
├─ README.md       concise current project navigation
├─ requirements.txt
└─ requirements-dev.txt
```

Commercial workbooks and commercial-derived core panels are local-only and protected by `.gitignore`.

## 2. Source-of-truth hierarchy

### Project status

1. `docs/project_status_2026_09_15.md`
2. latest phase memo
3. `README.md`
4. historical plans / acquisition reports

### Structural specification

- equations / state order / shock order: `docs/phase2a_structural_mvp_spec.md` + `src/structural/`
- admissible parameter ranges: `configs/phase2a.yaml`
- Kalman / likelihood convention: Phase 2B code and memo
- selected estimation specification: Phase 2C memo

Do not duplicate Phase 2A parameter bounds into later configs unless a later phase deliberately defines a sensitivity range.

### Data definitions

- current variable definitions: `docs/data_dictionary.md`
- current freeze status: `docs/project_status_2026_09_15.md`
- source-specific details: corresponding audit / metadata files

## 3. Data flow

```text
public raw / local commercial workbooks
        ↓
scripts/data/* ingestion / audit
        ↓
metadata + local commercial processed layer
        ↓
local core_monthly_panel.csv  [ignored]
        ↓
Data Freeze v1 hash gate
        ↓
Phase 1 transformed dataset  [ignored]
        ↓
Phase 1 diagnostics / baselines
        ↓
Phase 2 measurement preparation
        ↓
state-space / likelihood / estimation
        ↓
phase outputs under outputs/  [ignored]
```

The repository intentionally commits metadata, public panels and code, but not licensed commercial values or generated Phase 2 state/chain outputs.

## 4. Code layers

### `src/data_audit/`

Reusable helpers for auditing secondary Excel / data-source consistency. It should not own structural-model logic.

### `src/diagnostics/`

Phase 1 transformations and empirical diagnostics:

- descriptive statistics;
- stationarity;
- break tests;
- lag screening;
- Phase 1A-2 diagnostics / figures.

### `src/baselines/`

Reduced-form forecast baselines:

- Random Walk;
- AR;
- VAR;
- independent-equation Minnesota BVAR.

### `src/evaluation/`

Forecast / evaluation utilities shared by baseline experiments.

### `src/structural/`

Structural MVP stack. Current responsibilities include:

- specification and equations;
- matrix construction;
- measurement mapping;
- stability / observability / identification;
- simulation;
- state-space preparation;
- Kalman / smoother / likelihood;
- parameter transforms;
- constrained estimation;
- profiles / curvature / optimization diagnostics.

Phase 2D Bayesian modules should be added here rather than embedded entirely inside runner scripts.

## 5. Script layers

### `scripts/data/`

Data acquisition, ingestion, reconciliation, audit and panel construction. These scripts must preserve provider separation and must not silently overwrite Data Freeze v1.

### `scripts/phase1/`

Dataset preparation specific to Phase 1.

### root phase runners

- `run_phase1a1_descriptives.py`
- `run_phase1a2_diagnostics.py`
- `run_phase1b_baselines.py`
- `run_phase2a_structural_design.py`
- `run_phase2b_kalman_validation.py`
- `run_phase2c_estimation_preflight.py`

Future runners should follow the same naming convention and remain orchestration layers; reusable logic belongs in `src/`.

## 6. Configuration rules

- `phase1.yaml`: Phase 1 experiment settings.
- `phase2a.yaml`: structural design and canonical parameter ranges.
- `phase2b.yaml`: Kalman / likelihood validation settings.
- `phase2c.yaml`: optimization / profile / curvature operational settings.

Later phase configs should reference earlier canonical bounds rather than re-copying them. Config files should contain operational choices, not result tables.

## 7. Output rules

Generated experiment outputs belong under:

```text
outputs/phase1/
outputs/phase2/
```

They are local artifacts and ignored by Git. Result memos may commit compact aggregate numbers, but must not commit:

- licensed monthly commercial observations;
- raw chain draws;
- monthly latent-state histories unless later explicitly approved for publication;
- optimization traces containing protected observations;
- commercial Excel workbooks.

## 8. Testing discipline

Tests are not only unit tests; they are research-safety gates. Existing suites check:

- data hashes and frozen ranges;
- no future-data contamination;
- transformation / stationarity logic;
- forecast stability;
- state-space dimensions;
- covariance PSD / finite Kalman calculations;
- likelihood consistency;
- optimization and profile logic;
- Git/data safety assumptions.

A new research phase should add tests before it is marked COMPLETE.

## 9. What should not be refactored during Phase 2D

Until Bayesian estimation is stable, avoid large path or module moves in:

- `src/structural/`;
- existing phase runner names;
- `configs/phase2a.yaml` bounds;
- Data Freeze construction scripts.

Documentation/navigation cleanup is safe; structural refactoring should wait until the posterior stage is frozen.
