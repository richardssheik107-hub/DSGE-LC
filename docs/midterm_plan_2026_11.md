# 中期答辩前剩余计划（R1-6 修订，2026-09-16）

旧版见 Git 提交 `ef2eb3785b8dad58b7d4532298f5a184972b8260`。既有阶段运行记录保留，但独立审计后不能写“只剩格式”。R1-0—R1-6 的本轮技术修正、结论登记和源稿同步已于 2026-09-16 验收，仍有明确解释限制；下表原定周期保留作时间规划，已完成项不再要求重复运行。中期预计11月中旬，具体安排以学院为准。

| 原定周期 | 已有证据／当前行动 | 验收边界 |
|---|---|---|
| 9/16—9/22 | [R1-1](audits/r1_posterior_diagnostics.md)七套后验诊断已核；模型范围/毕业日期仍待导师 | baseline `PASS_RECONSTRUCTED`，未重采样；导师确认另行登记 |
| 9/23—9/29 | [R1-2](audits/r1_historical_and_fevd.md) HD/FEVD 技术修正已核 | 后期六项 `AMBIGUOUS`，论文不可写无条件稳健 |
| 9/30—10/6 | [R1-3](audits/r1_spot_futures_alignment.md)同口径期现复核已核 | 月频 +1 不再是峰；日频 +1 为探索性描述 |
| 10/7—10/13 | [R1-4](audits/r1_measurement_and_units.md)旧 scaler、共同支持期对照和历史原始 log 已核 | 共同支持期未估计；库存状态非吨数；A06 导师范围待确认 |
| 10/14—10/20 | [R1-5](audits/r1_forecast_and_external_validation.md)完整预测键、MAP 准入与点预测对象已核 | 递归历史 OOS 不是严格 prospective 或完整实时 vintage |
| 10/21—10/27 | [R1-5](audits/r1_forecast_and_external_validation.md) filtered/smoothed、配对时间块已核 | 库存变化量弱、成本同源；其他断点/代理稳健性未完成 |
| 10/28—11/3 | R1-6 已提前完成；继续文献正式版本核验与导师可读稿审阅 | 关键引用无占位、导师反馈记录；不凭文件存在宣称引用通过 |
| 11/4—11/10 | 学校模板、DOCX/PPTX 实排、15分钟讲稿与问答仍待做 | 文件实际可打开、逐页图表/数字检查、提交清单 |
| 11月中旬 | 导师/中期反馈尚未发生 | 学院实际日期、反馈台账和修改闭环 |

完整依赖、数据更新、2027提前路线及2028定稿路线见[总计划](plans/thesis_finalization_2026_2028.md)。不因 P0 技术修复就自动进入大型模型；已通过的工程测试不替代统计、解释、引用和行政审核。当前状态以[CURRENT_STATUS](CURRENT_STATUS.md)为准。
