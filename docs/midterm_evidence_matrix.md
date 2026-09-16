# Midterm Evidence Matrix

本矩阵把中期研究问题、可复现证据、可写结论和必须保留的限制绑定在一起。`Strength` 是当前证据链强度，不是因果识别等级。

| Research question | Evidence | Phase / authoritative artifact | Result | Strength | Warning | Midterm claim |
|---|---|---|---|---|---|---|
| 核心数据是否形成稳定研究样本？ | Data Freeze hash、coverage、missingness | Data Freeze v1；`data/processed/core_monthly_panel.csv`；Phase 1A-1 | 2020-01—2025-09 共 69 个月，核心月度面板内部缺失 0；结构样本 2021-01—2025-09，N=57 | STRONG | 商业源尾部不能自动延伸；Data Freeze v2 未就绪 | 中期所有核心结果来自同一冻结样本，未用 2025-10 以后数据美化结果 |
| 成本压力是否推高碳酸锂价格？ | reduced-form timing、posterior loading、IRF、HD、external validation | Phase 1A-2；`baseline_posterior_summary.csv`；Phase 2E/2F/2H | `b_c` median 0.357；cost shock 对 price 的核心 IRF 为正；2021–2022 cost 是最大正向结构贡献；`c_t` 与锂辉石路线成本 dlog Pearson 0.988 | STRONG / RELATIVELY STRONG | 0.988 部分来自共同 SC6 成本锚，不能当成独立因果证明 | 成本是当前最稳定、证据链最完整的基本面机制，但不能声称完全解释价格 |
| 需求冲击是否推高价格？ | battery measurement、posterior `b_d`、IRF、HD | Phase 2D—2F | `b_d` median 0.151，90% interval 约 [0.015, 0.356]；demand shock 对 price 的 IRF 为正；2021–2022 demand 为正向贡献 | PARTIAL | `rho_d / sigma_d` 对 battery measurement sd 敏感；battery 不是纯需求 | 需求通道方向有支持，但强度与历史归因需保留测量假设限制 |
| 供给扩张是否压低价格？ | `b_q` posterior、supply IRF、historical contribution | Phase 2D—2F | `b_q` median 0.116，price equation 中以前置负号进入；supply shock 的 price IRF 为负；历史供给净贡献相对成本和价格残差较弱 | PARTIAL / WEAK MAGNITUDE | `b_q` lower-bound mass 较高；短样本下 loading 方向弱识别 | 供给冲击方向符合经济机制，但中期不强调其数量大小或主导地位 |
| 潜在库存压力是否有外部含义？ | posterior `b_n`、observed inventory validation、`rho_n` sensitivity | Phase 2D、2H | baseline `n_t` 与 log monthly-mean inventory Pearson median 0.650；`rho_n=.50/.95` 为 0.388/0.891 | PARTIAL | `b_n` median 0.034、lower-bound mass 0.448；相关强度高度依赖固定 `rho_n` | latent inventory state 得到方向性外部验证，但 magnitude 不是稳定识别量 |
| Bayesian posterior 是否收敛？ | R-hat、ESS、MCSE、sampler/synthetic gates | Phase 2D；`rhat_ess_diagnostics.csv`；`phase2d_gate_summary.csv` | max R-hat 1.0079；min bulk ESS 627.9；min tail ESS 484.2；baseline/prior sensitivity gates 通过 | STRONG NUMERICAL | 收敛不等于所有参数强识别；固定假设仍有 warning | 后验数值收敛充分，可用于 IRF/FEVD/HD，但弱识别参数必须单列 |
| 哪类冲击解释预测误差？ | posterior FEVD | Phase 2E；`fevd_price_summary.csv` | 12m price residual share median 0.653 [0.473, 0.808]；cost 0.202，demand 0.071，supply 0.038 | STRONG DESCRIPTIVE | residual shock 不是“投机”标签；只表示结构方程未解释部分 | 价格残差在预测误差中仍重要，模型解释力不应被夸大 |
| 2021–2022 上涨由什么共同推动？ | posterior historical decomposition | Phase 2F；`episode_net_contributions.csv` | median net contribution：cost +7.759、demand +3.727、supply +1.206、price residual -3.359 | PARTIAL HISTORICAL ATTRIBUTION | 基于 conditional smoothed state means；不是反事实因果实验 | 成本是最大正向结构贡献，需求也为正，但不声称单一因素造成上涨 |
| 2023 下跌如何分解？ | posterior historical decomposition | Phase 2F | cost -4.578、price residual -3.763、demand -2.534、supply -0.499 | PARTIAL HISTORICAL ATTRIBUTION | 多个负向成分同时存在；残差不能命名为投机 | 2023 下跌中成本回落是最大负向基本面贡献，价格残差与需求也重要 |
| 2024—2025 价格为何仍有偏离？ | posterior historical decomposition | Phase 2F | demand -3.965、cost -2.299、supply -1.630，被 price residual +4.611 部分抵消 | PARTIAL HISTORICAL ATTRIBUTION | 样本仅至 2025-09 | 后期负向基本面与正向价格残差并存，说明结构变量不能穷尽短期定价 |
| 结构模型是否有预测增量？ | strict expanding-window OOS、common-sample U2 | Phase 2G；`structural_oos_u2_table.csv` | Structural H1/H3/H6 U2 = 0.914/1.240/1.131；H1 优于 RW，三期限优于 unrestricted VAR；BVAR 更强 | PARTIAL / COMPETITIVE | common forecasts 仅 21/19/16；H3/H6 不优于 RW | 结构模型提供合理而非支配性的预测表现，其主要增量是机制解释 |
| 外部成本/库存数据是否支持 latent states？ | state-vs-validation correlations | Phase 2H | inventory direction positive；route-cost correlation strong | PARTIAL-TO-STRONG CONSTRUCT VALIDITY | cost validation 部分机械；inventory magnitude `rho_n`-sensitive | 外部数据支持状态含义，但不升级为额外识别方程或因果验证 |
| GFEX futures 是否包含领先 spot 的信息？ | monthly/daily cross-correlation、HAC lag tests | Phase 2I；`lead_lag_summary.csv`；`daily_granger_summary.csv` | monthly/daily Pearson 均在 +1 达峰值：0.710/0.475；daily futures→spot 1–5 lag HAC p 均极小，reverse 不显著 | PARTIAL / PRELIMINARY | 27 个月；SMM quote 无 intraday timestamp；连续合约为构造序列 | 可写 preliminary futures-leading evidence，不能写稳定或永久 price discovery dominance |
| 现货与期货是否存在长期均衡？ | ADF/KPSS + predeclared cointegration gate | Phase 2I；`stationarity_diagnostics.csv`；`cointegration_diagnostics.csv` | log levels/returns 均为 BORDERLINE；两者不满足固定 I(1) rule | NOT SUPPORTED IN CURRENT SAMPLE | small-sample asymptotics；不得为得到显著结果调 lag | 当前不能声称 cointegration，VECM 明确标为 not justified |
| basis 是否反映库存压力？ | basis–`n_t` Pearson/Spearman + `rho_n` sensitivity | Phase 2I；`basis_inventory_summary.csv` | contemporaneous Pearson median 0.119/0.187/0.399 (`rho_n=.50/.80/.95`)；Spearman -0.107/0.004/0.129 | WEAK / NOT ROBUST | rank direction 改变，短样本，simple basis 未 carry-adjust | 仅报告弱而敏感的关联，不把 basis 解释成已识别便利收益 |

## Freeze decision

Phase 1A-1 through Phase 2I form the complete pre-midterm empirical chain. No new large model is required for the midterm defense. The claim boundary is fixed by this matrix and the companion claim registry.
