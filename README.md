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

## Model path

长期目标仍然围绕：

**需求 → 价格 → 利润 → 投资/潜在产能 → 未来产量 → 价格反馈**

并保留库存状态：

**产量 - 需求 → 潜在库存 → 现货价格**

期货上市后扩展：

**现货 + 预期 + carry + 风险溢价 → 期货价格**

方法路线：

1. 核心数据可得性审计
2. Random Walk / AR / VAR-BVAR 基线
3. 现货 state-space MVP
4. latent margin / inventory
5. latent investment / capacity
6. 期货扩展
7. mixed-frequency Kalman
8. Bayesian MCMC
9. stochastic cycle ablation
10. 必要时 nonlinear / regime extension

## Documents

- [论文/研究整体计划](docs/research_master_plan.md)
- [稀疏观测数据策略](docs/data_strategy_sparse_observations.md)
- [实验第一阶段计划](docs/phase1_experiment_plan.md)

## Research principle

本项目采用 **experiment-first** 原则：

- 不以高 R² 作为单一成功标准；
- 参数必须可识别，MCMC 必须收敛；
- IRF 的符号和时间顺序必须符合产业机制；
- FEVD 不允许由单一“万能周期项”未经检验地吸收绝大部分波动；
- 必须做历史分解；
- 预测必须与 Random Walk、AR、VAR/BVAR 等基线进行严格样本外比较；
- 任何复杂模块都需要通过 ablation 证明其增量价值；
- 不让难以获得的长期产业数据成为项目单点依赖。

## Status

当前阶段：**Phase 1 — 核心数据可得性审计与机制预检**。

第一轮只确认：`lc_spot`、`lc_output`、`spodumene_price`、`battery_install`、`lc_futures_*`。
