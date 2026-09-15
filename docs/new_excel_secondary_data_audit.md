# New Excel Secondary Data Audit

## 1. Objective

本次只读审计两份 2026 年更新工作簿，判断其中的数据能否进入 Data Freeze v2 candidate layer。审计顺序是 source identification、definition check、overlap reconciliation、calendar/aggregation audit、candidate decision。Data Freeze v1 没有被覆盖、追加或合并，Phase 1A/1B 没有重跑。

## 2. Files and Hashes

| File | Size (bytes) | Modified time | SHA256 | Sheets |
|---|---:|---|---|---:|
| 动力电池行业数据库-20260819.xlsx | 506,372 | 2026-09-15 10:36:40 | `E00614C96C88D3426FFE89FE75DE60124D3EFCEC8430DE06ED8D011A62C7AFF9` | 9 |
| 【东吴电新数据库】锂电池材料价格周报-20260612.xlsx | 2,556,832 | 2026-09-15 10:36:45 | `5DFD059C9224CF735BEF5A4B544B43C560A756220FBF7DDAF42A17A4D38966A2` | 15 |

完整 sheet 名称记录在 `data/metadata/new_excel_secondary_audit.csv`。两份文件均以 read-only 模式打开；运行前后哈希和修改时间一致。

## 3. Dongwu SMM LC Spot Definition

目标列位于 `锂!F`，标题为 `SMM电池级碳酸锂`，日期位于 `锂!A`。非空覆盖期为 2019-12-27—2026-06-12，共 1,591 条，覆盖期内缺失 0、重复日期 0。

表头没有直接写出该列单位，因此不能标为 `UNIT_CONFIRMED`。但原值数量级约为 5—20，与 canonical 全重叠期按 `raw × 10000` 换算后的高度一致性共同支持 `UNIT_INFERRED_WITH_HIGH_CONFIDENCE`，候选单位为万元/吨，换算后为 CNY/t。该列属于 `SECONDARY_SMM_TRANSCRIPTION`，不能升级为 `A_CORE`。

## 4. Quote-Day / Holiday Audit

2020-01—2025-09 直接使用现有 canonical SMM daily quote-date set，只有出现在该日期集合中的东吴观测才进入月均。canonical 结束后，不采用“所有 weekday”规则，而使用明确的中国节假日闭市日期与工作簿自身报价行：2025-10-01—08、2026-01-01—02、2026-02-16—23、2026-04-06、2026-05-01—05 被排除或解释为无报价期。

连续相同价格本身不会被删除。只有日期不在 canonical quote calendar，或落入明确节假日闭市集合时才排除。完整逐日决定保存在本地 ignored 的 `dongwu_smm_quote_calendar_audit.csv`。

## 5. Full Overlap Reconciliation

2020-01—2025-09 的 69 个共同月份中：57 个 `EXACT_MATCH`、9 个 `ROUNDING_MATCH`、1 个 `SMALL_DIFFERENCE`、2 个 `REVIEW_REQUIRED`。66/69 个月的差异不超过 0.1%，主要偏差集中在 2020 年初；2020-04 以后匹配显著增强。

逐日共同报价日期共 1,399 条。部分日期有转录或修订差异，因此整条序列的最终判断是 `WITH_REVIEW`，不是无条件等同于直接 SMM 授权导出。

## 6. Known Public-Month Reconciliation

| Month | Public/accepted SMM | Dongwu derived | Difference | Relative difference | Status |
|---|---:|---:|---:|---:|---|
| 2025-10 | 75,291.18 | 75,291.18 | -0.00 | -0.000005% | ROUNDING_MATCH |
| 2025-11 | 86,457.50 | 86,005.00 | -452.50 | -0.523% | REVIEW_REQUIRED |
| 2026-01 | 156,000.00 | 155,125.00 | -875.00 | -0.561% | REVIEW_REQUIRED |
| 2026-02 | 149,600.00 | 149,642.86 | 42.86 | 0.029% | ROUNDING_MATCH |
| 2026-03 | 156,700.00 | 156,686.14 | -13.86 | -0.009% | ROUNDING_MATCH |

分类阈值固定为：数值完全一致为 `EXACT_MATCH`；相对差异不超过 0.1% 为 `ROUNDING_MATCH`；不超过 0.5% 为 `SMALL_DIFFERENCE`；超过 0.5% 为 `REVIEW_REQUIRED`。没有逐月调整阈值。

## 7. Tail Candidate Decisions

| Month | Derived CNY/t | Effective quote days | Coverage | Decision |
|---|---:|---:|---|---|
| 2025-12 | 99,613.04 | 23 | FULL_MONTH_CANDIDATE | ACCEPTABLE_WITH_REVIEW |
| 2026-04 | 166,133.33 | 21 | FULL_MONTH_CANDIDATE | ACCEPTABLE_WITH_REVIEW |
| 2026-05 | 186,951.50 | 18 | FULL_MONTH_CANDIDATE | ACCEPTABLE_WITH_REVIEW |
| 2026-06 | 168,675.00 | 10 | PARTIAL_MONTH | PARTIAL_MONTH_DO_NOT_USE |

前三个月覆盖完整报价周期，但由于单位来自高置信推断，且 2025-11、2026-01 两个公开 benchmark 的差异略高于 0.5%，当前不标记 `ACCEPTED_SECONDARY_SMM_TRANSCRIPTION`。2026-06 只到 6 月 12 日，不能用于月度 canonical。

## 8. Updated Battery Database

新版工作簿 `全球&中国动力电池行业装机规模-月度` 中的中国总装机量与现有 public patch 在 2026-03—06 完全一致：56.5、62.4、71.9、76.5 GWh。2026-07 为 74.6 GWh，只登记 `NEW_TAIL_CANDIDATE`，不进入 Data Freeze v1。

## 9. LFP / NCM and Battery Production

2026-03—07 的 LFP/NCM 装机量均可提取。3 月 LFP+NCM 正好等于 total；4—6 月差 0.1 GWh，7 月差 0.4 GWh。差异可能来自其他化学体系或一位小数取整，因此不强制 total=LFP+NCM。

`中国锂电池产量规模` 提供 2026-01—07 的动力和储能电池合计产量、三元产量和铁锂产量，单位 GWh。自 2023-08 起口径注明为动力与储能电池合并统计。用途标记为 `ROBUSTNESS`，不进入 Phase 1 main observables。

## 10. Average Battery Capacity

`中国新能源单车平均带电量` 的 2026 年列名依次是“1月平均”“前2月平均”至“前7月平均”，属于 `CUMULATIVE_YTD_METRIC`，不是独立 monthly flow。用途仅为 `MECHANISM_SUPPORT / ROBUSTNESS`。

## 11. SC6 Search Result

两份工作簿中没有定义匹配的 SMM SC6 Li₂O、CIF China 序列。电池企业排名中的普通百分比文本不视为 SC6 命中。结论：`NO_MATCHING_SC6_CIF_CHINA_SERIES`。

## 12. LC Output Search Result

两份工作簿中没有与 canonical `中国碳酸锂总产量` 同定义的 SMM 月度序列。电池产量和材料价格不能替代 LC output。结论：`NO_CANONICAL_OUTPUT_FILL`。

## 13. Data Freeze v2 Gap Status

- LC Spot：新增 2025-12、2026-04、2026-05 三个 review candidates；2026-06 仍为 partial；严格 canonical 缺口尚未关闭。
- SC6：原有 8 个月缺口全部保留。
- LC Output：2025-10—12、2026-03—06 的 7 个月精确值仍缺。
- Battery：2026-03—06 与现有值完全一致，至 2026-06 无缺口；2026-07 为未来 candidate。

## 14. Decision

Q1：东吴 SMM 电池级碳酸锂是否是高质量同定义二次转录？**WITH_REVIEW**。

Q2—Q4：2025-12、2026-04、2026-05 是否可接受？**ACCEPTABLE_WITH_REVIEW**，暂不直接 promotion。

Q5：2026-06 是否仍为 partial？**YES**。

Q6：新版 battery 2026-03—06 是否与现有数据完全一致？**YES**。

Q7：2026-07 battery 是否可登记 candidate？**YES**。

Q8：SC6 是否有真正新补充？**NO**。

Q9：LC Output 是否有真正新补充？**NO**。

Q10：Data Freeze v2 仍缺 Spot 的严格确认/完整 2026-06、SC6 的 8 个月和 LC Output 的 7 个月。

**DATA FREEZE V2 READY: NO.** 本轮仅形成 candidate status，不生成 Data Freeze v2，也不进入 Phase 2。
