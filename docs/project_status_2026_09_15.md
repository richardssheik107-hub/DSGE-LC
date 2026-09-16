# Project Status — 2026-09-15

本页是仓库的**当前状态源**，用于回答“现在做到哪里、哪些结果已冻结、还缺什么、下一步是什么”。历史数据获取与阶段审计请见各自 memo，不应覆盖本页的当前状态。

## 1. Executive summary

截至 2026-09-15：

- Data Freeze v1 已锁定并支持主实验；不再等待 Data Freeze v2 才继续研究。
- Phase 1A-1、1A-2、1B 已完成，数据诊断、机制预检和 RW/AR/VAR/BVAR 基线均已形成。
- Phase 2A、2B、2C、2D 已完成：结构 MVP、Kalman/likelihood、constrained MLE 和 Bayesian posterior convergence / identification 均已通过阶段门槛。
- 当前主模型是 `M0_CORE5`；当前估计规格是 `M0_FULL14`。
- Phase 2E 已修复 sensitivity artifact persistence gap，六套 posterior IRF/FEVD sensitivity propagation 全部完成并通过。
- Phase 2F posterior historical decomposition 已完成；shock reconstruction、decomposition identity 和 critical sensitivity gates 全部通过。
- Phase 2G strict Structural OOS 已完成：H1 优于 RW，H3/H6 优于 AR，三期限均优于 unrestricted VAR，但 BVAR 仍是最强预测 challenger；结果定位为 competitive forecasting 而非 forecast dominance。
- Phase 2H key robustness / external validation 已完成：physical inventory 与 latent `n_t` 同向且显著跟踪，direct route-cost changes 与 `c_t` 高度同步；inventory correlation magnitude 对 `rho_n` 敏感。
- Phase 2I preliminary spot-futures extension 已完成：36 个 GFEX 5-minute contracts 通过只读 audit，roll-safe volume-main series 覆盖 2023-07—2025-09；daily/monthly diagnostics 提供 preliminary futures-leading evidence，但 I(1) gate 未通过，不能声称 cointegration / VECM，basis–inventory rank relation 不稳健。
- Phase 2J midterm evidence freeze 已完成：evidence matrix、claim registry、10 张主图、11 张主表、result digest 与 reproducibility manifest 已冻结。
- **CORE MIDTERM EXPERIMENTS: FROZEN.** M1 真实数据估计中期前不再启动；下一阶段为 Phase 3A midterm research report。

项目实际进度已超过原中期计划约第 6 周（10 月中旬）的任务深度；posterior mixing 已通过，但 prior/fixed-assumption sensitivity 与 inventory-price weak direction 必须继续随结构结果报告。

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
| Phase 2D | **COMPLETE** | Bayesian posterior convergence PASS；sensitivity completed | complete with warnings |
| Phase 2E IRF / FEVD | **COMPLETE** | core price signs stable；all FEVD shifts LOW | complete |
| Phase 2F Historical decomposition | **COMPLETE** | episode attribution stable；numerical audits PASS | complete |
| Phase 2G Structural OOS | **COMPLETE** | strict expanding-window MAP OOS；H1 U2=0.914, H3=1.240, H6=1.131 | key robustness / external validation |
| Phase 2H External validation | **COMPLETE** | inventory Pearson median 0.650 baseline；cost-route Pearson 0.988 | complete with `rho_n` magnitude warning |
| Phase 2I Preliminary spot-futures | **COMPLETE** | 36 contracts；535 daily / 27 monthly observations；lead-lag peaks at +1；no justified cointegration/VECM | complete with short-sample / timing / `rho_n` warnings |
| Phase 2J Midterm evidence freeze | **COMPLETE** | claim boundaries and 10-figure / 11-table evidence chain frozen | complete |
| Phase 3A Midterm report | **NEXT** | 19-section Chinese thesis-core draft | use frozen evidence only |

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

Phase 2C selected **`M0_FULL14`** with 14 Bayesian free parameters:

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

Phase 2D Bayesian results:

- baseline four-chain posterior passed after one equal extension to 18,000 production draws per chain;
- max R-hat `1.00788`, min bulk ESS `627.90`, min tail ESS `484.18`, max MCSE/SD `0.03991`;
- flat and moderate-shrink prior sensitivity specifications converged without broad prior domination;
- all four fixed-assumption specifications converged, with material `rho_d/sigma_d` battery-noise sensitivity and `b_n` sensitivity to fixed `rho_n`;
- phase decision: **READY FOR POSTERIOR STRUCTURAL RESULTS — YES, WITH WARNINGS**.

This establishes a converged posterior under the audited specifications, not final causal or structural certainty.

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

Higher battery measurement noise causes material posterior drift in `rho_d/sigma_d`, while fixed `rho_n` materially affects `b_n`. These remain explicit warnings rather than reasons to select a preferred fixed value after seeing the data.

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

## 10. Phase 2G Structural OOS — COMPLETE

Phase 2E artifact recovery/sensitivity and Phase 2F historical decomposition are complete. Phase 2G then ran a strict expanding-window structural OOS with training-only scaling and release-safe Output/Battery treatment. Structural M0 has U2 `0.914 / 1.240 / 1.131` at H1/H3/H6: it beats RW at H1, AR at H3/H6, and VAR at all horizons, but not BVAR. The result supports a `mechanism + competitive forecasting` contribution, not universal forecast superiority.

The key robustness round is complete. Baseline latent inventory pressure has Pearson correlation `0.650` with log SMM monthly-mean inventory (28 months), remaining positive under `rho_n=.50/.95` but with large magnitude shifts; the cost state has Pearson `0.988` with SMM spodumene-route production-cost dlog (35 months).

Phase 2I then used only the already-held 28.7 MB five-minute GFEX files. The deterministic volume-main series has 535 frozen-window trading days and seven audited switches. July 2023 is explicitly treated as a partial listing month and excluded from comparable monthly-return inference. Monthly and daily return correlations both peak at lag `+1` (`0.710` monthly Pearson; `0.475` daily Pearson), and HAC lag tests point from futures to subsequent spot assessments rather than the reverse. This is preliminary price-discovery evidence, not a definitive timing claim. The 27-month price levels fail the fixed I(1) gate, so Engle–Granger and VECM are not run. Contemporaneous basis–inventory Pearson medians are positive (`0.119 / 0.187 / 0.399` for `rho_n=.50/.80/.95`), but Spearman direction is not stable.

## 11. Timeline to midterm

The original schedule targeted State-Space + Kalman + likelihood by about 2026-10-19. These components, constrained MLE preflight and Phase 2D Bayesian convergence are already complete by 2026-09-15.

Current revised sequence:

- **complete:** Phase 2E artifact recovery and full posterior IRF/FEVD sensitivity;
- **complete:** Phase 2F historical decomposition of major episodes;
- **complete:** Phase 2G strict structural OOS;
- **complete:** Phase 2H key robustness / external validation;
- **complete:** Phase 2I preliminary spot-futures extension using existing GFEX data;
- **complete:** Phase 2J midterm evidence / claim / figure / table freeze;
- **next:** Phase 3A midterm research report / thesis-core draft;
- **by 2026-11-10:** freeze major experiments and switch to result organization / midterm materials.

## 12. Source-of-truth order

When historical documents conflict, use this order:

1. `docs/project_status_2026_09_15.md` — current project state.
2. `README.md` — concise current navigation.
3. latest phase memo (`phase2d_bayesian_estimation.md`) — stage-specific evidence.
4. `docs/data_dictionary.md` — current data definitions and usage layers.
5. `docs/high_value_industry_data_update.md` / `public_gap_closure_report.md` — latest data-layer detail.
6. older acquisition / availability / OPD reports — historical snapshots only.

## 13. Current decision

**Stop broad data/model expansion. Keep Data Freeze v1 immutable. Phase 2E—2J are complete. CORE MIDTERM EXPERIMENTS ARE FROZEN. Phase 3A report drafting is next.**

Structural OOS, key external validation, and the bounded preliminary spot-futures extension have been run and synthesized into the evidence/claim freeze. A full structural futures model and `M1` real-data estimation have not been run and are outside the remaining pre-midterm scope.

## 14. Repository lineage clarification

The canonical remote `main` lineage is:

```text
f2fd8928e1804b04f10be64357a77e001b5df7ef  Phase 2C
→ 5e1407f23f6532a4191b65e34446cf08401bd654  repository/docs/reproducibility refresh
→ 9d4bf73a0307afecbdce4ab8bc497c976dbc452b  Phase 2D Bayesian estimation
```

The Phase 2D implementation was initially reported from a local lineage that started at `f2fd892`, producing a local commit id `88faa8...`. Before remote integration, the repository-maintenance commit `5e1407f...` had already advanced `main`. Reapplying/integrating the same Phase 2D change on top of that parent necessarily changed the Git commit SHA to `9d4bf73...`.

Therefore:

- `9d4bf73...` is the canonical remote Phase 2D commit;
- `88faa8...` is a pre-integration local commit identifier and should not be used as a remote source-of-truth reference;
- this SHA difference is a Git-history/parent difference, not evidence of a changed Data Freeze or a different Phase 2D statistical result.
