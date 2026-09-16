# 源码指南

| 包 | 职责 |
|---|---|
| baselines | RW/AR/VAR/BVAR |
| diagnostics | 变换、描述统计、平稳性/断点/滞后 |
| evaluation | 预测拆分、递归预测、指标 |
| data_audit | 数据源和工作簿复核 |
| structural | 方程/矩阵/观测、Kalman/likelihood、MLE、Bayes、IRF/FEVD、HD、结构预测与外部验证 |
| futures | 合约审计、连续主力/换月收益、期现对齐与统计 |

## 当前结构栈

spec/equations → matrices/measurement → stability/identification → state_space/kalman/likelihood → parameter_transform/estimation/profiles → priors/mcmc/posterior_artifacts → irf/fevd/historical_decomposition → structural_forecasting/external_validation。

## 必须先修的边界

`mcmc_diagnostics`的ESS配对、MCSE和常数链；HD runner的HIGH分类/最终门槛；`measurement`的实际scaler样本；`spot_futures`的月度收益定义。详细证据见docs/audits/2026_09_16_research_audit.md。

本轮不无痕替换冻结主算法。独立checker在scripts中，作为对现有实现的外部复核；下一步只有在独立测试和真实artifacts重算后，才更新正式算法与结果版本。冻结接口不意味着禁止修bug，也不允许为修bug顺便改经济方程或先验。
