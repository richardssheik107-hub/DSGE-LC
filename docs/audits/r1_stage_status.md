# 研究修正版 R1：阶段状态

run_id：`R1_20260916_190253`。只有已执行的检查才可标为完成；旧阶段 PASS 不自动继承。

| 阶段 | 状态 | 关闭证据／待办 |
|---|---|---|
| R1-0 工作区与输入预检 | COMPLETE | [预检记录](r1_preflight.md)；冻结哈希吻合、旧文件及用户修改已备份、revision 输出目录已验证忽略；22 项现有诊断测试通过 |
| R1-1 A01 | COMPLETE | [独立后验诊断](r1_posterior_diagnostics.md)：七套门槛通过；baseline 为有证据的重建来源，非原始 sidecar；draws 未改动 |
| R1-2 A02/A05 | COMPLETE（技术） | [历史与FEVD修正](r1_historical_and_fevd.md)：七套原后验输入不变；FEVD 168 PASS + 7 个数学上未定义单元；历史数值技术 PASS，但后期窗口 6 个 AMBIGUOUS，解释门槛为 `INTERPRETATION_REVIEW_REQUIRED` |
| R1-3 A03 | COMPLETE（描述性） | [期现同区间复核](r1_spot_futures_alignment.md)：535 日、七次换月、月末/双方月均/日频严格键控；旧月频+1 0.710→同端点约0.526，月频峰转同期；日频+1约0.475保留。整体 `DIRECTION_OR_PEAK_SENSITIVE`，不作因果或可交易解释 |
| R1-4 A04/A06 | OPEN | LEGACY 输入/scaler/单位尚未核验 |
| R1-5 A07/A08 | OPEN | 预测键、外部不确定性尚未复核 |
| R1-6 论文与计划 | OPEN | 等前面实际结果形成后同步 |

本表的 COMPLETE 仅指该行的工作项，绝不等于论文提交就绪。
