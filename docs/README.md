# Documentation Index

本目录同时包含**当前 source of truth、阶段结果 memo、数据审计和历史获取记录**。阅读时不要把早期 acquisition report 中的旧缺口当成当前状态。

## A. Current source of truth

1. [`project_status_2026_09_15.md`](project_status_2026_09_15.md) — 当前总状态：做到哪里、主模型、主要风险、下一步。
2. [`../README.md`](../README.md) — 仓库总览、当前阶段和快速导航。
3. [`research_master_plan.md`](research_master_plan.md) — 当前执行路线与长期模型愿景。
4. [`midterm_plan_2026_11.md`](midterm_plan_2026_11.md) — 中期答辩时间表，已按实际提前进度更新。
5. [`data_dictionary.md`](data_dictionary.md) — 当前数据定义、coverage、usage layer 和版本规则。
6. [`repository_architecture.md`](repository_architecture.md) — 代码、脚本、数据和配置之间的依赖关系。

若这些文件与更早文档冲突，以 `project_status_2026_09_15.md` 和最新 phase memo 为准。

## B. Active structural-model evidence

- [`phase2a_structural_mvp_spec.md`](phase2a_structural_mvp_spec.md) — `M0_CORE5` / `M1_CAPACITY6` 方程、状态、观测和归一化。
- [`phase2a_identification_precheck.md`](phase2a_identification_precheck.md) — stability / observability / reachability / local Jacobian 预检。
- [`phase2b_kalman_likelihood_validation.md`](phase2b_kalman_likelihood_validation.md) — Kalman filter、RTS smoother、likelihood 和 numerical audit。
- [`phase2c_estimation_preflight.md`](phase2c_estimation_preflight.md) — constrained MLE、multi-start、profile、Hessian/OPG 和 weak-ID 结论。
- [`phase2d_bayesian_estimation.md`](phase2d_bayesian_estimation.md) — proper prior、z-space MCMC、Jacobian、多链收敛、prior/fixed-assumption sensitivity 与 posterior identification。
- [`phase2e_artifact_recovery.md`](phase2e_artifact_recovery.md) — 六套 sensitivity posterior deterministic recovery 与完整 integrity audit。
- [`phase2e_posterior_irf_fevd.md`](phase2e_posterior_irf_fevd.md) — 完整 posterior IRF/FEVD sensitivity propagation 与 structural-results gate。
- [`phase2f_historical_decomposition.md`](phase2f_historical_decomposition.md) — posterior shock reconstruction、历史分解、episode attribution 与 sensitivity。
- [`phase2g_structural_oos.md`](phase2g_structural_oos.md) — strict expanding-window structural OOS、RW/AR/VAR/BVAR 对比与 leakage audit。
- [`phase2h_external_validation.md`](phase2h_external_validation.md) — SMM inventory / route-cost external validation 与 inventory-persistence sensitivity。
- [`phase2i_spot_futures.md`](phase2i_spot_futures.md) — 5-minute GFEX contract audit、roll-safe main contract、期现 basis、lead-lag 与 inventory sensitivity。
- [`midterm_evidence_matrix.md`](midterm_evidence_matrix.md) — 研究问题到证据、强度、warning 和可写 claim 的映射。
- [`midterm_claim_registry.md`](midterm_claim_registry.md) — STRONG / PARTIAL / WEAK / NOT_SUPPORTED 结论边界。
- [`midterm_figure_manifest.md`](midterm_figure_manifest.md) / [`midterm_table_manifest.md`](midterm_table_manifest.md) — 中期主图主表冻结。
- [`midterm_result_digest.md`](midterm_result_digest.md) — 3–5 页导师速览版结果链。
- [`midterm_reproducibility_manifest.md`](midterm_reproducibility_manifest.md) — SHA、commits、configs、runners、seeds 与 ignored artifacts。
- [`midterm_report_2026.md`](midterm_report_2026.md) — 19-section 中期研究报告 / thesis-core draft，数字与结论边界来自 frozen evidence。
- [`midterm_slides_2026.md`](midterm_slides_2026.md) / [`midterm_speaker_notes_2026.md`](midterm_speaker_notes_2026.md) — 18页答辩源文件与逐页讲稿。
- [`midterm_defense_qa.md`](midterm_defense_qa.md) — 40个答辩问题、直接回答、依据和限制。
- [`midterm_one_minute_summary.md`](midterm_one_minute_summary.md) / [`midterm_three_minute_summary.md`](midterm_three_minute_summary.md) — 压缩汇报版本。
- [`midterm_defense_checklist.md`](midterm_defense_checklist.md) — 数据、测试、图表、措辞和Git交付检查。

**Phase 2E—2J、Phase 3A 与 Phase 3B 均已完成，CORE MIDTERM EXPERIMENTS 已冻结。** 下一阶段是 Final Midterm Readiness Audit。

## C. Phase 1 empirical results

- [`phase1_data_diagnostics_memo.md`](phase1_data_diagnostics_memo.md) — 描述统计、统一变换、异常保留、基础图形与同期相关。
- [`phase1a2_mechanism_diagnostics_memo.md`](phase1a2_mechanism_diagnostics_memo.md) — stationarity / break / lead-lag / mechanism diagnostics。
- [`phase1b_baseline_results_memo.md`](phase1b_baseline_results_memo.md) — RW / AR / VAR / BVAR expanding-window OOS。
- [`phase1_experiment_plan.md`](phase1_experiment_plan.md) — Phase 1 当时的执行计划；属于阶段计划，不覆盖当前总路线。

## D. Data governance and audits

- [`industry_data_ingestion_audit.md`](industry_data_ingestion_audit.md) — 商业行业工作簿首次正式入库审计。
- [`high_value_industry_data_update.md`](high_value_industry_data_update.md) — robustness / validation 高价值产业数据更新。
- [`new_excel_secondary_data_audit.md`](new_excel_secondary_data_audit.md) — Dongwu / later battery workbook 二级审计。
- [`public_gap_closure_report.md`](public_gap_closure_report.md) — 公开尾部补缺与 reconciliation。
- [`public_data_acquisition_report.md`](public_data_acquisition_report.md) — 早期公开数据获取记录，属于历史快照。
- [`opd_data_availability_report.md`](opd_data_availability_report.md) — OPD 可用性审计；登录受限结论为历史数据源治理信息。
- [`opd_manual_search_checklist.md`](opd_manual_search_checklist.md) — OPD 手工登录搜索清单。

数据层的当前规则以 `data_dictionary.md` 与 `project_status_2026_09_15.md` 为准。

## E. Reference and long-term design

- [`REFERENCE_HOG_PAPER.md`](REFERENCE_HOG_PAPER.md) — 参考生猪 MF-DSGE 论文的仓库内简要说明。
- [`hog_mfdsge_guided_execution_plan.md`](hog_mfdsge_guided_execution_plan.md) — 从参考论文映射到锂价研究的详细执行框架。
- [`data_strategy_sparse_observations.md`](data_strategy_sparse_observations.md) — sparse observations + latent states 数据策略。

这些文件用于理论与长期设计，不表示所有候选模块已经实现。

## F. Reading order for a new collaborator

建议顺序：

```text
README.md
→ project_status_2026_09_15.md
→ data_dictionary.md
→ phase1b_baseline_results_memo.md
→ phase2a_structural_mvp_spec.md
→ phase2b_kalman_likelihood_validation.md
→ phase2c_estimation_preflight.md
→ phase2d_bayesian_estimation.md
→ midterm_report_2026.md
→ midterm_slides_2026.md
→ midterm_defense_qa.md
→ research_master_plan.md
→ midterm_plan_2026_11.md
```

## G. Documentation maintenance rule

- `project_status_YYYY_MM_DD.md`：当前状态快照，只写“现在是什么”。
- `phaseX...md`：阶段完成后的结果 memo；允许补充勘误或 lineage note，但不得无痕改写历史结论。
- `*_audit.md` / `*_report.md`：数据或实现审计，保留当时口径。
- `research_master_plan.md`：长期路线，可随 evidence 更新，但必须区分 current MVP 与 future extension。
- 旧文档中的“下一步”是历史语境，不自动覆盖最新 project status。
