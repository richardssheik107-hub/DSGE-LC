# 2026 年 11 月中旬中期答辩执行计划

> 版本日期：2026-09-07
>
> 硬截止：2026 年 11 月中旬中期答辩。
>
> 中期目标不是完成最终完整版论文，而是完成一个**小而完整、可复现、已有核心实证结果的研究闭环**。

---

## 1. 中期答辩目标形态

到 11 月中旬，项目应至少形成以下闭环：

```text
Data
  ↓
Diagnostics / Mechanism Screening
  ↓
Random Walk / AR / VAR-BVAR
  ↓
MVP Structural Model
  ↓
State-Space
  ↓
Kalman Filter / Likelihood
  ↓
Parameter Estimation
  ↓
IRF + FEVD
  ↓
Historical Decomposition
  ↓
Out-of-Sample Forecast
  ↓
Preliminary Spot-Futures Extension
```

中期答辩时应能够回答：

1. 碳酸锂价格波动能否由需求、供给和上游成本冲击解释？
2. 不要求完整观测产能、库存和投资时，稀疏观测状态空间模型能否稳定估计？
3. 需求、成本、供给冲击的动态传导方向和持续时间是什么？
4. 各类冲击分别解释多少价格波动？
5. 模型能否解释 2021–2022 上涨、2023 快速下跌以及后续震荡阶段？
6. 结构模型在样本外预测中相对 Random Walk、AR、VAR/BVAR 的表现如何？
7. 现货与期货之间是否存在初步可识别的价格发现/领先滞后关系？

---

## 2. 中期版本范围冻结

### 2.1 必须完成

| 模块 | 11 月中旬目标 |
|---|---|
| 核心数据 | 核心产业序列形成 canonical dataset |
| 数据审计 | coverage、缺失、异常、平稳性、结构突变 |
| Random Walk / AR | 完成并作为最低预测基准 |
| VAR/BVAR | 完成机制预检、IRF 和预测基线 |
| MVP 结构模型 | 完成 |
| State-Space | 完成 |
| Kalman Filter | 可稳定运行 |
| 参数估计 | 至少一套稳定参数结果 |
| IRF | 必须完成 |
| FEVD | 必须完成 |
| Historical Decomposition | 目标必须完成 |
| OOS Forecast | 目标必须完成 |
| 期现初步结果 | 做轻量级 daily spot-futures 扩展 |
| 中期材料 | 图、表、模型逻辑、结果、PPT 可直接展示 |

### 2.2 中期前不作为硬目标

- tick 级微观结构模型
- 分钟级期权定价
- 完整期权模块
- Markov Switching
- 大型非线性状态空间
- 完整 stochastic cycle
- 全部参数都用 Bayesian MCMC 估计
- 长历史 observed inventory
- 长历史 capacity / utilization
- 企业级 capex / investment 数据库
- 大规模政策、情绪、地缘风险模块

原则：**主模型结果优先于复杂扩展。**

---

## 3. 当前数据状态与中期核心观测

### 3.1 已有数据

- 碳酸锂期货：已获取至 2026-06-30，包含分钟级与 tick 级完整数据
- 碳酸锂期权：已获取至 2026-06-30，包含分钟级与 tick 级完整数据
- USD/CNY：2020-01-02 至 2026-06-30，1,623 个日度观测
- CPI 同比：2021-09 至 2026-06，已有 53 个月官方 NBS 公告数据

期货和期权原始高频数据在中期前视为 **READ ONLY**，不作为主线数据工程对象。

### 3.2 仍需优先解决的四条产业序列

| 数据 | Canonical name | 目标频率 | 目标区间 | 角色 |
|---|---|---:|---|---|
| 电池级碳酸锂现货价格 | `lc_spot` | 日/月 | 尽量 2020-01 至 2026-06 | 核心价格 |
| 国内碳酸锂产量 | `lc_output` | 月 | 尽量 2020-01 至 2026-06 | 供给锚 |
| 锂辉石价格/原料成本 | `spodumene_price` | 日/周/月 | 尽量 2020-01 至 2026-06 | 成本锚 |
| 动力电池装车量 | `battery_install` | 月 | 尽量 2020-01 至 2026-06 | 需求锚 |

### 3.3 第一版观测向量

长样本现货模型优先使用：

\[
Y_t^{obs}=[LCSpot_t,LCOutput_t,Battery_t,Spodumene_t,FX_t]'
\]

期货上市后再增加：

\[
Futures_t
\]

### 3.4 第一版潜在状态

中期前不要求直接找到真实长历史观测：

- `capacity`
- `investment`
- `inventory_gap`
- `margin`
- `expected_price`
- `productivity`

它们通过结构方程和 Kalman Filter 推断。

---

## 4. 中期 MVP 模型边界

中期版本只保留四个核心经济模块：

\[
\boxed{Demand + Cost + Supply + Spot}
\]

并允许少量 latent states。

### 4.1 Demand

第一版可先使用简化动态：

\[
D_t=\rho_DD_{t-1}+\varepsilon_t^D
\]

观测锚：动力电池装车量。

### 4.2 Cost

\[
C_t=\rho_CC_{t-1}+\beta_{FX}FX_t+\varepsilon_t^C
\]

核心成本观测：锂辉石价格；若美元报价则通过 USD/CNY 转换。

### 4.3 Margin

\[
Margin_t=P_t-\theta C_t
\]

中期版本不要求额外购买企业利润数据。

### 4.4 Latent Supply Capacity

候选：

\[
K_{t+1}=\rho_KK_t+\gamma Margin_t+\varepsilon_t^K
\]

用于表达高利润对未来有效供给能力的滞后推动。

### 4.5 Production

候选：

\[
Q_t=\alpha_KK_t-\alpha_CC_t+\varepsilon_t^Q
\]

真实观测：碳酸锂月度产量。

### 4.6 Latent Inventory Gap

候选：

\[
INV_t=\rho_IINV_{t-1}+Q_t-D_t
\]

中期 baseline 不要求真实库存数据进入观测方程。

### 4.7 Spot Price

候选最小形式：

\[
P_t=\rho_PP_{t-1}+\beta_DD_t-\beta_QQ_t-\beta_IINV_t+\beta_CC_t+\varepsilon_t^P
\]

最终方程可根据 Phase 1 机制预检结果调整，但中期前必须保持小规模和可识别。

---

## 5. 总时间表

| 阶段 | 时间 | 核心任务 | 硬产出 |
|---|---|---|---|
| Phase 1 | 9/8–9/21 | 数据获取 + 数据冻结 | canonical dataset + coverage audit |
| Phase 2 | 9/22–10/5 | 数据诊断 + RW/AR/VAR-BVAR | 第一批可展示实证结果 |
| Phase 3 | 10/6–10/19 | MVP 结构模型 + State-Space | Kalman + likelihood 跑通 |
| Phase 4 | 10/20–11/2 | 参数估计 + IRF + FEVD | 核心结构结果 |
| Phase 5 | 11/3–11/9 | Historical Decomposition + Forecast + Futures preliminary | 完整结果闭环 |
| Phase 6 | 11/10–11/15 | 冻结结果 + 中期答辩材料 | PPT / 中期报告 / 可复现实验 |

三个硬 Gate：

- **9 月 21 日：停止无限找数据，冻结中期数据版本**
- **10 月 19 日：State-Space + Kalman + Likelihood 必须跑通**
- **11 月 2 日：IRF + FEVD 必须完成**

---

## 6. Phase 1：9/8–9/21 — 数据冻结

### 6.1 工作重点

优先解决：

1. `lc_spot`
2. `lc_output`
3. `spodumene_price`
4. `battery_install`

已有 `usd_cny` 直接进入数据层；高频 futures/options 暂不扩展。

### 6.2 Data Gate

以 `lc_spot + lc_output + spodumene_price + battery_install` 的共同月度样本为准：

| 共同样本 | 决策 |
|---|---|
| >= 60 个月 | Go，正常做中期 MVP |
| 48–59 个月 | Go，减少自由参数 |
| 36–47 个月 | Go with calibration，加强先验/校准 |
| < 36 个月 | 不硬做大 DSGE，改成更小的 structural state-space |

9 月 21 日后不再因为追求“完美历史数据”延迟模型开发。

---

## 7. Phase 2：9/22–10/5 — 机制预检与基线

### 7.1 数据处理

统一形成月度主表：

```text
month
lc_spot
lc_output
spodumene_price
battery_install
usd_cny
```

保留：

- level
- log level
- first difference
- log difference / growth

检查：

- ADF
- KPSS（可选）
- missing / duplicates / outliers
- rolling mean / variance
- break candidates
- contemporaneous / cross-correlation

### 7.2 Baselines

必须完成：

1. Random Walk
2. AR(1)
3. Small VAR/BVAR

Small VAR/BVAR 第一版最多 4–5 个变量：

\[
[Spot,Output,Battery,Spodumene]
\]

必要时加入 FX。

### 7.3 机制预检

重点检查：

\[
Battery\uparrow \Rightarrow Spot\uparrow
\]

\[
Spodumene\uparrow \Rightarrow Spot\uparrow
\]

\[
Output\uparrow \Rightarrow Spot\downarrow
\]

并扫描约 1、3、6、12 个月滞后。

### 7.4 10 月 5 日前可展示结果

- coverage timeline
- 核心变量历史图
- correlation / cross-correlation
- break candidates
- VAR/BVAR IRF
- VAR/BVAR FEVD
- RW / AR / VAR-BVAR 初步预测结果

---

## 8. Phase 3：10/6–10/19 — MVP State-Space 跑通

这一阶段是中期前最关键的工程节点。

必须完成：

```text
structural equations
      ↓
state transition matrix
      ↓
observation equation
      ↓
Kalman filter
      ↓
log-likelihood
```

验收：

- 状态转移不爆炸
- covariance 数值稳定
- Kalman filter 可完整跑过样本
- likelihood 为有限值且对参数变化有响应
- latent states 可滤出合理路径
- 初始 IRF 符号基本合理

若 10 月 19 日还未达到此 Gate，立即停止期货、期权、非线性等所有支线工作，只修主模型。

---

## 9. Phase 4：10/20–11/2 — 参数估计、IRF、FEVD

### 9.1 参数策略

采用：

\[
\boxed{Calibration + Estimation}
\]

而不是中期前强行全部参数 Bayesian。

产业转换系数、稳态参数等可校准；真正影响动态传导的持久性和弹性参数重点估计。

### 9.2 估计层级

优先顺序：

1. MLE / MAP 跑通
2. 参数敏感性与识别检查
3. Bayesian MCMC（在时间允许且模型稳定时）

若 MCMC 到 10 月底仍不稳定，中期版本允许使用稳定的 MLE/MAP + 部分 Bayesian 结果；完整版 Bayesian 放到中期后继续完成。

### 9.3 中期必须有的三类 IRF

#### Demand Shock +

预期：

\[
Demand\uparrow \Rightarrow Price\uparrow \Rightarrow Margin\uparrow \Rightarrow FutureSupply\uparrow
\]

#### Raw Material Cost Shock +

预期：

\[
Spodumene\uparrow \Rightarrow Cost\uparrow \Rightarrow Margin\downarrow \Rightarrow Output\downarrow \Rightarrow Price\uparrow
\]

#### Supply Shock +

预期：

\[
Output\uparrow \Rightarrow InventoryGap\uparrow \Rightarrow Price\downarrow
\]

### 9.4 FEVD

至少输出 1、6、12 个月 horizon，回答价格波动中：

- Demand shock
- Cost shock
- Supply shock
- Price-specific shock

分别解释多少。

---

## 10. Phase 5：11/3–11/9 — 把模型结果变成研究结果

### 10.1 Historical Decomposition

至少解释三个阶段：

1. 2021–2022：快速上涨
2. 2023：快速下跌
3. 2024–2026：阶段性震荡

目标表达：

\[
Price_t=DemandContribution_t+CostContribution_t+SupplyContribution_t+Residual_t
\]

不得提前规定各阶段的贡献率，必须由模型估计结果决定。

### 10.2 Out-of-Sample Forecast

比较：

- Random Walk
- AR
- VAR/BVAR
- Structural model / DSGE MVP

至少报告：

- RMSE
- MAE
- Theil U
- Direction Accuracy

结构模型不要求所有预测指标都第一，但必须与简单基线进行严格比较。

### 10.3 Futures Preliminary

中期前高频数据只聚合到 daily 层使用。

从现有 tick/minute 数据构造：

```text
date
contract
near_contract
main_contract
close
settlement
volume
open_interest
basis
```

中期只做轻量级：

- spot-futures correlation
- lead-lag
- Granger
- VECM / price discovery preliminary（视平稳性与协整结果）

不进入完整 tick/option 模型。

---

## 11. Phase 6：11/10–11/15 — 中期版本冻结

原则：**禁止增加新模块。**

只做：

- 结果复现
- 图表统一
- 参数表整理
- IRF / FEVD 图完善
- historical decomposition 图完善
- forecast table
- 中期 PPT
- 中期报告
- 答辩问题准备

所有中期核心结果必须能够通过固定脚本重新生成。

---

## 12. 按周执行清单

| 周次 | 日期 | 必须完成 |
|---|---|---|
| W1 | 9/8–9/14 | 补 Spot / Output / Spodumene / Battery |
| W2 | 9/15–9/21 | 数据冻结 + canonical dataset |
| W3 | 9/22–9/28 | 数据诊断 / break / correlation |
| W4 | 9/29–10/5 | RW + AR + VAR/BVAR |
| W5 | 10/6–10/12 | MVP structural equations |
| W6 | 10/13–10/19 | State-Space + Kalman + likelihood |
| W7 | 10/20–10/26 | 参数估计 / calibration / identification |
| W8 | 10/27–11/2 | MCMC/MAP + IRF + FEVD |
| W9 | 11/3–11/9 | Historical decomposition + Forecast + Futures preliminary |
| W10 | 11/10–11/15 | PPT + 中期报告 + rehearsal + 版本冻结 |

---

## 13. 中期答辩结果展示顺序

推荐 PPT 主线：

1. 研究问题与锂周期事实
2. 为什么采用 sparse observations + latent states
3. 数据与样本
4. Reduced-form 机制预检
5. MVP 结构模型
6. State-Space / Kalman 方法
7. 参数估计结果
8. IRF
9. FEVD
10. Historical Decomposition
11. Forecast comparison
12. 期现货初步结果
13. 当前限制与中期后扩展

目标是让答辩老师看到的是“已经有结果的研究”，而不是“正在准备搭模型”。

---

## 14. 三档完成标准

### 最低可接受

- 核心数据完成
- RW / AR / VAR 完成
- MVP structural model 可估计
- IRF 完成

结论：可答辩，但研究闭环仍偏弱。

### 目标版本

- 上述全部完成
- FEVD
- Historical Decomposition
- OOS Forecast

这是本项目的**中期主目标**。

### 理想版本

- 目标版本全部完成
- 稳定 Bayesian MCMC
- 期现货初步 price discovery

属于中期前超额完成，不应牺牲主模型稳定性去追求。

---

## 15. 中期前主线与支线

### 主线 A — 必须完成

```text
Data
→ Diagnostics
→ RW / AR / VAR-BVAR
→ MVP Structural Model
→ State-Space
→ Kalman
→ Estimation
→ IRF
→ FEVD
→ Historical Decomposition
→ OOS Forecast
```

### 支线 B — 不得拖慢主线

```text
Full Futures
→ Options
→ Tick Microstructure
→ Observed Inventory
→ Capacity Extension
→ Stochastic Cycle
→ Nonlinear / Regime Switching
```

---

## 16. 中期后再做的升级

中期答辩后再依次评估：

1. observed inventory validation
2. capacity / utilization observed-data validation
3. latent investment-capacity block refinement
4. full Bayesian MCMC
5. stochastic cycle ablation
6. full futures pricing / convenience yield
7. options / implied volatility
8. tick/minute microstructure
9. nonlinear / regime switching

每个扩展都必须通过增量实验验证其价值。

---

## 17. 最终中期项目定位

中期版本的目标表述冻结为：

> **完成一个基于少量混频产业观测的碳酸锂结构状态空间模型，识别需求、供给与上游成本冲击对碳酸锂价格的动态传导，并通过 IRF、FEVD、历史分解和样本外预测验证模型；同时利用已有期货数据给出初步的期现联动结果。**

核心原则：

> **先把一个小模型做完整、做稳定、做出结果，再增加复杂度。**
