# 生猪 MF-DSGE 参考下的碳酸锂研究执行总计划

> 版本日期：2026-09-15  
> 项目：`DSGE-LC`  
> 研究题目：《碳酸锂价格波动的影响因素与定价机制研究》  
> 核心方法参考：张慧明、令雪婷、黄兵海《我国生猪价格波动研究——基于 DSGE 模型的分析》

---

## 1. 计划定位

本计划用于把当前项目从“数据准备完成”推进到“可复现的结构实证闭环”。核心参考不是照搬生猪模型的具体方程或参数，而是借鉴其四个最有价值的方法论原则：

1. **产业机制优先**：先把价格形成、供给调整、成本、需求、期货联动写成结构关系，再决定哪些状态需要观测、哪些可以潜在。
2. **稀疏观测 + 潜在状态**：不要求每个内生变量都有长期观测序列，少量高质量观测负责锚定模型，产能、库存、利润、预期等可以先作为 latent states。
3. **混合频率状态空间**：不同频率的数据不通过机械插值强行对齐，而是通过时变观测矩阵和不规则 Kalman 更新进入同一状态空间。
4. **结构结果必须经过 IRF、FEVD、预测和稳健性检验**：结构模型不能只靠样本内拟合或高 R² 成立。

本项目在此基础上进一步增加两条约束：

- **先月度 MVP，后 mixed-frequency**。当前 69 个月月度核心样本已经足够先验证需求—成本—供给—价格结构，不先把日度期货、周度库存和月度基本面一次性混在一起。
- **随机周期不是先验必选项**。生猪论文用 Harvey 随机周期刻画猪周期，但本项目首先检验锂行业自身的“利润—投资—滞后产能—产量—库存—价格”能否内生地产生周期；只有基础结构解释力不足时，再把 stochastic cycle 作为 ablation 扩展。

---

## 2. 生猪论文的方法论骨架与本项目映射

| 生猪论文设计 | 方法含义 | 碳酸锂项目对应设计 | 是否直接采用 |
|---|---|---|---|
| 养殖户 + 家庭消费者 + 政府 + 期货市场四部门 | 把产业供给、需求、政策和衍生品统一进结构框架 | 需求端 + 锂盐生产端 + 库存/现货市场 + 期货市场；宏观变量作为外生环境 | **部分采用**，不机械照搬家庭部门 |
| 猪粮比价、能繁母猪、饲料成本 | 利润与慢变量决定未来供给 | LC价格、SC6成本、利润、投资、潜在产能 | **核心借鉴** |
| 能繁母猪滞后调整 | 价格信号通过生物周期滞后影响未来产量 | 高利润通过投资/扩产滞后影响未来 LC 产量 | **核心借鉴** |
| 日度价格 + 月度基本面 | 数据异频 | 日度现货/期货 + 周度库存 + 月度产量/需求 | **后续采用** |
| 时变观测矩阵 | 只有当期真实到达的数据进入更新 | 月度变量仅在发布时点更新，日度价格按交易日更新 | **核心借鉴** |
| 不规则混频 Kalman | 避免插值和强制同频 | mixed-frequency state-space | **核心借鉴** |
| 贝叶斯 MCMC | 结合先验与样本识别结构参数 | 稳定的 state-space + likelihood 后再做 Bayesian estimation | **采用，但不复制固定迭代数** |
| Harvey 随机周期 | 用准周期状态补充 AR(1) 冲击 | 作为 lithium cycle 的后续增量模块 | **不进入 baseline** |
| 无套利期货定价 + 预期 + 套保/投机压力 | 期现联动 | carry + convenience yield + risk premium + expectations | **期货扩展采用** |
| IRF + FEVD | 解释冲击路径与相对贡献 | demand/cost/supply/inventory shock decomposition | **必须** |
| 一步向前滚动预测 | 检验模型真实预测能力 | expanding / rolling OOS vs RW/AR/VAR/BVAR | **必须，而且标准更严格** |

### 2.1 明确不照搬的内容

以下内容不能因为生猪论文使用过，就直接复制到碳酸锂：

- 代表性家庭 CRRA、劳动供给、完整 Taylor rule 不作为中期 MVP 必选模块；
- 生猪论文的参数先验不能直接作为锂行业先验；
- 生猪论文的两条 MCMC 链、每链 5000 次、burn-in 1000 次只是实现参考，不是本项目的固定标准；
- 生猪论文中随机周期冲击解释现货 67.82%、期货 89.50% 不能成为本项目追求的目标；如果某个“万能周期项”吸收绝大多数波动，必须做 ablation 和识别检查；
- 生猪论文报告的期货方向预测准确率 95.33% 不能作为本项目的目标值；本项目必须严格和 Random Walk、AR、VAR/BVAR 比较，防止信息泄漏或过拟合。

---

## 3. 当前数据基线

### 3.1 Data Freeze v1

当前正式结构样本：

```text
2020-01 ~ 2025-09
69 months
internal missing = 0
DATA_GATE = GO
```

核心观测：

- `lc_spot`：SMM 国产电池级碳酸锂 99.5%，CNY/t，月均
- `lc_output`：中国碳酸锂总产量，metric tons，月度
- `spodumene_price`：SC6 Li2O，CIF China，USD/t，月均
- `battery_install`：中国动力电池当月总装车量，GWh
- `usd_cny_mean`：USD/CNY 月均

辅助成本代理：

```text
spodumene_cny_t = spodumene_price × usd_cny_mean
```

该变量只是人民币计价锂辉石价格代理，不是碳酸锂生产成本。

### 3.2 非核心但已经可用的数据层

**Robustness**：

- Mysteel 电池级碳酸锂月均价
- Mysteel SC6 CIF China 月均价
- LC 进出口
- SMM filtered 锂精矿进口
- 分路线 LC 产量
- LFP / NCM 装车
- NEV 产销

**Validation only**：

- SMM LC 库存组件
- Mysteel 澳洲 SC6 路线 LC 成本
- Mysteel 澳洲 SC6 路线即期利润

### 3.3 不再作为阻塞项

以下变量第一版不要求形成 2020—2026 完整观测：

- capacity
- utilization
- investment / capex
- long-history inventory
- enterprise profit
- expected price
- risk premium

这些优先作为 latent states 或 validation variables。

---

## 4. 碳酸锂结构模型的经济骨架

中期版本不直接搭建“大型完整 DSGE”，而先建立一个具有结构解释力、可识别、可进入状态空间的 **MVP structural model**。

核心机制：

```text
Demand ↑
→ Inventory pressure ↑
→ LC Spot ↑
→ Margin ↑
→ Investment / Capacity ↑ with lag
→ Output ↑
→ Inventory rebuild ↑
→ LC Spot ↓
```

同时：

```text
SC6 Cost ↑
→ Production cost ↑
→ Margin ↓
→ Output / investment pressure ↑
→ LC Spot receives cost support
```

期货上市后：

```text
Spot + Expected Spot + Carry + Convenience Yield + Risk Premium
→ Futures
```

---

## 5. MVP 状态与观测设计

### 5.1 第一版观测向量

月度 MVP：

\[
y_t=[P_t^{LC},Q_t^{LC},D_t^{Battery},C_t^{Ore}]'
\]

其中：

- \(P_t^{LC}\)：`lc_spot`
- \(Q_t^{LC}\)：`lc_output`
- \(D_t^{Battery}\)：`battery_install`
- \(C_t^{Ore}\)：优先使用 `spodumene_cny_t`，同时保留 USD 口径做 robustness
- `usd_cny_mean` 作为外生或辅助观测

第一版不强制把 CPI、PPI、利率、贸易同时塞入状态向量。

### 5.2 第一版 latent states

优先控制在 3–5 个：

- `demand_state`
- `cost_state`
- `capacity_state`
- `inventory_gap`
- `margin_state`（可先设为确定性派生变量，而非独立状态）

后续再考虑：

- `investment`
- `expected_price`
- `risk_premium`
- `productivity`
- `stochastic_cycle`

### 5.3 参数数量纪律

69 个月样本不支持一次估计大量自由参数。中期 MVP 目标：

- 核心动态参数尽量不超过 10–15 个；
- 可以校准的行业参数先校准，不把所有系数都交给 MCMC；
- 每增加一个 latent state 或 shock，都必须说明增加了什么可检验机制。

---

## 6. 第一版结构方程候选

以下方程是执行起点，不是最终论文形式。每一条都要经过 Phase 1 诊断结果修正。

### 6.1 需求状态

\[
D_t=\rho_D D_{t-1}+\varepsilon_t^D
\]

观测锚：

\[
BatteryInstall_t=\mu_D+\lambda_D D_t+\eta_t^D
\]

后续 robustness 可替换为 NEV sales / production、LFP/NCM。

### 6.2 成本状态

\[
C_t=\rho_C C_{t-1}+\beta_{FX}FX_t+\varepsilon_t^C
\]

主观测：SC6 CIF China；主成本代理用人民币矿价。

### 6.3 利润状态/利润代理

初期可以不用独立状态，先定义：

\[
Margin_t=P_t^{LC}-\theta C_t
\]

或者在变量标准化阶段先用相对利润环境：

\[
MarginProxy_t=z(P_t^{LC})-z(C_t)
\]

`theta` 不允许凭感觉固定，必须来自行业口径、短样本成本利润验证或后续参数估计。

### 6.4 潜在产能

\[
K_{t+1}=\rho_K K_t+\gamma_M Margin_{t-L}+\varepsilon_t^K
\]

其中 \(L\) 不提前锁定，先由 price/margin → future output 的 lag screening 给出候选范围。

### 6.5 产量

\[
Q_t=\alpha_K K_t-\alpha_C C_t+\varepsilon_t^Q
\]

根据 diagnostics 结果可以加入惯性：

\[
Q_t=\rho_Q Q_{t-1}+\alpha_K K_t-\alpha_C C_t+\varepsilon_t^Q
\]

### 6.6 库存缺口

\[
INV_t=\rho_I INV_{t-1}+Q_t-D_t+\varepsilon_t^I
\]

库存短样本不作为长样本必需观测，而用于后续 validation。

### 6.7 现货价格

第一版候选：

\[
P_t=\rho_P P_{t-1}+\beta_D D_t-\beta_Q Q_t-\beta_I INV_t+\beta_C C_t+\varepsilon_t^P
\]

预期符号：

- \(\beta_D>0\)
- \(\beta_Q>0\) 前面的符号为负，因此供给增加压低价格
- \(\beta_I>0\) 前面的符号为负，因此库存上升压低价格
- \(\beta_C>0\)

如果该最小结构都无法识别，不允许通过增加更多变量来“救模型”。

---

## 7. 实验总路线

```text
Phase 1A-1  描述统计与数据理解
    ↓
Phase 1A-2  平稳性 / 滞后 / 结构变化 / margin proxy
    ↓
Phase 1B    RW / AR / VAR-BVAR baselines
    ↓
Phase 2     MVP structural equations
    ↓
Phase 3     State-space + Kalman + likelihood
    ↓
Phase 4     Parameter estimation / Bayesian MCMC
    ↓
Phase 5     IRF + FEVD
    ↓
Phase 6     Historical decomposition
    ↓
Phase 7     Strict OOS forecast
    ↓
Phase 8     Spot-futures extension
    ↓
Phase 9     Mixed-frequency upgrade
    ↓
Phase 10    Stochastic-cycle ablation / nonlinear extension if needed
```

原则：**任何后续阶段都必须以前一阶段 Gate 通过为前提。**

---

## 8. Phase 1A-1：描述统计与数据理解

时间：2026-09-16 ～ 2026-09-22

### 任务

- 固定 Data Freeze v1：69 个月；
- 生成 level / log / dlog / MoM / YoY；
- 画核心变量走势图；
- 识别春节、疫情、极端 MoM，但不自动删除；
- 计算 contemporaneous correlation；
- 12 个月 rolling mean / volatility；
- 形成 `phase1_data_diagnostics_memo.md`。

### Gate A1

必须回答：

1. 核心变量是否存在明显单位或口径问题？
2. 价格/矿价波动是否远大于数量变量？
3. battery/output 是否有明显季节性？
4. 是否存在需要下一阶段专门处理的异常区间？

### 输出

- `monthly_structural_v1.csv`（本地、ignored）
- descriptive tables
- core figures
- data QA report
- diagnostics memo

---

## 9. Phase 1A-2：平稳性、滞后与结构变化

时间：2026-09-23 ～ 2026-09-29

### 9.1 平稳性

对核心变量至少比较：

- level
- log level
- first log difference
- YoY log change

检验：

- ADF
- KPSS

目的不是决定 DSGE “必须差分”，而是服务于 reduced-form、baseline 和参数先验。

### 9.2 领先—滞后扫描

扫描 \(k=-12,\ldots,+12\)：

- Battery → Spot
- Output → Spot
- Ore Cost → Spot
- Spot → Future Output
- Margin Proxy → Future Output

尤其关注：

\[
Price_t / Margin_t \rightarrow Output_{t+L}
\]

如果存在稳定正向领先关系，就是 lithium investment/capacity lag 的现实证据。

### 9.3 结构变化

第一轮使用：

- rolling mean / variance
- break candidate screening
- 事件对照

至少检查：

- 2021–2022 涨价阶段
- 2023 快速下跌
- 2023-07-21 LC futures 上市
- 2025/2026 新一轮价格变化
- 2026-01 SMM SC6 methodology change（在 v2 样本中）

### Gate A2

形成一张 `mechanism_evidence_table`：

| Mechanism | Best lag | Sign | Stability | Structural implication |
|---|---:|---:|---|---|
| Demand → Price | ? | ? | ? | demand equation |
| Cost → Price | ? | + | ? | cost pass-through |
| Output → Price | ? | - | ? | supply pressure |
| Price/Margin → Future Output | ? | + | ? | capacity lag |

不允许先写固定滞后再强迫数据匹配。

---

## 10. Phase 1B：Reduced-form baselines

时间：2026-09-30 ～ 2026-10-06

### Baseline 0 — Random Walk

\[
\hat P_{t+1}=P_t
\]

### Baseline 1 — AR

使用价格自身惯性，滞后阶数由信息准则和样本规模共同控制。

### Baseline 2 — Small VAR

第一版最多：

```text
Spot
Output
Battery Demand
Ore Cost
```

必要时增加 FX，但避免 69 个月样本下维度爆炸。

### Baseline 3 — BVAR

用于小样本下的收缩估计，作为结构模型的重要预测基准。

### OOS 协议

必须使用 expanding window 或预先固定的 rolling window；禁止：

- 先用全样本选参数，再声称 OOS；
- 使用未来发布日期的数据；
- 在测试集上调超参数。

### 指标

- RMSE
- MAE
- Theil U
- Direction Accuracy
- Up Accuracy
- Down Accuracy

可以补充 Diebold-Mariano，但小样本下只作辅助。

### Gate B

baseline 必须可稳定复现，作为结构模型的最低比较对象。

---

## 11. Phase 2：MVP Structural Model

时间：2026-10-07 ～ 2026-10-13

### 目标

冻结中期结构，不追求完整大型 DSGE。

建议中期模块：

```text
Demand
Cost
Latent Capacity / Supply
Inventory Gap
Spot Price
```

### 工作顺序

1. 写清每个状态的经济含义；
2. 明确每个结构参数的符号和可行范围；
3. 明确观测方程；
4. 明确 shocks；
5. 先检查 deterministic steady state / local stability；
6. 再进入滤波。

### 第一版 shocks

最多 4 个：

- demand shock
- ore-cost shock
- supply/capacity shock
- inventory / price-markup shock

不能一开始给每个变量一个独立冲击。

### Gate C

- 稳态/均衡路径存在；
- 小扰动不爆炸；
- 参数符号可解释；
- shock 数量少于或接近主要观测维度；
- 不依赖 stochastic cycle 才能运行。

---

## 12. Phase 3：State-Space + Kalman + Likelihood

时间：2026-10-14 ～ 2026-10-20

### 12.1 月度 state-space 先跑通

\[
x_{t+1}=A(\theta)x_t+B(\theta)\varepsilon_t
\]

\[
y_t=H(\theta)x_t+v_t
\]

先在月度 69 个月样本上实现：

- prediction
- update
- filtered state
- smoothed state
- log likelihood

### 12.2 数值检查

必须测试：

- covariance 正定/半正定；
- likelihood 对参数变化连续；
- 极端参数不会产生 silent NaN；
- 初始化对结果影响可控；
- synthetic-data recovery test。

### 12.3 对生猪论文的直接借鉴

生猪论文最值得复制的不是具体参数，而是“观测子集随时点变化”的思想。月度 MVP 跑稳后，下一阶段把 `H_t` 改成动态观测矩阵：

- 当天有现货/期货 → 价格行参与更新；
- 月度产量/装车数据到达 → 相应行参与更新；
- 没有新观测 → 只 prediction，不 update。

### Gate D — 2026-10-19 左右

**State-Space + Kalman + likelihood 必须可以端到端运行。**

若失败，优先减少状态和参数，不引入更多复杂模块。

---

## 13. Phase 4：参数估计与 Bayesian MCMC

### 13.1 估计顺序

不要一开始就 MCMC。

顺序：

1. calibrated parameters
2. simple likelihood / optimization
3. MAP / posterior mode
4. local identification / sensitivity
5. Bayesian MCMC

### 13.2 先验来源

优先级：

1. 本项目 Phase 1 lag / reduced-form 结果；
2. 锂产业工程和成本逻辑；
3. 相近商品/产业文献；
4. 宽松、弱信息先验。

不能直接复制生猪论文先验均值。

### 13.3 MCMC 收敛要求

生猪论文使用两条 5000 次链作为实现参考。本项目 production estimation 以诊断标准而不是固定迭代数为准：

- 多链；
- R-hat 优先 < 1.05；
- 关键参数 ESS 充足；
- random-walk MH 接受率大致 20%–40% 时通常较合理，但不机械追求；
- posterior 不应完全复制 prior；
- 关键参数不能长期贴边界；
- 不同初始化结果应一致。

### Gate E

如果核心参数不可识别：

1. 减少自由参数；
2. 固定弱识别弹性；
3. 合并 latent states；
4. 缩减 shocks；
5. 最后才考虑增加数据。

---

## 14. Phase 5：IRF

时间：2026-10-21 ～ 2026-10-27

预期核心响应：

| Shock | LC Price | Output | Inventory | Margin | Capacity |
|---|---:|---:|---:|---:|---:|
| Demand + | ↑ | lagged ↑ | ↓ | ↑ | lagged ↑ |
| Ore Cost + | ↑ | ↓ / delayed ↓ | ↓ or mixed | ↓ | ↓ |
| Supply/Capacity + | ↓ | ↑ | ↑ | ↓ | ↑ |
| Inventory + | ↓ | weak | ↑ | ↓ | weak |
| RMB depreciation | ↑ through imported cost | possible ↓ | mixed | ↓ | ↓ |

验收看两件事：

- **符号**是否符合产业逻辑；
- **时间顺序**是否符合产能和库存机制。

如果 IRF 只能靠参数约束才能“看起来正确”，说明识别不足。

---

## 15. Phase 5：FEVD

至少报告：

- 1 month
- 3 months
- 6 months
- 12 months

核心对象：

- LC spot
- LC output
- latent inventory
- latent capacity / margin（若可识别）

### FEVD 红线

如果一个新增 stochastic-cycle shock 在没有强数据证据的情况下解释了绝大多数价格方差，必须：

1. 与无 cycle 模型比较；
2. 检查 likelihood / OOS forecast 是否改善；
3. 检查其他结构 shock 是否被挤出；
4. 检查 posterior 是否由 prior 主导。

生猪论文的高 cycle share 只能作为研究现象参考，不能成为我们的目标。

---

## 16. Phase 6：Historical Decomposition

时间：2026-10-28 ～ 2026-11-03

这是本项目区别于简单预测论文的重要输出。

必须解释至少三个阶段：

### Episode 1 — 2021–2022 上涨

检查：

- demand contribution
- cost contribution
- inventory tightening
- capacity/supply lag

### Episode 2 — 2023 快速下跌

检查：

- capacity release
- output expansion
- demand expectation correction
- inventory rebuild

### Episode 3 — 2024–2025 调整/震荡

检查：

- cost floor
- supply persistence
- demand growth normalization
- inventory state

历史分解必须能够把模型结构和真实市场叙事连接起来。

---

## 17. Phase 7：Strict Out-of-Sample Forecast

结构模型预测不能只报告样本内 fitted path。

### 17.1 预测设计

- expanding window 为主；
- horizon：1M、3M、6M；
- 所有参数只能使用预测时点之前的信息；
- 发布滞后的月度数据必须按真实信息可得性处理。

### 17.2 Baselines

必须比较：

- Random Walk
- AR
- VAR
- BVAR

### 17.3 Metrics

- RMSE
- MAE
- Theil U
- Direction Accuracy
- turning-point hit / miss summary

高 R² 不能代替 OOS。

### 17.4 关键解释

如果结构模型：

- 水平误差小但方向预测弱 → 可能需要 regime/nonlinear；
- 方向好但水平差 → 可能结构 shock 尺度或 measurement equation 有问题；
- 既不优于 RW 也不优于 BVAR → 不继续堆复杂模块。

---

## 18. Phase 8：期现货扩展

时间：2026-11-04 ～ 2026-11-10，以“轻量可展示”为中期目标。

LC futures 自 2023-07-21 上市，已有完整合约高频数据。

第一版不要直接上 tick 微观结构，而先构建日度：

```text
date
contract
close
settlement
volume
open_interest
time_to_maturity
spot
risk_free_rate
usd_cny
```

### 18.1 期货定价候选

\[
F_{t,T}=S_t\exp[(r_t+s_t-y_t)\tau]+RP_t
\]

其中：

- \(r_t\)：无风险利率
- \(s_t\)：仓储/持有成本
- \(y_t\)：convenience yield
- \(RP_t\)：risk premium

### 18.2 生猪论文可借鉴部分

借鉴：

- expected spot
- no-arbitrage anchor
- hedging pressure / speculative demand
- spot/futures 联动

但不要求中期前一次性估计所有期货行为参数。

中期最低交付：

- basis
- lead-lag
- cointegration / error-correction preliminary evidence
- carry consistency
- 一个可运行的 futures observation equation

---

## 19. Phase 9：Mixed-Frequency Upgrade

这是对生猪论文技术路线最直接的复现与扩展，但放在月度 MVP 成功之后。

### 19.1 高频时间轴

以日为状态推进单位：

- 日度 spot / futures：当日更新
- 周度 inventory：仅公布日更新
- 月度 output / battery：仅信息到达日更新

### 19.2 时变观测矩阵

\[
y_t=H_t x_t+v_t
\]

`H_t` 根据当日真实可用变量动态构造。

当无任何新观测时：

```text
predict only
no measurement update
```

禁止把月度产量复制到每一天，禁止线性插值成日频。

### 19.3 Mixed-frequency Gate

只有当以下条件同时满足才进入正式估计：

- monthly model 已识别；
- daily futures dataset 可复现；
- release timing 可追踪；
- dynamic H_t 有单元测试；
- irregular Kalman 与 synthetic test 通过。

---

## 20. Phase 10：Harvey Stochastic Cycle Ablation

只有基础模型已经稳定之后再做。

候选周期状态：

\[
\begin{bmatrix}c_t\\c_t^*\end{bmatrix}
=\rho_c
\begin{bmatrix}
\cos\lambda_c & \sin\lambda_c\\
-\sin\lambda_c & \cos\lambda_c
\end{bmatrix}
\begin{bmatrix}c_{t-1}\\c_{t-1}^*\end{bmatrix}
+\varepsilon_t^c
\]

### 对比组

- M0: Base structural model
- M1: Base + investment/capacity lag
- M2: Base + Harvey stochastic cycle
- M3: Base + investment/capacity lag + cycle

### 判断是否保留 cycle

必须同时看：

- likelihood / marginal likelihood
- posterior identification
- FEVD concentration
- residual structure
- OOS forecast
- historical decomposition

如果 cycle 只提高样本内拟合、却让 FEVD 被单一成分统治且 OOS 不改善，则删除。

---

## 21. Robustness / Validation 设计

### 21.1 价格源替代

主序列：SMM。

robustness：

- `lc_spot_mysteel`
- `spodumene_mysteel`

禁止把不同 provider 直接拼成同一 canonical series。

### 21.2 需求替代

- battery installation → NEV sales / production
- total battery → LFP / NCM

### 21.3 供给替代

- total output → route-specific output
- 加入 LC import / net import
- 加入 SMM filtered concentrate imports

### 21.4 latent state validation

**Inventory**：

\[
\widehat{Inventory}_t \quad vs \quad SMM\ observed\ inventory_t
\]

只允许同一 inventory methodology regime 内比较。

**Margin**：

\[
\widehat{Margin}_t \quad vs \quad Mysteel/SMM\ observed\ cost\ and\ margin
\]

不要求点对点完美拟合，重点检查方向和阶段一致性。

### 21.5 Sample robustness

- Data Freeze v1：2020-01—2025-09
- Data Freeze v2：目标 2020-01—2026-06

v2 完成后统一重跑，不重新设计模型。

---

## 22. 模型识别与失败处理规则

### Case A — Demand → Price 很弱

不马上删除需求模块。先检查：

- battery installation 是否是滞后实现量而非预期量；
- 是否 price leads demand；
- NEV / chemistry mix 是否更合适。

若仍弱，则把 demand shock 设为 latent demand expectation，而 battery 只作 noisy anchor。

### Case B — Cost → Price 极强，其他机制弱

检查是否只是共同趋势造成；用 dlog、break-adjusted 和 robustness provider 复核。

### Case C — Price/Margin 不领先 Output

则不要强行加入长 investment lag。可以把 capacity state 简化为较高 persistence 的 supply state。

### Case D — Inventory latent state 不可识别

先删除 inventory shock，只保留 inventory accumulation identity；或者把 inventory 作为 deterministic state。

### Case E — MCMC 不收敛

顺序：

1. 减参数；
2. 固定弱识别参数；
3. 减 shock；
4. 检查尺度与观测误差；
5. 再调整 prior。

### Case F — Structural model OOS 不优于 BVAR

保留结构模型作为解释工具的前提是 IRF/HD 有清晰经济价值；如果解释和预测都没有增量，则回到更小 state-space，不增加复杂度。

---

## 23. 代码结构目标

```text
src/
├── data/
│   ├── schema.py
│   ├── alignment/
│   └── release_calendar/
├── diagnostics/
│   ├── descriptive.py
│   ├── stationarity.py
│   ├── lag_screening.py
│   └── break_tests.py
├── baselines/
│   ├── random_walk.py
│   ├── ar.py
│   ├── var.py
│   └── bvar.py
├── models/
│   └── lc_mvp/
│       ├── equations.py
│       ├── steady_state.py
│       ├── transition.py
│       └── observation.py
├── state_space/
│   ├── kalman.py
│   ├── irregular_kalman.py
│   └── likelihood.py
├── estimation/
│   ├── priors.py
│   ├── map.py
│   └── mcmc.py
├── analysis/
│   ├── irf.py
│   ├── fevd.py
│   ├── historical_decomposition.py
│   └── forecast.py
└── futures/
    ├── contracts.py
    ├── basis.py
    └── carry.py
```

脚本：

```text
scripts/
├── run_phase1a1_descriptives.py
├── run_phase1a2_diagnostics.py
├── run_baselines.py
├── run_mvp_state_space.py
├── run_estimation.py
├── run_irf_fevd.py
├── run_historical_decomposition.py
├── run_oos_forecast.py
└── build_daily_futures_dataset.py
```

所有阶段必须支持 config-driven 运行，不允许把样本区间、滞后阶数和参数范围散落硬编码。

---

## 24. 测试要求

### 数据层

- Data Freeze hash immutable
- no future leakage
- no interpolation unless explicitly declared robustness
- date/month uniqueness
- unit checks

### 状态空间

- transition dimensions
- observation dimensions
- covariance PSD
- predict/update consistency
- missing-observation handling
- dynamic `H_t`
- synthetic state recovery

### 估计

- likelihood finite
- boundary handling
- reproducible seed
- posterior diagnostics

### 分析

- IRF zero-shock baseline
- FEVD shares sum to ~100%
- historical decomposition reconstruction identity
- forecast origin respects information set

---

## 25. 中期时间表与硬 Gate

| 日期 | 任务 | 必须交付 |
|---|---|---|
| 9/16–9/22 | Phase 1A-1 | 描述统计、图、QA、diagnostics memo |
| 9/23–9/29 | Phase 1A-2 | ADF/KPSS、lag、break、mechanism evidence table |
| 9/30–10/6 | Baselines | RW/AR/VAR/BVAR + first OOS |
| 10/7–10/13 | MVP structure | 方程、steady-state / local stability、参数表 |
| 10/14–10/20 | State-space | Kalman + likelihood 端到端跑通 |
| 10/21–10/27 | Estimation + IRF/FEVD | 参数、状态、IRF、FEVD |
| 10/28–11/3 | HD + OOS | 历史分解 + 严格样本外比较 |
| 11/4–11/10 | Futures + robustness | 初步期现关系、替代数据源和状态验证 |
| 11/11–中期 | Freeze | 中期报告、PPT、复现检查，不开大型新模型 |

硬 Gate：

- **2026-09-21**：Data Freeze v1 主线锁定；v2 尾部补数仅作为并行更新。
- **2026-10-19**：State-Space + Kalman + likelihood 必须能运行。
- **2026-11-02**：IRF + FEVD 必须形成稳定版本。
- **2026-11-10**：主要实验冻结。

---

## 26. 中期答辩最终希望展示的研究闭环

中期不需要展示一个“终极 DSGE”，而要展示一个小而完整、能被验证的闭环：

```text
产业事实
→ 数据诊断
→ reduced-form evidence
→ structural equations
→ state-space / Kalman
→ parameter estimation
→ latent states
→ IRF / FEVD
→ historical decomposition
→ OOS comparison
→ preliminary spot-futures extension
```

答辩核心问题：

1. 为什么需求、成本、供给能够共同解释碳酸锂价格？
2. 哪类冲击最重要，作用多久？
3. 价格上涨如何通过利润和滞后扩产反馈到未来供给？
4. latent inventory / margin 是否与短样本真实数据方向一致？
5. 模型能否解释 2021–2022 上涨和 2023 下跌？
6. 结构模型是否比 RW/AR/VAR/BVAR 提供了额外解释或预测价值？
7. 期货上市后，价格发现和 carry/risk premium 机制是否存在初步证据？

---

## 27. 当前立即执行项

当前只执行 **Phase 1A-1**。

下一次 Codex 任务必须严格限制为：

```text
Data Freeze v1
→ QA
→ transformations
→ descriptive statistics
→ figures
→ seasonality notes
→ contemporaneous correlations
→ rolling descriptive diagnostics
```

暂时不要执行：

```text
ADF/KPSS
lag screening
break tests
VAR/BVAR
MVP model
Kalman
MCMC
IRF/FEVD
```

Phase 1A-1 完成后，由研究负责人先审查图表和描述统计，再释放 Phase 1A-2。

---

## 28. 最终研究纪律

1. **先证据，后结构。** 结构滞后、先验和状态设计必须受 diagnostics 约束。
2. **先小模型，后大模型。** 不用复杂度替代识别。
3. **先月度，后混频。** 生猪论文的 mixed-frequency 是技术终点之一，不是第一天就复制的起点。
4. **不插值低频基本面。** 后续混频直接使用动态观测矩阵。
5. **不把 latent state 当事实。** 必须用库存、利润等短样本做外部 validation。
6. **不追求高 R²。** 重点是参数识别、IRF、FEVD、历史解释和 OOS。
7. **随机周期必须 ablation。** 不能让一个周期项未经验证地解释一切。
8. **预测必须有基线。** 任何“预测好”都必须相对 RW/AR/VAR/BVAR 说话。
9. **所有阶段可复现。** 数据版本、配置、随机种子、输出和 commit 必须可追踪。
10. **中期前冻结范围。** 主线优先，期权、tick 微观结构、非线性大扩展推迟。

本计划作为 2026 年中期答辩前的**方法执行总纲**。`phase1_experiment_plan.md` 负责 Phase 1 的局部细节，`midterm_plan_2026_11.md` 负责时间管理；若二者与本计划在方法顺序上冲突，以本计划的“先诊断—基线—MVP—状态空间—估计—结构结果—预测—期货扩展”的顺序为准。
