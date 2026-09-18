# 文档导航：文献、经济方程与受保护基线

2026-09-18更新。当前优先D01，而非重新排版R3或直接运行更大模型。

## 最新研究入口

- [CURRENT_STATUS](CURRENT_STATUS.md)
- [45来源地图与阅读层级](references/industry_literature_map_20260918.md)
- [12张重点阅读卡](research/industry_model_reading_cards_20260918.md)
- [模块化28组候选关系v2](theory/lithium_modular_equation_blueprint_v2.md)
- [下一轮文献到模型任务](plans/industry_literature_to_model_20260918.md)
- [导师产业模型讨论稿](thesis/supervisor_industry_model_expansion_20260918.md)
- [本轮实际交付/测试审计](audits/2026_09_18_industry_literature_expansion.md)

## 前一轮五式基础

[逐式五问](research/equation_foundations_20260918.md) · [局部推导v1](theory/lithium_partial_equilibrium_v1.md) · [18来源登记](references/equation_evidence_20260918.md) · [机制门槛](plans/equation_design_gate_20260918.md) · [前批交付](audits/2026_09_18_equation_research.md)

原18来源与本批45来源有重叠；原论文20项引用也另有编号，不把三个表相加。候选不自动成为正式论文引用。

## 科学结果与修正

| 内容 | 入口 |
|---|---|
| 数据 | [入库审计](industry_data_ingestion_audit.md)、[二次资料](new_excel_secondary_data_audit.md) |
| 探索/基准 | [描述](phase1_data_diagnostics_memo.md)、[机制](phase1a2_mechanism_diagnostics_memo.md)、[基准预测](phase1b_baseline_results_memo.md) |
| 模型与估计 | [M0](phase2a_structural_mvp_spec.md)、[Kalman](phase2b_kalman_likelihood_validation.md)、[MLE预检](phase2c_estimation_preflight.md)、[后验](phase2d_bayesian_estimation.md) |
| R1 | [诊断](audits/r1_posterior_diagnostics.md)、[HD/FEVD](audits/r1_historical_and_fevd.md)、[期现](audits/r1_spot_futures_alignment.md)、[测量](audits/r1_measurement_and_units.md)、[预测/外部](audits/r1_forecast_and_external_validation.md)、[最终验收](audits/r1_final_validation.md) |

历史memo不覆盖R1修正；新理论也不自动替旧模型获得微观基础。PRIVATE outputs不在Git，代码/文件存在不能证明真实实验重跑。

## 稿件与计划

[R3短稿](thesis/reference_style_manuscript.md) · [单栏验收](audits/r3_single_column_layout.md) · [R2历史稿](thesis/advisor_draft.md) · [稿件入口](thesis/README.md) · [导师反馈台账](thesis/advisor_feedback_tracker.md)

[长期开题后深化路线](plans/thesis_deepening_2026_2028.md) · [旧比较协议草案](protocols/thesis_comparison_protocol_v1.md) · [学位稿蓝图](thesis/degree_thesis_blueprint.md) · [原A01—A12](plans/correction_backlog.md)

旧NOINV/成本反馈/COMMON57/期货预测是未执行的比较草案；先满足机制门槛，不把它们误称物理库存或新多部门均衡。学位稿和正式学校验收状态见CURRENT_STATUS。

## 来源与复现

[原20项引用核验](references/verified_literature_20260916.md) · [生猪方法对照](references/hog_paper_comparison.md) · [前批8候选](references/literature_expansion_20260917.md) · [复现](REPRODUCIBILITY.md) · [架构](repository_architecture.md)

机器入口：`data/metadata/industry_literature_library_20260918.json`、`configs/industry_equation_blueprint_v2.json`、`configs/thesis_workplan.json`。新增`audit_industry_library.py`只核对登记；`audit_thesis_governance.py`只核对任务/证据，不认证经济识别。读取层级、政策日期、来源不确定性及学生/导师审批必须如实保留。
