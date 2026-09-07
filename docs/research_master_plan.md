# DSGE-LC 研究整体计划

> 项目定位：先做实验、再决定最终论文形态。
>
> 当前目标不是立刻完成论文写作，而是验证一个针对中国碳酸锂产业链的结构模型是否真的具有经济解释力、参数可识别性、历史解释能力与样本外预测价值。

---

## 1. 核心研究问题

本项目围绕一个总问题展开：

> **中国碳酸锂价格的大幅上涨、快速下跌与阶段性震荡，能否由“需求—库存—利润—投资—滞后产能—供给—价格”的产业链动态机制解释，并进一步统一现货与期货定价？**

拆分为 6 个可检验问题：

1. 新能源汽车、动力电池、储能等下游需求变化，对碳酸锂现货价格的冲击有多大、持续多久？
2. 锂辉石等上游成本冲击，是否主要通过利润压缩、开工率下降与供给收缩传导至价格？
3. 高利润是否会诱发资本开支和新增产能，并通过建设/投产滞后形成内生的“锂周期”？
4. 库存是否是连接供需变化与短期价格波动的关键状态变量？
5. 期货价格是否通过预期、持有成本、便利收益、套保压力和投机需求，更快地反映产业信息？
6. 一个结构化 MF-DSGE 是否能在样本外预测和历史解释中优于 Random Walk、AR、VAR/BVAR 等简单基线？

---

## 2. 总体研究策略

本项目采用 **experiment-first + staged complexity** 原则。

不直接搭建一个包含几十个方程、几十个冲击的大型 DSGE，而是按模块逐步增加复杂度。每增加一个模块，都必须回答：

- 是否改善参数识别？
- 是否改善 IRF 的经济合理性？
- 是否改善历史分解？
- 是否改善样本外预测？
- 是否只是提高了拟合，但没有真正增加解释力？

只有通过增量验证的模块，才进入最终模型。

---

## 3. 最终候选模型的经济结构

### 3.1 需求模块

碳酸锂是中间投入品，不直接采用“居民消费碳酸锂”的代表性家庭逻辑。

候选需求结构：

\[
D_t^{LC}=D_t^{EV}+D_t^{ESS}+D_t^{Other}
\]

其中重点由以下变量驱动：

- 新能源汽车销量/产量
- 动力电池装车量
- 储能需求
- 正极材料产量
- 单位电池锂耗/技术路线变化

预期机制：

\[
Demand\uparrow \Rightarrow Inventory\downarrow \Rightarrow Price\uparrow
\]

---

### 3.2 供给/生产模块

基础生产函数候选：

\[
Q_t=A_t K_t^{\alpha} M_t^{\beta} u_t
\]

其中：

- \(Q_t\)：碳酸锂产量
- \(A_t\)：技术、提锂效率、管理效率
- \(K_t\)：有效产能
- \(M_t\)：矿石/盐湖资源投入
- \(u_t\)：产能利用率/开工率

预期机制：

\[
Capacity\uparrow \Rightarrow Output\uparrow \Rightarrow Inventory\uparrow \Rightarrow Price\downarrow
\]

---

### 3.3 成本与利润模块

构造碳酸锂产业利润指标：

\[
Margin_t=P_t^{LC}-Cost_t
\]

成本项可由：

\[
Cost_t=\omega_1 P_t^{Spodumene}+\omega_2 Energy_t+\omega_3 FX_t+\omega_4 Other_t
\]

构成。

核心机制：

\[
Margin\uparrow \Rightarrow Utilization\uparrow
\]

以及中长期：

\[
Margin\uparrow \Rightarrow Investment\uparrow
\]

---

### 3.4 投资—产能滞后模块

这是碳酸锂模型最关键的结构之一。

候选形式：

\[
K_{t+1}=(1-\delta_K)K_t+I_{t-L}
\]

其中 \(L\) 表示矿山、盐湖或锂盐加工项目的建设/投产滞后。

目标是让模型在不依赖额外随机周期项的情况下，先测试能否自然生成：

\[
Price\uparrow \rightarrow Margin\uparrow \rightarrow Investment\uparrow \rightarrow Capacity_{t+L}\uparrow \rightarrow Output\uparrow \rightarrow Inventory\uparrow \rightarrow Price\downarrow
\]

如果该机制已经能产生稳定周期，则 stochastic cycle 只作为后续增量模块，而不是先验必选项。

---

### 3.5 库存模块

库存是碳酸锂相对生猪模型最重要的新增结构。

基础恒等式：

\[
INV_{t+1}=INV_t+Q_t-D_t
\]

候选价格机制：

\[
P_t=f(Q_t-D_t,INV_t,E_tP_{t+1})
\]

预期：

- 需求冲击 → 库存下降 → 价格上升
- 产能释放 → 库存增加 → 价格下降
- 库存过低 → 便利收益上升 → 近月现货/期货定价发生变化

---

### 3.6 现货价格模块

第一阶段不追求复杂价格粘性结构，先验证最小可识别形式。

候选因素：

- 供需缺口
- 库存水平
- 预期未来供需
- 成本与利润状态
- 外生供给扰动

后续视数据与残差特征决定是否引入：

- 非线性价格调整
- 状态切换
- 阈值效应
- Regime-dependent shock

---

### 3.7 期货与基差模块

候选定价骨架：

\[
F_{t,T}=S_t e^{(r_t+s_t-y_t)(T-t)}+RP_t
\]

其中：

- \(r_t\)：资金成本
- \(s_t\)：仓储/持有成本
- \(y_t\)：便利收益
- \(RP_t\)：风险溢价

风险溢价候选：

\[
RP_t=f(Hedging_t,Speculation_t,Inventory_t)
\]

重点研究：

\[
Inventory \rightarrow Convenience\ Yield \rightarrow Basis \rightarrow Futures
\]

以及：

\[
Expectation + Hedging + Speculation \rightarrow Futures
\]

---

### 3.8 宏观与外部冲击

第一版只保留少量高价值冲击：

1. 新能源需求冲击
2. 锂矿/原料成本冲击
3. 供给/产能冲击
4. 库存冲击
5. 汇率/进口成本冲击

后续根据识别结果再考虑：

- 利率冲击
- 产业政策冲击
- 地缘政治风险
- 市场情绪
- stochastic cycle

原则：**冲击越少越好，前提是能够解释主要机制。**

---

## 4. 数据体系设计

### 4.1 核心数据层

| 模块 | 变量 | 建议频率 | 主要用途 |
|---|---|---:|---|
| 现货 | 电池级碳酸锂现货价格 | 日/周 | 价格核心观测 |
| 期货 | 主力/连续合约、近月合约 | 日 | 期货定价与预测 |
| 基差 | Spot - Futures | 日 | 期现结构 |
| 供给 | 碳酸锂产量 | 月 | 生产模块 |
| 产能 | 有效产能/投产项目/开工率 | 月 | 产能周期 |
| 成本 | 锂辉石精矿价格 | 日/周/月 | 原料成本冲击 |
| 成本 | 能源价格、汇率 | 日/月 | 成本传导 |
| 需求 | 新能源汽车销量/产量 | 月 | 需求冲击 |
| 需求 | 动力电池装车量 | 月 | 需求冲击 |
| 需求 | 储能、正极材料产量 | 月 | 需求稳健性 |
| 库存 | 交易所库存/仓单 | 日/周 | 库存状态 |
| 库存 | 社会库存/企业库存代理 | 周/月 | 库存稳健性 |
| 贸易 | 碳酸锂进口量 | 月 | 外部供给 |
| 金融 | 利率 | 日/月 | 期货持有成本 |

### 4.2 两层样本设计

**长样本现货模型**：尽可能使用更早期的现货与产业数据，用于供需、库存、成本、产能机制识别。

**短样本期货扩展模型**：以碳酸锂期货上市之后的日度数据为主，用于期现联动、基差、套保/投机和预测。

原则：不为了期货模块，把整个结构模型都压缩到一个过短样本。

---

## 5. 实验路线图

### Experiment 0 — 数据可行性

目标：确认哪些机制能被数据支持。

输出：

- canonical dataset
- data dictionary
- 缺失率/频率/起止时间审计
- 结构突变和异常值报告
- 同步规则

### Experiment 1 — Reduced-form 机制预检

使用：

- AR/ARIMA
- VAR/BVAR
- ARDL/VECM（视平稳性和协整而定）
- Granger/lag screening

目的：

- 估计潜在滞后长度
- 识别变量方向
- 给 DSGE prior 与结构参数范围提供依据

### Experiment 2 — 最小结构模型 MVP

仅包含：

- Demand
- Production
- Inventory
- Spot Price

验收标准：

- 稳态可解
- 动态稳定
- 需求/供给/库存冲击 IRF 符号合理
- 关键参数可识别

### Experiment 3 — 产能投资滞后

新增：

- Margin
- Investment
- Capacity Lag

核心检验：

模型是否能够内生生成“高利润—扩产—滞后过剩—价格回落”的周期。

### Experiment 4 — 期货模块

新增：

- Futures
- Basis
- Carry
- Convenience Yield
- Hedging/Speculation

检验：

期货是否比现货更快反映基本面与预期。

### Experiment 5 — Mixed-Frequency

构建：

- 日度价格
- 周度库存
- 月度产业数据

进入统一状态空间，用不规则 Kalman Filter 处理异频观测。

### Experiment 6 — Bayesian MCMC

目标：

- posterior estimation
- 多链收敛
- posterior-vs-prior identification
- posterior predictive check

### Experiment 7 — Stochastic Cycle Ablation

比较：

- Base Model
- Base + Stochastic Cycle

必须评估：

- likelihood / marginal likelihood
- FEVD 是否被单一周期项过度支配
- forecast 是否真正改善
- residual 是否改善
- turning-point detection 是否改善

### Experiment 8 — 非线性扩展（仅必要时）

如果模型出现：

- 水平拟合很好
- 转折点预测差
- 尾部残差明显厚尾

再考虑：

- Markov switching
- Threshold state
- Regime-dependent shock
- 非线性状态空间

---

## 6. 统一验收指标

### 6.1 求解层

- steady state 成功
- BK/stability 条件满足
- 无爆炸路径
- 初值扰动后回归稳态

### 6.2 参数层

- 多链收敛
- \(\hat R\) 合格
- ESS 足够
- 关键 posterior 不完全复制 prior
- 参数不长期贴边界
- 不同初始化结果稳定

### 6.3 IRF 层

重点检查“符号 + 时间顺序”，而不是只看图是否平滑。

预期核心模式：

| 冲击 | Price | Output | Inventory | Margin | Future Capacity |
|---|---:|---:|---:|---:|---:|
| Demand + | ↑ | 滞后↑ | ↓ | ↑ | ↑ |
| Raw Material Cost + | ↑ | ↓ | ↓/不确定 | ↓ | ↓ |
| Capacity + | ↓ | ↑ | ↑ | ↓ | ↓ |
| Technology + | ↓ | ↑ | ↑ | 短期不确定 | ↑ |
| FX Depreciation | ↑ | ↓ | ↓ | ↓ | ↓ |
| Inventory + | ↓ | 近端弱 | ↑ | ↓ | ↓ |

### 6.4 FEVD 层

目标：解释“谁驱动价格波动”。

但设置防过拟合规则：

- 如果一个抽象周期项解释 >70% 的多数核心变量，必须做 ablation；
- 如果去掉该项后模型仍能合理解释历史，则优先保留经济机制模型；
- FEVD 必须和 historical decomposition 相互印证。

### 6.5 历史分解

重点解释：

- 2021–2022 上涨阶段
- 高位转折
- 2023 快速下跌阶段
- 后续低位震荡/反弹阶段

希望模型能够区分：

- demand-driven rally
- supply-release correction
- inventory accumulation/depletion
- cost shock
- expectation/futures shock

### 6.6 样本外预测

至少比较：

- Random Walk
- AR(1)
- VAR/BVAR
- Simple Carry/Futures Model
- Structural Model / MF-DSGE

指标：

- RMSE
- MAE
- Theil’s U
- Direction Accuracy
- Up Accuracy
- Down Accuracy
- Turning-point Accuracy

重点：**不把高 R² 当作样本外预测成功。**

---

## 7. Go / No-Go 决策规则

### Gate A — 数据

Go：关键变量样本长度足够、频率可统一、库存/产能至少有可靠代理。

No-Go：核心变量长期缺失、样本重叠过短、无法建立最小供需库存系统。

### Gate B — 结构模型

Go：MVP 可稳定求解，核心冲击 IRF 符号和时序合理。

No-Go：长期出现不可解释反向响应，且无法通过结构调整解决。

### Gate C — 参数识别

Go：关键参数 posterior 被数据更新且多链收敛。

No-Go：大部分参数 posterior≈prior 或严重贴边界。

### Gate D — 历史解释

Go：上涨与下跌阶段由不同结构冲击主导，符合产业事实。

No-Go：模型主要靠一个抽象残差/周期项解释全部波动。

### Gate E — 预测

Go：至少在部分关键指标上稳定优于 Random Walk/AR/VAR baseline，且 Theil’s U < 1。

No-Go：高拟合但样本外无增量价值。

---

## 8. 论文最终可能形成的三档版本

### Version A — 最稳妥

产业链结构模型 + VAR/BVAR 稳健性 + 期现价格发现。

适用于：Mixed-Frequency/MCMC 增量有限，但核心产业机制成立。

### Version B — 目标版本

产业链 MF-DSGE + Bayesian MCMC + Historical Decomposition + Forecast Benchmark。

这是当前首选目标。

### Version C — 扩展版本

Version B + Stochastic Cycle / Regime Switching / Nonlinear Extension。

只有在实验明确证明有增量价值时采用。

---

## 9. 建议仓库结构

```text
DSGE-LC/
├── README.md
├── docs/
│   ├── research_master_plan.md
│   ├── phase1_experiment_plan.md
│   ├── data_dictionary.md
│   ├── model_equations.md
│   └── decision_log.md
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── src/
│   ├── data/
│   ├── diagnostics/
│   ├── baselines/
│   ├── model/
│   ├── estimation/
│   └── evaluation/
├── scripts/
├── configs/
├── notebooks/
├── tests/
└── outputs/
    ├── figures/
    ├── tables/
    ├── diagnostics/
    └── runs/
```

原则：raw data 不覆盖，processed data 可复现生成，所有实验有 run config 与输出目录。

---

## 10. 项目阶段规划

### Phase 1 — 数据可行性与机制预检

目标：确认数据、滞后、方向、结构突变，决定 MVP 变量集。

### Phase 2 — 最小结构模型

目标：Production + Demand + Inventory + Spot 能稳定求解并产生合理 IRF。

### Phase 3 — 利润、投资与产能滞后

目标：测试内生锂周期。

### Phase 4 — 期货与基差

目标：建立 inventory/carry/expectation/futures 链条。

### Phase 5 — Mixed-Frequency + Bayesian Estimation

目标：统一异频观测并完成参数后验估计。

### Phase 6 — 历史分解、样本外预测、消融

目标：决定最终论文究竟保留哪些模块。

### Phase 7 — 论文正式写作

只有完成前六阶段的关键 Go/No-Go 决策后，才冻结最终模型与论文框架。

---

## 11. 当前最重要的研究纪律

1. 不为了“论文更复杂”增加模块。
2. 不为了提高 R² 调整结构。
3. 不允许用全样本拟合冒充样本外预测。
4. 不允许 stochastic cycle 在未经消融的情况下成为万能解释变量。
5. 所有结构假设必须有数据、文献或产业机制至少一种支持。
6. 所有关键结果都必须能够被复现实验脚本一键生成。
7. 每个阶段结束时都记录“保留/删除/待验证”的决策。

---

## 12. 当前项目结论

当前最值得优先验证的不是完整 MF-DSGE，而是一个更小的核心闭环：

\[
Demand \rightarrow Inventory \rightarrow Spot\ Price
\]

以及：

\[
Spot\ Price-Cost \rightarrow Margin \rightarrow Investment/Utilization \rightarrow Lagged\ Capacity \rightarrow Output \rightarrow Inventory
\]

如果这两个闭环可以在真实碳酸锂数据上得到稳定、可解释、可识别的实验结果，则本研究方向成立；后续 Mixed-Frequency、期货、stochastic cycle 和非线性模型均作为增量扩展。
