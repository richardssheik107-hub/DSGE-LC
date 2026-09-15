# Phase 1 data dictionary

> 更新时间：2026-09-15
>
> 本文件描述当前项目实际使用的数据口径。Data Freeze v1 的核心样本为 2020-01—2025-09，共 69 个月，`DATA_GATE=GO`。

## 1. Core / A_CORE

| Canonical variable | Source / definition | Frequency | Unit | Current coverage | Use |
|---|---|---:|---:|---|---|
| `lc_spot` | SMM 国产电池级碳酸锂 99.5% 现货评估价；日频算术月均为主，月末/中位数做稳健性 | daily → monthly | CNY/t | canonical complete through 2025-09 | 核心价格观测 |
| `lc_output` | SMM 中国碳酸锂总产量；实际月度产量，不是排产/预测 | monthly | metric tons | canonical complete through 2025-09 | 供给锚 |
| `spodumene_price` | SMM Spodumene Concentrate 6% Li₂O, CIF China | daily → monthly | USD/t | canonical complete through 2025-09 | 原料成本锚 |
| `battery_install` | 中国动力电池产业创新联盟，中国动力电池当月总装车量 | monthly | GWh | 2020-01—2026-06 | 需求锚 |
| `usd_cny_mean` | USD/CNY 日度汇率的月度算术均值；1 USD 对应多少 CNY | daily → monthly | CNY per USD | 2020-01—2026-06 | 进口成本换算/宏观控制 |

核心派生量：

- `spodumene_cny_t = spodumene_price × usd_cny_mean`
- 含义：人民币计价的 SC6 精矿价格代理；**不是**碳酸锂生产成本。

### Core versioning

- **Data Freeze v1**：2020-01—2025-09，69 个共同完整月份，内部缺失 0。
- **Data Freeze v2 candidate**：目标 2020-01—2026-06，78 个自然月；当前仍受 SMM 价格尾部与部分产量精确值审核限制。
- 禁止用 Mysteel、长江有色或其他机构的价格直接拼接到 SMM canonical series。

## 2. Remaining canonical tail gaps

| Variable | Remaining strict gap through 2026-06 | Status |
|---|---|---|
| `lc_spot` | 2025-12；2026-04、05、06 | 需 SMM 严格月均或完整日频 |
| `lc_output` | 2025-10、11、12；2026-03、04、05、06 | 已有实际值候选，仍需精确值确认 |
| `spodumene_price` | 2025-10—2026-02；2026-04—06 | 需 SMM SC6 CIF China 严格月均或完整日频 |
| `battery_install` | 无 | 已补至 2026-06 |

已公开接受但尚未改变 v1 的尾部包括：

- `lc_spot`：2025-10、2025-11、2026-01、2026-02、2026-03 的 SMM 官方严格月均；
- `lc_output`：2026-01、2026-02 的 SMM 官方实际值；
- `spodumene_price`：2026-03 的 SMM SC6 CIF China 严格月均。

## 3. Public / macro variables

| Variable | Frequency | Unit | Definition / source rule | Current status |
|---|---:|---:|---|---|
| `cpi_yoy` | monthly | % | 国家统计局 CPI 同比；不是指数水平 | 78/78 |
| `ppi_yoy` | monthly | % | 国家统计局 PPI 同比；不是指数水平 | 78/78 |
| `nev_sales` | monthly | 万辆 / standardized local unit | CAAM/MIIT 口径新能源汽车销量 | 78/78 |
| `nev_production` | monthly | 万辆 / standardized local unit | CAAM/MIIT 口径新能源汽车产量 | 78/78 |
| `china_gov_3m_mean` | daily → monthly | % | ChinaBond 中国国债收益率曲线 0.25Y 节点月均 | 78/78 |
| `china_gov_6m_mean` | daily → monthly | % | ChinaBond 中国国债收益率曲线 0.50Y 节点月均 | 78/78 |
| `lpr_1y` / `lpr_5y` | policy quote / monthly state | % | 中国货币网 / 全国银行间同业拆借中心 LPR | ROBUSTNESS |
| `lc_import_qty` / `lc_export_qty` | monthly | metric tons | 锂的碳酸盐物理贸易量；kg 必须除以 1,000 | public tail through 2026-06 available; canonical merge governed by reconciliation |

ChinaBond 当前不再是 `MANUAL_REQUIRED`。已取得 2020-01-02—2026-06-30 共 1,618 条官方日频国债曲线记录，并计算 3M/6M 月均。

## 4. Robustness variables

| Variable | Provider | Frequency | Unit | Definition | Use |
|---|---|---:|---:|---|---|
| `lc_spot_mysteel` | Mysteel | monthly mean | CNY/t | 中国电池级碳酸锂，出厂含税月均 | ROBUSTNESS |
| `spodumene_mysteel` | Mysteel | monthly mean | USD/t | SC6 Li₂O, CIF China 月均 | ROBUSTNESS |
| `spodumene_concentrate_import_smm_filtered` | SMM / China Customs | monthly | metric tons | 海关总来矿经 SMM 进一步筛选后的锂精矿估计 | ROBUSTNESS |
| route-specific LC output | SMM | monthly | metric tons | 盐湖/锂云母/锂辉石路线产量 | ROBUSTNESS |
| `battery_install_lfp` / `battery_install_ncm` | 动力电池联盟 | monthly | GWh | LFP/NCM 当月装车量 | ROBUSTNESS |

Mysteel 与 SMM 保持提供商分离。当前可比重叠期内，Mysteel 仅用于替代来源稳健性，不用于补 SMM canonical 缺口。

## 5. Validation-only variables

| Variable | Frequency | Unit | Definition | Constraint |
|---|---:|---:|---|---|
| SMM LC inventory components | weekly | metric tons | 冶炼厂、下游、其他、总量等库存 | `VALIDATION_ONLY`; 2026-05 起存在扩样/口径断点 |
| `lc_cost_spodumene_mysteel` | sparse weekly | CNY/t LC | Mysteel 明确披露的澳洲 SC6 路线折算碳酸锂成本 | `VALIDATION_ONLY` |
| `lc_margin_spodumene_mysteel` | sparse weekly | CNY/t LC | Mysteel 明确披露的澳洲 SC6 路线即期利润/亏损 | `VALIDATION_ONLY` |

库存不得把旧样本“总库存”与扩样后的“全环节总计”直接拼接。跨 methodology regime 的长期增长率比较默认禁止。

## 6. Aggregation and missing-data rules

- 日频 spot / spodumene：月度算术均值为主；同时保留月末与中位数做 robustness。
- 月度产量/装车：使用当月实际流量，不把累计值当单月值。
- 周度库存：保留周频 canonical validation 文件；月均/EOM 仅作辅助。
- 不做 linear interpolation、forward fill、backward fill、spline 或基于预测的填补。
- `forecast / estimate / planned` 不得写入 actual。
- 不从折线图、柱状图像素或环比反推 strict canonical 值。
- 所有来源、定义、单位、方法变化和接受状态必须进入 metadata / source manifest。

## 7. Methodology notes

- SMM SC6 CIF China 在 2025 年进行方法论征询，新年度方法论自 2026-01-01 生效；保留为潜在制度审查窗口，不做机械统计调整。
- SMM 碳酸锂库存于 2026-05 扩大样本，并在 2026-06 调整字段定义；库存验证必须 regime-aware。
