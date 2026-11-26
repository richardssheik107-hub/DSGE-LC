# OPD Data Availability Report

## 1. Platform access status

`https://www.originp.com/` 可公开访问，公开页面为 OPD 数据超市。其前端公开产品检索接口可返回年鉴及研究包目录；未发现可公开验证的锂产业逐指标目录。平台内部指标检索与导出尚需账号登录，未尝试绕过认证。

## 2. Core four-series summary

| Data | Found | Coverage | Frequency | Unit | Downloadable | Suitable as Core? |
|---|---|---|---|---|---|---|
| lc_spot | LOGIN_REQUIRED | unknown | unknown | unknown | unknown | PENDING |
| lc_output_total | LOGIN_REQUIRED | unknown | unknown | unknown | unknown | PENDING |
| spodumene_price | LOGIN_REQUIRED | unknown | unknown | unknown | unknown | PENDING |
| battery_install_total_gwh | LOGIN_REQUIRED | unknown | unknown | unknown | unknown | PENDING |

## 3. Lithium carbonate spot

After login, search the product tree with “电池级碳酸锂”“碳酸锂价格”. Retain only a China spot series with an explicit Li2CO3 grade of at least 99.5%; industrial grade, lithium hydroxide, futures and export prices are candidates for separate records only.

## 4. Lithium carbonate output

Confirm a China total monthly output series. Keep spodumene, lepidolite, brine and recycling routes as separate candidates rather than adding them without a documented reconciliation rule.

## 5. Spodumene price

Search “锂辉石精矿”“6%Li2O”“CIF中国”. CIF China, FOB Australia and different grades must not be spliced.

## 6. Battery installation

Confirm China monthly total power-battery installation in GWh. LFP and NCM are useful subseries but not substitutes for the total.

## 7. Inventory / capacity / utilization

Check the sample definition. Exchange warehouse receipts, social inventory, producer inventory and capacity are distinct concepts.

## 8. Cost / profit

Record production route and sample definition. These are validation or robustness candidates, not a prerequisite for the first model.

## 9. Downstream demand

Existing NEV production and sales remain authoritative project series. OPD battery installation, LFP/NCM and ESS should be assessed as additional candidates only.

## 10. Trade data

An OPD trade series must identify its original source, HS code, commodity definition and unit before it can extend the existing Comtrade series.

## 11. Macro and financial data

The principal OPD check is the China government-bond 0.25Y/0.5Y yield curve. Do not accept SHIBOR as the same series.

## 12. Downloadability

No OPD commercial data were exported. Exports allowed by the authenticated platform should be stored in `data/raw/commercial/opd/` and excluded from Git.

## 13. Licensing / Git handling

Commercial raw data, credentials and cookies are excluded from Git. Only metadata, schemas, reproducible scripts and audit documents may be committed unless the OPD terms expressly permit redistribution.

## 14. Recommended canonical series

No OPD series is recommended until the authenticated catalog confirms definition, frequency, coverage and export rights. The P0 evaluation standard is approximately 2020-01 to 2026-06 with a stable definition.

## 15. Variables not worth using

Do not use an ambiguous product catalogue listing, chart-only values, undocumented series, or a series combining changing delivery basis/grades as a canonical input.

## 16. Manual actions required

Use [OPD 人工检索清单](opd_manual_search_checklist.md) after logging in. The requested output is a catalog record first; export only series whose normal UI permits it.
