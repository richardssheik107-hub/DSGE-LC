# Public Data Acquisition Report

> 累计状态更新时间：2026-09-15
>
> 本文件现记录**截至 2026-06 的公开数据累计状态**。早期轮次中的“缺失 / MANUAL_REQUIRED”若与本页当前状态冲突，以本页和 `public_gap_closure_report.md` 为准。

## 1. Current public-data status

| Variable | Coverage | Obs / completeness | Current status | Main source |
|---|---|---:|---|---|
| `usd_cny_mean` | 2020-01—2026-06 | 78/78 | OK | existing protected daily FX source |
| `cpi_yoy` | 2020-01—2026-06 | 78/78 | OK | 国家统计局 |
| `ppi_yoy` | 2020-01—2026-06 | 78/78 | OK | 国家统计局 |
| `nev_sales` | 2020-01—2026-06 | 78/78 | OK | MIIT/CAAM |
| `nev_production` | 2020-01—2026-06 | 78/78 | OK | MIIT/CAAM |
| `china_gov_3m_mean` | 2020-01—2026-06 | 78/78 | OK | ChinaBond 0.25Y |
| `china_gov_6m_mean` | 2020-01—2026-06 | 78/78 | OK | ChinaBond 0.50Y |
| `lc_import_qty` / `lc_export_qty` | 2020-01—2024-12 canonical public + later supplements through 2026-06 | tail available | RECONCILIATION-GOVERNED | UN Comtrade + China Customs/SMM public references |
| `battery_install` tail | 2026-03—2026-06 | 4/4 | ACCEPTED_PUBLIC_PATCH | 动力电池联盟权威转载 |

公开宏观层已不再是当前建模 blocker。

## 2. ChinaBond status — resolved

早期尝试因官方接口连接重置而失败；后续公开补缺轮中 ChinaBond 官方端点恢复可访问。

当前已取得：

- 1,618 条官方日频中国国债曲线记录
- 日期：2020-01-02—2026-06-30
- 0.25Y 节点 → `china_gov_3m_mean`
- 0.50Y 节点 → `china_gov_6m_mean`
- 两个期限月度均值均为 78/78

这些不是 SHIBOR、DR007、LPR 或国开债。ChinaBond **不再需要人工导出**。

## 3. CPI / PPI status — resolved

此前 CPI 缺 3 个月、PPI 缺 4 个月；后续均由国家统计局官方原文补齐。

当前：

- CPI：78/78
- PPI：78/78

未使用插值或非官方替代。

## 4. NEV and battery demand data

NEV 产量、销量已覆盖 2020-01—2026-06，共 78 期。

动力电池装车量核心历史来自商业行业工作簿；公开渠道已补齐：

| Month | Total GWh | LFP GWh | NCM GWh | Status |
|---|---:|---:|---:|---|
| 2026-03 | 56.5 | 45.8 | 10.7 | ACCEPTED_PUBLIC_PATCH |
| 2026-04 | 62.4 | 50.8 | 11.5 | ACCEPTED_PUBLIC_PATCH |
| 2026-05 | 71.9 | 58.4 | 13.4 | ACCEPTED_PUBLIC_PATCH |
| 2026-06 | 76.5 | 63.7 | 12.7 | ACCEPTED_PUBLIC_PATCH |

2026-01、2026-02 的公开联盟数据与商业工作簿完全一致，因此公开尾部被接受。

## 5. Lithium carbonate trade

UN Comtrade HS 283691、中国 156、World 0 的 `netWgt` 构成 2020-01—2024-12 的公共基础序列；kg 除以 1,000 转为 metric tons。

商业行业表与 Comtrade 重叠期的既有对账结果：

- `MATCH`: 54 months
- `MINOR_DIFFERENCE`: 3 months
- `MATERIAL_DIFFERENCE`: 1 month
- `NOT_COMPARABLE / supplement-only`: 2025 early tail

公开 SMM 页面明确引用中国海关的数据已补出 2025-09—2026-06 的月度进口/出口数量。它们进入候选/辅助面板；最终 canonical trade merge 必须继续遵循 reconciliation，不静默覆盖历史来源。

## 6. Public industry tail status

### 6.1 SMM battery-grade lithium carbonate spot

公开严格月均已找到并接受：

- 2025-10: 75,291.18 CNY/t
- 2025-11: 86,457.5 CNY/t
- 2026-01: 156,000 CNY/t
- 2026-02: 149,600 CNY/t
- 2026-03: 156,700 CNY/t

仍缺 strict canonical：

- 2025-12
- 2026-04
- 2026-05
- 2026-06

以上仍需 SMM 授权日频或严格月均。

### 6.2 SMM lithium carbonate output

已接受：

- 2026-01: 97,900 t
- 2026-02: 83,090 t

仍为 `REVIEW_REQUIRED` 的精确值候选：

- 2025-10: 92,260 t
- 2025-11: 95,350 t
- 2025-12: 99,200 t
- 2026-03: 106,620 t
- 2026-04: 110,030 t
- 2026-05: 113,295 t
- 2026-06: 115,320 t

这些值均不得在未完成最终核验前自动写入 Data Freeze v1。

### 6.3 SMM SC6 CIF China

2026-03 严格月均 2,081.4 USD/t 已公开确认。

仍缺：

- 2025-10—2026-02
- 2026-04—2026-06

公开页面中的日点值、月末值、区间和近似月均均不能替代 strict monthly mean。

## 7. High-value public robustness / validation data

已新增：

- Mysteel 电池级碳酸锂月均：`ROBUSTNESS`
- Mysteel SC6 CIF China 月均：`ROBUSTNESS`
- Mysteel 澳洲 SC6 路线碳酸锂成本/即期利润：`VALIDATION_ONLY`
- SMM filtered 锂精矿进口：`ROBUSTNESS`
- SMM 库存扩样/方法制度断点：`VALIDATION_ONLY`

这些数据不替代 SMM core canonical series。

## 8. Variables intentionally not pursued as blockers

以下变量目前不是 Phase 1 Go/No-Go 条件：

- 长期产能
- 长期开工率
- 完整长期社会库存
- 企业 capex / 投资
- 企业利润
- PMI
- 工业增加值
- M2
- DR007 / MLF / reverse repo
- 大规模政策、情绪与地缘风险文本指标

其中产能、投资、库存、利润等可先作为 latent states；已有短样本用于后续验证。

## 9. Data gate

Data Freeze v1：

- 2020-01—2025-09
- 69 个共同完整月份
- 核心产业变量内部缺失 0
- `DATA_GATE = GO`

因此当前主线已从“继续寻找更多公开数据”切换到 Phase 1 diagnostics 和 baselines；剩余 SMM 尾部授权补齐与实证并行进行。

## 10. Related reports

- `docs/industry_data_ingestion_audit.md`：商业行业工作簿正式入库审计
- `docs/public_gap_closure_report.md`：公开尾部补缺与 reconciliation
- `docs/high_value_industry_data_update.md`：Mysteel、filtered imports、库存制度断点和成本利润验证层
- `docs/project_status_2026_09_15.md`：当前项目总状态
