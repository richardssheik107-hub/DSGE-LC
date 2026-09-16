# Midterm Claim Registry

本表是中期报告、PPT 和答辩的措辞边界。任何 stronger wording 都需要新增证据，而不能只靠改写。

## STRONG / Relatively strong

| ID | Approved claim | Evidence | Required qualifier |
|---|---|---|---|
| S01 | Data Freeze v1 is internally complete for the defined 2020-01—2025-09 core panel. | fixed SHA256；69 months；internal missing 0 | 只限已定义核心变量，不等于所有候选变量完整 |
| S02 | The Phase 2D posterior passed the declared numerical convergence gates. | max R-hat 1.0079；bulk/tail ESS minima 627.9/484.2 | convergence 不等于每个参数强识别 |
| S03 | Core IRF price directions are stable: demand and cost positive, supply negative. | Phase 2E posterior IRF sign probabilities and sensitivity propagation | 这是模型内结构响应，不是自然实验因果估计 |
| S04 | The cost block is the most stable fundamental mechanism in the current model. | `b_c` posterior、IRF、HD、route-cost validation | 写“most stable current mechanism”，不写“fully explains price” |
| S05 | The structural model improves on the unrestricted VAR at H1/H3/H6 on the strict common sample. | U2 Structural 0.914/1.240/1.131 vs VAR 1.103/1.430/1.414 | 不推广为对所有 benchmark 的预测优势 |
| S06 | The latent inventory state is directionally validated by observed physical inventory. | baseline Pearson 0.650；all `rho_n` variants positive | magnitude 对 `rho_n` 敏感 |

## PARTIAL

| ID | Approved claim | Evidence | Limitation that must stay adjacent |
|---|---|---|---|
| P01 | Demand shocks raise price within the model and contributed positively in 2021–2022. | positive demand IRF；HD median +3.727 | battery measurement noise changes `rho_d / sigma_d`; not sole driver |
| P02 | Supply shocks lower price in the model. | negative supply IRF | `b_q` magnitude weakly identified；historical contribution small |
| P03 | Cost was the largest positive structural contribution in 2021–2022 and largest negative fundamental contribution in 2023. | HD medians +7.759 / -4.578 | conditional smoothed decomposition, not causal proof |
| P04 | The residual price shock remained economically important. | 12m FEVD median share 0.653；HD episodes | residual is not synonymous with speculation |
| P05 | Structural forecasting is competitive and adds mechanism interpretation. | H1 U2 < 1；all horizons better than VAR | BVAR stronger; H3/H6 worse than RW; OOS short |
| P06 | GFEX returns provide preliminary leading information for later SMM spot changes. | monthly/daily +1 peak；HAC futures→spot vs reverse | quote timestamp unknown；history starts 2023-07；constructed main contract |
| P07 | Spot and futures show substantial short-run co-movement. | contemporaneous return correlations and normalized paths | no supported long-run cointegration claim |

## WEAK

| ID | Claim allowed only as a warning or research question | Evidence |
|---|---|---|
| W01 | Higher cost may reduce short-run output through `a_c`. | `a_c` median 0.060 with 27.1% lower-bound mass; near-zero concentration |
| W02 | Inventory loading `b_n` has a stable quantitative magnitude. | median 0.034 with 44.8% lower-bound mass; fixed-`rho_n` sensitivity |
| W03 | `rho_p` is precisely identified. | posterior direction/curvature remains weak relative to other persistence parameters |
| W04 | basis rises monotonically with inventory pressure. | Pearson positive but Spearman changes sign across `rho_n` |
| W05 | monthly futures price discovery is stable. | only 25 comparable +1-month pairs after excluding partial listing month |

## NOT_SUPPORTED

| ID | Prohibited claim | Why it is not supported | Safe replacement |
|---|---|---|---|
| N01 | “Cost fully explains lithium-carbonate price.” | FEVD residual share remains large; other contributions matter | Cost is the strongest current fundamental mechanism |
| N02 | “Demand is the sole driver of the 2021–2022 rise.” | cost median contribution is larger; residual/initial conditions matter | Demand contributed positively alongside a larger cost contribution |
| N03 | “The model causally proves the 2022 rise or 2023 decline.” | HD is model-conditional smoothing, not experimental identification | The model attributes these episodes conditionally |
| N04 | “The structural model forecasts best at all horizons.” | BVAR is better; RW beats structural at H3/H6 | Structural performance is competitive, especially relative to VAR |
| N05 | “The price shock measures speculation.” | residual absorbs all omitted/non-structural price movements | Call it residual price/markup shock only |
| N06 | “Spot and futures are cointegrated.” | predeclared I(1) gate fails; Engle–Granger not run | Long-run cointegration is not established in the current sample |
| N07 | “Futures always lead spot.” | short history, quote-timing uncertainty, one market regime | Evidence is preliminary and specific to 2023-07—2025-09 |
| N08 | “The basis identifies convenience yield or risk premium.” | no delivery/financing/storage reconciliation | Report simple percentage basis only |
| N09 | “The current model is a complete DSGE.” | no household/firm optimization or full market clearing | Semi-structural linear state-space MVP |
| N10 | “This is the first study to fill a domestic research gap.” | no systematic novelty review proving priority | State bounded current contributions without “first” language |

## Mandatory warnings in every long-form synthesis

`a_c` near zero；`b_n / b_q / rho_p` weak directions；`rho_d / sigma_d` battery-measurement sensitivity；`b_n` fixed-`rho_n` sensitivity；N=57；important residual price shock；conditional-smoothed HD；short OOS；no universal forecast dominance；short futures overlap and quote-timing uncertainty。
