# 2026 年 11 月中旬中期答辩执行计划

> 状态日期：2026-09-15  
> 硬截止：2026 年 11 月中旬  
> 当前原则：**主模型闭环优先；已经提前完成的阶段不重复返工，后续时间缓冲用于 Bayesian 收敛、结构结果和必要稳健性。**

## 1. 当前实际进度

原始计划按周推进，但截至 2026-09-15，实际进度已经明显领先：

| 原计划 | 原定任务 | 当前状态 |
|---|---|---|
| W1 9/9—9/15 | 核心数据 | **COMPLETE** |
| W2 9/16—9/22 | 数据整理/描述统计 | **COMPLETE AHEAD OF SCHEDULE** |
| W3 9/23—9/29 | 平稳性/相关性/滞后/断点 | **COMPLETE AHEAD OF SCHEDULE** |
| W4 9/30—10/6 | RW/AR/VAR/BVAR | **COMPLETE AHEAD OF SCHEDULE** |
| W5 10/7—10/13 | 结构模型框架 | **COMPLETE AHEAD OF SCHEDULE** |
| W6 10/14—10/20 | State-space / Kalman / 初步估计 | **MOSTLY COMPLETE AHEAD OF SCHEDULE** |
| W7 10/21—10/27 | IRF / FEVD | **NOT STARTED — GATED BY PHASE 2D** |
| W8 10/28—11/3 | 历史分解 / 预测 | **NOT STARTED** |
| W9 11/4—11/10 | 稳健性 / 期现扩展 | **NOT STARTED** |
| W10 | 中期整理 | **NOT STARTED** |

当前已经完成的不仅是 State-Space + Kalman，还包括 constrained MLE、multi-start、profile likelihood、Hessian/OPG 与 weak-ID preflight。因此，实际研究位置约相当于原计划 **10 月中旬**。

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

### Phase 2A—2C

- `M0_CORE5` 结构 MVP；
- `M1_CAPACITY6` 预设扩展；
- stability / observability / reachability / identification precheck；
- Kalman filter / RTS smoother / innovation likelihood；
- synthetic likelihood validation；
- 真实数据 constrained MLE multi-start；
- profile likelihood、boundary、Hessian、OPG、fixed-assumption sensitivity。

Selected next-stage specification：`M0_FULL14`。

## 3. 当前主要风险

提前不等于可以放松门槛。当前剩余风险主要是：

1. **MCMC mixing / convergence**：57 个月样本、14 参数仍可能导致弱方向混合慢；
2. **prior sensitivity**：`a_c` 与 inventory-price block 可能被 prior 明显影响；
3. **battery measurement noise sensitivity**：Phase 2C 已发现较高 `battery_sd` 会带来参数漂移；
4. **线性模型解释极端行情的幅度能力**：需由后续 IRF / historical decomposition 真实检验；
5. **结构预测不一定优于 RW/BVAR**：这不等于论文失败，但需要严格报告。

## 4. Revised execution plan

### Immediate — Phase 2D Bayesian estimation

优先完成：

- prior design；
- transformed-space posterior target 与 Jacobian 审计；
- 多链 MCMC；
- rank-normalized split R-hat；
- bulk / tail ESS；
- MCSE；
- posterior boundary / stability；
- prior-to-posterior contraction；
- prior sensitivity；
- targeted `rho_n` / battery measurement-noise sensitivity；
- posterior predictive sanity。

只有 Phase 2D convergence gate PASS 才进入结构结果。

### Next — Posterior IRF + FEVD

目标：

- Demand shock；
- Cost shock；
- Supply shock；
- Price shock；
- posterior uncertainty bands；
- sign / timing / persistence consistency；
- FEVD 1/3/6/12 月或与最终模型频率一致的预设 horizons。

此阶段不追求“所有冲击都漂亮”，重点是机制是否清晰且不被单一残差冲击吞噬。

### Then — Historical decomposition

重点解释：

- 2021—2022 上涨；
- 2023 快速下跌；
- 后续震荡阶段。

如果线性 MVP 对极端行情幅度解释不足，先诚实记录 limitation，再决定是否需要局部 robustness，而不是立即引入大型非线性模型。

### Then — Structural OOS

继续遵守 Phase 1B 的严格时间顺序原则，与：

- Random Walk；
- AR；
- VAR；
- BVAR

进行可比 OOS 评估。

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

不把以下内容设为默认硬任务：

- full nonlinear DSGE；
- Markov switching；
- stochastic cycle；
- M1 capacity 的完整 Bayesian 估计；
- mixed-frequency full model；
- tick 微观结构；
- 期权定价扩展；
- 大量新增宏观、情绪、政策变量。

这些只在核心 MVP 结果暴露明确解释缺口时启动。

## 7. Hard gates

- Data Freeze v1：**already locked**；
- Phase 2D posterior convergence：必须 PASS 才能解释结构结果；
- IRF / FEVD：目标仍为 2026-11-02 前完成；
- 主要实验：2026-11-10 前冻结；
- 11 月 10 日后原则上只做结果整理、复现、必要修正和答辩材料。

## 8. Final execution principle

当前项目已经从“能不能搭出模型”进入“posterior 是否可信、结构结果是否有经济解释力”的阶段。

因此接下来不再通过增加变量、增加方程或反复换模型来制造进度。优先顺序固定为：

```text
Phase 2D posterior convergence
→ IRF / FEVD
→ historical decomposition
→ structural OOS
→ robustness
→ futures extension
→ midterm report / PPT
```
