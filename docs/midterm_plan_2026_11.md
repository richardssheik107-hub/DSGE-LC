# 2026 年 11 月中旬中期答辩执行计划

> 状态日期：2026-09-15  
> 硬截止：2026 年 11 月中旬  
> 当前原则：**主模型闭环优先；已经提前完成的阶段不重复返工，后续时间缓冲用于结构结果、历史解释、OOS 与必要稳健性。**

## 1. 当前实际进度

截至 2026-09-15，实际进度明显领先原始周计划：

| 原计划 | 原定任务 | 当前状态 |
|---|---|---|
| W1 9/9—9/15 | 核心数据 | **COMPLETE** |
| W2 9/16—9/22 | 数据整理/描述统计 | **COMPLETE AHEAD OF SCHEDULE** |
| W3 9/23—9/29 | 平稳性/相关性/滞后/断点 | **COMPLETE AHEAD OF SCHEDULE** |
| W4 9/30—10/6 | RW/AR/VAR/BVAR | **COMPLETE AHEAD OF SCHEDULE** |
| W5 10/7—10/13 | 结构模型框架 | **COMPLETE AHEAD OF SCHEDULE** |
| W6 10/14—10/20 | State-space / Kalman / 初步估计 | **COMPLETE AHEAD OF SCHEDULE** |
| W7 10/21—10/27 | Bayesian + IRF / FEVD | **COMPLETE** |
| W8 10/28—11/3 | 历史分解 / 预测 | **COMPLETE AHEAD OF SCHEDULE** |
| W9 11/4—11/10 | 稳健性 / 期现扩展 | **NOT STARTED** |
| W10 | 中期整理 | **NOT STARTED** |

Phase 2D 已完成，因此实际研究位置已经超过原计划 W6，并正式进入 posterior structural-results 阶段。

## 2. 已完成的研究闭环部分

### 数据与治理

- Data Freeze v1：2020-01—2025-09，69 个月，0 internal missing；
- core / robustness / validation / candidate 分层已经建立；
- public macro layer 基本补至 2026-06；
- v2 尾部核验不再阻塞主实验。

### Phase 1

- 描述统计与统一变换；
- ADF/KPSS、Zivot-Andrews、断点、季节性与 lead-lag；
- cost / demand / supply / margin proxy 机制筛选；
- RW / AR / VAR / BVAR expanding-window OOS。

### Phase 2A—2D

- `M0_CORE5` 结构 MVP；
- `M1_CAPACITY6` 预设扩展；
- stability / observability / reachability / identification precheck；
- Kalman filter / RTS smoother / innovation likelihood；
- synthetic likelihood validation；
- constrained MLE multi-start；
- profile likelihood、boundary、Hessian、OPG；
- proper prior + Jacobian-correct z-space MCMC；
- baseline 4-chain posterior convergence；
- flat / moderate-shrink prior sensitivity；
- targeted `battery_sd` / `rho_n` fixed-assumption sensitivity；
- posterior predictive sanity。

Selected structural specification remains `M0_FULL14`.

## 3. 当前主要风险

Phase 2D 已通过，不再把 MCMC mixing 当作当前 blocker。现在风险转为：

1. **Structural-result sensitivity**：`a_c` near-zero、`b_n/b_q/rho_p` weak direction 是否会让关键 IRF/FEVD 区间过宽；
2. **Measurement-assumption sensitivity**：`battery_sd` 对 `rho_d/sigma_d` 的影响必须进入结构结果稳健性；
3. **Inventory persistence sensitivity**：固定 `rho_n` 对 `b_n` 的影响需要在解释库存通道时保留警告；
4. **线性模型解释极端行情的幅度能力**：需由 IRF / historical decomposition 真实检验；
5. **结构预测不一定优于 RW/BVAR**：这不等于论文失败，但必须严格报告。

## 4. Revised execution plan

### Immediate — Posterior IRF + FEVD

目标：

- Demand shock；
- Cost shock；
- Supply shock；
- Price shock；
- posterior uncertainty bands；
- sign / timing / persistence consistency；
- FEVD 1/3/6/12 月；
- 检查 residual price shock 是否异常吞噬解释度；
- 针对 weak/fixed-assumption warnings 做最小必要敏感性。

只有该 structural consistency gate PASS，才进入 historical decomposition。

### Historical decomposition — COMPLETE

重点解释：

- 2021—2022 上涨；
- 2023 快速下跌；
- 后续震荡阶段。

如果线性 MVP 对极端行情幅度解释不足，先诚实记录 limitation，再决定是否需要局部 robustness，而不是立即引入大型非线性模型。

### Structural OOS — COMPLETE

已完成 strict expanding-window Structural OOS：training-only scaling、release-safe Output/Battery、每个 origin 重新 MAP 估计。结构 M0 的 H1/H3/H6 U2 为 `0.914 / 1.240 / 1.131`；预测表现具有竞争力但不支配 BVAR/RW。

### Next — Key robustness / external validation

优先使用现有 SMM social inventory 与 route cost/margin series 对 latent inventory-pressure 和 cost blocks 做独立外部验证；不改变 Data Freeze v1 与 frozen core model。

### Early November — Robustness / futures

只有核心 structural result 已冻结后再进行：

- output-break robustness；
- alternative price source robustness；
- measurement assumption robustness；
- preliminary spot-futures relation / price-discovery extension。

不重新下载已经完整的期货/期权高频数据。

## 5. Midterm minimum deliverable

中期版本至少应有：

1. 数据治理与 Data Freeze v1；
2. 描述统计和机制诊断；
3. RW / AR / VAR / BVAR 基线；
4. `M0_CORE5` 状态空间模型；
5. posterior parameter estimation 与 convergence diagnostics；
6. IRF；
7. FEVD；
8. historical decomposition；
9. structural OOS 或至少可复现的第一版；
10. 一轮关键稳健性；
11. 如时间允许，初步期现分析。

## 6. What is no longer required before midterm

不把以下内容设为默认硬任务：full nonlinear DSGE、Markov switching、stochastic cycle、M1 capacity 完整 Bayesian 估计、mixed-frequency full model、tick 微观结构、期权定价扩展、大量新增宏观/情绪/政策变量。

这些只在核心 MVP 结果暴露明确解释缺口时启动。

## 7. Hard gates

- Data Freeze v1：**already locked**；
- Phase 2D posterior convergence：**PASS**；
- posterior IRF / FEVD structural consistency：**PASS**；
- historical decomposition：**PASS**；
- strict Structural OOS：**PASS**；
- key robustness / external validation：**CURRENT GATE**；
- IRF / FEVD：目标仍为 2026-11-02 前完成；
- 主要实验：2026-11-10 前冻结；
- 11 月 10 日后原则上只做结果整理、复现、必要修正和答辩材料。

## 8. Final execution principle

当前项目已经从“posterior 是否可信”进一步进入“结构结果是否具有经济解释力”的阶段。

```text
Phase 2D posterior convergence        [COMPLETE]
→ posterior IRF / FEVD                [COMPLETE]
→ historical decomposition             [COMPLETE]
→ structural OOS                       [COMPLETE]
→ robustness / external validation      [CURRENT]
→ futures extension
→ midterm report / PPT
```
