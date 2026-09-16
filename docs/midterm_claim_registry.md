# Midterm Claim Registry

> 修订日期：2026-09-16（研究修正版 R1）。范围：R1-1—R1-5 对后验诊断、FEVD/HD、测量单位、期现、OOS 与外部验证的结论校正；旧版定位：Git `ef2eb37`。本表直接替换过强措辞，相关图表须使用 R1 审计版本；未完成文献/导师/学校验收。

本表是中期报告、PPT 和答辩的措辞边界。任何 stronger wording 都需要新增证据，而不能只靠改写。

## STRONG / Relatively strong

| ID | Approved claim | Evidence | Required qualifier |
|---|---|---|---|
| S01 | Data Freeze v1 is internally complete for the defined 2020-01—2025-09 core panel. | fixed SHA256；69 months；internal missing 0 | 只限已定义核心变量，不等于所有候选变量完整 |
| S02 | 原七套 posterior 在 R1-1 修正算法、来源、支持、稳定性和参考收敛门槛下通过。 | baseline max R-hat 1.00788；min bulk/tail ESS 621.49/482.27；max mean MCSE/SD 0.03654；[R1-1](audits/r1_posterior_diagnostics.md) | baseline 来源 `PASS_RECONSTRUCTED` 非同期 sidecar；收敛不等于强识别 |
| S03 | 给定模型限制下，需求/成本为正、供给为负的价格 IRF 方向稳定。 | Phase 2E posterior IRF；[R1-4](audits/r1_measurement_and_units.md) | `b_d/b_c/b_q≥0` 等支持与方程符号部分规定 impact 方向；不是独立因果识别 |
| S05 | The structural model improves on the unrestricted VAR at H1/H3/H6 on the strict common sample. | U2 Structural 0.914/1.240/1.131 vs VAR 1.103/1.430/1.414 | 不推广为对所有 benchmark 的预测优势 |
| S06 | 冻结 LEGACY 测量输入和原七套后验可追溯，不与共同支持期新版 scaler 混用。 | 228 个观测值一致、12 个生产 draw 的 loglik 回放；[R1-4](audits/r1_measurement_and_units.md) | 新 scaler 仅构建、未估计；原后验 sidecar 无原生 scaler ID |

## PARTIAL

| ID | Approved claim | Evidence | Limitation that must stay adjacent |
|---|---|---|---|
| P01 | 给定模型中，需求创新对应正向价格 IRF，2021—2022 年条件历史贡献为正。 | positive demand IRF；R1-2 HD 边际中位数 +3.727 标准化价格压力 | impact 符号有支持约束；装车同比不是锂总需求，measurement sd 改变 `rho_d / sigma_d`；不是单一驱动 |
| P02 | Supply shocks lower price in the model. | negative supply IRF | `b_q` magnitude weakly identified；historical contribution small |
| P03 | R1-2 基线中，成本是 2021—2022 最大正向结构贡献，也是 2023 最大负向基本面贡献。 | HD 边际中位数 +7.759 / −4.578，单位为标准化价格变化压力；[R1-2](audits/r1_historical_and_fevd.md) | 条件平滑而非因果；后期 6 个替代规格—窗口为 AMBIGUOUS，不能概括为全历史稳健；原始 log 还须加确定性均值 |
| P04 | 价格残差冲击在预测误差和历史活动中重要。 | 12m FEVD 后验均值 0.648897、边际中位数 0.652723；HD 分窗口；[R1-2](audits/r1_historical_and_fevd.md) | residual 不是 speculation；FEVD 与绝对历史活动份额是不同统计量 |
| P05 | 给定规格的递归历史 OOS 中，结构点预测 H1 相对 RW 有增量、三期限优于普通 VAR。 | H1/H3/H6 U2 0.914/1.240/1.131；56 完整键复核；[R1-5](audits/r1_forecast_and_external_validation.md) | BVAR 全期限更强、H3/H6 弱于 RW；模型选择曾参考全样本、非实时 vintage/prospective；`exp(ElogP)` 非 `E[P]` |
| P06 | 同交易期日频期货收益与下一 SMM 报价期收益有探索性正相关。 | 事后/滞后主力 +1 Pearson 0.475/0.473，N=533；[R1-3](audits/r1_spot_futures_alignment.md) | 月末同端点月频 +1 仅 0.526/0.528，峰值转 lag 0；报价时点未知、多 lag、短样本，不能断言稳定价格发现或策略收益 |
| P07 | Spot and futures show substantial short-run co-movement. | contemporaneous return correlations and normalized paths | no supported long-run cointegration claim |
| P08 | 潜在库存压力与库存 log 水平存在有限构念/方向支持。 | baseline smoothed 约 0.650；28 月时间块 95% 区间：3 月 [0.394,0.885]、6 月 [0.161,0.904]；[R1-5](audits/r1_forecast_and_external_validation.md) | `n_t` 对 Δlog 库存约 0.154、块区间跨零；`rho_n` 敏感；非独立识别或实时验证 |
| S04（由 STRONG 降至 PARTIAL） | 成本是当前模型内**相对**最稳定的基本面通道。 | `b_c` posterior、IRF、FEVD可加总均值、2021—2023条件HD；[R1-6主张复核](audits/r1_claim_revision.md) | 外部0.988有共同矿价成分，后期历史解释不稳健；不写“独立验证”“完全解释价格”或成本冲击因果已识别 |

## WEAK — 仅可作为未证实的研究问题

| ID | 未证实命题（不得写成已成立结论） | 反证/限制 |
|---|---|---|
| W01 | `a_c` 是否显著抑制短期产出，尚未确定。 | `a_c` median 0.060，27.1% posterior mass 在下边界邻域；不能作强数量结论 |
| W02 | `b_n` 是否具有稳定数量幅度，尚未确定。 | median 0.034，44.8% posterior mass 在下边界邻域，且固定`rho_n`敏感 |
| W03 | `rho_p` 是否精确识别，尚未确定。 | 相比其他持续性参数，后验方向/曲率仍弱 |
| W04 | 基差是否随库存压力单调上升，当前不支持。 | Pearson虽为正，Spearman却随`rho_n`变号 |
| W05 | 月频期货是否稳定领先现货一个月，当前不支持。 | 同端点月末+1 Pearson约0.526/0.528（N=25），同期约0.676/0.669（N=26）；旧0.710为错配聚合历史值 |
| W06 | 2024—2025年历史冲击排序是否跨规格稳健，当前不支持强断言。 | R1-2后期六个替代规格—窗口为`AMBIGUOUS`；0个`HIGH`不等于全部稳定 |

## NOT_SUPPORTED

| ID | Prohibited claim | Why it is not supported | Safe replacement |
|---|---|---|---|
| N01 | “Cost fully explains lithium-carbonate price.” | FEVD residual share remains large; other contributions matter | Cost is the strongest current fundamental mechanism |
| N02 | “Demand is the sole driver of the 2021–2022 rise.” | cost median contribution is larger; residual/initial conditions matter | Demand contributed positively alongside a larger cost contribution |
| N03 | “The model causally proves the 2022 rise or 2023 decline.” | HD is model-conditional smoothing, not experimental identification | The model attributes these episodes conditionally |
| N04 | “The structural model forecasts best at all horizons.” | BVAR is better; RW beats structural at H3/H6 | Structural performance is competitive, especially relative to VAR |
| N05 | “The price shock measures speculation.” | residual absorbs all omitted/non-structural price movements | Call it residual price/markup shock only |
| N06 | “Spot and futures are cointegrated.” | predeclared I(1) gate fails; Engle–Granger not run | Long-run cointegration is not established in the current sample |
| N07 | “月频和日频均在期货领先一期达到峰值，证明稳定价格发现。” | R1-3 月末同端点月频峰值在 lag 0；日频 +1 仅描述相关，报价时点未知 | 仅可报告具体口径、N 和正 lag 的探索性相关 |
| N08 | “The basis identifies convenience yield or risk premium.” | no delivery/financing/storage reconciliation | Report simple percentage basis only |
| N09 | “The current model is a complete DSGE.” | no household/firm optimization or full market clearing | Semi-structural linear state-space MVP |
| N10 | “This is the first study to fill a domestic research gap.” | no systematic novelty review proving priority | State bounded current contributions without “first” language |
| N11 | “OBS_MIXED4 已实现混合频率模型。” | 四列均为月度，仅变换不同；产量/装车同比存在 12 月重叠 | 月度混合变换观测规格；混频仍属未实现扩展 |
| N12 | “FEVD 四个边际中位数应加总为 100%。” | R1-2 基线 12 月边际中位数合计 0.964508，后验均值合计 1 | 加总图使用逐 draw 份额的后验均值；中位数分别报告且不归一化 |
| N13 | “历史分解冲击分量可直接写成元/吨或可加总的百分比。” | `p_t` 是标准化 log 变化压力；原始 log 恢复需 LEGACY 均值和 SD | 单分量是可加总 log 变化；仅总量转换简单百分比 |

## Mandatory warnings in every long-form synthesis

`a_c` near zero；`b_n / b_q / rho_p` weak directions；`rho_d / sigma_d` battery-measurement sensitivity；`b_n` fixed-`rho_n` sensitivity；N=57；LEGACY 68/57 拟合期与共同 57 期入模分开；important residual price shock；conditional-smoothed HD、后期 AMBIGUOUS 和原始 log 均值项；short OOS：短且非 prospective、`exp(ElogP)` 不是 `E[P]`；库存变化量支持弱、成本验证有共同原料；short futures overlap：月频 +1 峰值撤回、报价时点不明。

## R1 主要结论变更登记

| 结论 | R1 状态 | 可用表述与证据 |
|---|---|---|
| 成本为相对最稳定的基本面通道 | WEAKENED | 相对比较保留，但外部 0.988 主要是同源构念支持，不是独立因果识别 |
| 需求方向与幅度 | UNCHANGED | 原有条件性方向保留；符号支持和 battery measurement 敏感性必须相邻 |
| 直接供给与 `a_c` | UNCHANGED | 模型内供给价格方向可述，数量弱；`a_c` 不作强效应 |
| 库存外部方向 | WEAKENED | 水平相关保留，变化量与时间块结果不支持强验证 |
| 12 月 FEVD | NUMERICALLY_REVISED | 可加总均值 0.089121/0.212966/0.049015/0.648897；边际中位数不可加总 |
| 三个历史窗口 | NUMERICALLY_REVISED | 旧中位分量保留标注；主展示采用可加总均值、LEGACY log 单位与确定性均值；后期解释 AMBIGUOUS |
| 历史结构 OOS | WEAKENED | 旧指标重放一致，但降级为给定规格的递归历史样本外、非 prospective |
| 期货价格发现整体结论 | WEAKENED | 同端点月末 +1 峰值转 lag 0，但日频 +1 描述相关仍在；不能写稳定领先 |
| 原库存/成本外部验证精度 | WEAKENED | 原 posterior draw 区间不替代 28 月时间样本不确定性；成本同源 |
