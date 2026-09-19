# 文档导航｜当前重建主线与历史档案分开

## 当前必读

[当前状态](CURRENT_STATUS.md) → [新版总计划](rebuild/MASTER_PLAN.md) → [研究问题草案](rebuild/RESEARCH_CHARTER.md) → [方程轮次](rebuild/EQUATION_ROUNDS.md) → [下一工作包](rebuild/NEXT_WORK_PACKAGE.md)。

[导师讨论包](rebuild/SUPERVISOR_PACKET.md)和[硕士论文结构](rebuild/THESIS_OUTLINE.md)是当前讨论/写作设计。都不代表已经批准或完成新论文。

## 继续利用，但必须核验的候选资料

[45来源地图](references/industry_literature_map_20260918.md)、[重点阅读卡](research/industry_model_reading_cards_20260918.md)、[28组关系库](theory/lithium_modular_equation_blueprint_v2.md)、[C0原候选推导](theory/c0_state_space_derivation_v1.md)、[生猪方法对照](references/hog_paper_comparison.md)。

现有来源不是全部全文精读，旧18/20/45表有重叠。C0不自动升格为新主模型，复核清单在新方程轮次中。

## 数据与旧研究

数据字典、入库/口径审计、phase报告、midterm材料、R1审计、R2/R3稿件继续保留，供历史复现和资料核验；不是当前“下一步”。新样本/观测需独立冻结，不改变原数据。

旧操作计划的完整原文在 `archive/pre-masters-rebuild-20260919` 分支；固定提交为 `c6a61b72e1c21acb042be47b13c6138854c8d8df`。本分支保留短跳转避免旧链接失效。旧源码与原结果不删除，不要求写进新硕士论文。

## 管理与测试

[生命周期配置](../configs/repository_lifecycle_20260919.json)、[当前机器计划](../configs/masters_rebuild_plan_v1.json)、[本次梳理审计](rebuild/REPOSITORY_AUDIT.md)、[架构](repository_architecture.md)。

当前验证入口是 `scripts/audit_masters_rebuild.py`。旧 `audit_thesis_governance.py` 验证历史D任务格式，不判断新路线，也不自动安排新研究。
