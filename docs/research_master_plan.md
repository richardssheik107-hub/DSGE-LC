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

当前主模型是 **semi-structural linear state-space MVP**，不是完整微观基础 DSGE。

Primary model：`M0_CORE5`

- states: `[d,c,q,n,p]`
- observations: `[spot,ore_cost,output,battery]`
- shocks: Demand / Cost / Supply / Price
- primary measurement: `OBS_MIXED4`
- sample: 2021-01—2025-09，N=57
- selected estimation specification: `M0_FULL14`

Phase 2D—2H 已完成：posterior convergence、IRF/FEVD、historical decomposition、strict Structural OOS 与关键 external validation 均通过各自 gate。外部验证显示 latent inventory-pressure 与 physical inventory 同向，但 magnitude 对 `rho_n` 敏感；cost state 与 direct route-cost changes 高度一致。当前立即目标是 preliminary spot-futures extension。

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

实际执行顺序冻结为：

```text
Phase 1A-1  Descriptive diagnostics
→ Phase 1A-2  Stationarity / lag / break / mechanism diagnostics
→ Phase 1B    RW / AR / VAR / BVAR OOS baselines
→ Phase 2A    Structural MVP design + identification precheck
→ Phase 2B    State-space + Kalman + likelihood validation
→ Phase 2C    Constrained MLE / profile / curvature / weak-ID preflight
→ Phase 2D    Bayesian posterior + convergence / posterior identification   [COMPLETE]
→ Phase 2E    Posterior IRF + FEVD                                             [COMPLETE]
→ Phase 2F    Historical Decomposition                                         [COMPLETE]
→ Phase 2G    Strict Structural OOS Forecast                                    [COMPLETE]
→ Phase 2H    Key robustness / external validation                            [COMPLETE]
→ Preliminary Spot-Futures Extension                                           [NEXT]
→ Capacity / Mixed-Frequency / Stochastic-Cycle extensions only if justified
```

这是当前 source-of-truth 路线。早期文档中把 Mixed-Frequency 放在 Bayesian MCMC 之前的编号属于长期设想，不再代表当前执行顺序。

## 4. 当前核心经济结构

### Demand

真实需求状态 `d_t` 是 latent state，动力电池装车是 noisy measurement anchor，而不是需求本身。Phase 2D fixed-assumption sensitivity 表明 `battery_sd` 会明显影响 `rho_d/sigma_d`，因此需求 block 的解释必须保留测量假设警告。

### Cost

`c_t` 由人民币计价的 SC6 成本代理锚定。前序诊断中 Cost → Price 是最稳定的短期机制候选；Phase 2D 中 `b_c` 属于 partially informative 且相对稳定的 price-loading mechanism。

### Supply

`q_t` 表示短期供给/产量状态。价格对短期产量的 reduced-form evidence 偏弱，但 Phase 2C/2D 对 `a_p` 提供内部 likelihood/posterior 集中，因此当前继续保留。

### Inventory pressure

`n_t` 是由滞后 `q-d` 累积的库存/供需松紧状态，不具有长期直接库存观测。`b_n` 靠近下界，并对固定 `rho_n` 明显敏感，属于 weakly identified structural channel。

### Price

`p_t` 由自身惯性、需求、成本、供给和 inventory pressure 共同决定。`rho_p`、`b_n`、`b_q` 继续作为 weak-direction 重点报告。

## 5. Slow-capacity extension

`M1_CAPACITY6` 作为预设 extension 保留：

`k_t = rho_k k_(t-1) + gamma_m m_(t-L)`

其中 margin proxy 只是 `z(log Spot) - z(log Ore CNY)`，不是实际企业利润。

Phase 1A-2 的 margin → future output growth 在约 9—11 个月形成 moderate candidate，因此慢产能机制具有研究价值；但 Phase 2A/2B 已显示 `gamma_m` 需要外生 margin-input variation 才能被识别，且 capacity 无独立 shock 时 smoother covariance 退化。因此 M1 不进入当前主 posterior structural-result 阶段。

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

## 7. Phase 2D — Bayesian posterior estimation [COMPLETE]

已完成：

- prior design 不使用同一数据的 MLE 作为窄先验中心；
- transformed-space target 正确包含 Jacobian；
- 4 条独立链；
- rank-normalized split R-hat；
- bulk / tail ESS；
- MCSE；
- posterior stability / boundary mass；
- prior-to-posterior contraction；
- flat / moderate-shrink prior sensitivity；
- targeted `rho_n` / battery noise sensitivity；
- posterior predictive sanity。

Baseline 通过全部预设 gate。必须继续保留的 warnings：

- `a_c` near-zero / boundary concentration；
- `b_n/b_q/rho_p` weak direction；
- battery-noise sensitivity in `rho_d/sigma_d`；
- fixed-`rho_n` sensitivity in `b_n`。

## 8. Posterior structural results [COMPLETE]

### IRF

核心 shocks：

- Demand +；
- Cost +；
- Supply +；
- Price residual shock。

优先检验符号、峰值时间与衰减顺序，并传播 posterior uncertainty；不得只报告 posterior median 曲线。

### FEVD

至少报告与月度模型一致的 1/3/6/12 月 horizons，检查是否存在单一冲击不合理吸收大多数价格波动。

### Structural consistency gate

进入 historical decomposition 前必须检查：

- IRF sign / timing 是否符合模型经济含义；
- posterior uncertainty 是否过宽到无法解释；
- weak parameters 是否导致关键 IRF/FEVD 对 prior / fixed assumptions 极度敏感；
- residual price shock 是否异常吞噬 FEVD。

## 9. Historical decomposition [COMPLETE]

核心解释窗口：

- 2021—2022 上涨；
- 2023 下跌；
- 后续震荡。

如果线性 MVP 对极端行情幅度解释不足，应先报告 limitation，再决定是否需要非线性扩展。

## 10. Structural OOS [COMPLETE]

结构模型已按严格 expanding-window、training-only scaling 与 release-safe approximation 完成 OOS。H1/H3/H6 U2 分别为 `0.914 / 1.240 / 1.131`。结构 M0 在 H1 优于 RW、H3/H6 优于 AR、三个期限均优于 unrestricted VAR，但 BVAR 仍更强。结论定位为 `mechanism + competitive forecasting`，不宣称普遍预测优势。

Phase 2H 已完成该 external validation。Baseline `n_t` 与 log monthly-mean inventory Pearson median 为 `0.650`，在 `rho_n=.50/.95` 下仍保持正向但强度变化明显；`c_t` 与 spodumene-route cost dlog Pearson 为 `0.988`。该结果强化 cost proxy 与 inventory-state interpretation，同时保留 inventory-persistence sensitivity warning。

## 11. Futures extension

在核心 spot model 冻结后，再进入：

`F_{t,T} = S_t exp[(r_t+s_t-y_t)(T-t)] + RP_t`

候选机制：inventory → convenience yield → basis；expectations / hedging / speculation → futures risk premium；spot-futures lead-lag / price discovery。期货/期权高频数据已存在，不重复大规模下载。

## 12. Mixed-frequency / cycle / nonlinear extensions

Mixed-frequency、stochastic cycle、Markov switching、threshold state、regime-dependent shocks 都是后续 extension，只在 core model 暴露明确缺口时启动。不得复制参考生猪论文的周期冲击占比或固定 MCMC 次数。

## 13. Unified success criteria

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

## 14. Midterm boundary

中期前优先完成：

1. posterior IRF / FEVD；
2. historical decomposition；
3. structural OOS；
4. one key robustness round；
5. preliminary spot-futures extension if time permits。

中期前默认不强求：M1 Bayesian estimation、mixed-frequency full model、stochastic cycle、large nonlinear extensions、tick microstructure、options pricing。

## 15. Final principle

**先做小模型完整闭环，再增加结构；先证明可识别和可解释，再追求复杂度。**
