# Phase 2A Structural MVP Specification

## 1. Objective

本阶段把 Phase 1 的经验约束翻译为两个可计算的月度线性结构候选：五状态核心模型 `M0_CORE5` 与六状态慢产能扩展 `M1_CAPACITY6`。目标仅是冻结方程、归一化、矩阵映射和后续识别边界。

## 2. Why This Is Not Yet a Full DSGE

这是 centered stationary deviations 上的 **MVP structural state-space design / semi-structural linear model**，不是由家庭、企业最优化及市场出清完整推导的 DSGE。本阶段没有 Kalman filter、likelihood、参数估计、IRF、FEVD 或历史分解。

## 3. Phase 1 Evidence Used

设计保留 0–1 月较强的 Cost→Price 通道；把 Demand 作为带测量噪声的潜在锚；弱化短期 Supply 反馈；保留 9–11 月 Margin→Future Output Growth 的慢通道候选；并要求以后显式处理 2022-02/03 的 Output 断点候选。Phase 1B 的 MIXED4 优于 DLOG4、但相对 RW 的优势依期限与窗口而变，是保持小模型和强归一化的理由。

## 4. Measurement Design

观测顺序固定为 `y=[spot, ore_cost, output, battery]'`。主规格 `OBS_MIXED4` 使用 Spot dlog、人民币 SC6 代理 dlog、Output YoY log change、Battery YoY log change，各自在冻结样本内标准化；有效期为 2021-01—2025-09，N=57。对照 `OBS_DLOG_MOY4` 对四项 dlog 先按日历月去均值再标准化；有效期为 2020-02—2025-09，N=68。它只检验状态空间变换可行性，不作模型选择或估计。

测量方程为 `y_t=H x_t+v_t`。Spot、Ore、Output 的测量误差固定为零；Battery 的测量标准差只在 `{0.10,0.25,0.50}` 做敏感性，基线为 0.25。所有 loading 固定为 1。

## 5. State Definitions

`d` 是需求状态，`c` 是人民币精矿成本状态，`q` 是短期产出状态，`n` 是潜在库存压力，`p` 是现货价格状态。M1 另加慢产能状态 `k`。这些都是无量纲、中心化、平稳化偏离，不是物理数量水平。

## 6. Shock Definitions

冲击顺序固定为 `[epsilon_d,epsilon_c,epsilon_q,epsilon_p]'`，分别表示需求、成本、供给/生产和价格/markup 扰动。设计基线取 `Cov(epsilon_t)=I` 且对角；不允许相关结构冲击。M1 不增加独立产能冲击。

## 7. M0 Core Model

状态顺序为 `x=[d,c,q,n,p]'`：

```text
d_t = rho_d d_(t-1) + sigma_d eps_d,t
c_t = rho_c c_(t-1) + sigma_c eps_c,t
q_t = rho_q q_(t-1) + a_p p_(t-1) - a_c c_(t-1) + sigma_q eps_q,t
n_t = rho_n n_(t-1) + q_(t-1) - d_(t-1)
p_t = rho_p p_(t-1) + b_d d_t + b_c c_t - b_q q_t - b_n n_t + sigma_p eps_p,t
```

计算顺序固定为 d、c、q、n、p，因此不存在当期 p↔q 代数环。

## 8. Inventory Pressure Interpretation

`n` 是未观测的供需累积压力，不是直接观测的社会库存。其 `q` 与 `d` 累积 loading 固定为 `+1/-1`，`rho_n` 只在 `{0.50,0.80,0.95}` 做敏感性，基线 0.80；M0 不设库存冲击。

## 9. Demand as a Noisy Latent State

Battery 只以固定 loading 1 锚定 `d`，并允许预设测量噪声。这样承认装车量的季节性、发布口径与“纯需求冲击”之间的差异，同时避免 `lambda_battery` 与 `b_d` 的任意尺度交换。

## 10. Cost Channel

`c` 由 `spodumene_cny_t` 的平稳变换锚定，因该代理已包含 USD/CNY。`b_c>=0` 允许快速成本传导，`a_c>=0` 表示较高滞后成本压低当前供给。该设计不把精矿价格称为完整碳酸锂生产成本。

## 11. Short-Run Supply Channel

`q` 只响应滞后价格与滞后成本，符号为 `a_p>=0,a_c>=0`。价格方程中 `b_q>=0` 以前置负号进入。该通道依据 Phase 1 的弱证据保留，但不预设强响应。

## 12. M1 Slow Capacity Extension

M1 状态顺序为 `[d,c,k,q,n,p]'`，新增：

```text
k_t = rho_k k_(t-1) + gamma_m m_(t-L)
q_t = rho_q q_(t-1) + k_t + a_p p_(t-1) - a_c c_(t-1) + sigma_q eps_q,t
```

其余方程不变。`L∈{9,10,11}`，基线 10；`rho_k∈{0.80,0.90,0.97}`，基线 0.90。产能到供给 loading 固定为 1，仅新增自由参数 `gamma_m`，故总数为 15。

## 13. Margin Driver

`m = z(log LC spot)-z(log ore CNY)` 是预定的相对价格/成本环境指标，不是外生结构冲击、实际利润或 CNY/t margin。三个 L 下主观测期均为 2021-01—2025-09、N=57；真实数据只用于确认覆盖和滞后可用性。

## 14. Parameter Classification

M0 的 14 个未来候选待估参数为四个核心 persistence、六个效果系数和四个 shock sd。M1 仅加 `gamma_m`。`rho_n`、`rho_k`、L 与 Battery measurement sd 是预设敏感性参数；所有 measurement loading、库存累积 loading 和 capacity loading 均固定。

## 15. Normalizations

四项观测 loading 固定为 1；库存累积固定为 `q-d`；产能到供给 loading 固定为 1；结构冲击协方差固定对角且单位化，再由四个 `sigma` 缩放。这些规则阻断 demand、capacity、inventory 及 shock scale 的任意重标度。

## 16. Sign Restrictions

Persistence 在 `[0,1)`；`a_p,a_c,b_d,b_c,b_q,b_n,gamma_m>=0`；四个 shock sd 为正。数值扫描中的 persistence `[0.05,0.95]`、effect `[0,1.5]` 和 shock sd `[0.05,1.5]` 是设计范围，不是 Bayesian priors。

## 17. Steady State

因所有状态是中心化平稳偏离且确定性 margin 输入取零，两个模型的设计稳态均为 `x*=0`。这不是产业物理水平的稳态校准。

## 18. Matrix Representation

两个模型均写作 `x_t=A(theta)x_(t-1)+B(theta)epsilon_t+G(theta)m_(t-L)`、`y_t=Hx_t+v_t`。M0 的 G 为空。M1 的 G 按状态顺序为 `[0,0,gamma_m,gamma_m,0,-b_q gamma_m]'`。H 的行固定映射 Spot→p、Ore→c、Output→q、Battery→d。代码从有序结构方程生成 A/B/G/H，并以测试验证方程转移与矩阵转移完全一致。

## 19. Output Break Robustness Design

Phase 2B 必须在同一预设模型上比较全样本与 2022-02/03 Output break-aware 观测处理或样本敏感性；不得据真实结果回改 Phase 2A 方程或在本阶段估计 break 参数。

## 20. FX Extension Design

FX 不进入核心，因为 `spodumene_cny_t` 已含汇率。未来扩展应把 Ore 拆为美元 SC6 与 FX 两个观测/状态，而不是同时加入人民币 Ore 与 FX 造成重复计量。

## 21. Limitations

57 个月主样本短；Battery 锚含噪；库存与产能未被长样本直接观测；margin 仅是代理；稳定性和局部矩秩是设计预检而非经验识别。本文档不提供因果归因、参数值、冲击分解或预测结论。
