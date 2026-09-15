# 2026 年 11 月中旬中期答辩执行计划

> 版本日期：2026-09-15
>
> 硬截止：2026 年 11 月中旬中期答辩。
>
> 当前目标：**尽量在中期答辩前把主要实验部分做完整。中期答辩后以论文写作、结果修改和针对导师意见补实验为主，不再把大型新模块作为默认任务。**

---

## 0. 当前进展快照（2026-09-15）

数据阶段已经达到 Phase 1 开工门槛：

- Data Freeze v1：2020-01—2025-09，共 69 个共同完整月份；内部缺失 0；`DATA_GATE=GO`。
- 四条核心产业变量均已正式入库并评级 `A_CORE`：`lc_spot`、`lc_output`、`spodumene_price`、`battery_install`。
- `battery_install` 已补到 2026-06。
- USD/CNY、CPI、PPI、中国国债 3M/6M 已覆盖 2020-01—2026-06。
- LC 进出口公开尾部已补到 2026-06；Mysteel 替代价格、成本利润、SMM filtered 锂精矿进口和 regime-aware 库存已进入 robustness / validation 层。
- 剩余 canonical 数据只集中在 SMM 价格尾部和 7 个月产量精确值核验，不再阻塞 Phase 1。

当前执行原则：

> **用 Data Freeze v1 立即开始 diagnostics 和 baselines；SMM 尾部授权补齐与实证并行推进。**

---

## 1. 中期答辩前总体目标

中期前尽量完成以下研究闭环：

```text
核心数据
  ↓
数据特征与变量关系分析
  ↓
Random Walk / AR / VAR-BVAR
  ↓
最小结构模型
  ↓
State-Space + Kalman Filter
  ↓
参数估计
  ↓
IRF + FEVD
  ↓
Historical Decomposition
  ↓
Out-of-Sample Forecast
  ↓
初步期现货分析 + 稳健性检验
```

中期答辩时，希望主要实验已经基本定型，而不是刚开始搭模型。

重点回答：

1. 需求、供给和上游成本是否能够解释碳酸锂价格变化？
2. 这些冲击对价格的影响方向、持续时间和相对重要性如何？
3. 模型能否解释 2021–2022 上涨、2023 下跌以及之后的震荡阶段？
4. 结构模型的样本外预测表现与简单基准模型相比如何？
5. 现货和期货之间是否存在初步的领先滞后或价格发现关系？

---

## 2. 中期版本范围

### 2.1 中期前优先完成

- 核心数据版本冻结与可复现构建
- 描述统计、相关性、滞后关系和结构变化分析
- Random Walk、AR、VAR/BVAR 基准模型
- Demand、Cost、Supply、Spot 最小结构模型
- State-Space、Kalman Filter 和参数估计
- 需求、成本、供给冲击的 IRF
- FEVD
- Historical Decomposition
- 严格样本外预测
- 初步期现货分析
- 至少一轮稳健性检验

### 2.2 中期前不强求的大型扩展

- tick 级微观结构模型
- 完整期权定价模块
- 大型非线性模型
- Markov Switching
- 完整 stochastic cycle
- 所有参数都使用完整 Bayesian MCMC
- 大规模政策、情绪和地缘风险模块

原则：**优先把主实验做完整，而不是不断增加模型复杂度。**

---

## 3. 当前核心数据

### 3.1 Data Freeze v1

长样本结构模型当前正式版本：

```text
2020-01 ~ 2025-09
69 months
0 internal missing
DATA_GATE = GO
```

核心观测：

| Variable | Definition | Current canonical status |
|---|---|---|
| `lc_spot` | SMM 国产电池级碳酸锂 99.5% 月均 | complete through 2025-09 |
| `lc_output` | SMM 中国碳酸锂总产量 | complete through 2025-09 |
| `spodumene_price` | SMM SC6 Li₂O CIF China 月均 | complete through 2025-09 |
| `battery_install` | 中国动力电池当月总装车量 | complete through 2026-06 |
| `usd_cny_mean` | USD/CNY 月均 | complete through 2026-06 |

期货/期权高频数据已获取至 2026-06-30，中期前不重复做大规模高频数据采集。

### 3.2 Data Freeze v2 candidate

目标：2020-01—2026-06，共 78 个月。

真正尚需授权/精确确认的 core gaps：

- SMM 电池级碳酸锂：2025-12、2026-04—06。
- SMM SC6 CIF China：2025-10—2026-02、2026-04—06。
- SMM LC output：2025-10、11、12 与 2026-03—06 的精确月度实际值。

这些尾部不阻塞当前实验。v2 完成后统一重跑，不重做研究设计。

### 3.3 Robustness / validation 已就绪

- Mysteel LC spot / SC6 monthly means：`ROBUSTNESS`
- Mysteel SC6-route cost / margin：`VALIDATION_ONLY`
- SMM filtered concentrate imports：`ROBUSTNESS`
- SMM inventory：`VALIDATION_ONLY`，严格按 regime 比较
- route-specific output、LFP/NCM、LC trade：辅助/稳健性

产能、投资、库存缺口、利润等第一版仍可作为潜在状态，不要求中期前全部找到长期真实观测。

---

## 4. 中期最小结构模型

第一版主要围绕四个模块：

```text
Demand + Cost + Supply + Spot
```

基本经济逻辑：

```text
需求上升 → 价格上涨 → 利润改善 → 未来供给增加 → 价格回落
```

以及：

```text
锂辉石成本上升 → 生产成本上升 → 利润下降 / 供给受压 → 碳酸锂价格变化
```

第一版允许使用少量潜在状态，例如：

- capacity
- inventory_gap
- margin
- expected_price

模型以“小规模、能稳定估计、经济含义清楚”为优先。

---

## 5. 按周执行计划

| 周次 | 主要任务 | 当前状态 / 具体安排 | 预期结果 |
|---|---|---|---|
| **第1周（9/9—9/15）** | 核心数据收集 | **已完成主目标**：核心四变量正式入库；公开宏观和尾部补缺完成；高价值 robustness / validation 层建立；仅保留少量 SMM canonical 尾部授权核验 | Data Freeze v1 已达到 GO，数据阶段不再阻塞实证 |
| **第2周（9/16—9/22）** | 数据整理与初步分析 | 以 v1 为固定输入，统一分析口径；生成描述统计、走势图、变换版本、异常/方法断点摘要；同步完成最后的 SMM 尾部核验 | 得到可直接用于后续建模的数据集和第一批基础图表；9/21 左右冻结版本 |
| **第3周（9/23—9/29）** | 变量关系分析 | 平稳性、相关性、结构变化和领先滞后分析；重点考察需求、产量、锂辉石价格与现货价格的关系 | 初步确定主要变量关系、滞后设定和后续模型方向 |
| **第4周（9/30—10/6）** | 基准模型分析 | Random Walk、AR、VAR/BVAR；第一版 OOS 预测；形成结构模型参照 | 第一批较完整实证结果和 baseline benchmark |
| **第5周（10/7—10/13）** | 结构模型搭建 | 建立 Demand / Cost / Supply / Spot 最小结构；冻结观测变量和潜在状态；完成 State-Space 第一版 | 最小结构模型代码框架完成 |
| **第6周（10/14—10/20）** | 模型估计与调试 | Kalman Filter、likelihood、初步参数估计；检查稳定性、识别和潜在状态路径 | 结构模型稳定运行，得到第一版参数和状态估计 |
| **第7周（10/21—10/27）** | 核心结果分析 | 完成需求、供给、成本冲击 IRF 和 FEVD；完善参数估计 | 得到论文核心动态结果 |
| **第8周（10/28—11/3）** | 历史解释与预测 | Historical Decomposition；解释 2021—22 上涨、2023 下跌及之后阶段；严格 OOS 预测 | 历史阶段解释和预测结果形成 |
| **第9周（11/4—11/10）** | 补充实验与期现分析 | 用已有期货数据做初步期现关系；替代价格源、样本和验证序列稳健性 | **主要实验基本完成并冻结** |
| **第10周（11/11—中期答辩）** | 中期答辩准备 | 原则上不再增加大型新实验；统一图表、结果、模型逻辑和结论 | 中期报告和 PPT 完成 |

---

## 6. 关键节点

### 2026-09-21：数据版本冻结

Data Freeze v1 已满足 GO。到该节点只允许：

- 完成 v2 尾部授权核验；
- 修正文档和可复现构建；
- 不再新增大规模变量搜集支线。

### 第 4 周结束

基准模型和第一批实证结果完成，可以开始用数据结果反推结构模型设定。

### 2026-10-19 左右

最小结构模型必须能够稳定运行，Kalman Filter、likelihood 和第一版参数估计基本跑通。

### 2026-11-02 左右

IRF 和 FEVD 完成，Historical Decomposition 与预测进入收尾。

### 第 9 周结束

主要实验冻结。之后只允许结果整理、小范围修正和必要补充实验。

---

## 7. 中期答辩时希望达到的状态

- 核心数据集和完整数据治理说明
- 数据特征、变量关系和滞后分析
- RW / AR / VAR-BVAR 基准模型
- 最小结构状态空间模型
- 参数估计
- IRF
- FEVD
- Historical Decomposition
- OOS Forecast
- 初步期现货分析
- 基本稳健性检验

目标不是只证明“模型可以做”，而是让论文的**主要实验部分已经基本形成**。

---

## 8. 中期后的安排

中期答辩后原则上不再重新搭建大型模型，工作重点转为：

1. 根据导师和答辩意见修改现有模型与结果；
2. 对有争议的结论补充必要的稳健性或对比实验；
3. 完善参数估计和 Bayesian MCMC（若中期版本尚未完全完成）；
4. 根据实际需要完善期现货分析，而不是默认增加复杂模块；
5. 集中撰写论文正文，整理图表、参考文献和结论；
6. 后期主要进行论文修改、补实验和定稿。

只有当中期结果明确显示主模型存在解释缺口时，再考虑：

- stochastic cycle
- observed inventory / capacity validation
- nonlinear / regime switching
- 更完整的期货定价或期权扩展

---

## 9. 最终执行原则

当前节奏已经从“找数据”正式切到“做实验”：

```text
9月中旬：冻结数据治理 + diagnostics
9月底—10月初：baselines
10月：结构模型 + Kalman + IRF/FEVD
11月上旬：历史分解 + OOS + 期现稳健性
11月中旬：答辩版本冻结
```

核心原则：**不等待完美数据，不无限扩张变量；先把最小结构完整跑通。**
