# Midterm Result Digest

## 1. What has been completed

中期主线已经从数据冻结推进到完整的半结构实证闭环：Phase 1 完成描述统计、平稳性/断点/领先滞后诊断及 RW/AR/VAR/BVAR 基准预测；Phase 2 完成 `M0_CORE5` 设计、Kalman/RTS 与 likelihood、constrained MLE preflight、Bayesian posterior、IRF/FEVD、历史分解、严格结构样本外预测、库存/成本外部验证，以及 GFEX 期现初步扩展。

当前模型必须准确称为 **semi-structural linear state-space model / MVP**。它用 `[d,c,q,n,p]` 表示潜在需求、成本压力、短期产出、库存压力和价格压力，以 SMM spot、SC6 人民币成本代理、产量和动力电池装机作为观测或测量锚。它不是由家庭和企业最优化完整推导的 DSGE。

## 2. Data and identification boundary

Data Freeze v1 固定为 2020-01—2025-09 的 69 个月，SHA256 为 `9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`。结构规格 `OBS_MIXED4` 覆盖 2021-01—2025-09，N=57。中期前没有把 2025-10 以后数据、Mysteel 替代序列、库存验证数据或 GFEX futures 写入核心 likelihood。

模型识别采用固定 measurement loading、固定库存累积 `q-d`、对角结构冲击和有界参数空间。`rho_n=.80`、battery measurement sd=.25 为基线，并只在预先声明值上做 sensitivity。主要弱点不是数值失败，而是短样本和若干参数的经济方向弱识别：`a_c` near zero，`b_n/b_q/rho_p` 较弱，`rho_d/sigma_d` 对 battery noise 敏感，`b_n` 对固定 `rho_n` 敏感。

## 3. Bayesian credibility

Phase 2D 所有 numerical gates 通过。Baseline max R-hat 为 `1.0079`，minimum bulk ESS `627.9`，minimum tail ESS `484.2`。prior sensitivity 通过，fixed-assumption block 为 `PASS_WITH_WARNING`。这意味着 posterior 可用于结构结果传播，但不能把收敛误写成所有参数都被数据精确识别。

后验中 `b_c` median `0.357`，是最稳定的价格 loading；`b_d` median `0.151`，方向为正但更受 demand measurement 假设影响；`b_q` median `0.116`、`b_n` median `0.034`，靠近下边界的质量更高。`a_c` median `0.060` 且 lower-bound mass 约 `27%`，不支持强成本抑制短期产出的数量结论。

## 4. IRF and FEVD

Posterior IRF 的核心 price directions 在 baseline 和 sensitivity 中保持：Demand→Price positive，Cost→Price positive，Supply→Price negative。这里的“结构”是模型方程与冲击正交化下的响应，不是外生政策或自然实验。

12-month price FEVD median shares 为：demand `0.071`、cost `0.202`、supply `0.038`、residual price `0.653`。价格残差占比高但不达到文档定义的 severe dominance；它说明价格方程仍有大量未被三类基本面冲击解释的部分。它不能直接命名为 speculation。

## 5. Historical episodes

Phase 2F 的 shock reconstruction 与 decomposition identity 通过，误差在 numerical tolerance 内。Baseline episode median net contributions 显示：

- 2021-02—2022-12：cost `+7.759` 为最大正向结构贡献，demand `+3.727`、supply `+1.206` 也为正；price residual `-3.359`。
- 2023：cost `-4.578` 为最大负向基本面贡献，price residual `-3.763`、demand `-2.534` 也重要；supply `-0.499` 较小。
- 2024-01—2025-09：demand `-3.965`、cost `-2.299`、supply `-1.630`，被 price residual `+4.611` 部分抵消。

这些是 posterior conditional smoothed state means 下的模型归因，不是“成本导致上涨/下跌”的因果证明。

## 6. Forecasting evidence

严格 expanding-window structural OOS 使用 training-only scaling 和 release-safe observable treatment。Structural M0 在 H1/H3/H6 的 Theil U2 为 `0.914 / 1.240 / 1.131`：H1 优于 RW，H3/H6 优于 AR，三个期限均优于 unrestricted VAR；但 BVAR 在全部三个期限更强，RW 在 H3/H6 也优于 structural。

因此预测结论必须是 **competitive forecasting, not universal dominance**。结构模型的核心增量是把需求、成本、供给、库存和 residual price shock 放在同一解释框架内，同时维持合理预测表现。common forecast counts 只有 21/19/16，不能把一次短样本排序推广为一般规律。

## 7. External validation

库存验证中，baseline latent `n_t` 与 log SMM monthly-mean inventory 的 Pearson median 为 `0.650`；固定 `rho_n=.50/.95` 时为 `0.388 / 0.891`。方向始终为正，但强度随库存 persistence 大幅改变。可写“directionally validated”，不可写“inventory magnitude precisely identified”。

成本验证中，`c_t` 与 SMM spodumene-route production-cost dlog Pearson 为 `0.988`，与 lepidolite-route 为 `0.679`。这对成本代理和 timing 是有力 construct validity，但由于 route cost 本身大量由 SC6 原料成本构造，0.988 具有一定机械性，不能作为完全独立识别。

## 8. Spot–futures extension

Phase 2I 自动发现 36 个 GFEX LC five-minute contracts（约 28.7 MB），没有下载或提交 raw files。全量 raw audit 没有重复/逆序 timestamp、缺失 OHLC、非正价格或负 volume。冻结窗口内 volume-main series 有 535 个交易日、7 次换月；换月 return 均使用新合约前一交易日 close，而不是旧/新合约价差。

Canonical daily SMM spot 与 69 个月 Data Freeze 月均的最大绝对 reconciliation error 仅约 `5.8e-11`，因此日频分析 gate 通过。monthly price overlap 为 27 个月；2023-07 是 partial listing month，其收益不进入 comparable monthly-return inference。

Monthly/daily Pearson cross-correlation 都在 `+1` 达峰值，分别为 `0.710 / 0.475`。daily HAC joint lag tests 在 1–5 阶均支持 futures→subsequent spot，而 reverse direction 不显著。这是相互一致的 preliminary leading evidence，但 SMM quote 缺少 intraday timestamp、市场历史很短且主力合约是构造序列，不能写“futures always lead spot”。

现货/期货 levels 未通过预先固定的 I(1) gate，所以 Engle–Granger 不运行，VECM 标为 `VECM_NOT_JUSTIFIED_BY_SAMPLE`。simple monthly-mean basis（F/S-1）在排除 partial listing month 后平均约 `-1.09%`。basis–inventory Pearson 为正，但 Spearman 在不同 `rho_n` 下改变方向；当前不能建立稳健 inventory/carry mechanism。

## 9. What is strong, partial, and unsupported

相对强的结论是：数据冻结可复现、Bayesian numerical convergence 通过、IRF 三个核心方向稳定、成本是最完整的基本面证据链、结构模型优于 unrestricted VAR、库存 latent state 得到方向性外部验证。

部分支持的结论是：需求的价格作用、历史 episode attribution、residual shock 的经济重要性、结构模型的预测增量、futures-leading evidence。弱结论包括 `a_c`、`b_n` magnitude、`rho_p`、basis–inventory monotonicity。当前不支持 cost fully explains price、demand sole driver、HD causal proof、structural forecasts best、price shock equals speculation、cointegration、stable VECM 或 identified convenience yield。

## 10. What remains after the midterm

中期核心实验自 Phase 2J 起正式冻结。答辩前只做报告、PPT、数字/图表交叉核验、bug fix 和必要的小型说明性 robustness。中期以后再考虑真正的新 2026–2027 observations、Data Freeze v2/v3、prospective true OOS、改进库存 observation、M1 capacity、mixed-frequency 或 nonlinear extensions。当前不自动启动这些工作。
