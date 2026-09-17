# 文档导航：基线、深化、学位稿

2026-09-17更新。当前入口已从R2/R3出版收尾转为学位论文深化，原研究与出版记录保留。

## 当前必读

- [当前状态](CURRENT_STATUS.md)
- [本轮全仓基线审计](audits/2026_09_17_baseline_repository_audit.md)
- [深化到定稿计划](plans/thesis_deepening_2026_2028.md)
- [四项比较协议草案](protocols/thesis_comparison_protocol_v1.md)
- [文献补读与候选](references/literature_expansion_20260917.md)
- [学位论文八章蓝图](thesis/degree_thesis_blueprint.md)

## 可复用科学证据

| 内容 | 入口 |
|---|---|
| 核心数据 | [入库审计](industry_data_ingestion_audit.md)、[二次资料](new_excel_secondary_data_audit.md) |
| 前置/基准 | [描述](phase1_data_diagnostics_memo.md)、[机制](phase1a2_mechanism_diagnostics_memo.md)、[预测基准](phase1b_baseline_results_memo.md) |
| 结构/估计 | [M0设计](phase2a_structural_mvp_spec.md)、[Kalman](phase2b_kalman_likelihood_validation.md)、[估计预检](phase2c_estimation_preflight.md)、[后验](phase2d_bayesian_estimation.md) |
| R1修正 | [后验诊断](audits/r1_posterior_diagnostics.md)、[HD/FEVD](audits/r1_historical_and_fevd.md)、[期现](audits/r1_spot_futures_alignment.md)、[测量](audits/r1_measurement_and_units.md)、[预测/外部](audits/r1_forecast_and_external_validation.md)、[最终验收](audits/r1_final_validation.md) |
| 旧任务状态 | [A01—A12](plans/correction_backlog.md)，与新D00—D08区分 |

旧阶段memo用于追溯，不能覆盖R1结论降级。PRIVATE outputs不在clone中，文献和配置存在不能证明实验已重跑。

## 稿件与出版

[稿件版本说明](thesis/README.md) · [R3短稿](thesis/reference_style_manuscript.md) · [R3单栏验收](audits/r3_single_column_layout.md) · [R3本地出版说明](plans/r3_reference_style_completion.md)

[R2历史稿](thesis/advisor_draft.md) · [R2图版验收](audits/r2_full_figure_draft.md) · [导师反馈台账](thesis/advisor_feedback_tracker.md)

R3已经出版验收，不重复作为下一研究阶段；如需修新排版可使用原R3说明，但不能用旧提示词覆盖当前深化计划。

## 文献与学校

[原20项证据登记](references/verified_literature_20260916.md) · [生猪方法对照](references/hog_paper_comparison.md) · [例文体例对照](thesis/reference_style_map.md)

原20项核验层级不变；本轮8条候选未自动插入正文。学校/学位类别/模板和量化要求需实际资料核定，不抄其他学院条件。

## 治理与历史

[研究总计划](research_master_plan.md) · [定稿路线入口](plans/thesis_finalization_2026_2028.md) · [复现](REPRODUCIBILITY.md) · [架构](repository_architecture.md)

机器台账：`configs/research_baseline_20260917.json`、`configs/thesis_workplan.json`、`configs/finalization_tasks.json`。治理检查命令：`python scripts/audit_thesis_governance.py --check-git-baseline`。只检验元数据/证据路径，不代替统计和行政验收。

中期源稿、旧日期快照、R2交接提示词和早期蓝图保持历史路径。旧NEXT与现行路线冲突时以CURRENT_STATUS及thesis_workplan为准，不删除历史记录。
