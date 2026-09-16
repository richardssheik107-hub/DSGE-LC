# 文档导航

## 当前入口（优先阅读）

- [CURRENT_STATUS](CURRENT_STATUS.md)：当前判定、P0任务、已做/未做边界。
- [全论文与仓库审计](audits/2026_09_16_research_audit.md)：代码、口径、结论及复现问题。
- [生猪参考稿对照](references/hog_paper_comparison.md)：35页修改稿的实际方法、差异与核对事项。
- [修正清单](plans/correction_backlog.md)：每个发现的关闭条件。
- [直到定稿的完整计划](plans/thesis_finalization_2026_2028.md)：中期前逐周、2027提前路线与2028主路线。
- [复现指南](REPRODUCIBILITY.md)及[仓库架构](repository_architecture.md)。

## 模型与阶段证据

| 范围 | 文档 |
|---|---|
| 数据 | [数据字典](data_dictionary.md)、[正式入库](industry_data_ingestion_audit.md)、[二次工作簿审计](new_excel_secondary_data_audit.md) |
| 探索/基准 | [描述统计](phase1_data_diagnostics_memo.md)、[机制诊断](phase1a2_mechanism_diagnostics_memo.md)、[基准预测](phase1b_baseline_results_memo.md) |
| 结构/数值 | [2A规格](phase2a_structural_mvp_spec.md)、[2A预检](phase2a_identification_precheck.md)、[2B](phase2b_kalman_likelihood_validation.md)、[2C](phase2c_estimation_preflight.md) |
| 后验 | [2D](phase2d_bayesian_estimation.md)、[artifact恢复](phase2e_artifact_recovery.md) |
| 结构结果 | [2E IRF/FEVD](phase2e_posterior_irf_fevd.md)、[2F历史分解](phase2f_historical_decomposition.md) |
| 预测/验证 | [2G OOS](phase2g_structural_oos.md)、[2H外部验证](phase2h_external_validation.md)、[2I期现](phase2i_spot_futures.md) |

阶段memo保持当时结果，**与当前审计一起阅读**。例如旧“无HIGH敏感性”不能覆盖审计发现的分类程序没有HIGH分支。

## 中期工作草稿（需按审计修订，不是终稿）

[报告](midterm_report_2026.md) · [演示源](midterm_slides_2026.md) · [讲稿](midterm_speaker_notes_2026.md) · [问答](midterm_defense_qa.md) · [一分钟](midterm_one_minute_summary.md) · [三分钟](midterm_three_minute_summary.md) · [检查表](midterm_defense_checklist.md)

[证据矩阵](midterm_evidence_matrix.md) · [原论断登记](midterm_claim_registry.md) · [图清单](midterm_figure_manifest.md) · [表清单](midterm_table_manifest.md) · [结果摘要](midterm_result_digest.md) · [复现记录](midterm_reproducibility_manifest.md)

这些原始材料未被本轮无痕改写；使用前落实审计的单位、加总、诊断和期現收益口径修正。图文件存在不等于图内结果已最终验收。

## 计划与历史

- [研究总计划](research_master_plan.md)、[中期剩余周计划](midterm_plan_2026_11.md)：现在的行动顺序。
- [参考文献说明](REFERENCE_HOG_PAPER.md)、[参考指导路线](hog_mfdsge_guided_execution_plan.md)：核验后的定位。
- [旧项目状态](project_status_2026_09_15.md)、[旧中期ready记录](midterm_readiness_2026.md)：保留的历史快照，不是当前准入结论。
- [早期生猪指导蓝图原样副本](archive/hog_mfdsge_blueprint_2026_09_15.md)：候选方程/旧日期/旧门槛不得覆盖现行规范。
- public acquisition、OPD、high-value data等旧报告继续保留在原路径，当前缺口见元数据与完整计划。

## 维护规则

先更改当前状态与修正清单，再追加带日期的阶段勘误；不要只在旧文档末尾追加“COMPLETE”而保留互相冲突的NEXT。数据、scaler、模型、prior、诊断和输出版本分开追踪。不得为增加测试数量而锁定错误算法。
