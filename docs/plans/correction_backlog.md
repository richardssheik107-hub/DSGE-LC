# 定稿修正清单

基点：674020c，2026-09-16。详细证据见[审计报告](../audits/2026_09_16_research_audit.md)。下表是任务，不是已经完成的实验。

| ID | 优先级 | 当前状态 | 最小处理 | 关闭证据 |
|---|---|---|---|---|
| A01 | P0 | CLOSED（R1-1；baseline来源为PASS_RECONSTRUCTED） | 修正ESS配对/MCSE和冻结链判定；七套原draw只读复核 | [R1-1独立诊断](../audits/r1_posterior_diagnostics.md)：ArviZ对照、反例、七套真实draw新旧表、全量测试；原NPZ未变 |
| A02 | P0 | CLOSED（实现；解释需复核） | HD HIGH/AMBIGUOUS/NOT_EVALUATED 与全部必要门槛、数值/经济分级已实现 | [R1-2审计](../audits/r1_historical_and_fevd.md)：七套数值 PASS；18 组合 10 STABLE/2 MODERATE/6 AMBIGUOUS；不可无条件声称稳健 |
| A03 | P0 | CLOSED（R1-3；仅描述性） | 旧错配口径保留为LEGACY；同端点月末、双方完整月均、严格相邻日频与滞后成交量主力均已核验 | [R1-3审计](../audits/r1_spot_futures_alignment.md)：月频+1 0.710→约0.526且峰转同期；日频+1约0.475保留；整体 `DIRECTION_OR_PEAK_SENSITIVE`，不作因果/策略声称 |
| A04 | P0 | CLOSED（R1-4；LEGACY保留） | 逐列scaler manifest；原v1与共同支持期对照 | [R1-4审计](../audits/r1_measurement_and_units.md)：原输入/后验似然回放、68/57逐列拟合、两版 hash、历史log均值项与端点；COMMON仅构建未估计 |
| A05 | P1 | CLOSED（R1-2） | FEVD/HD逐draw和均值加总、边际区间、先累计后分位、正负堆叠已修正 | [R1-2审计](../audits/r1_historical_and_fevd.md)：FEVD 168 PASS、H1库存7个 NOT_DEFINED；基线12月中位数和0.964508属合法边际统计 |
| A06 | P1 | PARTIAL（R1-4操作定义完成） | 月度/同比/库存指数定义与产业推导 | [R1-4审计](../audits/r1_measurement_and_units.md)已固定方程-观测-状态-单位和符号限制；导师方法范围与最终论文表述仍待确认 |
| A07 | P1 | OPEN | OOS成功状态、预测目标与同键公平比较 | 不选未收敛解；origin/target/horizon一致；伪实时/真前瞻分开 |
| A08 | P1 | OPEN | 外部验证加入时间样本误差与filtered对照 | 同源成本机械成分明示；库存制度和block依赖处理 |
| A09 | P1 | PARTIAL | 核心参考稿映射已写；实际理论章节与导师确认待做 | 不宣称已实现四部门/混频/联合期现；引用正式版本可追踪 |
| A10 | P1 | OPEN | 引文核实、19章草稿收束、图表/公式/格式 | 无待核验关键引用；正式DOCX/PPTX实排；导师反馈逐条闭合 |
| A11 | P1 | PARTIAL | pandas最低版本已修；构建便携/集成分层和私有artifact备份 | 干净环境执行记录、依赖锁、数据/scaler/code绑定、恢复演练 |
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
