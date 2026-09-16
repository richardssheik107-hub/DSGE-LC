# Midterm Reproducibility Manifest

## 1. Freeze and repository anchor

- Data Freeze v1: `data/processed/core_monthly_panel.csv`
- SHA256: `9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`
- Core panel: 2020-01—2025-09, 69 months
- Structural OBS_MIXED4: 2021-01—2025-09, N=57
- Phase 2J pre-commit source anchor: `5af059fa87683a214ec3dca30da3451ddb22a182`
- Phase 2J is intentionally not self-hashed inside its own commit; resolve the freeze commit with `git log --grep="freeze midterm evidence" -1 --format=%H`.

## 2. Canonical phase commits

| Phase | Commit | Message |
|---|---|---|
| Phase 1A-1 | `aac2079` | `phase1: add frozen-sample descriptive diagnostics` |
| Phase 1A-2 | `bd5298b` | `phase1: add mechanism and lag diagnostics` |
| Phase 1B | `941c2e9` | `phase1: add reduced-form forecast baselines` |
| Phase 2A | `dd4cc0a` | `phase2: define structural mvp and identification precheck` |
| Phase 2B | `5b99a00` | `phase2: add kalman and likelihood validation` |
| Phase 2C | `f2fd892` | `phase2: add constrained estimation preflight` |
| Phase 2D | `9d4bf73` | `phase2: add bayesian estimation and convergence diagnostics` |
| Phase 2E | `8eeea87`, `99021af` | posterior IRF/FEVD + sensitivity propagation |
| Phase 2F | `db1d8bf` | `phase2: add posterior historical decomposition` |
| Phase 2G | `5d350c4` | `phase2: add strict structural out-of-sample evaluation` |
| Phase 2H | `0731818` | `phase2: add external validation robustness` |
| Phase 2I | `5af059f` | `phase2: add preliminary spot futures extension` |

## 3. Tests and runtime

- Python: 3.13
- Phase 2J freeze validation command: `py -3.13 -m pytest -q`
- Result: `600 passed`, 0 failed
- Phase 2I new-code compile: PASS
- Phase 2I experiment gates: `PHASE_2I_READY=YES`
- Phase 2J evidence-freeze tests: `4 passed`; included in the full `600 passed` total.

## 4. Configs and runners

| Phase | Config | Runner / builder |
|---|---|---|
| Phase 1A-1 | `configs/phase1.yaml` | `scripts/run_phase1a1_descriptives.py` |
| Phase 1A-2 | `configs/phase1a2.yaml` | `scripts/run_phase1a2_diagnostics.py` |
| Phase 1B | `configs/phase1b.yaml` | `scripts/run_phase1b_baselines.py` |
| Phase 2A | `configs/phase2a.yaml` | `scripts/run_phase2a_structural_design.py` |
| Phase 2B | `configs/phase2b.yaml` | `scripts/run_phase2b_kalman_validation.py` |
| Phase 2C | `configs/phase2c.yaml` | `scripts/run_phase2c_estimation_preflight.py` |
| Phase 2D | `configs/phase2d.yaml` | `scripts/run_phase2d_bayesian_estimation.py` |
| Phase 2E | `configs/phase2e.yaml` | `scripts/run_phase2e_irf_fevd.py` |
| Phase 2F | `configs/phase2f.yaml` | `scripts/run_phase2f_historical_decomposition.py` |
| Phase 2G | `configs/phase2g.yaml` | `scripts/run_phase2g_structural_oos.py` |
| Phase 2H | `configs/phase2h.yaml` | `scripts/run_phase2h_external_validation.py` |
| Phase 2I | `configs/phase2i.yaml` | `scripts/run_phase2i_spot_futures.py` |
| Midterm figures | frozen phase outputs | `scripts/build_midterm_evidence_figures.py` |

## 5. Main numerical controls

- Common principal seed: `20260915`
- Phase 2C synthetic design: effective T=1000, 16 starts
- Phase 2D: four chains; production posterior artifacts only
- Phase 2F/H/I posterior integration: fixed-seed equal-per-chain subsets
- Phase 2G horizons: 1, 3, 6 months; expanding-window release-safe design
- Phase 2I analysis end: 2025-09 even though raw futures audit extends later

## 6. Ignored artifacts

- Phase outputs: `outputs/phase1/`, `outputs/phase2/`
- Midterm rendered figures/documents/slides: `outputs/midterm/`
- Commercial raw/interim data: `data/raw/commercial/`, `data/interim/industry/`, `data/processed/industry/`
- Posterior draws (`*.npz`) remain under ignored `outputs/phase2/phase2d/`
- GFEX five-minute/tick raw files remain outside the repository; only code/config/memo are tracked

## 7. Reproduction order

Do not rerun completed heavy stages merely to rebuild the report. Read frozen CSVs and memos first. For a clean full scientific rerun, follow Phase 1A-1 → 1A-2 → 1B → 2A → 2B → 2C → 2D → 2E → 2F → 2G → 2H → 2I, respecting each config and Data Freeze hash gate. Generate the ten main figures only after all underlying artifacts exist.

## 8. Safety assertions

- Commercial raw data committed: NO
- Posterior raw artifacts committed: NO
- Futures raw files committed: NO
- Generated outputs committed: NO
- 2025-10+ observations used in the core model: NO
- Data Freeze modified by Phase 2I/2J: NO
- Credentials committed: NO
