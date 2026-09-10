# Public Data Acquisition Report

## 1. 本轮目标

完成 2020-01 至 2026-06 的可公开获取数据，并保留原始响应、审计与缺口；未运行任何模型，亦未改动期货、期权、tick、分钟数据或既有 USD/CNY 原始文件。

## 2. 覆盖结果

| Variable | Start | End | Obs | Missing | Status |
|---|---|---|---:|---:|---|
| cpi_yoy | 2020-01 | 2026-06 | 75 | 3 | PARTIAL |
| ppi_yoy | 2020-01 | 2026-06 | 74 | 4 | PARTIAL |
| nev_sales | 2020-01 | 2026-06 | 78 | 0 | OK |
| nev_production | 2020-01 | 2026-06 | 78 | 0 | OK |
| china_gov_3m_mean |  |  | 0 | 78 | MANUAL_REQUIRED |
| china_gov_6m_mean |  |  | 0 | 78 | MANUAL_REQUIRED |
| lc_import_qty | 2020-01 | 2024-12 | 60 | 18 | PARTIAL |
| lc_export_qty | 2020-01 | 2024-12 | 60 | 18 | PARTIAL |
| usd_cny_mean | 2020-01 | 2026-06 | 78 | 0 | OK |

## 3. 已取得数据

- NBS：CPI、PPI 取国家统计局原始公告 HTML。滚动档案之外的历史月通过国家统计局官网站内检索定位原文；无插值。HTML 对照见 `data/metadata/nbs_reconciliation.csv`。
- MIIT：全国新能源汽车月度产量、销量均为 78 期，单位为万辆。原文的顺序为“产销”；2020-08 为唯一累计值反推，记录于 `data/metadata/nev_derived_months.csv`。
- UN Comtrade：HS 283691、中国（156）、World（0）月度进口/出口响应已保存。仅使用 `netWgt`，kg 除以 1,000 转吨；2025-01 以后 API 无可用净重，保留 NA。

## 4. 仍不可取得

- ChinaBond：已尝试官方国债收益率曲线接口 `queryXyz`，参数明确为 0.25Y/0.50Y（不是 SHIBOR）；远端重置连接，故两序列保持 NA，并在 source manifest 留存失败信息。建议人工在中债历史曲线页导出后再放入日频文件。

## 5. 审计与验证

- 缺失月份、覆盖率和描述统计：`data/metadata/public_data_audit.csv`。
- 原始来源留存检查：`data/metadata/public_data_validation.csv`。
- Comtrade 重复文件只审计、不删除：`data/metadata/comtrade_duplicate_audit.csv`。
- USD/CNY 既有 raw SHA-256 保护台账：`data/metadata/protected_raw_hashes.csv`。

# Round 3 — Auxiliary Data

## 1. 本轮目标

仅获取可追溯的辅助变量；主月度面板及四条人工收集的产业数据均未改动，未开始任何建模。

## 2. GFEX 仓单结果

尝试访问广州期货交易所官方站点时，本环境的 TLS 握手失败。未以商业站点替代，`gfex_lc_warehouse_receipt` 保持 `FAILED`；未假设仓单与吨数换算关系。

## 3. 宏观与金融数据结果

- LPR：从全国银行间同业拆借中心（中国货币网）官方历史接口取得 1Y、5Y 公布日数据，并保留于 `lpr_quotes_daily.csv`。月度值是当月有效的政策报价状态，而不是统计插值。
- 制造业 PMI、规模以上工业增加值：国家统计局官方检索服务的批量请求出现超时阻塞；为避免单一来源拖慢项目，未使用非官方替代，保持失败状态。
- M2：本轮未找到可稳定、可批量复现的人民银行官方历史接口，保持失败状态。

## 4. 下游辅助数据结果

复用已保存的工信部月报原文，新增汽车总产量、总销量及新能源汽车渗透率。渗透率优先使用报告直接值；报告未直接给出时，仅用同月 `nev_sales / auto_sales * 100` 计算，且任一基础值缺失即保持 NA。

## 5. 可选数据、质量与推荐

- 未获取 DR007、逆回购、MLF、充电桩、锂矿石进口和 Brent，以避免无明确官方稳定口径的扩张。
- 推荐：`lpr_1y`、`lpr_5y` 为 **ROBUSTNESS**；`auto_sales`、`auto_production`、`nev_penetration` 为 **ROBUSTNESS**。
- `gfex_lc_warehouse_receipt` 为 **FUTURES_ONLY / VALIDATION_ONLY**，且当前不可用；PMI、工业增加值、M2 为 **DO_NOT_USE**，直至获得可复现官方序列。
