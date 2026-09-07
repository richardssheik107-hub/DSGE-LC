# DSGE-LC 数据策略：稀疏观测 + 潜在状态

> 本文档记录 2026-09-07 后的数据策略调整。
>
> 核心原则：参照生猪 MF-DSGE 的真实做法，不要求模型中的每一个经济变量都有现实观测，而是使用少量高质量、可持续获取的观测序列去锚定模型，其余变量作为 latent states 由结构方程和 Kalman Filter 推断。

---

## 1. 为什么调整数据策略

原计划试图同时获取：现货、期货、产量、产能、开工率、库存、消费、锂辉石、进口、正极材料、储能、利润等大量产业数据。

现实问题是：

- 多年前的碳酸锂产能、开工率和社会库存很难获得统一口径长历史；
- SMM、Mysteel、百川等商业数据库的历史权限并不稳定；
- 库存和产能口径可能随样本覆盖、统计方法变化；
- 如果把这些变量都设为“必须观测”，项目会被数据获取而不是模型研究卡住。

因此改为：

**少量可靠观测 + 结构方程 + latent states + mixed-frequency Kalman。**

---

## 2. 参考生猪论文的数据思想

参考论文并没有为完整 DSGE 状态向量中的每个变量都寻找真实数据，而是只用少量现实观测变量锚定模型，例如：

- 生猪现货价格
- 生猪期货价格
- 猪粮比价
- 能繁母猪存栏
- 豆粕价格
- 替代品价格
- 居民收入
- CPI

资本、投资、部分需求、政策冲击等并不要求逐项观测。

我们迁移的不是“生猪变量名称”，而是这种 **sparse observation** 设计思想。

---

## 3. 第一版真正需要的核心观测数据

### 3.1 五个核心产业/市场观测

| 优先级 | 数据 | Canonical name | 频率 | 作用 | 第一版是否必须 |
|---|---|---|---:|---|---|
| P0 | 电池级碳酸锂现货价格 | `lc_spot` | 日 / 月 | 核心价格观测 | 必须 |
| P0 | 碳酸锂月度产量 | `lc_output` | 月 | 供给锚 | 必须 |
| P0 | 锂辉石价格或等价原料成本 | `spodumene_price` | 日 / 周 / 月 | 成本锚 | 必须 |
| P0 | 动力电池装车量 | `battery_install` | 月 | 下游需求锚 | 必须 |
| P0-F | 碳酸锂期货各合约价格 | `lc_futures_*` | 日 | 期货扩展、预期、价格发现 | 期货模型必须；现货模型不必 |

### 3.2 两个容易补齐的宏观观测

| 优先级 | 数据 | Canonical name | 频率 | 作用 |
|---|---|---|---:|---|
| P1 | USD/CNY | `usd_cny` | 日 / 月 | 美元计价矿石成本换算、进口成本冲击 |
| P1 | 3M/6M 国债收益率或等价无风险利率 | `risk_free_rate` | 日 / 月 | 融资成本、期货 carry |

因此第一版可将核心观测向量压缩为：

\[
Y_t^{obs}=[P_t^{LC},Q_t^{LC},Cost_t^{Ore},Demand_t^{Battery},r_t]'
\]

期货上市后的扩展样本增加：

\[
F_t^{LC}
\]

若锂辉石为美元报价，再加入：

\[
FX_t
\]

---

## 4. 不再要求第一阶段必须观测的数据

以下变量仍可进入模型，但不再作为 Phase 1 的数据生死线：

| 变量 | 新定位 |
|---|---|
| 有效产能 `capacity` | latent state；有真实数据时用于验证 |
| 资本开支/投资 `investment` | latent state |
| 开工率 `utilization` | latent state 或简化掉；有数据时做外部验证 |
| 社会库存 `inventory` | baseline 可作为 latent state；真实库存后续做扩展/验证 |
| 企业利润 | 不单独购买；优先由 spot 与 ore cost 构造 margin proxy |
| 完整实际消费量 | 不要求；以动力电池装车量作为需求锚 |
| 新增项目/投产表 | 后续做 capacity validation，不是 baseline 必需 |
| LFP/NCM/储能 | robustness/需求扩展，不在第一轮强制获取 |
| 政策/地缘/情绪 | shock 或后期扩展，不要求一开始构造长序列 |

---

## 5. 第一版潜在状态设计

候选完整状态向量可包括：

\[
X_t=[P_t,F_t,Q_t,D_t,Cost_t,Margin_t,Capacity_t,Investment_t,Inventory_t,ExpectedPrice_t,RiskPremium_t,r_t,A_t]'
\]

其中真实可观测只占一部分。

重点 latent states：

### 5.1 产能

\[
K_{t+1}=(1-\delta_K)K_t+I_{t-L}
\]

不要求找到 2018 年以来统一口径月度产能。

### 5.2 投资

\[
I_t=\rho_I I_{t-1}+\phi_M Margin_t+\varepsilon_t^I
\]

不要求获得全行业资本开支数据。

### 5.3 库存

候选库存恒等式：

\[
INV_{t+1}=INV_t+Q_t-D_t
\]

第一版允许库存不进入观测方程；如果后续能获得可靠库存，则增加为稀疏观测，用于过滤状态和验证。

### 5.4 Margin

第一版不购买独立利润序列，优先构造：

\[
MarginProxy_t=P_t^{LC}-\theta P_t^{Spodumene}FX_t
\]

Mysteel/SMM 若有生产成本或即期利润，可作为 robustness benchmark。

---

## 6. 两层样本设计

### Model A — 长样本现货结构模型

目标：尽可能使用期货上市前后的产业信息识别结构机制。

优先数据：

- `lc_spot`
- `lc_output`
- `spodumene_price`
- `battery_install`
- `usd_cny`
- `risk_free_rate`

建议不要先固定起点，先做 coverage audit。目标优先争取：

**2020-01 至 2026-08**

若关键数据能稳定追溯到更早，再向前扩展；不要为了追求 2018 起点而使用明显断裂或拼接质量差的数据。

### Model B — 期货扩展模型

样本从广州期货交易所碳酸锂期货上市开始：

**2023-07-21 至最新完整交易日**

增加：

- 各 LC 合约价格
- 结算价
- 成交量
- 持仓量
- 到期时间
- 后续可加入仓单、基差、期限结构

原则：**不为了期货模块，将长样本现货结构模型整体截断到 2023 年。**

---

## 7. 数据源优先级

第一版数据获取优先顺序：

1. 学校/机构已有 Wind、iFinD、Mysteel 等授权；
2. Mysteel/钢联数据可导出历史产业序列；
3. 官方公开数据：GFEX、PBOC、ChinaBond、行业协会；
4. SMM/百川作为补充，不让单一商业数据源成为项目单点依赖；
5. 必要时使用可解释 proxy，并显式记录 proxy 规则。

核心原则：**宁可少 1–2 个变量，也不要为了凑全模型使用无法复现、口径断裂严重的历史数据。**

---

## 8. Phase 1 现在只需要确认的五项数据

第一轮 data availability audit 只围绕：

1. `lc_spot`
2. `lc_output`
3. `spodumene_price`
4. `battery_install`
5. `lc_futures`

对每项记录：

- 数据源
- 最早日期
- 最新日期
- 频率
- 单位
- 口径
- 是否可批量导出
- 是否存在权限限制
- 缺失率
- 是否发生方法/样本调整

`usd_cny` 与 `risk_free_rate` 属于后续容易补齐的公共数据，不作为第一轮难点。

---

## 9. Go / Revise / Stop 条件

### Go

满足以下条件即可进入第一版结构实验：

- 现货、产量、锂辉石、动力电池至少形成约 60 个以上共同月度观测；
- 价格和产量口径稳定；
- 成本代理有明确经济含义；
- 需求代理不存在大量不可解释缺口；
- 期货数据可从 2023-07-21 后单独建立日频数据库。

### Revise

如果长样本只有 36–60 个月：

- 减少状态与待估参数；
- 增强 prior；
- 先跑简化 state-space；
- 推迟 stochastic cycle 和复杂期货风险溢价模块。

### Stop / Change Topic Trigger

只有在以下情况同时发生时才考虑放弃当前结构：

- 现货价格长历史无法获得；
- 产量无法得到连续月度历史；
- 锂辉石/成本没有任何可靠历史代理；
- 需求代理也无法形成稳定月度序列。

目前判断该情况发生概率较低。

---

## 10. 当前工作原则

从现在起，不再把以下任务放在数据获取第一优先级：

- 寻找 2018 起完整月度产能；
- 寻找 2018 起完整开工率；
- 寻找 2018 起统一口径社会库存；
- 拼接所有企业资本开支；
- 拼接所有投产项目；
- 同时收集 EV、Battery、LFP、NCM、ESS 全部需求变量。

当前唯一目标是先证明：

\[
Spot + Output + OreCost + BatteryDemand
\]

能否对碳酸锂价格形成一个可识别、可解释的结构系统；随后再加入 Futures 和 mixed-frequency。

---

## 11. 与后续实验的接口

Phase 1 完成后，按以下顺序推进：

1. Random Walk / AR price baselines
2. 小型 VAR/BVAR 机制预检
3. 现货结构 state-space MVP
4. latent capacity / investment / inventory
5. 期货扩展
6. mixed-frequency Kalman
7. Bayesian MCMC
8. stochastic cycle ablation
9. 必要时 nonlinear/regime extension

本数据策略的目标不是减少理论深度，而是减少对不可获得历史产业数据的依赖，让模型复杂度由实验效果而不是数据想象决定。
