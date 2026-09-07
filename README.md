# DSGE-LC

Lithium Carbonate (LC) price dynamics and pricing mechanism research project.

本仓库用于验证并逐步构建一个面向中国碳酸锂产业链的结构模型。当前优先级不是立即写论文，而是先通过可复现实验判断：产业链结构模型是否能够稳定估计、产生符合产业逻辑的动态响应、解释历史大行情，并在严格的样本外预测中优于简单基线。

## Current research direction

核心候选框架：

**需求 → 库存 → 现货价格 → 利润 → 开工/投资 → 滞后产能 → 产量 → 库存 → 价格**

并在后续阶段扩展：

**现货 + 库存/便利收益 + 预期 + 套保/投机 → 期货价格**

方法路线采用分阶段验证，而不是一开始直接搭建完整 MF-DSGE：

1. 数据可行性与机制预检
2. Reduced-form 基线与滞后关系识别
3. 最小结构模型（Production + Demand + Inventory + Spot）
4. 产能投资滞后与内生“锂周期”
5. 期货/基差/套保模块
6. Mixed-Frequency 状态空间与 Bayesian MCMC
7. Stochastic Cycle 消融实验
8. 必要时加入非线性/状态切换

## Documents

- [论文/研究整体计划](docs/research_master_plan.md)
- [实验第一阶段计划](docs/phase1_experiment_plan.md)

## Research principle

本项目采用 **experiment-first** 原则：

- 不以高 R² 作为单一成功标准；
- 参数必须可识别、MCMC 必须收敛；
- IRF 的符号和时间顺序必须符合产业机制；
- FEVD 不允许由单一“万能周期项”未经检验地吸收绝大部分波动；
- 必须做历史分解；
- 预测必须与 Random Walk、AR、VAR/BVAR 等基线进行严格样本外比较；
- 任何复杂模块都需要通过 ablation 证明其增量价值。

## Status

当前阶段：**Phase 1 — 数据可行性与机制预检**。
