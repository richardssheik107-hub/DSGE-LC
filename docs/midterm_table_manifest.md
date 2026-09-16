# Midterm Table Manifest

| Table | Contents | Authoritative path | Main figures / claims supported | Status |
|---|---|---|---|---|
| Table 1 | Core data definitions and coverage | `data/metadata/core_common_sample_audit.csv`；`docs/data_dictionary.md` | Data Freeze / sample | FROZEN |
| Table 2 | Descriptive statistics | `outputs/phase1/tables/descriptive_statistics_levels.csv`；`descriptive_statistics_growth.csv` | market background | FROZEN |
| Table 3 | Reduced-form baseline forecasting | `outputs/phase1/baseline_results/baseline_metrics.csv` | benchmark context | FROZEN |
| Table 4 | Baseline posterior estimates | `outputs/phase2/phase2d/baseline_posterior_summary.csv` | parameter signs / weak directions | FROZEN |
| Table 5 | MCMC convergence | `outputs/phase2/phase2d/rhat_ess_diagnostics.csv`；`phase2d_gate_summary.csv` | numerical credibility | FROZEN |
| Table 6 | Price FEVD | `outputs/phase2/phase2e/fevd_price_summary.csv` | residual/cost/demand/supply shares | FROZEN |
| Table 7 | Historical episode contributions | `outputs/phase2/phase2f/episode_net_contributions.csv` | 2021–2022 / 2023 / 2024–2025 | FROZEN |
| Table 8 | Strict structural OOS | `outputs/phase2/phase2g/structural_oos_metrics.csv`；`structural_oos_u2_table.csv` | competitive forecasting | FROZEN |
| Table 9 | External validation | `outputs/phase2/phase2h/external_validation_correlations.csv` | inventory/cost state validity | FROZEN |
| Table 10 | Spot-futures summary | `outputs/phase2/phase2i/phase2i_result_summary.csv`；`lead_lag_summary.csv`；`basis_inventory_summary.csv` | preliminary futures extension | FROZEN |
| Table 11 | Robustness and warning registry | `docs/midterm_claim_registry.md` | all bounded claims | FROZEN |

All CSV artifacts are generated outputs and remain ignored. Reported values must be copied or programmatically read from these paths; memory-based manual substitution is not accepted.
