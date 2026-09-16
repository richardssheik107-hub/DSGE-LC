# Midterm Result Digest

> 修订日期：2026-09-16（研究修正版 R1）。范围：A01—A08 的诊断、FEVD/历史分解、测量单位、期现同口径、预测与外部验证；旧稿可在 Git 提交 `ef2eb37` 定位。本版不新增模型或重估后验；受影响的图表、结论以各 R1 审计和最终结果登记为准。文献、导师方法范围和学校提交验收仍未关闭。

## 1. What has been completed

中期主线从数据冻结推进到可复核的半结构实证链：Phase 1 完成描述统计、平稳性/断点/领先滞后诊断及 RW/AR/VAR/BVAR 基准预测；Phase 2 完成 `M0_CORE5` 设计、Kalman/RTS 与 likelihood、constrained MLE preflight、Bayesian posterior、IRF/FEVD、历史分解、给定已选规格的递归历史样本外预测、库存/成本构念对照及 GFEX 期现初步扩展。R1 修正了若干展示和解释边界；该链不等于正式提交就绪。

当前模型必须准确称为 **semi-structural linear state-space model / MVP**。它用 `[d,c,q,n,p]` 表示潜在需求、成本压力、短期产出、库存压力和价格压力，以 SMM spot、SC6 人民币成本代理、产量和动力电池装机作为观测或测量锚。它不是由家庭和企业最优化完整推导的 DSGE。

## 2. Data and identification boundary

Data Freeze v1 固定为 2020-01—2025-09 的 69 个月，SHA256 为 `9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`。结构规格 `OBS_MIXED4` 是**四种月度变换的组合，不是混合频率模型**；实际入模为 2021-01—2025-09、N=57。原 LEGACY scaler 先逐列按所有可用月份拟合、再取共同完整行：spot/ore 各用 2020-02—2025-09 的 68 期，output/battery 各用 57 期。原后验与该输入逐值及似然回放相符。共同支持期 57 期 scaler 仅构建对照、**没有估计相应后验**，不能把其与旧后验混用。2025-10 以后数据、Mysteel 替代序列、库存验证数据或 GFEX futures 未写入核心 likelihood；详见 [R1-4](audits/r1_measurement_and_units.md)。

模型识别采用固定 measurement loading、固定库存累积 `q-d`、对角结构冲击和有界参数空间。`rho_n=.80`、battery measurement sd=.25 为基线，并只在预先声明值上做 sensitivity。主要弱点不是数值失败，而是短样本和若干参数的经济方向弱识别：`a_c` near zero，`b_n/b_q/rho_p` 较弱，`rho_d/sigma_d` 对 battery noise 敏感，`b_n` 对固定 `rho_n` 敏感。

## 3. Bayesian credibility

R1-1 用参考定义重算原七套 production draws，来源、参数支持、稳定性、收敛和实现对照门槛均通过，没有重跑 MCMC。Baseline 最大 R-hat 为 `1.00788`，最小 bulk ESS `621.49`、tail ESS `482.27`，最大均值 MCSE/后验 SD `0.03654`；旧 `627.9/484.2/0.03991` 是过时诊断算法输出，不再作为正式数值。Baseline 来源为有证据的 `PASS_RECONSTRUCTED`，并非原生 sidecar；其余六套来源通过。收敛可支持后验传播，但不等于每个参数被强识别；详见 [R1-1](audits/r1_posterior_diagnostics.md)。

后验中 `b_c` median `0.357`，是最稳定的价格 loading；`b_d` median `0.151`，方向为正但更受 demand measurement 假设影响；`b_q` median `0.116`、`b_n` median `0.034`，靠近下边界的质量更高。`a_c` median `0.060` 且 lower-bound mass 约 `27%`，不支持强成本抑制短期产出的数量结论。

## 4. IRF and FEVD

Posterior IRF 的核心 price directions 在 baseline 和 sensitivity 中保持：Demand→Price positive，Cost→Price positive，Supply→Price negative。`b_d/b_c/b_q≥0` 等参数支持与价格方程符号使部分 impact 方向有机械成分；方向稳定不等于独立因果识别。这里的“结构”是给定方程和正交冲击的模型内响应，不是外生政策或自然实验。

R1-2 在每个原后验 draw 上计算并验收 FEVD。12 个月价格 FEVD **后验均值**为：demand `0.089121`、cost `0.212966`、supply `0.049015`、residual price `0.648897`，四项可加总为 1；四个**边际中位数**分别为 `0.071252/0.202190/0.038343/0.652723`，合计 `0.964508`，不应再归一化或称作漏掉的冲击。价格残差在预测误差中占比较高，但不能直接命名为 speculation。H=1 库存 FEVD 因零预测方差标为 `NOT_DEFINED`，不是零份额；详见 [R1-2](audits/r1_historical_and_fevd.md)。

## 5. Historical episodes

R1-2 的七套条件平滑历史分解通过逐 draw、窗口和状态恒等式技术审计；本表以下为**标准化价格变化压力的边际后验中位数**，各中位数本身不要求相加等于窗口总变化：

- 2021-02—2022-12：cost `+7.759` 为最大正向结构贡献，demand `+3.727`、supply `+1.206` 也为正；price residual `-3.359`。
- 2023：cost `-4.578` 为最大负向基本面贡献，price residual `-3.763`、demand `-2.534` 也重要；supply `-0.499` 较小。
- 2024-01—2025-09：demand `-3.965`、cost `-2.299`、supply `-1.630`，被 price residual `+4.611` 部分抵消。

为恢复可加总的原始月度现货对数变化，须使用 LEGACY spot scaler 的 `g_t = 0.006078769514 + 0.149189542122 × p_t`；冲击和初始条件各乘 SD，另加每月确定性均值。三窗口的均值项分别为 `+0.139812/+0.072945/+0.127654` log，端点总 log 变化分别为 `+2.172933/−1.620285/−0.384397`。只有**总** log 变化可转换为简单百分比；不能把单个冲击百分比或元/吨贡献相加。后期六个替代规格×窗口结果属 `AMBIGUOUS`，故不能无条件宣称历史故事对先验和固定假设稳健。这些是参数后验传播下的条件平滑均值分解，不是完整状态抽样区间或因果证明；详见 [R1-2](audits/r1_historical_and_fevd.md)、[R1-4](audits/r1_measurement_and_units.md)。

## 6. Forecasting evidence

给定已选规格的递归历史样本外检验使用 training-only scaling 和发布日期近似，**不是完全未看过测试期的模型选择，也不是真实历史 vintage 或 prospective 验证**。R1-5 独立核对了 21 起点、56 个完整 `(forecast_origin,target_month,horizon)` 共同键及 15 行评分：Structural M0 在 H1/H3/H6 的 Theil U2 仍为 `0.914 / 1.240 / 1.131`，H1 优于 RW，H3/H6 优于 AR，三期限优于 unrestricted VAR；但 BVAR 全部更强，RW 在 H3/H6 也更强。旧全部 86 次优化尝试均成功，未来运行已增加未收敛候选禁入；旧点预测数值没有因代码防护而改变。各模型的 `exp(E[log P])` 是近似条件中位数型价格点预测，不能直接写成 `E[P]`；详见 [R1-5](audits/r1_forecast_and_external_validation.md)。

因此预测结论必须是 **competitive forecasting, not universal dominance**。结构模型的核心增量是把需求、成本、供给、库存和 residual price shock 放在同一解释框架内，同时维持合理预测表现。common forecast counts 只有 21/19/16，不能把一次短样本排序推广为一般规律。

## 7. External validation

库存验证中，baseline 条件平滑 latent `n_t` 与 log SMM 月均库存的 posterior draw 相关中位数约 `0.650`；固定 `rho_n=.50/.95` 时约为 `0.388/0.891`。但固定中位状态路径的 28 个月样本相关约 `0.650`，3 月配对块 95% 区间约 `[0.394,0.885]`、6 月块约 `[0.161,0.904]`；`n_t` 对当月 Δlog 库存的相关约 `0.154`，块区间均跨零。原狭窄的 draw 区间不是时间样本精度。水平口径提供有限方向/构念支持，不足以证明库存变化机制或精确数量；filtered 路径仍使用全样本后验参数，不能冒称实时检验。详见 [R1-5](audits/r1_forecast_and_external_validation.md)。

成本验证中，`c_t` 与 SMM spodumene-route production-cost dlog 的相关约 `0.988`；该成本状态被人民币矿价变化观测精确锚定，而路线成本也大量使用原料价格，因此高相关主要支持共同口径/构念，**不是独立因果验证**。锂云母路线旧相关约 `0.679`；本轮未把它升级为新独立识别证据。

## 8. Spot–futures extension

Phase 2I 自动发现 36 个 GFEX LC five-minute contracts（约 28.7 MB），没有下载或提交 raw files。R1-3 在 535 个期货交易日比较两种主力规则：旧“当日成交量主力”只属收盘后描述；新增“前一日成交量主力”仅用 t−1 可得选择信息，534 个有效日期、7 次换月均按新合约自身前一收盘价计算收益。这仍不自动构成可执行策略回测。

Canonical daily SMM spot 与 69 个月 Data Freeze 月均的最大绝对 reconciliation error 约 `5.8e-11`。Monthly overlap 有 27 个共同月末端点；2023-07 是上市不完整月份，**不能作为完整月均收益的一端**，但其有效月末端点可用来计算 2023-08 的同端点月末收益。两种月频定义的纳入规则不得混写。

旧月频 `+1` Pearson `0.710` 来自**现货月均 log 差与月内 roll-safe 期货收益之和的错配**，只保留历史参照。同月末端点的主月频：事后主力同期 `0.676`（N=26）、`+1` 为 `0.526`（N=25）；滞后主力分别约 `0.669/0.528`，两者绝对相关峰值均改在 lag 0。严格相邻交易期日频 `+1` 约 `0.475/0.473`（N=533，事后/滞后主力），峰值仍在 +1。旧日频 HAC 只能作为旧定义的探索性辅助，不把它升级为同口径显著性或因果证据；报价日内时点未知、短样本和多 lag 搜索继续限制价格发现解释。详见 [R1-3](audits/r1_spot_futures_alignment.md)。

现货/期货 levels 未通过预先固定的 I(1) gate，所以 Engle–Granger 不运行，VECM 标为 `VECM_NOT_JUSTIFIED_BY_SAMPLE`。simple monthly-mean basis（F/S-1）在排除 partial listing month 后平均约 `-1.09%`。basis–inventory Pearson 为正，但 Spearman 在不同 `rho_n` 下改变方向；当前不能建立稳健 inventory/carry mechanism。

## 9. What is strong, partial, and unsupported

相对强的结论是：冻结数据与 LEGACY 输入可复现、修正定义下 Bayesian numerical convergence 通过、模型内核心 IRF 方向稳定、成本是当前最完整的基本面证据链、历史结构 OOS 对普通 VAR 的点预测排序占优。库存水平相关仅给有限构念支持，不能列为强且独立的验证。

部分支持的结论是：需求的模型内价格作用、2021—2023 条件历史归因、residual shock 的描述重要性、结构模型短期预测增量、日频期货领先型描述相关。弱或敏感的结论包括 `a_c`、`b_n` 数量、`rho_p`、库存变化量外部关系、后期历史故事和月频期货 +1 峰值；后两项必须依 R1-2/R1-3 明确降级。当前不支持 cost fully explains price、demand sole driver、HD causal proof、structural forecasts best、price shock equals speculation、cointegration、stable VECM 或 identified convenience yield。

## 10. What remains after the midterm

中期核心实验自 Phase 2J 起正式冻结。答辩前只做报告、PPT、数字/图表交叉核验、bug fix 和必要的小型说明性 robustness。中期以后再考虑真正的新 2026–2027 observations、Data Freeze v2/v3、prospective true OOS、改进库存 observation、M1 capacity、mixed-frequency 或 nonlinear extensions。当前不自动启动这些工作。
