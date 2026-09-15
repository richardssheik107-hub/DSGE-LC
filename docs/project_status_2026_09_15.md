# Project Status — 2026-09-15

本页是仓库的**当前状态源**，用于回答“现在做到哪里、哪些结果已冻结、还缺什么、下一步是什么”。历史数据获取与阶段审计请见各自 memo，不应覆盖本页的当前状态。

## 1. Executive summary

截至 2026-09-15：

- Data Freeze v1 已锁定并支持主实验；不再等待 Data Freeze v2 才继续研究。
- Phase 1A-1、1A-2、1B 已完成，数据诊断、机制预检和 RW/AR/VAR/BVAR 基线均已形成。
- Phase 2A、2B、2C 已完成：结构 MVP、Kalman/likelihood、constrained MLE / weak-ID preflight 均已通过阶段门槛。
- 当前主模型是 `M0_CORE5`；当前估计规格是 `M0_FULL14`。
- 当前下一阶段是 **Phase 2D Bayesian prior design + MCMC + convergence / posterior-identification diagnostics**。
- IRF、FEVD、历史分解、结构预测和 M1 真实数据估计仍处于 gate 之后，尚未开始。

项目实际进度已达到原中期计划约第 6 周（10 月中旬）的任务深度，较日历计划明显提前；但 posterior mixing、prior sensitivity、inventory-price weak direction 仍可能导致返工。

## 2. Milestone table

| Milestone | Status | Key result | Next dependency |
|---|---|---|---|
| Data Freeze v1 | **READY / LOCKED** | 2020-01—2025-09，69 个月，0 internal missing | none |
| Phase 1A-1 | **COMPLETE** | 描述统计、统一变换、季节性/异常审计 | complete |
| Phase 1A-2 | **COMPLETE** | ADF/KPSS/ZA、lead-lag、break、margin proxy | complete |
| Phase 1B | **COMPLETE** | RW/AR/VAR/BVAR expanding-window OOS | complete |
| Phase 2A | **COMPLETE** | `M0_CORE5` primary；`M1_CAPACITY6` extension | complete |
| Phase 2B | **COMPLETE** | Gaussian state-space、Kalman、RTS、likelihood | complete |
| Phase 2C | **COMPLETE** | `M0_FULL14` selected；synthetic + real multi-start pass | complete |
| Phase 2D | **NEXT** | Bayesian posterior + convergence / identification | Phase 2C warnings carried forward |
| Posterior IRF / FEVD | **GATED** | not run | Phase 2D convergence PASS |
| Historical decomposition | **GATED** | not run | posterior structural results PASS |
| Structural OOS / futures | **LATER** | not run | core structural model stable |

## 3. Data Freeze v1

Current canonical main-sample version:

- common start: `2020-01`
- common end: `2025-09`
- common months: `69`
- internal missing: `0`
- data gate: `GO`
- SHA256: `9146B3C858AA0F1BE5FA59720B0446515F0A21C60FA032712F76DD248AEAB7F5`

Core variables:

- `lc_spot`
- `lc_output`
- `spodumene_price`
- `battery_install`
- `usd_cny_mean`

Derived `spodumene_cny_t = spodumene_price × usd_cny_mean` is a RMB-denominated SC6 price proxy and **not** a full lithium-carbonate production-cost series.

## 4. Current structural model

Primary model: **`M0_CORE5`**

State order:

`[d, c, q, n, p]`

Observation order:

`[spot, ore_cost, output, battery]`

Shock order:

`[demand, cost, supply, price]`

Primary structural measurement set:

- `OBS_MIXED4`
- 2021-01—2025-09
- `N=57`
- Spot dlog
- Ore CNY dlog
- Output YoY log
- Battery YoY log

Current model positioning is **semi-structural linear state-space MVP**. It should not be described as a fully microfounded DSGE.

`M1_CAPACITY6` remains a pre-specified extension. Its slow-capacity mechanism is economically relevant but not part of the Phase 2D primary estimation specification.

## 5. Current estimation status

Phase 2C selected **`M0_FULL14`** with 14 future Bayesian free parameters:

`rho_d, rho_c, rho_q, rho_p, a_p, a_c, b_d, b_c, b_q, b_n, sigma_d, sigma_c, sigma_q, sigma_p`

Fixed sensitivity-only values in the baseline specification:

- `rho_n = 0.80`
- `battery_sd = 0.25`

Phase 2C key numerical results:

- synthetic recovery: 16/16 strict converged, normalized RMSE `0.019749`;
- real data: 32/32 finite optimizer successes;
- 28/32 solutions in the top cluster;
- best loglik: `-262.600888`;
- Powell cross-check and L-BFGS-B mode agree to numerical tolerance;
- Hessian and OPG are full rank but weakly conditioned.

This establishes a usable likelihood mode, not final statistical certainty.

## 6. Main empirical findings carried forward

The following are the most defensible current conclusions and should not be overstated as causal proof:

1. **Cost → Price: strongest reduced-form mechanism candidate.** Spot and RMB SC6 changes show the most stable short-horizon relationship.
2. **Demand: noisy latent anchor.** Battery installation should not be equated one-for-one with the structural demand shock.
3. **Short-run supply response: mixed evidence.** Reduced-form evidence was weak, but structural `a_p` has an interior Phase 2C likelihood profile; therefore it remains in `M0_FULL14`.
4. **Inventory pressure: economically useful but weakly identified.** `b_n` is near the lower region and interacts with `b_q` and `rho_p`.
5. **Slow capacity: extension, not current core.** Margin-to-future-output evidence supports testing it later, but current data do not justify making it part of the primary 14-parameter posterior.

## 7. Main risks

### 7.1 Weak curvature

- `a_c` is near the lower boundary and dominates the weakest Hessian direction.
- `b_n / b_q / rho_p` form an important weak direction.
- Hessian and OPG remain full rank, so this is weak identification rather than catastrophic rank failure.

### 7.2 Fixed measurement assumption sensitivity

Higher battery measurement noise caused larger parameter drift in Phase 2C. Phase 2D must include explicit posterior sensitivity rather than silently treating `battery_sd=0.25` as known truth.

### 7.3 Small structural sample

`OBS_MIXED4` has only 57 monthly observations. Bayesian posterior concentration must therefore be judged together with prior-to-posterior contraction, R-hat, ESS and prior sensitivity.

### 7.4 Linear-model limitation

The 2021–2022 surge and 2023 decline are extreme episodes. A linear stationary-deviation MVP may get mechanisms and timing broadly right without matching all nonlinear amplitudes. Nonlinear extensions remain conditional on evidence, not default next steps.

## 8. Remaining canonical data gaps to 2026-06

Data Freeze v2 target remains 2020-01—2026-06 (78 months) and is **NOT READY / NON-BLOCKING**.

Remaining strict canonical gaps:

- SMM SC6 CIF China: 2025-10, 11, 12; 2026-01, 02, 04, 05, 06.
- SMM LC output: 2025-10, 11, 12; 2026-03, 04, 05, 06 require direct verification of candidate actuals.
- SMM battery-grade LC spot: 2025-12, 2026-04, 05 require direct confirmation; 2026-06 requires complete-month confirmation.

Battery installation is already complete through 2026-06. Capacity, utilization, long inventory, investment and enterprise profit are not current blockers.

## 9. Public / robustness / validation layers

Public macro coverage is essentially complete through 2026-06 for FX, CPI, PPI, NEV, China Gov 3M/6M and battery installation.

Provider and usage layers remain separated:

- `A_CORE`: SMM core + battery + FX used by frozen main sample.
- `ROBUSTNESS`: Mysteel alternative prices, route output, filtered concentrate imports, LFP/NCM, trade auxiliary series.
- `VALIDATION_ONLY`: SMM inventory by methodology regime, route cost/profit short samples.
- `CANDIDATE`: Data Freeze v2 tail values and secondary transcriptions not yet canonical.

No provider may be silently spliced into the SMM canonical price series.

## 10. Immediate next phase — Phase 2D

Only the following should start next:

1. fine likelihood-profile refinement for near-boundary weak parameters where useful;
2. prior design independent of Phase 2C MLE centering;
3. auditable multi-chain Bayesian sampling;
4. rank-normalized split R-hat, bulk/tail ESS and MCSE diagnostics;
5. posterior boundary/stability and prior-to-posterior contraction analysis;
6. prior sensitivity and targeted `rho_n` / battery-noise sensitivity;
7. posterior predictive sanity checks.

IRF / FEVD / historical decomposition remain blocked until posterior convergence and identification diagnostics pass.

## 11. Timeline to midterm

The original schedule targeted State-Space + Kalman + likelihood by about 2026-10-19. These components plus constrained MLE preflight are already complete by 2026-09-15.

Current revised sequence:

- **now:** Phase 2D Bayesian estimation and convergence;
- **after Phase 2D PASS:** posterior IRF + FEVD and structural sign/economic consistency checks;
- **then:** historical decomposition of major episodes;
- **then:** structural OOS and robustness;
- **early November:** preliminary spot-futures extension if the core model is already stable;
- **by 2026-11-10:** freeze major experiments and switch to result organization / midterm materials.

## 12. Source-of-truth order

When historical documents conflict, use this order:

1. `docs/project_status_2026_09_15.md` — current project state.
2. `README.md` — concise current navigation.
3. latest phase memo (`phase2c...`, then future phase memos) — stage-specific evidence.
4. `docs/data_dictionary.md` — current data definitions and usage layers.
5. `docs/high_value_industry_data_update.md` / `public_gap_closure_report.md` — latest data-layer detail.
6. older acquisition / availability / OPD reports — historical snapshots only.

## 13. Current decision

**Stop broad data expansion. Keep Data Freeze v1 immutable. Enter Phase 2D.**

A Phase 2D failure would trigger a targeted estimation/specification revision, not a return to indiscriminate data hunting or automatic model expansion.
