# High-Value Industry Data Update

## 1. Scope

本轮仅补充公开可核验且具有较高研究价值的替代价格、成本利润、筛选进口、库存制度断点和产量尾部核验资料。数据用途限于 `ROBUSTNESS`、`VALIDATION_ONLY`、`LATENT-STATE VALIDATION` 与 `SUPPLY-SIDE ROBUSTNESS`。未启动模型，未插值，未修改 Data Freeze v1，也未把不同提供商的数据拼接为同一核心序列。

公开网页采用来源 URL、提供商、统计口径与接受状态逐条登记。动态网页及其可能附带的版权内容未批量镜像到仓库；可复核证据入口保存在 `high_value_industry_source_manifest.csv`。

## 2. Mysteel alternative price series

`mysteel_price_monthly.csv` 固定覆盖 2025-01 至 2026-06，共 18 个自然月，缺失保持为空值。

| Variable | Non-missing | Strict SOURCE_A/OK | Coverage | Unit | Definition | Use |
|---|---:|---:|---|---|---|---|
| `lc_spot_mysteel` | 10 | 8 | 2025-01—2026-05 | CNY/t | 中国电池级碳酸锂、出厂含税、月均 | ROBUSTNESS |
| `spodumene_mysteel` | 9 | 8 | 2025-01—2026-04 | USD/t | SC6 Li2O、CIF China、月均 | ROBUSTNESS |

原文以万元/吨披露的碳酸锂月均统一乘以 10,000。没有使用图表估值、月末价、环比反推或第三方猜测。2026-01 同一 Mysteel 报告的表格与正文存在冲突，且相对 2025-12 出现明显水平跳升，文件保留表格值并标记 `INTRA_SOURCE_CONFLICT_REVIEW; LEVEL_JUMP_REVIEW`；2026-05 碳酸锂值来自 Mysteel 公开索引页，标为 `SOURCE_B`。其余无法严格确认的月份保持缺失。

## 3. SMM vs Mysteel price comparison

Data Freeze v1 截止 2025-09，因此两套价格的可比重叠期为 2025-01、2025-06、2025-07、2025-08、2025-09，共 5 个月。

| Variable | Overlap | Mean difference | Median difference | MAPE | Correlation | Definition match |
|---|---:|---:|---:|---:|---:|---|
| `lc_spot` | 5 | -464.786 CNY/t | -238.889 CNY/t | 0.706% | 0.9987 | PARTIAL |
| `spodumene_price` | 5 | 8.958 USD/t | 13.571 USD/t | 3.127% | 0.9675 | MATCH |

差值定义为 Mysteel 减 SMM。锂辉石均为 SC6、CIF China、USD/t，可用于稳健性比较；碳酸锂虽高度相关，但 SMM 价格评估与 Mysteel 出厂含税口径并非完全同义，只适合作为替代来源稳健性检验。5 个重叠点样本很小，相关系数仅是数据 QA 描述，不构成统计结论。

## 4. Mysteel spodumene-route cost and margin

公开周报中共确认 12 个明确披露点，覆盖 2025-01-24 至 2026-03-20。成本与即期利润均为澳洲 SC6 路线折算的碳酸锂口径，单位 CNY/t lithium carbonate；没有自行用现货价减矿价构造利润。

周频文件是原始 canonical validation 文件。月度文件仅在同月多个有效周点时计算 mean、median 和该月最后一个已披露点（EOM）；月度聚合不补齐缺周。推荐用途为 `VALIDATION_ONLY`，用于检验供给成本压力或模型隐含利润方向，不作为核心 observable。

## 5. SMM-filtered lithium concentrate imports

变量严格命名为 `spodumene_concentrate_import_smm_filtered`，提供商为 SMM，底层来源为 China Customs，转换为 SMM filtered estimate，不能解释为海关纯锂辉石进口。

| Month | Total ore import (t) | Filtered concentrate (t) | Share | Origin | Status |
|---|---:|---:|---:|---|---|
| 2025-10 | 652,000 | 531,000 | NA | DIRECT_SMM_VALUE | ACCEPTABLE_WITH_REVIEW |
| 2025-11 | 729,000 | 678,000 | 0.93 | DIRECT_SMM_VALUE | ACCEPTED |
| 2025-12 | 788,500 | 628,000 | 0.80 | DIRECT_SMM_VALUE | ACCEPTED |
| 2026-01 | 832,000 | 636,000 | 0.76 | DIRECT_SMM_VALUE | ACCEPTED |
| 2026-02 | 558,000 | 438,000 | 0.79 | DIRECT_SMM_VALUE | ACCEPTED |
| 2026-03 | 837,400 | 602,928 | 0.72 | DERIVED_FROM_SMM_SHARE | ACCEPTED_DERIVED |
| 2026-04 | 758,000 | 507,860 | 0.67 | DERIVED_FROM_SMM_SHARE | ACCEPTED_DERIVED |
| 2026-05 | 681,000 | NA | NA | NOT_AVAILABLE | TOTAL_ONLY |
| 2026-06 | 768,000 | 552,960 | 0.72 | DERIVED_FROM_SMM_SHARE | ACCEPTED_DERIVED |

2026-03、2026-04 与 2026-06 的绝对量仅按同月公开总来矿量乘 SMM 公开筛选占比计算，明确标记为派生值。2025-10 的精确筛选量仅找到正式研究报告对 SMM 的明确引用，故为 `SOURCE_C`，不升级为无条件接受。

## 6. SMM inventory methodology change

SMM 于 2026-05-13 公告扩充“其他环节”周度样本，新增更多贸易商与电芯厂，称贸易商覆盖约 70%—80%；扩样序列自 2026-05-21 发布，并与旧样本并行。2026-06-11 的月度口径说明把原“总库存”（冶炼厂加下游）改称“上下游总计”，另增含其他环节的“全环节总计”。历史数据不追溯修改。

2026-09-04 SMM 又调整为四类所有权口径、明确中国关境与实际货权原则，并回溯至 2026-04-30。该变化超出本轮目标窗口，但已登记，供未来更新时建立第三制度区间。

## 7. Regime-aware inventory dataset

为避免商业数据库内容进入公开提交层，新的制度感知文件只包含可公开核验的尾部点：2026-05-14 旧样本总库存 101,418 吨，以及 2026-05-21 扩样后的冶炼厂 18,374 吨、下游 42,729 吨、其他 76,157 吨、上下游总计 61,103 吨和全环节总计 137,260 吨。

旧总库存与新全环节总计在同一行不会同时赋值，也不会强制拼接。现有商业历史仍保留在被忽略的 industry 层，仅用于本地验证。推荐用途为 `VALIDATION_ONLY`：将 latent inventory 与 observed inventory 的比较限定在同一 `inventory_regime` 内，禁止跨断点计算简单长期增长率。

## 8. Lithium carbonate output tail verification

2026-01 与 2026-02 的既有接受状态不变。本轮重查的 7 个月均未获得 SMM 官方精确绝对量，或两个定义一致的权威来源，因此不升级：

| Month | Candidate (t) | Best grade | New status | Reason |
|---|---:|---|---|---|
| 2025-10 | 92,260 | SOURCE_A | REVIEW_REQUIRED | 官方公开页仅给大于 9 万吨及取整增速 |
| 2025-11 | 95,350 | SOURCE_C | REVIEW_REQUIRED | 未找到官方精确绝对量 |
| 2025-12 | 99,200 | SOURCE_C | REVIEW_REQUIRED | 仅一个正式报告明确引用 SMM |
| 2026-03 | 106,620 | SOURCE_C | REVIEW_REQUIRED | 官方回顾仅取整为 10.66 万吨 |
| 2026-04 | 110,030 | SOURCE_C | REVIEW_REQUIRED | 未找到第二个精确权威引用 |
| 2026-05 | 113,295 | SOURCE_C | REVIEW_REQUIRED | 未找到第二个精确权威引用 |
| 2026-06 | 115,320 | SOURCE_C | REVIEW_REQUIRED | 未找到第二个精确权威引用 |

这些数值继续只是 search targets，不写入 Data Freeze v1。

## 9. SMM spodumene methodology change

SMM 官方征询页发布日期为 2025-10-13，征询期为 2025-10-15 至 2025-11-15，问题包括 SC6 CIF China 指数对现货市场的代表性以及单笔成交量大于 2,000 干吨的门槛。官方索引中的综合征询决定记录新一年度方法论自 2026-01-01 生效，至 2026-12-31 失效。

这构成潜在制度审查窗口。数据层仅记录事件和制度区间，不进行 statistical adjustment。未来做跨 2026-01 的价格比较时应加入方法论断点敏感性检查。

## 10. Data quality

质量控制包括月份或日期唯一性、数值解析、非负价格与成本检查、单位和频率、定义一致性、来源等级、直接值与派生值区分、制度断点以及不覆盖核心序列。利润允许为负，代表公开披露的即期亏损，不作为异常删除。

所有缺失保持 NA。构建脚本不包含 interpolation、forward fill、backward fill 或 spline。2026-01 Mysteel 内部冲突、2025-10 SMM 筛选进口 SOURCE_C、产量尾部 SOURCE_C 和库存口径变化均保留显式 flag。

## 11. Recommended uses

| Dataset | Use | Decision |
|---|---|---|
| Mysteel LC and SC6 prices | ROBUSTNESS | YES；按提供商分离，不替换 SMM |
| Mysteel SC6-route cost and margin | VALIDATION_ONLY | YES；稀疏披露点 |
| SMM-filtered concentrate import | ROBUSTNESS | YES；直接值与派生值分别处理 |
| SMM inventory | VALIDATION_ONLY | YES；只在同一 regime 内比较 |
| LC output review targets | DO_NOT_USE in canonical | 继续审核 |

## 12. Remaining true data gaps

替代来源的存在没有解决以下 canonical 缺口。真正仍需 SMM/OPD 授权导出的是：

- SMM 电池级碳酸锂 2025-12、2026-04、2026-05、2026-06 的严格月均或完整日频。
- SMM SC6 CIF China 2025-10—2026-02、2026-04—2026-06 的严格月均或完整日频。
- SMM LC output 2025-10、2025-11、2025-12、2026-03、2026-04、2026-05、2026-06 的精确月度实际值或足以升级状态的正式双重证据。
- SMM 库存若需形成 2026-05 至 2026-06 的连续周度尾部，仍需授权导出各制度下并行口径及组件值；不能由公开两个点补齐。

在这些数据获得授权前，核心历史保持冻结，公开替代序列只进入 robustness 或 validation 工作流。
