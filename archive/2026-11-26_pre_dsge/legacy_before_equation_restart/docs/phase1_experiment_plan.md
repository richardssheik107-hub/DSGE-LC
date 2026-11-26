# Phase 1 实验计划：稀疏观测数据可行性与机制预检

> 2026-09-07 修订版。
>
> 阶段目标：不再要求把碳酸锂产业链所有变量都找齐，而是参照生猪 MF-DSGE 的数据策略，先确认少量高质量观测是否足以锚定一个结构模型。
>
> 核心思想：**sparse observations + latent states + mixed-frequency Kalman。**

---

## 1. Phase 1 现在只回答 6 个问题

1. 碳酸锂现货价格能获得多长、口径是否稳定？
2. 碳酸锂月度产量能否形成连续长样本？
3. 锂辉石价格/原料成本能否形成可解释的长期代理？
4. 动力电池装车量能否作为稳定的月度需求锚？
5. 期货上市后能否建立完整的日频 LC 合约数据库？
6. 仅依赖这几类观测，是否已经足够支持后续 state-space / DSGE 估计？

本阶段不再把“2018 年以来完整产能、开工率、社会库存”作为 Go/No-Go 条件。

---

## 2. 第一版 P0 数据：只保留五项

| 数据 | Canonical name | 原始频率 | 主要用途 | 是否必须 |
|---|---|---:|---|---|
| 电池级碳酸锂现货价格 | `lc_spot` | 日 | 核心价格观测 | 必须 |
| 国内碳酸锂产量 | `lc_output` | 月 | 供给锚 | 必须 |
| 锂辉石价格/原料成本 | `spodumene_price` | 日/周/月 | 成本锚 | 必须 |
| 动力电池装车量 | `battery_install` | 月 | 需求锚 | 必须 |
| 碳酸锂期货各合约 | `lc_futures_*` | 日 | 期货扩展 | 现货模型不必；期货模型必须 |

容易补齐但不是第一轮难点：

- `usd_cny`
- `risk_free_rate`

第一轮暂不强制：

- capacity
- utilization
- observed inventory
- investment
- enterprise profit
- NEV sales
- LFP/NCM/ESS
- policy / sentiment / geopolitical indices

---

## 3. 观测变量与潜在状态分离

### 3.1 第一版观测向量

长样本现货模型：

\[
Y_t^{obs}=[P_t^{LC},Q_t^{LC},Cost_t^{Ore},Demand_t^{Battery},r_t]'
\]

若锂辉石为美元报价，再加入：

\[
FX_t
\]

期货上市后增加：

\[
F_t^{LC}
\]

### 3.2 第一版 latent states

候选：

- `capacity`
- `investment`
- `inventory`
- `margin`
- `expected_price`
- `risk_premium`
- `productivity`

它们可以进入状态方程，但不要求都进入观测方程。

---

## 4. 两层样本设计

### Dataset A — Monthly Structural

目标：尽量形成比期货历史更长的产业样本。

第一目标区间：

**2020-01 至 2026-08**

但起点不先验锁死，由真实 coverage audit 决定。若 2018/2019 数据质量足够好，可向前扩展；若更早数据口径不稳定，则宁可从 2020 开始。

建议字段：

```text
month
lc_spot
lc_output
spodumene_price
battery_install
usd_cny
risk_free_rate
```

月度聚合：

- spot：主口径用月均，保留月末版本做 robustness；
- spodumene：月均；
- output：当月流量；
- battery_install：当月流量；
- FX / rate：月均。

### Dataset B — Daily Futures

时间：

**2023-07-21 至最新完整交易日**

建议字段：

```text
date
contract
open
high
low
close
settlement
volume
open_interest
time_to_maturity
spot
usd_cny
risk_free_rate
```

必须保留每个真实 LC 合约，不只保存主力连续。

---

## 5. 数据源策略

优先顺序：

1. 学校/机构现有 Wind、iFinD、Mysteel 权限；
2. Mysteel/钢联数据用于锂产业历史序列；
3. GFEX、PBOC、ChinaBond、行业协会等官方公开数据；
4. SMM/百川作为补充；
5. 最后才使用自构造 proxy。

对每个变量必须记录：

- source
- database field / URL
- first available date
- last available date
- frequency
- unit
- definition
- missing ratio
- whether exportable
- permission / license note
- revision / methodology break

---

## 6. Step 1 — Data availability matrix

第一阶段的第一份正式输出不是模型，而是：

`docs/data_availability_matrix.md`

至少包含：

| Variable | Source | Start | End | Freq | Unit | Exportable | Missing | Decision |
|---|---|---|---|---|---|---|---|---|

只围绕五项核心数据先做。

验收标准：每项都明确是：

- Keep
- Proxy
- Replace
- Drop

不能保留“以后再看看”状态。

---

## 7. Step 2 — Coverage audit

自动输出：

- start / end date
- observation count
- missing ratio
- longest missing gap
- duplicate ratio
- outlier candidates
- methodology breaks

核心问题：

> `lc_spot + lc_output + spodumene_price + battery_install` 的共同月度样本到底有多少个月？

### Gate

- **>= 60 个月**：Go
- **36–59 个月**：Revise，减少参数和状态，增强 prior
- **< 36 个月**：先不做完整 DSGE，改做简化 state-space / reduced-form

---

## 8. Step 3 — 变换与基本统计

对核心月度变量保存：

- level
- log level
- first difference
- log difference
- growth rate

检查：

- ADF
- KPSS（可选）
- 协整可能性
- rolling mean / variance
- break candidates

这些检验服务于 reduced-form 和 prior，不直接决定 DSGE 是否能使用 level state。

---

## 9. Step 4 — 最小机制预检

第一版只检查四条主关系：

### Demand

\[
BatteryDemand_t \rightarrow LCSpot_{t+k}
\]

### Supply

\[
LCOutput_t \rightarrow LCSpot_{t+k}
\]

### Cost

\[
Spodumene_t \rightarrow LCSpot_{t+k}
\]

### Profit-to-supply

构造：

\[
MarginProxy_t=P_t^{LC}-\theta P_t^{Spodumene}FX_t
\]

再检查：

\[
MarginProxy_t \rightarrow LCOutput_{t+k}
\]

扫描：

- 1–3 个月
- 4–6 个月
- 7–12 个月

如果能看到利润领先未来供给，则为后续 latent investment/capacity 结构提供现实依据。

---

## 10. Step 5 — Reduced-form baselines

### Baseline 0 — Random Walk

\[
\hat P_{t+1}=P_t
\]

### Baseline 1 — AR

价格自身惯性基线。

### Baseline 2 — Small VAR/BVAR

第一版最多 4–5 个变量：

\[
[Spot,Output,Demand,Cost]
\]

必要时增加 FX。

目的不是把 VAR 当最终模型，而是：

- 看符号；
- 看滞后；
- 看 IRF；
- 给 DSGE prior 和参数范围提供依据；
- 建立未来样本外预测基准。

---

## 11. Step 6 — 期货数据库只做独立准备

Phase 1 不要求马上把期货和月度基本面强行混成一个表。

先完成：

- 每个 LC 合约历史行情；
- 到期日；
- 成交量；
- 持仓量；
- settlement；
- spot 同步；
- risk-free rate；
- FX。

后续再进入：

- basis
- carry
- term structure
- convenience yield
- mixed-frequency observation matrix

---

## 12. 第一版不再做的数据工作

Phase 1 暂停：

- 拼完整 2018–2026 月度产能；
- 拼完整 2018–2026 开工率；
- 拼完整长期社会库存；
- 企业级 capex；
- 所有锂盐项目投产时间表；
- 同时收集 EV、Battery、LFP、NCM、ESS 全部需求变量；
- 大规模政策/情绪文本指标。

这些全部推迟到 baseline 模型证明值得继续之后。

---

## 13. Phase 1 最低代码结构

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
│   ├── lag_screening.py
│   └── break_tests.py
├── baselines/
│   ├── random_walk.py
│   ├── ar.py
│   ├── var.py
│   └── bvar.py
└── evaluation/
    └── metrics.py

scripts/
├── build_monthly_structural_dataset.py
├── build_daily_futures_dataset.py
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

## 14. Phase 1 最终交付物

1. `docs/data_availability_matrix.md`
2. `docs/data_dictionary.md`
3. `data/processed/monthly_structural.csv`
4. `data/processed/daily_futures.csv`
5. coverage report
6. core-variable plots
7. lag screening table
8. Random Walk / AR / VAR-BVAR baseline results
9. margin proxy test
10. `docs/phase1_decision_memo.md`

---

## 15. Go / Revise / Stop

### Go

- Spot、Output、OreCost、BatteryDemand 共同样本 >= 60 个月；
- 关键口径稳定；
- 至少 3 条核心机制符号基本可解释；
- baseline 可稳定运行；
- 期货数据库可独立建立。

### Revise

- 共同样本 36–59 个月；
- 部分序列有方法断点；
- 需要用 proxy 代替矿石成本或需求；
- 则减少待估参数，先做简化 state-space。

### Stop / Change Structure

只有在以下情况同时存在时才停止：

- 现货长历史不可得；
- 产量连续月度历史不可得；
- 锂辉石/成本没有可靠代理；
- 需求代理无法形成稳定序列。

目前 Phase 1 的任务就是用真实数据确认这一点，而不是提前假设失败。

---

## 16. Phase 1 之后的实验顺序

若 Go：

1. 现货 state-space MVP
2. latent margin / inventory
3. latent investment / capacity
4. 期货扩展
5. mixed-frequency Kalman
6. Bayesian MCMC
7. stochastic-cycle ablation
8. 必要时 nonlinear/regime extension

核心原则保持不变：**先证明最小结构有用，再增加复杂度。**
