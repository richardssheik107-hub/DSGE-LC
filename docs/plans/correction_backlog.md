# 定稿修正清单

基点：674020c，2026-09-16；R1-6 最终同步日：2026-09-16。详细证据见[审计报告](../audits/2026_09_16_research_audit.md)和[最终验收](../audits/r1_final_validation.md)。状态中的 `CLOSED` 仅指本轮约定任务完成；`RESOLVED_WITH_DOCUMENTED_LIMITATION` 指本轮验收通过但结论限制必须相邻呈现，不等于论文提交就绪。

| ID | 优先级 | 当前状态 | 最小处理 | 关闭证据 |
|---|---|---|---|---|
| A01 | P0 | RESOLVED_WITH_DOCUMENTED_LIMITATION（baseline来源为PASS_RECONSTRUCTED） | 修正ESS配对/MCSE和冻结链判定；七套原draw只读复核 | [R1-1独立诊断](../audits/r1_posterior_diagnostics.md)：ArviZ对照、反例、七套真实draw新旧表、全量测试；原NPZ未变 |
| A02 | P0 | RESOLVED_WITH_DOCUMENTED_LIMITATION（解释需复核） | HD HIGH/AMBIGUOUS/NOT_EVALUATED 与全部必要门槛、数值/经济分级已实现 | [R1-2审计](../audits/r1_historical_and_fevd.md)：七套数值 PASS；18 组合 10 STABLE/2 MODERATE/6 AMBIGUOUS；不可无条件声称稳健 |
| A03 | P0 | RESOLVED_WITH_DOCUMENTED_LIMITATION（仅描述性） | 旧错配口径保留为LEGACY；同端点月末、双方完整月均、严格相邻日频与滞后成交量主力均已核验 | [R1-3审计](../audits/r1_spot_futures_alignment.md)：月频+1 0.710→约0.526且峰转同期；日频+1约0.475保留；整体 `DIRECTION_OR_PEAK_SENSITIVE`，不作因果/策略声称 |
| A04 | P0 | CLOSED（R1-4；LEGACY保留） | 逐列scaler manifest；原v1与共同支持期对照 | [R1-4审计](../audits/r1_measurement_and_units.md)：原输入/后验似然回放、68/57逐列拟合、两版 hash、历史log均值项与端点；COMMON仅构建未估计 |
| A05 | P1 | CLOSED（R1-2） | FEVD/HD逐draw和均值加总、边际区间、先累计后分位、正负堆叠已修正 | [R1-2审计](../audits/r1_historical_and_fevd.md)：FEVD 168 PASS、H1库存7个 NOT_DEFINED；基线12月中位数和0.964508属合法边际统计 |
| A06 | P1 | IN_PROGRESS（R1-4操作定义完成） | 月度/同比/库存指数定义与产业推导 | [R1-4审计](../audits/r1_measurement_and_units.md)已固定方程-观测-状态-单位和符号限制；导师方法范围与最终论文表述仍待确认 |
| A07 | P1 | RESOLVED_WITH_DOCUMENTED_LIMITATION（历史复核/未来防护） | OOS成功状态、预测目标与同键公平比较 | [R1-5审计](../audits/r1_forecast_and_external_validation.md)：旧 86/86 起点优化成功、56 完整键真值一致、15 指标复算；未收敛解未来禁入；真前瞻验证仍属未来研究 |
| A08 | P1 | RESOLVED_WITH_DOCUMENTED_LIMITATION（解释降级） | 外部验证加入时间样本误差与filtered对照 | [R1-5审计](../audits/r1_forecast_and_external_validation.md)：同 draw 滤波/平滑、原水平/log/变化/去趋势、固定 2,000×3/6 月配对块；高成本相关有同源成分，库存变化量区间跨零 |
| A09 | P1 | IN_PROGRESS | 核心参考稿映射已写；实际理论章节与导师确认待做 | 不宣称已实现四部门/混频/联合期现；引用正式版本可追踪 |
| A10 | P1 | IN_PROGRESS | R1 已同步11份中期源稿，仍需引文核实、正式图表/公式/格式 | 无待核验关键引用；正式DOCX/PPTX实排；导师反馈逐条闭合 |
| A11 | P1 | IN_PROGRESS | pandas最低版本已修；构建便携/集成分层和私有artifact备份 | 干净环境执行记录、依赖锁、数据/scaler/code绑定、恢复演练 |
| A12 | 管理 | OPEN | 2027/2028日期与学院流程统一 | 导师/学院实际日期登记；此前不阻塞当前P0 |

## 执行纪律

1. 修改前保存原版本、输入/后验hash，确认工作区无未解释冲突。
2. 先造能暴露问题的独立测试，再修最小代码；不重写模型或改先验救结果。
3. 仅当修正改变输入/目标密度时，才重估相应版本；诊断/画图修正优先复用draw。
4. 新旧输出放不同路径，不覆盖历史产物；记录受影响论文图表。
5. 用授权环境跑全量回归，缺数据不能伪装成PASS。
6. 结果、代码和引用一致后，再更新当前状态和计划并显式暂存推送。
7. 统计不支持某机制是可交付结果；实现错误或未执行的门槛不能被`PASS_WITH_WARNING`掩盖。

本轮独立入口：`python scripts/audit_posterior_independent.py`；它只检查收敛和最小artifact元数据，不替代A01的核心代码修补、支持区间/稳定性或全链验收。

R1-6 的 85 条结果登记、10 条主张修订和11份中期源稿同步见[主张复核](../audits/r1_claim_revision.md)；旧准备度/检查表仅作历史快照。R1-6 不自动关闭 A06/A09—A12 的导师、文献、学校与许可数据恢复事项。
