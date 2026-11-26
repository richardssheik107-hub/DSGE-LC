# DSGE-LC Data Dictionary

> 更新时间：2026-09-15  
> 当前主实验数据版本：**Data Freeze v1**  
> 当前主结构估计样本：`OBS_MIXED4`, 2021-01—2025-09, `N=57`

本文件描述当前项目实际使用的数据定义、usage layer、coverage 和版本规则。历史 acquisition / audit 文档不应覆盖这里的当前定义。

## 1. Usage layers

### `A_CORE`

进入 Data Freeze v1 并用于主实验构造的 canonical 核心数据。

### `ROBUSTNESS`

替代提供商、替代口径或辅助变量，只用于稳健性，不得静默填补 canonical 缺口。

### `VALIDATION_ONLY`

短样本、方法论分段明显或仅适合验证潜在机制的数据，不直接进入当前主测量方程。

### `CANDIDATE`

尚未完成 strict source verification 的尾部值、二级转录或 v2 候选数据，不进入当前 Phase 2 主估计。

### `PUBLIC_AUXILIARY`

公开宏观、金融和贸易数据，用于控制、后续扩展或稳健性。

## 2. Core / A_CORE

| Variable | Definition | Frequency | Unit | Current canonical coverage | Current model use |
|---|---|---:|---:|---|---|
| `lc_spot` | SMM 国产电池级碳酸锂 99.5% 现货评估价；日频算术月均为主 | daily → monthly | CNY/t | complete through 2025-09 | Spot price anchor |
| `lc_output` | SMM 中国碳酸锂总产量；实际月度产量 | monthly | metric tons | complete through 2025-09 | Supply / output anchor |
| `spodumene_price` | SMM Spodumene Concentrate 6% Li₂O, CIF China | daily → monthly | USD/t | complete through 2025-09 | Raw-material cost anchor |
| `battery_install` | 中国动力电池产业创新联盟，当月动力电池总装车量 | monthly | GWh | 2020-01—2026-06 | Noisy demand measurement anchor |
| `usd_cny_mean` | USD/CNY 日度汇率月度算术均值 | daily → monthly | CNY per USD | 2020-01—2026-06 | Cost conversion / extension |

Derived variable:

`spodumene_cny_t = spodumene_price × usd_cny_mean`

Interpretation: RMB-denominated SC6 concentrate-price proxy. It is **not** a full lithium-carbonate production-cost series.

## 3. Data Freeze versioning

### Data Freeze v1 — ACTIVE / LOCKED

- common period: 2020-01—2025-09
- common months: 69
- internal missing: 0
- data gate: GO
- SHA256: `9146B3C858AA0F1BE5FA59720B0446515F0A21C60FA032712F76DD248AEAB7F5`

This is the only canonical version for current Phase 1 / Phase 2 main experiments.

### Data Freeze v2 candidate — NOT READY / NON-BLOCKING

Target: 2020-01—2026-06, 78 natural months.

Do not use v2 candidate values inside current structural estimation until direct verification and a new freeze are explicitly completed.

## 4. Remaining strict canonical gaps to 2026-06

| Variable | Remaining strict gap | Status |
|---|---|---|
| `lc_spot` | 2025-12; 2026-04, 05, 06 | direct SMM monthly mean / complete daily confirmation still required |
| `lc_output` | 2025-10, 11, 12; 2026-03, 04, 05, 06 | candidate actuals exist but require direct verification |
| `spodumene_price` | 2025-10—2026-02; 2026-04—06 | direct SMM SC6 strict monthly mean / daily export required |
| `battery_install` | none through 2026-06 | complete |

Already accepted tail values that still do **not** alter v1 include:

- `lc_spot`: 2025-10, 2025-11, 2026-01, 2026-02, 2026-03;
- `lc_output`: 2026-01, 2026-02;
- `spodumene_price`: 2026-03.

## 5. Phase 2 measurement use

### `OBS_MIXED4` — PRIMARY

2021-01—2025-09, N=57:

- Spot dlog;
- Ore CNY dlog;
- Output YoY log;
- Battery YoY log.

This is the current `M0_CORE5 / M0_FULL14` estimation measurement set.

### `OBS_DLOG_MOY4` — SECONDARY / TRANSFORMATION CHECK

2020-02—2025-09, N=68:

- four-variable dlog;
- calendar-month demeaning.

Used for transformation feasibility / smoke testing, not for raw-likelihood comparison with `OBS_MIXED4`.

## 6. Robustness series

| Variable / group | Provider | Unit / frequency | Use |
|---|---|---|---|
| `lc_spot_mysteel` | Mysteel | monthly mean, CNY/t | `ROBUSTNESS` |
| `spodumene_mysteel` | Mysteel | monthly mean, USD/t | `ROBUSTNESS` |
| filtered concentrate imports | SMM / China Customs | monthly tons | `ROBUSTNESS` |
| route-specific LC output | SMM | monthly tons | `ROBUSTNESS` |
| `battery_install_lfp` / `battery_install_ncm` | battery alliance | monthly GWh | `ROBUSTNESS` |
| LC trade auxiliary series | public / reconciled | monthly tons | `ROBUSTNESS` / extension |

Mysteel and SMM remain separate providers. Robustness series cannot fill holes inside SMM canonical series.

## 7. Validation-only series

| Variable | Frequency | Unit | Constraint |
|---|---:|---:|---|
| SMM LC inventory components | weekly | metric tons | methodology-regime-aware only; 2026-05 onward expansion / definition change |
| `lc_cost_spodumene_mysteel` | sparse weekly | CNY/t LC | route-specific cost validation only |
| `lc_margin_spodumene_mysteel` | sparse weekly | CNY/t LC | route-specific spot margin validation only |

Inventory old-regime and expanded-regime totals must not be treated as one uninterrupted long series.

## 8. Secondary / candidate series

Dongwu workbook SMM battery-grade LC transcription is a secondary source audit, not a canonical replacement. Candidate full-month values for 2025-12, 2026-04 and 2026-05 remain review candidates; 2026-06 was partial in the audited workbook and must not be used as a full-month observation.

Any CCMN / Changjiang or future alternative-provider series must be stored under a distinct variable name and may only enter robustness or fallback experiments that are explicitly documented.

## 9. Public / macro variables

| Variable | Frequency | Definition | Status |
|---|---:|---|---|
| `cpi_yoy` | monthly | NBS CPI YoY | 78/78 through 2026-06 |
| `ppi_yoy` | monthly | NBS PPI YoY | 78/78 |
| `nev_sales` | monthly | NEV sales | 78/78 |
| `nev_production` | monthly | NEV production | 78/78 |
| `china_gov_3m_mean` | daily → monthly | ChinaBond 0.25Y node monthly mean | 78/78 |
| `china_gov_6m_mean` | daily → monthly | ChinaBond 0.50Y node monthly mean | 78/78 |
| `lpr_1y` / `lpr_5y` | quote / monthly state | LPR | auxiliary / robustness |
| LC import / export | monthly | physical trade quantity | public tail through 2026-06 available; merge remains reconciliation-governed |

ChinaBond 2020-01-02—2026-06-30 contains 1,618 official daily curve observations used to compute 3M/6M monthly means.

## 10. Aggregation and missing-data rules

- daily spot / spodumene: arithmetic monthly mean for main use; median / month-end may be robustness outputs;
- monthly production / installation: use actual monthly flow, never cumulative YTD as monthly flow;
- weekly inventory: preserve weekly validation source; monthly aggregation only for explicitly defined checks;
- no linear interpolation;
- no forward fill / backward fill;
- no spline or model-imputed canonical values;
- no `forecast / planned / estimate` values written as actual;
- no chart-pixel extraction into strict canonical series;
- no provider splicing to extend a core price series.

## 11. Methodology notes

- SMM SC6 CIF China had methodology consultation in late 2025; new annual methodology became effective 2026-01-01. Record the regime, do not mechanically adjust historical values.
- SMM LC inventory expanded sample coverage around 2026-05 and later field definitions changed; validation must be regime-aware.
- Battery chemistry totals may differ slightly from total installation due to other chemistries and rounding; do not force component sums to overwrite official totals.

## 12. Current modeling interpretation

Observed data do not need to exist for every structural state. Current latent / weakly observed concepts include demand state, inventory pressure and future capacity. Long histories of capacity, investment, inventory or enterprise profit are therefore not blockers for `M0_CORE5`.
