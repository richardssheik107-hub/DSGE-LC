# DSGE-LC

Lithium Carbonate (LC) price dynamics and pricing mechanism research project.

本仓库用于验证并逐步构建一个面向中国碳酸锂产业链的结构模型。当前优先级不是立即写论文，而是先通过可复现实验判断：结构模型是否能够稳定估计、产生符合产业逻辑的动态响应、解释历史行情，并在严格的样本外预测中优于简单基线。

## Current research direction

当前采用 **稀疏观测（sparse observations）+ 潜在状态（latent states）+ mixed-frequency Kalman** 的数据策略。

不再要求把产能、开工率、社会库存、投资、企业利润等所有产业变量都找成长期真实观测；第一版只优先确认少量高质量核心数据：

- 电池级碳酸锂现货价格
- 碳酸锂月度产量
- 锂辉石价格/原料成本
- 动力电池装车量
- 碳酸锂期货各合约价格
- 另补 USD/CNY 与无风险利率等易获取宏观变量

产能、投资、库存、预期价格、风险溢价等可先作为 latent states，由结构方程与 Kalman Filter 推断；后续若获得真实产业数据，再用于验证或扩展。

## November 2026 midterm target

当前硬目标是 **2026 年 11 月中旬中期答辩**。

中期前不追求最终完整版模型，而是完成一个小而完整、可复现、已有核心结果的研究闭环：

```text
Data
→ Diagnostics
→ Random Walk / AR / VAR-BVAR
→ MVP Structural Model
→ State-Space
→ Kalman Filter
→ Parameter Estimation
→ IRF + FEVD
→ Historical Decomposition
→ Out-of-Sample Forecast
→ Preliminary Spot-Futures Extension
```

三个硬 Gate：

- **2026-09-21：数据冻结**，停止无限寻找完美历史数据
- **2026-10-19：State-Space + Kalman + likelihood 必须跑通**
- **2026-11-02：IRF + FEVD 必须完成**

11 月 3–9 日完成历史分解、预测和轻量期现扩展；11 月 10–15 日只做答辩版本冻结、复现和材料整理。

## Model path

长期目标仍然围绕：

**需求 → 价格 → 利润 → 投资/潜在产能 → 未来产量 → 价格反馈**

并保留库存状态：

**产量 - 需求 → 潜在库存 → 现货价格**

期货上市后扩展：

**现货 + 预期 + carry + 风险溢价 → 期货价格**

中期版本先冻结为：

**Demand + Cost + Supply + Spot**

真实观测优先：

- `lc_spot`
- `lc_output`
- `spodumene_price`
- `battery_install`
- `usd_cny`

期货上市后增加 `lc_futures_*`。

`capacity`、`investment`、`inventory_gap`、`margin`、`expected_price` 等先作为 latent states。

## Documents

- [论文/研究整体计划](docs/research_master_plan.md)
- [稀疏观测数据策略](docs/data_strategy_sparse_observations.md)
- [实验第一阶段计划](docs/phase1_experiment_plan.md)
- [2026 年 11 月中旬中期答辩执行计划](docs/midterm_plan_2026_11.md)

## Research principle

本项目采用 **experiment-first** 原则：

- 不以高 R² 作为单一成功标准；
- 参数必须可识别，MCMC 必须收敛；
- IRF 的符号和时间顺序必须符合产业机制；
- FEVD 不允许由单一“万能周期项”未经检验地吸收绝大部分波动；
- 必须做历史分解；
- 预测必须与 Random Walk、AR、VAR/BVAR 等基线进行严格样本外比较；
- 任何复杂模块都需要通过 ablation 证明其增量价值；
- 不让难以获得的长期产业数据成为项目单点依赖；
- 中期前主模型优先于期权、tick 微观结构、非线性等支线。

## Status

当前阶段：**Phase 1 — 核心数据可得性审计与机制预检**。

第一轮只确认：`lc_spot`、`lc_output`、`spodumene_price`、`battery_install`、`lc_futures_*`。

当前已有：

- LC futures/options 至 2026-06-30 的完整分钟级与 tick 级数据；
- USD/CNY 2020-01-02 至 2026-06-30 的 1,623 个日度观测；
- CPI 同比 2021-09 至 2026-06 的部分官方数据。

中期前优先人工补齐：`lc_spot`、`lc_output`、`spodumene_price`、`battery_install`。
