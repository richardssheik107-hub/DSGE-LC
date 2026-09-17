# DSGE-LC

《碳酸锂价格波动的影响因素与定价机制研究》。当前实际方法为**M0_CORE5月度半结构状态空间**，不是完整DSGE、真正混频或联合期现结构定价。

## 当前入口：导师审阅初稿 R2

- [九章论文正文](docs/thesis/advisor_draft.md)：中英文摘要、模型/矩阵、后验/结构/预测/期现结果、结论与文献。
- [给导师的审阅说明](docs/thesis/advisor_review_note.md)：先确认题目与理论范围，避免无限扩展。
- [20项文献证据登记](docs/references/verified_literature_20260916.md)：核验题录/摘要/正文层级，不冒充全部全文精读。
- [真实图版与来源清单](docs/thesis/figure_completion_manifest.md)、[R2逐页验收](docs/audits/r2_full_figure_draft.md)、[导师反馈台账](docs/thesis/advisor_feedback_tracker.md)与[近期完成计划](docs/plans/advisor_draft_completion.md)。

**当前：本地完整图版导师讨论稿已验收，学生核对后可送导师；学校送审仍未就绪。** 中性A4文件在忽略的 `outputs/thesis/R2_20260917_095514/`：论文DOCX/PDF、审阅说明DOCX/PDF、逐图来源清单。私有图和商业派生文档不在公共Git。不保证毕业合格，不代替学生理解和导师审批。旧中期报告保留，R2正文是新的学术组织版本，不无痕覆盖历史实证。

## 实证基础与R1边界

数据/Phase1、M0设计、Kalman/MLE/Bayesian、IRF/FEVD、条件HD、递归历史OOS、库存/成本对照、期现扩展已有结果。R1已修正诊断、加总、单位、门槛和期现收益定义；七套原后验通过、未重采样。实际明细见[当前状态](docs/CURRENT_STATUS.md)、[R1最终验收](docs/audits/r1_final_validation.md)、[任务台账](docs/plans/correction_backlog.md)。

主要限制：a_c接近零；n是标准化压力不是吨库存；需求与库存依赖固定假设；残差约65%；后期六项历史歧义；结构预测不普遍胜RW/BVAR；月频峰值转同期；外部成本同源。不要在写作时重新写成强因果、预测冠军或稳定价格发现。

## 数据与模型

核心69个月（2020-01—2025-09），结构57个月（2021-01—2025-09）；状态[d,c,q,n,p]，观测[spot,ore_cost,output,battery]，四冲击。基线rho_n=.80、battery_sd=.25。LEGACY spot/ore scaler68期，数量同比57期；共同支持期scaler只有构建，未估计。

v1记录SHA256：`9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`。R2在用户授权的本地工作区核验了原面板、七套NPZ/sidecar及R1最终来源；商业观测、NPZ和生成结果不上传公共Git。R1历史705 passed/4 skipped与隔离44 passed单列；R2实际全仓717 passed/4 skipped，不互相相加。

## 导航

[文档索引](docs/README.md) · [研究审计](docs/audits/2026_09_16_research_audit.md) · [参考稿对照](docs/references/hog_paper_comparison.md) · [定稿总计划](docs/plans/thesis_finalization_2026_2028.md) · [复现指南](docs/REPRODUCIBILITY.md)。

src为可复用模型，scripts为执行/审计入口，configs为版本化设定，tests区分便携与授权集成，data保存可公开数据/元数据。不得以git add .、force push或删除untracked处理同步；原始商业数据、参考全文和凭证不提交。

## 接下来

R1不用重做 → R2本地完整图文已完成 → 学生核对与关键全文阅读 → 导师审阅 → 必要且有限的补实验 → 版本化扩样/前瞻检验 → 学校终稿。2028毕业是规划假设，不是拖延当前完整稿的理由，具体日期由学院确认。
