# Phase 2H External Validation of Inventory and Cost States

## 1. Objective

Phase 2H performs the bounded robustness round required before the midterm freeze. It does not re-estimate or redesign `M0_CORE5`. Instead, it asks whether two structural blocks line up with independent industry series that were deliberately kept outside Data Freeze v1.

Primary validation targets:

- latent inventory-pressure state `n_t` versus SMM total lithium-carbonate social inventory;
- latent cost state `c_t` versus SMM route-specific lithium-carbonate production-cost changes.

The canonical model sample remains 2021-01—2025-09 (`N=57`) and the Data Freeze v1 SHA-256 remains `9146B3C858AA0F1BE5FA59720B0446515F0A21C60FA032712F76DD248AEAB7F5`.

## 2. Posterior propagation

Baseline validation uses a deterministic equal-per-chain subset of 4,000 Phase 2D posterior draws (1,000 per chain). Inventory sensitivity additionally uses 1,000 draws each from the already-converged `RHO_N_050` and `RHO_N_095` posterior artifacts.

For each selected draw, the frozen Kalman filter and RTS smoother recover conditional state means. No new MLE/MAP/MCMC estimation is performed. No validation series enters the likelihood or measurement equation.

## 3. Validation data

Inventory validation uses SMM monthly total social inventory from 2023-06 through 2025-09, 28 overlapping months. The primary series is the monthly mean total inventory; month-end total inventory is a secondary check. Both are used in log levels because `n_t` is a persistent stock/pressure state rather than a monthly flow.

Cost validation uses SMM spodumene-route and lepidolite-route lithium-carbonate production costs. Monthly log changes are aligned contemporaneously with `c_t`, because the structural cost measurement is itself a monthly change state. The usable overlap is 2022-11 through 2025-09, 35 months.

## 4. Inventory-state result

Baseline `n_t` has a clearly positive external relationship with physical inventory:

| Validation series | Pearson median [5%,95%] | Spearman median [5%,95%] |
|---|---:|---:|
| log monthly-mean inventory | 0.650 [0.643, 0.654] | 0.542 [0.532, 0.542] |
| log month-end inventory | 0.659 [0.652, 0.662] | 0.550 [0.541, 0.551] |

For all posterior draws in the baseline subset, the correlations are positive. This provides independent support for interpreting `n_t` as an inventory / supply-demand pressure state rather than an arbitrary latent factor.

The magnitude is, however, highly sensitive to fixed `rho_n`, exactly as Phase 2D warned. For monthly-mean inventory, the Pearson median is about `0.388` under `rho_n=.50`, `0.650` under the baseline `.80`, and `0.891` under `.95`. The direction is robust; the quantitative strength is not.

## 5. Inventory timing diagnostic

The predeclared contemporaneous comparison remains the primary result. A secondary ±3 month lag scan shows Pearson correlations of roughly `0.559, 0.575, 0.610, 0.650, 0.689, 0.645, 0.489` for lags -3 through +3, where +1 means the latent state at month `t` is compared with measured inventory at `t+1`.

The modest peak at +1 month is economically plausible for a latent imbalance state that can lead subsequently reported/realized physical inventory. It is treated as a timing diagnostic, not as a post-hoc redefinition of the primary relationship.

## 6. Cost-state result

The cost block receives strong external validation. Baseline `c_t` versus SMM spodumene-route production-cost dlog has Pearson `0.988` and Spearman `0.982`. Against the alternative lepidolite-route cost dlog, Pearson is `0.679` and Spearman `0.787`.

The lag scan is sharply contemporaneous: the spodumene-route Pearson correlation is `0.988` at lag 0, about `0.466/0.487` at -1/+1, and near zero at ±2/±3. This timing pattern is consistent with a contemporaneous monthly cost-pressure state.

## 7. Interpretation limits

The cost result should not be oversold as a fully independent causal identification exercise. SMM route production cost is economically constructed from upstream raw-material costs, so its very high correlation with the SC6-anchored `c_t` primarily validates the chosen cost proxy and timing convention.

The inventory result is more informative for the latent-state interpretation because physical social inventory was not used in estimation. Still, only 28 overlapping months are available, and the correlation magnitude moves strongly with fixed `rho_n`. Therefore the defensible conclusion is: the inventory-pressure state has the expected external direction and meaningful tracking ability, but its quantitative loading remains weakly identified.

The inventory methodology break recorded for 2026-05 occurs after the frozen validation window and therefore does not contaminate this Phase 2H comparison.

## 8. Numerical and safety audit

All 6,000 smoother evaluations used here are finite. Kalman jitter is zero, smoothed covariance numerical minima are at machine-zero scale, and no new data were spliced into the canonical measurement set. Validation inputs remain outside Data Freeze v1.

The Phase 2H gates are:

- Freeze unchanged: PASS;
- smoother finite: PASS;
- inventory external sign: PASS;
- cost external sign: PASS;
- validation strength: PASS;
- `PHASE_2H_READY`: YES.

## 9. Phase decision

**PHASE 2H KEY ROBUSTNESS / EXTERNAL VALIDATION: COMPLETE — PASS WITH INVENTORY-MAGNITUDE SENSITIVITY WARNING.**

The robustness round strengthens the main thesis narrative: the cost block is strongly aligned with direct production-cost data, while the latent inventory-pressure block tracks physical inventory in the expected direction but remains quantitatively sensitive to `rho_n`.

This result does not justify replacing the latent inventory state with observed inventory, changing `rho_n` after seeing the validation data, or expanding the core model. The frozen `M0_CORE5/M0_FULL14` remains the midterm primary specification.

**Next canonical stage: preliminary spot–futures extension, provided existing GFEX data can be located and audited without redownloading.**