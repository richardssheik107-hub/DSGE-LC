# 文档导航

导航更新：2026-09-17。旧版见 Git 提交 `ef2eb3785b8dad58b7d4532298f5a184972b8260`。阶段历史 memo 保留，R1-6 结果登记及11份中期源稿已按[最终验收](audits/r1_final_validation.md)同步；R2本地导师全图讨论版已按[逐页验收](audits/r2_full_figure_draft.md)完成。当前判定以[最新状态](CURRENT_STATUS.md)为准，学校正式提交仍不就绪。

## 当前入口（优先阅读）

- [CURRENT_STATUS](CURRENT_STATUS.md)：当前判定、已做/未做边界。
- [R2论文目录](thesis/README.md)：九章正文、导师说明、真实图版来源及反馈台账。
- [R2文献预检](audits/r2_literature_preflight.md)、[图版验收](audits/r2_full_figure_draft.md)与[最终交接](audits/r2_final_handoff.md)：真实引用层级、本地DOCX/PDF、逐页检查与准备度。
- [R1 阶段状态](audits/r1_stage_status.md)：R1-0—R1-6 实际证据、技术与解释分级。
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

阶段 memo 保持当时结果，**与当前审计一起阅读**。例如旧“无 HIGH 敏感性”不能替代 R1-2 修正分类器后对 18 个组合的重新审查；本轮虽未出现 HIGH，后期六项仍为 `AMBIGUOUS`。

## R1 修正证据（覆盖受影响旧叙述，不覆盖历史文件）

| 问题 | 现行证据与必须保留的限制 |
|---|---|
| A01 后验 | [独立诊断](audits/r1_posterior_diagnostics.md)：七规格门槛通过；baseline 来源为 `PASS_RECONSTRUCTED`；无重采样 |
| A02/A05 历史与 FEVD | [历史/FEVD审计](audits/r1_historical_and_fevd.md)：均值可加总、边际中位数不必加总；后期六项 `AMBIGUOUS`，历史解释需复核 |
| A03 期现 | [同区间审计](audits/r1_spot_futures_alignment.md)：月频同端点 +1 约 0.526 且峰转同期；日频 +1 约 0.475 仅描述性 |
| A04/A06 测量/单位 | [scaler与单位审计](audits/r1_measurement_and_units.md)：保留旧估计输入；共同支持期仅构建；价格状态是标准化月度 dlog，库存是潜在压力指数 |
| A07/A08 预测/外部 | [预测与外部审计](audits/r1_forecast_and_external_validation.md)：历史 OOS 非真正前瞻；库存变化量支持弱，成本验证有共同原料价格成分 |
| R1-6 结论与材料 | [主张修订](audits/r1_claim_revision.md)和[最终验收](audits/r1_final_validation.md)：85 条私有聚合结果、10 条主张复核、11 份中期源稿同步；正式论文门槛仍开放 |

R1 的机器可核中间表及结果登记位于 Git 忽略的 `outputs/revisions/R1_20260916_190253/`；该私有目录不是仓库 clone 的一部分，不能只凭公开 memo 重建商业数据或后验。

## 中期工作源稿（R1-6 已同步，不是正式交付件）

[报告](midterm_report_2026.md) · [演示源](midterm_slides_2026.md) · [讲稿](midterm_speaker_notes_2026.md) · [问答](midterm_defense_qa.md) · [一分钟](midterm_one_minute_summary.md) · [三分钟](midterm_three_minute_summary.md) · [旧检查表快照](midterm_defense_checklist.md)

[证据矩阵](midterm_evidence_matrix.md) · [原论断登记](midterm_claim_registry.md) · [图清单](midterm_figure_manifest.md) · [表清单](midterm_table_manifest.md) · [结果摘要](midterm_result_digest.md) · [复现记录](midterm_reproducibility_manifest.md)

R1-6 的受影响文件已在开头标明修订日期、范围、受影响结论及 Git 旧版定位，并在正文替换过时强结论。R2论文DOCX/PDF已在本地实排，但学校格式、关键引文全文及导师反馈仍需单独验收。中期PPTX的正式学校版仍待要求明确；图文件存在不等于图内结果已最终验收。

## 计划与历史

- [研究总计划](research_master_plan.md)、[中期剩余周计划](midterm_plan_2026_11.md)：现在的行动顺序。
- [参考文献说明](REFERENCE_HOG_PAPER.md)、[参考指导路线](hog_mfdsge_guided_execution_plan.md)：核验后的定位。
- [旧项目状态](project_status_2026_09_15.md)、[旧中期ready记录](midterm_readiness_2026.md)：保留的历史快照，不是当前准入结论。
- [早期生猪指导蓝图原样副本](archive/hog_mfdsge_blueprint_2026_09_15.md)：候选方程/旧日期/旧门槛不得覆盖现行规范。
- public acquisition、OPD、high-value data等旧报告继续保留在原路径，当前缺口见元数据与完整计划。

## 维护规则

以实际关闭证据更新当前状态、修正清单和阶段勘误；不要只在旧文档末尾追加“COMPLETE”而保留互相冲突的 NEXT。数据、scaler、模型、prior、诊断和输出版本分开追踪。不得为增加测试数量而锁定错误算法，亦不得把历史阶段 PASS 当作论文提交许可。
