# Phase 1 实验计划：数据可行性与机制预检

> 阶段目标：**在写任何完整 DSGE 方程之前，先回答“数据是否支持核心机制、哪些变量值得进入结构模型、滞后大约是多少、哪些风险会让后续模型不可识别”。**
>
> 建议周期：2–3 周。
>
> 本阶段结束时必须形成明确的 Go / Revise / Stop 决策，而不是只得到一批描述性图表。

---

## 1. Phase 1 要回答的 8 个问题

1. 碳酸锂现货价格的可靠长样本从什么时候开始？
2. 供给、需求、库存、成本数据分别能够覆盖多长区间？
3. 关键变量的共同重叠样本是否足够支持月度结构模型？
4. 日度现货/期货与月度产业变量之间如何对齐，是否需要 Mixed-Frequency？
5. 需求、成本、库存、产量对价格的领先/滞后方向是否基本符合产业逻辑？
6. 是否存在明显结构突变，使单一线性模型不适用？
7. 哪些高度相关变量只能保留一个，避免后续参数识别失败？
8. 最小结构模型应保留哪些观测变量，哪些只能作为稳健性或代理变量？

---

## 2. 本阶段不做什么

Phase 1 明确不做：

- 不搭完整 MF-DSGE；
- 不做大规模 Bayesian MCMC；
- 不调参追求高拟合；
- 不加入 stochastic cycle；
- 不加入复杂 Markov switching；
- 不追求最终论文结论；
- 不把 VAR/ARDL 的结果直接当最终因果结论。

本阶段的 reduced-form 模型只是 **结构模型侦察工具**。

---

## 3. 第一版变量池

### 3.1 P0：必须拿到

| 模块 | 变量 | 目标频率 | Phase 1 角色 |
|---|---|---:|---|
| Spot | 电池级碳酸锂现货价格 | 日/月 | 核心被解释变量 |
| Supply | 国内碳酸锂产量 | 月 | 供给核心 |
| Demand | 新能源汽车销量或产量 | 月 | 需求候选 1 |
| Demand | 动力电池装车量 | 月 | 需求候选 2 |
| Cost | 锂辉石精矿价格 | 日/月 | 原料成本核心 |
| Inventory | 交易所库存/仓单或社会库存 | 日/周/月 | 库存核心 |
| Trade | 碳酸锂进口量 | 月 | 外部供给 |
| FX | USD/CNY | 日/月 | 进口成本 |

### 3.2 P1：强烈建议

- 锂盐开工率
- 碳酸锂有效产能
- 新增投产项目/产能
- 正极材料产量
- 储能需求
- 氢氧化锂价格
- 碳酸锂期货价格、成交量、持仓量、基差
- 交易所仓单

### 3.3 P2：后续再决定

- 地缘政治风险指数
- 市场情绪指标
- 利率
- 产业政策虚拟变量
- 电价/天然气等更细能源成本
- 企业级库存
- 全球锂矿供给

原则：Phase 1 优先保证 **P0 完整、口径一致、时间覆盖足够长**，而不是变量越多越好。

---

## 4. 数据源优先级

建议按以下顺序处理：

1. 已有可稳定访问的商业数据库（Wind / 同花顺 / SMM / 百川等）
2. 官方机构与交易所数据
3. 行业协会公开数据
4. 可复现的公开网页/报告数据
5. 代理变量

对每个变量记录：

- source
- source URL / database field
- unit
- frequency
- release lag
- first available date
- last available date
- missing ratio
- revision rule
- transform rule
- license / redistribution note

---

## 5. 仓库内建议实现

Phase 1 需要先建立以下最小工程结构：

```text
src/
├── data/
│   ├── loaders/
│   ├── cleaning/
│   ├── alignment/
│   └── schema.py
├── diagnostics/
│   ├── coverage.py
│   ├── stationarity.py
│   ├── correlation.py
│   ├── lag_screening.py
│   └── break_tests.py
├── baselines/
│   ├── ar.py
│   ├── var.py
│   └── ardl.py
└── evaluation/
    └── metrics.py

scripts/
├── build_phase1_dataset.py
├── run_phase1_diagnostics.py
└── run_phase1_baselines.py

configs/
└── phase1.yaml

outputs/phase1/
├── data_audit/
├── figures/
├── tables/
└── baseline_results/
```

---

## 6. Step 1 — 建立 canonical data dictionary

### 6.1 目标

为每个变量建立唯一标准命名和单位。

示例：

| canonical name | 含义 | 单位 | 原始频率 | 目标频率 |
|---|---|---|---:|---:|
| `lc_spot` | 电池级碳酸锂现货价格 | 元/吨 | 日 | 日/月 |
| `lc_output` | 国内碳酸锂产量 | 吨 | 月 | 月 |
| `ev_sales` | 新能源汽车销量 | 辆 | 月 | 月 |
| `battery_install` | 动力电池装车量 | GWh | 月 | 月 |
| `spodumene_price` | 锂辉石精矿价格 | USD/t | 日/周 | 月 |
| `lc_inventory` | 碳酸锂库存 | 吨 | 日/周 | 周/月 |
| `lc_import` | 碳酸锂进口量 | 吨 | 月 | 月 |
| `usd_cny` | 美元兑人民币 | CNY/USD | 日 | 月 |

### 6.2 验收

- 所有 P0 变量都有字段定义；
- 单位明确；
- 无同名不同口径；
- 价格含税/不含税、电池级/工业级等口径明确；
- 主力/连续期货构造规则明确。

输出：`docs/data_dictionary.md`。

---

## 7. Step 2 — 原始数据完整性审计

每个变量自动输出：

- start date
- end date
- number of observations
- missing ratio
- duplicate ratio
- min / median / max
- zero count
- negative count
- longest missing gap
- suspected outliers

### 关键图

1. coverage timeline
2. missingness heatmap
3. raw time-series panel
4. log-level / growth-rate comparison

### 验收

必须能一眼判断：

> “如果只保留 P0 变量，真正共同可用的月度样本到底有多少个月？”

这是 Phase 1 的第一条生死线。

---

## 8. Step 3 — 构造两个基础样本

### 8.1 Monthly Structural Dataset

用于后续供需—库存—价格结构模型。

建议包含：

```text
month
lc_spot
lc_output
ev_sales
battery_install
spodumene_price
lc_inventory
lc_import
usd_cny
```

月度聚合规则必须冻结，例如：

- spot：月均 / 月末，两者都保留但主口径固定；
- raw material price：月均；
- FX：月均；
- inventory：月末优先；
- output / sales / import：当月流量。

### 8.2 Daily Futures Dataset

用于后续期货扩展，不与长样本结构模型强行合并。

候选字段：

```text
date
lc_spot
lc_futures
basis
volume
open_interest
warehouse_receipt
usd_cny
rate
```

---

## 9. Step 4 — 变换与平稳性检查

对每个核心变量至少保存：

- level
- log level（适用时）
- first difference
- log difference / growth rate
- YoY（仅作为辅助，不默认进入动态模型）

检查：

- ADF
- KPSS（如实现方便）
- 必要时 PP
- 协整可能性

注意：平稳性结果用于决定 reduced-form 形式，不直接决定最终 DSGE 是否能使用 level/state 变量。

---

## 10. Step 5 — 机制方向预检

围绕核心链条：

\[
Demand \rightarrow Inventory \rightarrow Price
\]

和：

\[
Cost \rightarrow Margin/Supply \rightarrow Price
\]

先做：

- contemporaneous correlation
- cross-correlation
- lagged regression
- Granger screening
- pairwise plots

### 必须检查的关系

1. `ev_sales -> lc_spot`
2. `battery_install -> lc_spot`
3. `lc_output -> lc_spot`
4. `lc_inventory -> lc_spot`
5. `spodumene_price -> lc_spot`
6. `lc_import -> lc_spot`
7. `usd_cny -> spodumene_price / lc_spot`
8. `lc_spot -> future output/capacity`（如果有产能数据）
9. `margin -> future output/capacity`（如果可构造 margin）

输出不仅要报告 p-value，还要报告：

- direction
- lag length
- coefficient sign
- stability across subsamples

---

## 11. Step 6 — Reduced-form baseline

### 11.1 Baseline A：AR(1)

建立最简单价格动态基线。

### 11.2 Baseline B：VAR / BVAR

第一版变量不要超过 4–6 个。

候选：

\[
[Price, Inventory, Output, Demand, Cost]
\]

目标不是追求预测最优，而是观察 IRF/FEVD 的基础方向。

### 11.3 Baseline C：ARDL / VECM

- 如果变量存在协整：VECM；
- 如果平稳阶数不完全一致且满足 ARDL 条件：ARDL；
- 不强行所有模型都跑。

### 输出

- lag selection
- coefficients
- IRF
- FEVD
- residual diagnostics
- 简单滚动预测

---

## 12. Step 7 — 结构突变与阶段性检查

碳酸锂价格存在剧烈 regime change 风险，因此 Phase 1 必须检查：

- rolling mean / variance
- rolling correlation
- break-point candidate
- crisis / boom / correction subperiod

可选方法：

- Bai-Perron
- Zivot-Andrews
- CUSUM
- 简单事件分段

本阶段目的不是最终确定非线性模型，而是判断：

> 单一线性关系是否在各阶段严重失效？

如果答案是“是”，后续结构模型需要预留 regime extension。

---

## 13. Step 8 — 构造第一版 margin 指标

如果锂辉石和成本数据可用，至少先做一个粗略利润代理：

\[
MarginProxy_t=LCSpot_t-\theta \cdot SpodumenePrice_t \cdot FX_t
\]

\(\theta\) 第一阶段可以先用产业转换系数或区间敏感性分析，不急于估计最终参数。

然后检查：

\[
MarginProxy_t \rightarrow Output_{t+k}
\]

以及若有数据：

\[
MarginProxy_t \rightarrow Capacity_{t+k}
\]

扫描多个 \(k\)：

- 1–3 个月
- 4–6 个月
- 7–12 个月
- 更长滞后（视项目数据覆盖）

这一结果将直接决定 Phase 2/3 的产能滞后结构。

---

## 14. 第一阶段核心图表清单

至少生成以下图表：

1. 所有变量 coverage timeline
2. 核心变量标准化时间序列
3. LC spot 原始与 log/diff 序列
4. spot vs output
5. spot vs inventory
6. spot vs spodumene
7. spot vs EV/battery demand
8. cross-correlation heatmap
9. rolling correlation
10. candidate structural breaks
11. baseline VAR IRFs
12. margin proxy vs future output/capacity

这些图的目标是帮助结构设计，而不是直接作为最终论文图。

---

## 15. Phase 1 的最低实验基线

即便完整数据还没有全部拿到，也应该尽早建立以下 baseline：

### Price-only baseline

- Random Walk
- AR(1)

### Small multivariate baseline

- Price
- Inventory
- Demand
- Cost

后续所有结构模型都必须与这些 baseline 比较，避免出现“复杂模型只是在拟合价格惯性”的问题。

---

## 16. Phase 1 验收标准

### A. 数据覆盖 Gate

**Go**：至少 4–6 个核心月度变量存在较长共同样本，且缺失可控。

**Revise**：库存/产能缺失，但可找到可靠代理。

**Stop/Redesign**：共同样本过短，连最小供需库存模型都无法支撑。

### B. 经济方向 Gate

**Go**：至少需求、成本、库存、供给中的多数关系符号合理且具有一定滞后稳定性。

**Revise**：关系随阶段变化明显，需要 regime design。

**Stop/Redesign**：核心变量与价格几乎完全无稳定关系。

### C. 滞后 Gate

**Go**：能够识别出大致滞后区间，例如成本 0–3 月、需求 0–3 月、投资/产能 6–18 月等。

**Revise**：滞后不稳定，后续用分布滞后或状态变量处理。

### D. Baseline Gate

必须建立可复现的 Random Walk / AR / VAR(BVAR) 基线，作为之后所有复杂模型的固定比较对象。

---

## 17. Phase 1 结束时的决策输出

必须形成一个 `Phase 1 Decision Memo`，明确回答：

### Keep

哪些变量进入 MVP DSGE。

### Drop

哪些变量因为共线、缺失、经济解释弱而删除。

### Proxy

哪些变量需要代理。

### Lag

每条核心机制采用什么先验滞后范围。

### Breaks

是否需要在后续模型中考虑结构突变/状态切换。

### Sample

最终长样本现货模型和短样本期货模型分别使用什么区间。

### Phase 2 MVP

冻结 Phase 2 的第一版状态变量、观测变量和 3–4 个结构冲击。

---

## 18. 推荐执行顺序

### Day 1–3：数据字典与数据抓取

- 冻结 P0 变量
- 建立 loaders
- 保存 raw data
- 建立 metadata

### Day 4–6：数据审计与 canonical dataset

- 单位统一
- 时间对齐
- 缺失与异常值检查
- 月度结构样本生成
- 日度期货样本生成

### Day 7–9：统计与滞后机制预检

- stationarity
- correlation
- cross-correlation
- Granger
- margin proxy

### Day 10–12：baseline

- Random Walk
- AR(1)
- VAR/BVAR
- 必要时 ARDL/VECM

### Day 13–14：结构突变 + Decision Memo

- break diagnostics
- subsample stability
- Keep/Drop/Proxy/Lag 决策
- 冻结 Phase 2 MVP

如果数据获取耗时较长，周期可扩展至 3 周，但分析顺序不变。

---

## 19. Phase 1 完成定义（Definition of Done）

只有满足下面条件，Phase 1 才算完成：

- [ ] P0 数据字典完成
- [ ] 原始数据可追溯
- [ ] 月度 canonical dataset 可一键构建
- [ ] 日度期货 dataset 可一键构建（若数据已取得）
- [ ] data audit 自动生成
- [ ] 核心关系 lag screening 完成
- [ ] Random Walk / AR / VAR(BVAR) baseline 完成
- [ ] 结构突变初检完成
- [ ] margin proxy 初检完成
- [ ] Phase 1 Decision Memo 完成
- [ ] Phase 2 MVP 变量集冻结

---

## 20. Phase 1 成功后的 Phase 2 输入

Phase 2 不再从“所有可能变量”出发，而只接收 Phase 1 筛选后的最小变量集。

理想输入类似：

```text
Observed:
- lc_spot
- lc_output
- demand_index
- lc_inventory
- spodumene_cost

State / latent:
- expected_price
- margin
- production_capacity (if not directly observed)

Shocks:
- demand shock
- raw-material cost shock
- supply/capacity shock
- inventory shock
```

Phase 2 的目标只有一个：

> **把 Demand + Production + Inventory + Spot 的最小结构模型稳定跑通，并得到经济符号和时序合理的 IRF。**

在这之前，不进入完整 MF-DSGE。
