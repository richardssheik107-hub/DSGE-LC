# DSGE-LC 研究整体计划

> 项目原则：**experiment-first + staged complexity**。先验证最小结构模型是否可识别、可估、可解释，再按证据增加容量、期货、异频或周期模块。

## 1. 核心研究问题

本项目围绕一个总问题展开：

> 中国碳酸锂价格的大幅上涨、快速下跌和阶段性震荡，能否由需求、成本、供给、库存压力及滞后产能机制解释，并进一步统一现货与期货定价？

拆成六个研究问题：

1. 下游需求变化对碳酸锂现货价格的影响方向、强度与持续时间如何？
2. 锂辉石等上游成本如何传导至价格与供给？
3. 高利润是否会通过滞后投资/产能形成更慢的供给反馈？
4. 库存或供需松紧是否是连接生产、需求与价格的重要状态？
5. 期货是否通过预期、carry、便利收益与风险溢价更快反映信息？
6. 结构模型在历史解释和样本外预测中，相对 RW / AR / VAR / BVAR 能提供什么增量？

## 2. 当前模型定位与长期愿景必须区分

### 2.1 当前执行模型

当前主模型是：

**semi-structural linear state-space MVP**

不是完整微观基础 DSGE。

Primary model：`M0_CORE5`

- states: `[d,c,q,n,p]`
- observations: `[spot,ore_cost,output,battery]`
- shocks: Demand / Cost / Supply / Price
- primary measurement: `OBS_MIXED4`
- sample: 2021-01—2025-09，N=57
- selected estimation specification: `M0_FULL14`

当前目标是先确认：

- posterior 可收敛；
- cost / demand / supply / inventory-price 通道具有可解释 posterior；
- IRF / FEVD 合理；
- 主要历史阶段可以被结构冲击分解；
- structural OOS 至少具有可比较性。

### 2.2 长期模型愿景

长期候选模型可进一步加入：

- slow capacity / investment lag；
- observed / latent inventory validation；
- futures / basis / convenience yield；
- mixed-frequency observations；
- stochastic cycle ablation；
- nonlinear / regime-switching extensions。

这些不是当前已经实现的模块，也不是中期前默认必须实现的模块。

## 3. 当前已经执行的研究路径

实际执行顺序已经冻结为：

```text
Phase 1A-1  Descriptive diagnostics
→ Phase 1A-2  Stationarity / lag / break / mechanism diagnostics
→ Phase 1B    RW / AR / VAR / BVAR OOS baselines
→ Phase 2A    Structural MVP design + identification precheck
→ Phase 2B    State-space + Kalman + likelihood validation
→ Phase 2C    Constrained MLE / profile / curvature / weak-ID preflight
→ Phase 2D    Bayesian posterior + convergence / posterior identification
→ Posterior IRF + FEVD
→ Historical Decomposition
→ Structural OOS Forecast
→ Preliminary Spot-Futures Extension
→ Capacity / Mixed-Frequency / Stochastic-Cycle extensions only if justified
```

这是当前 source-of-truth 路线。早期文档中把 Mixed-Frequency 放在 Bayesian MCMC 之前的编号属于长期设想，不再代表当前执行顺序。

## 4. 当前核心经济结构

### Demand

真实需求状态 `d_t` 是 latent state，动力电池装车是 noisy measurement anchor，而不是需求本身。

Reduced-form evidence 对 Battery → Price 不强，因此模型不应写成 `Demand_t = BatteryInstall_t`。

### Cost

`c_t` 由人民币计价的 SC6 成本代理锚定。前序诊断中 Cost → Price 是最稳定的短期机制候选，因此 cost channel 保留为 core。

### Supply

`q_t` 表示短期供给/产量状态。价格对短期产量的 reduced-form evidence 偏弱，但 Phase 2C 的 `a_p` likelihood profile 有内部集中，因此当前仍保留该参数。

### Inventory pressure

`n_t` 是由滞后 `q-d` 累积的库存/供需松紧状态，不具有长期直接库存观测。它在当前模型中属于可解释但弱识别的结构状态，后验必须做 prior sensitivity。

### Price

`p_t` 由自身惯性、需求、成本、供给和 inventory pressure 共同决定。当前最需要警惕的弱方向是 `b_n / b_q / rho_p`。

## 5. Slow-capacity extension

`M1_CAPACITY6` 作为预设 extension 保留：

`k_t = rho_k k_(t-1) + gamma_m m_(t-L)`

其中 margin proxy 只是 `z(log Spot) - z(log Ore CNY)`，不是实际企业利润。

Phase 1A-2 的 margin → future output growth 在约 9—11 个月形成 moderate candidate，因此慢产能机制具有研究价值；但 Phase 2A/2B 已显示 `gamma_m` 需要外生 margin-input variation 才能被识别，且 capacity 无独立 shock 时 smoother covariance 退化。因此 M1 不进入当前 Phase 2D 主估计。

## 6. 数据策略

### Core / A_CORE

- SMM battery-grade LC spot；
- SMM total LC output；
- SMM SC6 CIF China；
- battery installation；
- USD/CNY。

Data Freeze v1：2020-01—2025-09，69 个月，作为当前 canonical main sample。

### Robustness

- Mysteel alternative LC / SC6 prices；
- route-specific LC output；
- filtered concentrate imports；
- LFP/NCM installation；
- trade auxiliary series。

### Validation only

- SMM social inventory components；
- route production cost / margin short samples。

### Candidate

- Data Freeze v2 tail values；
- Dongwu SMM secondary transcription；
- other unverified exact-month fills。

原则：不同 provider 不拼接成一条 canonical price series；不插值、不 ffill、不根据图表反推 strict canonical 值。

## 7. Phase 2D — Bayesian posterior estimation

当前立即执行的研究阶段。

目标：

- prior design 不用同一数据的 MLE 做窄先验中心；
- transformed-space MCMC target 正确包含 Jacobian；
- 至少 4 条独立链；
- rank-normalized split R-hat；
- bulk / tail ESS；
- MCSE；
- posterior stability / boundary mass；
- prior-to-posterior contraction；
- prior sensitivity；
- targeted `rho_n` / battery noise sensitivity；
- posterior predictive sanity。

只有该阶段 PASS，才有资格解释 IRF / FEVD。

## 8. Posterior structural results

### IRF

核心 shocks：

- Demand +；
- Cost +；
- Supply +；
- Price residual shock。

优先检验符号、峰值时间与衰减顺序，而不是追求曲线平滑。

### FEVD

至少报告与月度模型一致的 1/3/6/12 月 horizons，检查是否存在单一冲击不合理吸收大多数价格波动。

### Historical decomposition

核心解释窗口：

- 2021—2022 上涨；
- 2023 下跌；
- 后续震荡。

如果线性 MVP 对极端行情幅度解释不足，应先报告 limitation，再决定是否需要非线性扩展。

## 9. Structural OOS

结构模型预测必须与已有基线保持严格可比：

- Random Walk；
- AR；
- VAR；
- BVAR。

主张应限制为：结构模型是否增加机制解释和预测增量，而不是要求它在所有 horizon 都击败 RW/BVAR。

## 10. Futures extension

在核心 spot model 冻结后，再进入：

`F_{t,T} = S_t exp[(r_t+s_t-y_t)(T-t)] + RP_t`

候选机制：

- inventory → convenience yield → basis；
- expectations / hedging / speculation → futures risk premium；
- spot-futures lead-lag / price discovery。

期货/期权高频数据已存在，不重复大规模下载。

## 11. Mixed-frequency extension

Mixed-frequency 是后续扩展，而不是当前 Bayesian 估计的前置条件。

未来可把：

- 日度价格；
- 周度库存；
- 月度产业变量

映射到 dynamic observation matrix 中，继续复用已经验证的 Kalman core。

## 12. Stochastic-cycle ablation

只有当 base structural model 在 residual / turning point / historical decomposition 上暴露明确缺口时，才比较：

- Base model；
- Base + stochastic cycle。

必须评估：

- posterior / likelihood 改善；
- FEVD 是否被周期项过度支配；
- forecast 是否真正改善；
- turning-point / residual 是否改善。

不得复制参考生猪论文的周期冲击占比或固定 MCMC 次数。

## 13. Nonlinear extensions

Markov switching、threshold state、regime-dependent shocks 等只在下列证据出现时考虑：

- 极端期 residual 明显系统性偏离；
- historical decomposition 方向正确但幅度长期失真；
- posterior predictive check 显示线性模型持续失败；
- OOS turning points 明显无法捕捉。

## 14. Unified success criteria

### Numerical

- stable transition dynamics；
- Kalman covariance audit clean；
- no hidden pseudo-inverse / uncontrolled jitter；
- optimizer / sampler results reproducible。

### Identification

- multi-start / multi-chain agreement；
- R-hat / ESS / MCSE pass；
- prior sensitivity explicitly reported；
- weak parameters not hidden behind priors。

### Economics

- IRF signs and timing plausible；
- FEVD not dominated by an artificial residual factor without evidence；
- historical decomposition connects model shocks to major episodes without overclaiming causality。

### Forecasting

- strict OOS；
- compare with RW / AR / VAR / BVAR；
- horizon- and window-dependence must be reported。

## 15. Midterm boundary

中期前优先完成：

1. Phase 2D posterior estimation；
2. IRF / FEVD；
3. historical decomposition；
4. structural OOS；
5. one key robustness round；
6. preliminary spot-futures extension if time permits。

中期前默认不强求：M1 Bayesian estimation、mixed-frequency full model、stochastic cycle、large nonlinear extensions、tick microstructure、options pricing。

## 16. Final principle

**先做小模型完整闭环，再增加结构；先证明可识别和可解释，再追求复杂度。**
