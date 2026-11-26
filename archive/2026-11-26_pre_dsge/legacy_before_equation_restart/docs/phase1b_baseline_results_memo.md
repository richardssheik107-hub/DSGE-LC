# Phase 1B Reduced-Form Baselines Memo

## 1. Objective

本阶段只建立 Random Walk、AR、VAR 与 independent-equation Minnesota BVAR 的严格时间顺序样本外基线，回答月度产业基本面是否为碳酸锂现货价格提供增量预测信息。本阶段不是模型竞赛，也不估计 DSGE、结构状态空间、Kalman、MCMC、IRF、FEVD 或历史分解。

## 2. Frozen Sample

正式输入为 `data/processed/phase1/monthly_structural_v1.csv`，覆盖 2020-01—2025-09，共 69 个月。Data Freeze v1 以只读 `data/processed/core_monthly_panel.csv` 的 SHA256 `9146B3C858AA0F1BE5FA59720B0446515F0A21C60FA032712F76DD248AEAB7F5` 锁定；运行前后哈希一致。预测、标准化、选阶和先验尺度均未使用 2025-10 以后数据。

## 3. Phase 1A-2 Inputs

预设模型遵循 Phase 1A-2，而不根据测试集结果回改机制结论：Spot、Ore 与 FX 使用 dlog；Output 同时进入 dlog 与 YoY 稳健规格；Battery 的 dlog/YoY 均谨慎处理。Cost → Price 的 0–1 个月证据为强候选，Demand → Price 无清晰证据，Supply → Price 较弱，Output 在 2022-02/03 有强断点候选，Margin → Future Supply Growth 的 9–11 个月证据留给后续慢产能机制。

## 4. Forecast Protocol

主训练窗为 2020-01—2023-12（48 个 level months），首个 forecast origin 为 2023-12，首个 target 为 2024-01，末个 target 为 2025-09。每月扩展训练窗口并重新估计、重新选阶和重新标准化；h=1/3/6 均递归预测，不读取 t+1 以后实际解释变量。各期限有效预测数分别为 21、19、16，并在同一信息集和期限内用共同 origins 比较。

Spot dlog 预测通过 `log(P_hat_t+h)=log(P_t)+sum(predicted dlog)` 重构为同一真实价格水平。主指标为 level RMSE、MAE 与 Theil U2（模型 RMSE / 同期 RW_NO_DRIFT RMSE）；另报告累计 log change 误差及方向准确率。

## 5. Information Sets

主结果使用 `RELEASE_SAFE_APPROXIMATION`：origin t 可用 Spot、Ore 与 FX 的 t 月值，但 Output 和 Battery 统一只用 t-1 月值。辅助 `MONTH_INDEX_IDEALIZED` 允许使用 Output_t 与 Battery_t。

这是严格时间顺序 OOS，但不是 full vintage real-time OOS。当前仓库没有每条商业月度序列的历史发布日期与修订 vintage，因此“一期发布滞后”只是保守、透明且可复现的发布日期近似。

## 6. Random Walk

正式参照 `RW_NO_DRIFT` 固定未来价格为 origin 价格，累计预测变化为零。`RW_DRIFT` 仅作辅助，漂移只由当时训练窗内 Spot dlog 均值估计。RW 在 H3/H6 仍然很难击败，说明价格水平 persistence 是强基线。

## 7. AR

AR 在每个 origin 仅用训练样本、在 p∈{1,2,3} 中按 BIC 选阶，并记录 AIC。主结果 21 个 origins 全部选择 p=1。H1 RMSE 6,214.60、U2 0.913，较 RW 有改善；H3/H6 U2 分别为 1.298/1.398，反而弱于 RW。Spot 自身历史可解释一部分短期惯性，但不构成跨期限稳定优势。

## 8. VAR

固定两套核心规格：`SPEC_A_DLOG4=[spot dlog, ore CNY dlog, output dlog, battery dlog]`；`SPEC_B_MIXED4=[spot dlog, ore CNY dlog, output YoY log, battery YoY log]`。p∈{1,2} 在每个 origin 按训练窗 BIC 选择；主结果两套规格均在 21 个 origins 选择 p=2。

普通 VAR 未提供稳定预测增量。SPEC_A 的 H1/H3/H6 U2 为 1.619/2.185/2.178；SPEC_B 为 1.103/1.430/1.414。保留所有预测且逐 origin 审计 companion roots，没有通过 silent clipping 改写结果。

## 9. BVAR

BVAR 是透明的 `INDEPENDENT-EQUATION MINNESOTA BVAR`，并非 full unrestricted Bayesian VAR。每个方程使用 conjugate Normal-Inverse-Gamma 更新；实现并保存 posterior mean、posterior covariance 与 residual variance posterior，点预测使用 posterior mean。

所有变量在每个 origin 仅按训练窗 z-score；平稳变换的 lag coefficient prior mean 与截距 prior mean 均为 0。主规格固定 p=2、lambda=0.20、theta_cross=0.50、lag_decay=2.0；lambda=0.10/0.30 仅作事先规定的敏感性分析，没有依据 2024—2025 测试误差调参。

## 10. H1 Results

| Model | RMSE | MAE | U2 | Direction accuracy | N |
|---|---:|---:|---:|---:|---:|
| RW_NO_DRIFT | 6,804.54 | 5,206.11 | 1.000 | 0.000 | 21 |
| AR_BIC | 6,214.60 | 5,095.48 | 0.913 | 0.571 | 21 |
| VAR_SPEC_A | 11,015.63 | 8,027.36 | 1.619 | 0.571 | 21 |
| VAR_SPEC_B | 7,507.82 | 6,162.68 | 1.103 | 0.714 | 21 |
| BVAR_SPEC_A | 6,242.99 | 4,923.90 | 0.917 | 0.571 | 21 |
| BVAR_SPEC_B | 5,238.91 | 4,074.86 | 0.770 | 0.667 | 21 |

在有限 OOS 窗口内，BVAR_SPEC_B 的 H1 level RMSE/MAE 最低，较 AR 的 RMSE 改善 15.70%，较 RW 改善 23.01%。这支持小样本 shrinkage 和季节性稳健变换在短期预测中的作用，但不构成统计显著性或结构机制证明。

## 11. H3 Results

RW、AR、VAR_A、VAR_B、BVAR_A、BVAR_B 的 U2 依次为 1.000、1.298、2.185、1.430、1.249、1.007。BVAR_SPEC_B 相对 AR 的 RMSE 改善 22.38%，但相对 RW 仅差约 0.72%，应解释为与 RW 基本持平，而非跨期限胜出。

## 12. H6 Results

同一顺序的 U2 为 1.000、1.398、2.178、1.414、1.392、1.025。BVAR_SPEC_B 相对 AR 的 RMSE 改善 26.72%，但相对 RW 差约 2.47%。VAR_SPEC_B 的方向准确率较高（0.875），却没有转化为较低 level 或 change RMSE，不能据此单独评为最佳模型。

## 13. Fundamental Increment

主样本中，普通 VAR 相对 AR 在所有期限都更差；BVAR_SPEC_A 只在 H3/H6 很小幅度改善；BVAR_SPEC_B 相对 AR 在 H1/H3/H6 的 RMSE 分别改善 15.70%/22.38%/26.72%。因此，对“加入 Ore、Output、Battery 是否超越 AR”这一预先定义问题，BVAR_SPEC_B 的分类为 `FUNDAMENTALS_ADD_PREDICTIVE_VALUE`。

这一结论需要两层限制：第一，增量依赖 shrinkage 与 MIXED4 季节性规格，并未在普通 VAR 中复现；第二，相对最强 persistence 基准 RW，优势是 horizon-dependent（H1 胜出，H3/H6 持平或略差）。因此不能写成“基本面稳定击败所有基线”。Ore 历史的预测能力也不能直接确认或否定 Phase 1A-2 的同期成本传导，因为 contemporaneous mechanism evidence 不等于 forecastability。

## 14. Seasonal Specification Robustness

MIXED4 明显优于 DLOG4：VAR_B 在三期限均比 VAR_A 接近 RW，BVAR_B 也在三期限均比 BVAR_A 低 RMSE。这与 Output/Battery 明显季节性的诊断一致，支持 Phase 2 对季节性观测方程保持谨慎。它不支持为 Battery 设置测试集驱动的特殊超参数。

## 15. Break / Training-Window Robustness

由于本阶段的最小 VAR 实现不安全支持 deterministic exogenous dummy，按预案使用 `training-start-2020-04` 替代正式 break-aware 模型。排除 2020 年前三个月后，VAR_A 的 H1/H3/H6 U2 从 1.619/2.185/2.178 降至 1.212/1.733/1.854，但仍未击败 RW；BVAR_B 的结果基本不变。Output 的 2022-02/03 断点候选仍应在 Phase 2 做显式稳健性处理。

42 个月窗口从更早 targets 开始评估（H1/H3/H6 N=27/25/22），故不与主表作纯训练窗因果比较。在该更长且不同的评价期，BVAR_B U2 为 1.050/1.271/1.454，不再优于 RW；AR 为 0.975/1.236/1.431。说明 forecast ranking 对评价窗口敏感，主结论必须限定为 `within this limited OOS window`。

## 16. Model Stability

主结果的 VAR_A、VAR_B、BVAR_A、BVAR_B 各 21 个 origin 均满足 companion-root stability；stable-only summary 因而与全样本 summary 相同。对应最大 condition number 约为 15.45、22.69、14.44、24.89。模型失败、singular fits、numerical fallback、unstable origins 与 BVAR posterior numerical failures 均为 0。所有潜在失败路径仍会逐 horizon 写入 audit 表。

lambda 敏感性没有单一赢家：BVAR_A 的 lambda=0.10 在 H3/H6 优于 0.20，0.20 在 H1 优于 0.10/0.30；因此保持事先固定的 0.20，不做测试集调参。FX5 只带来极小的 BVAR_A 改善（U2 0.917→0.917、1.249→1.243、1.392→1.385），不足以升级为核心规格。

## 17. What The Forecast Results Mean

RW 是强基线；AR 主要带来 H1 增量；普通 VAR 在 69 个月小样本中方差较大；Minnesota shrinkage 明显缩小普通 VAR 的预测损失。经季节性处理的产业基本面在 BVAR 中相对 AR 包含可复现的增量信息，但无法在所有期限稳定击败 RW。Phase 1B 已建立后续结构模型必须超越或至少解释的 reduced-form benchmark。

## 18. What They Do NOT Mean

这些结果不识别结构因果，不证明 Battery 是纯需求冲击，也不推翻 0–1 个月 Cost → Price 的同期证据。预测失败不等于经济机制不存在；同步共同定价、测量噪声、发布滞后、结构断点和短评价窗都可能削弱历史变量对未来价格的预测。当前结果也不是 full vintage real-time evidence，不能外推为长期稳定排名。

## 19. Implications for Structural MVP

- Cost channel：`KEEP`。Phase 1A-2 的强同期证据仍成立，Phase 1B 仅调整其预测先验强度。
- Demand state：`KEEP AS NOISY LATENT ANCHOR`。Battery 有季节性且机制证据不清晰，不宜当作无噪声结构需求。
- Short-run supply：`WEAKEN`。保留供给方程，但使用较弱、受约束的短期响应。
- Slow capacity：`KEEP CANDIDATE`。保留 margin/capacity 慢通道，不冻结 L=10。
- Inventory latent state：`KEEP`。缺少长一致库存观测，暂作潜在状态并以后用短样本验证。
- FX：`EXTENSION`。FX5 增量很小，不进入核心四变量观测块。
- Output break robustness：`REQUIRED`。结构 MVP 需显式核验 2022 年断点或参数稳定性。

这些建议只规定下一阶段的模型设计与识别预检，不声称已估计 structural causality。

## 20. Phase Decision

**PHASE 1B READY FOR PHASE 2 STRUCTURAL MVP: YES.**

理由是 RW/AR/VAR/BVAR 均可稳定复现，严格 expanding-window OOS 已贯通，信息集、共同 origins、失败与稳定性均已审计，并形成了清晰 benchmark。下一阶段仅进入 MVP structural equations、state definitions、steady state / local stability 与 identification pre-check；暂不开始 Kalman、MCMC、IRF 或 FEVD。
