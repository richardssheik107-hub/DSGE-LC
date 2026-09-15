# Phase 1A-2 Mechanism Diagnostics Memo

## 1. Objective

本轮只在 Data Freeze v1 上检查平稳性、季节性稳健性、受限领先滞后关系、辅助 HAC 回归、轻量结构断点和无量纲 margin proxy。所有结果都是描述性或预测性诊断，不构成因果识别。本轮未运行 Random Walk、AR、VAR、BVAR、VECM、DSGE、状态空间、Kalman、MCMC、IRF、FEVD、历史分解或样本外预测。

## 2. Frozen Sample

输入为 2020-01 至 2025-09 的 69 个月共同样本，内部缺失为 0。只读上游 `core_monthly_panel.csv` 的 SHA256 为 `9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`。诊断没有加入 2025-10 以后观测，没有插值、前向填充、后向填充、删点或平滑。商业原始数据与 Data Freeze v1 均未改写。

## 3. Stationarity

ADF 使用 AIC 选择滞后；KPSS 使用自动带宽。两者的原假设相反，因此分类综合两项检验，并将冲突证据记为 `BORDERLINE`。

- Spot：log level 在仅常数规格为 `STATIONARY`，在趋势规格为 `NONSTATIONARY`，说明结论依赖确定性项；dlog 为 `STATIONARY`；YoY 为 `BORDERLINE`。
- Output：log level 在仅常数规格为 `NONSTATIONARY`，在趋势规格为 `STATIONARY`；dlog 和 YoY 均为 `STATIONARY`。
- Ore Cost：log level 在仅常数规格为 `STATIONARY`、趋势规格为 `BORDERLINE`；dlog 为 `STATIONARY`；YoY 为 `NONSTATIONARY`。
- Battery：log level、dlog 和 YoY 均出现 ADF/KPSS 冲突，分类为 `BORDERLINE`。
- FX：log level 为 `NONSTATIONARY`；dlog 为 `STATIONARY`；YoY 为 `BORDERLINE`。

这组结果支持 Phase 1B 优先测试 dlog，并对 Output 和 Battery 同时测试 YoY；它不意味着结构模型不能使用 level state。

## 4. Seasonality Robustness

对 dlog 使用日历月固定效应残差，即按月份组内去均值。该处理保留原行序和原样本，Battery 与 Output 的每个日历月残差均值在数值误差范围内为零。Cost → Price、Demand → Price、Supply → Price 和 Price → Future Supply 的峰值 Pearson 方向在 MoY 残差规格中保持一致；Battery 与 Output 的季节性仍使 dlog 单点解释需要谨慎。

## 5. Cost → Price

主规格为人民币精矿价格代理 dlog 对 Spot dlog。候选窗口为 0–1 个月，峰值在 lag 0：Pearson 0.625，Spearman 0.777；YoY 同方向且更强，MoY 残差 Pearson 0.680。lag 0 的 HAC 辅助回归系数为 0.705，HAC SE 0.165，n=68。数据表现出与快速成本传导一致的同期/短期关系，证据等级为 `STRONG`，但共同冲击和双向定价仍使因果表述不成立。

## 6. Demand ↔ Price

Battery → Spot 的 dlog 峰值位于 lag 3（Pearson 0.193，Spearman 0.215），但该点缺乏邻近 lag 稳定性；3–4 个月仅作为弱峰值区域记录，证据为 `NO_CLEAR_EVIDENCE`。排除 2020 年前三个月后峰值方向保持，不能消除局部不稳定问题。

Spot → Battery 的候选区域为 9–10 个月，lag 10 的 Pearson 为 0.154、Spearman 为 0.027，方向在 YoY、MoY 残差和早期 2020 稳健性样本中保持，但秩相关很弱，证据为 `WEAK`。两方向相比，Spot → Battery 略有连续性，但不能据此把装车量解释为价格导致的结果。更稳妥的含义是：实际装车量不宜机械地作为纯同期外生需求状态。

## 7. Supply ↔ Price

Output → Spot 的候选区域为 2–3 个月，lag 3 的 Pearson 为 -0.190、Spearman 为 -0.297；MoY 残差为 -0.311，排除早期 2020 后为 -0.263，但 YoY 在该 lag 接近零，因此证据为 `WEAK`。

Spot → Future Output 的候选区域为 1–2 个月，lag 1 的 Pearson 为 0.192、Spearman 为 0.259；YoY、MoY 残差和早期 2020 样本同方向。HAC 辅助回归 p 值约 0.046，但 R² 仅 0.037，且扫描 25 个 lag 存在多重比较风险，故证据仍为 `WEAK`。这只是短期供给响应候选，不是已经冻结的产能 lag。

## 8. Price / Margin → Future Output

`margin_proxy_zlevel = z(log(Spot)) - z(log(Ore CNY))`，表示相对价格/成本环境；`margin_proxy_dlog_gap = z(Spot dlog) - z(Ore CNY dlog)`，表示短期价格改善相对矿价变化的差异。两者均为无量纲诊断指数，不是 actual profit，也不是 CNY/t margin；没有引入生产转换系数。

由于 Output log level 含强趋势，Proxy A 与其未来水平在 1–12 个月呈负相关，不能作为扩产证据。更合理的主规格是 Proxy A 对未来 Output YoY：候选区域为 9–11 个月，lag 10 的 Pearson 为 0.320、Spearman 为 0.219，早期 2020 稳健性 Pearson 为 0.316；HAC 辅助回归系数 0.144，HAC SE 0.068，n=57。Proxy B 对 dlog 的对应关系较弱，MoY 残差的秩相关也不稳定，因此综合等级上限为 `MODERATE`。

真实 Mysteel 路线利润仅在冻结样本内重叠 2025-01、2025-02 和 2025-06 三个月。三个月的观测利润和 Proxy A 均为负，仅记录方向/符号一致性；因 overlap < 6，没有报告 Pearson、Spearman 或正式验证结论，也没有调参拟合真实利润。

## 9. Structural Break Screening

Zivot–Andrews 使用 log level、常数和趋势两种规格，最大滞后 6 并由 AIC 选择；BIC 分段均值筛选最多两个断点、每段至少 18 个月。经济事件只作事后对照，不被算法预设。

- Spot：ZA 候选为 2021-07 / 2021-11，但均不拒绝单位根原假设；BIC 候选为 2021-09、2023-10。只有单一方法支持，`WEAK / METHOD_ONLY`。
- Ore Cost：ZA 候选为 2021-07 / 2021-10，均不拒绝；BIC 候选为 2021-11、2023-12。`WEAK / METHOD_ONLY`。
- Output：ZA 候选为 2020-11、2022-02，均在 5% 水平拒绝；BIC 候选为 2022-03、2024-04，其中 2022-02/03 高度接近。`STRONG_CANDIDATE`。
- Battery：ZA 候选为 2023-12、2020-12并拒绝；BIC 候选为 2021-07、2023-06，但日期一致性较弱。`MODERATE_CANDIDATE`。

24 个月滚动相关图只展示关系稳定性，不作为断点检验。

## 10. Early-2020 Robustness

对涉及 Battery 或 Output 的主要 pair 增加 `EXCLUDE_EARLY_2020_ROBUSTNESS`，不删除或覆盖全样本。Demand → Price、Price → Demand、Supply → Price、Price → Future Supply 和 Margin → Future Supply 的峰值方向均保持，绝对相关变化不超过约 0.08，因此标为方向稳健。Demand → Price 仍缺乏局部 lag 稳定性；稳健性检查不会把弱关系升级为强机制。

## 11. Mechanism Evidence Table

| Mechanism | Candidate region | Peak | Sign | Strength |
|---|---:|---:|---|---|
| Cost → Price | 0–1 | 0 | positive | STRONG |
| Demand → Price | 3–4 | 3 | positive | NO_CLEAR_EVIDENCE |
| Price → Demand | 9–10 | 10 | positive | WEAK |
| Supply → Price | 2–3 | 3 | negative | WEAK |
| Price → Future Supply | 1–2 | 1 | positive | WEAK |
| Margin → Future Supply | 9–11 | 10 | positive | MODERATE |

表中区域是后续待测试范围，不是已经确定的单一 lag。完整 Pearson、Spearman、样本量、稳健性和结构含义保存在本地结果表中。

## 12. Implications for Baselines

Phase 1B 建议测试而非提前冻结：Spot dlog、Ore Cost dlog、FX dlog；Output 同时测试 dlog 与 YoY；Battery 优先测试 YoY，并用 dlog / MoY 残差作稳健性。最小变量集合建议从 Spot、Ore Cost、Output、Battery 开始，FX 作为扩展控制。lag 搜索应围绕 Cost 0–1、Supply → Price 2–3、Price → Output 1–2，并将 Margin → Output Growth 9–11 作为较慢机制候选；Demand → Price 的 3–4 月弱峰值不应当作强先验。

## 13. Implications for Structural MVP

- capacity lag candidate：短期价格响应候选 1–2 个月；相对价格/成本环境对应未来产量增长的较慢候选为 9–11 个月。正式 `L` 仍待 Phase 1B 与 structural MVP 联合决定。
- cost pass-through timing：0–1 个月，传导可能较快。
- demand-state interpretation：实际装车具有明显季节性且双向领先证据不强，不宜视为纯同期外生需求状态。
- inventory latent state necessity：`UNRESOLVED`。本轮没有核心库存观测，价格—成本强相关也无法替代库存状态识别。
- structural-break robustness：`YES`。Output 的断点候选较强，Battery 为中等候选，后续基线应做分段或断点稳健性检查。

## 14. What Is NOT Yet Proven

本轮没有证明矿价导致现货价格、需求导致价格、价格导致装车或价格/利润导致扩产。HAC p 值只是候选窗口的辅助确认，不能抵消小样本、多重 lag 扫描、共同冲击、趋势、内生性和测量误差。Margin proxy 不是实际利润，真实利润重叠月份不足以正式验证。ZA 与 BIC 断点也不自动等同于具体产业事件或 GFEX 上市效应。

## 15. Phase Decision

**PHASE 1A-2 READY FOR PHASE 1B: YES.**

理由是冻结样本与商业数据安全约束保持不变，平稳性、季节性、候选 lag、HAC 辅助确认、断点和 margin 诊断均已形成可复现输出；弱关系与冲突证据被保留而没有被包装成因果结论。下一阶段只进入 RW、AR、VAR、BVAR reduced-form baselines。
