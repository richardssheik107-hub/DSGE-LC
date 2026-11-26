# 研究修正版 R1：阶段状态

run_id：`R1_20260916_190253`。只有已执行的检查才可标为完成；旧阶段 PASS 不自动继承。

| 阶段 | 状态 | 关闭证据／待办 |
|---|---|---|
| R1-0 工作区与输入预检 | COMPLETE | [预检记录](r1_preflight.md)；冻结哈希吻合、旧文件及用户修改已备份、revision 输出目录已验证忽略；22 项现有诊断测试通过 |
| R1-1 A01 | COMPLETE | [独立后验诊断](r1_posterior_diagnostics.md)：七套门槛通过；baseline 为有证据的重建来源，非原始 sidecar；draws 未改动 |
| R1-2 A02/A05 | COMPLETE（技术） | [历史与FEVD修正](r1_historical_and_fevd.md)：七套原后验输入不变；FEVD 168 PASS + 7 个数学上未定义单元；历史数值技术 PASS，但后期窗口 6 个 AMBIGUOUS，解释门槛为 `INTERPRETATION_REVIEW_REQUIRED` |
| R1-3 A03 | COMPLETE（描述性） | [期现同区间复核](r1_spot_futures_alignment.md)：535 日、七次换月、月末/双方月均/日频严格键控；旧月频+1 0.710→同端点约0.526，月频峰转同期；日频+1约0.475保留。整体 `DIRECTION_OR_PEAK_SENSITIVE`，不作因果或可交易解释 |
| R1-4 A04/A06 | COMPLETE（测量与单位；导师范围待确认） | [测量与单位审计](r1_measurement_and_units.md)：情形 A，原输入 228 值完全重建、12 个生产 draw 似然回放一致；共同支持期仅构建未估计；78 个历史原始 log/端点键通过。A06 的导师理论范围确认仍开放 |
| R1-5 A07/A08 | COMPLETE（技术；解释限于描述性） | [预测与外部验证审计](r1_forecast_and_external_validation.md)：21 起点的 86/86 旧优化成功；五模型 56 完整键/15 指标复算通过；MAP 候选准入修复；同 draw filtered/smoothed 与 3/6 月配对 block bootstrap。库存变化量弱，成本同源，非实时/非因果 |
| R1-6 论文与计划 | COMPLETE（源稿与技术验收；正式提交未就绪） | [主张修订](r1_claim_revision.md)及[最终验收](r1_final_validation.md)：85 条结果、10 条主张、11 份中期源稿及导航同步；完整 `tests/` 705 passed、0 failed、4 skipped；图表/路径/哈希复核。后期历史解释、引文、导师、学校与许可恢复限制保留 |

本表的 COMPLETE 仅指该行的工作项，绝不等于论文提交就绪。
