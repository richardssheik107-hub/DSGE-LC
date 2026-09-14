# Industry Data Ingestion and Audit

## 1. Source files

Two licensed industry workbooks were copied unchanged to `data/raw/commercial/manual/`. SHA-256 protection is recorded in `data/metadata/manual_industry_raw_hashes.csv`.

## 2. Workbook structure

All sheets, used ranges, inferred header/data rows, date columns, merged ranges, hidden columns, units and source notes are catalogued in `data/metadata/manual_excel_sheet_inventory.csv`.

## 3. Lithium carbonate spot price

Canonical field: `碳酸锂（99.5%电池级/国产,元/吨）`, SMM, CNY/t. Daily observations are aggregated by arithmetic mean; EOM and median are retained. October 2025 is excluded as a partial month.

QA: start=2017-01, end=2025-09, obs=105, missing=0, mean=157839.9954, median=97050.0000, std=139693.5988, min=39821.4286, max=565704.5455, p01=39972.7866, p99=549750.4545. First five: [{'month': '2017-01', 'lc_spot_mean': 124500.0}, {'month': '2017-02', 'lc_spot_mean': 124500.0}, {'month': '2017-03', 'lc_spot_mean': 124500.0}, {'month': '2017-04', 'lc_spot_mean': 125868.42105263156}, {'month': '2017-05', 'lc_spot_mean': 134880.95238095237}]. Last five: [{'month': '2025-05', 'lc_spot_mean': 63744.73684210526}, {'month': '2025-06', 'lc_spot_mean': 60435.0}, {'month': '2025-07', 'lc_spot_mean': 66634.78260869565}, {'month': '2025-08', 'lc_spot_mean': 78885.71428571429}, {'month': '2025-09', 'lc_spot_mean': 74129.54545454546}].

## 4. Lithium carbonate production

Canonical field: total lithium carbonate actual monthly output, physical tons. Industrial/battery grade and brine/lepidolite/spodumene routes are retained separately. Route differences are reported and never used to overwrite total output.

QA: start=2018-08, end=2025-09, obs=86, missing=0, mean=32143.0930, median=23619.0000, std=21918.1606, min=6390.0000, max=87260.0000, p01=8306.7500, p99=85543.0000. First five: [{'month': '2018-08', 'lc_output_total': 11675.0}, {'month': '2018-09', 'lc_output_total': 11645.0}, {'month': '2018-10', 'lc_output_total': 10785.0}, {'month': '2018-11', 'lc_output_total': 11265.0}, {'month': '2018-12', 'lc_output_total': 11265.0}]. Last five: [{'month': '2025-05', 'lc_output_total': 72080.0}, {'month': '2025-06', 'lc_output_total': 78090.0}, {'month': '2025-07', 'lc_output_total': 81530.0}, {'month': '2025-08', 'lc_output_total': 85240.0}, {'month': '2025-09', 'lc_output_total': 87260.0}].

## 5. Spodumene price

Canonical field: 6% Li2O spodumene concentrate, CIF China, USD/t. The 613 pre-July-2019 zeros are treated as unavailable placeholders. October 2025 is excluded as a partial month.

QA: start=2019-07, end=2025-09, obs=75, missing=0, mean=1778.3608, median=861.5909, std=1701.5092, min=387.5000, max=5504.0909, p01=388.1938, p99=5489.7324. First five: [{'month': '2019-07', 'spodumene_price_mean': 632.6190476190476}, {'month': '2019-08', 'spodumene_price_mean': 611.5909090909091}, {'month': '2019-09', 'spodumene_price_mean': 575.75}, {'month': '2019-10', 'spodumene_price_mean': 540.0}, {'month': '2019-11', 'spodumene_price_mean': 533.3333333333334}]. Last five: [{'month': '2025-05', 'spodumene_price_mean': 706.6842105263158}, {'month': '2025-06', 'spodumene_price_mean': 625.95}, {'month': '2025-07', 'spodumene_price_mean': 706.9130434782609}, {'month': '2025-08', 'spodumene_price_mean': 878.4285714285714}, {'month': '2025-09', 'spodumene_price_mean': 862.3636363636364}].

## 6. Battery installation

Canonical field: China monthly total power-battery installation, GWh, from the China Automotive Power Battery Industry Innovation Alliance. LFP and NCM components are retained for robustness and reconciliation.

QA: start=2020-01, end=2026-02, obs=74, missing=0, mean=30.9058, median=27.7674, std=22.7075, min=0.5981, max=98.1000, p01=1.8527, p99=94.7420. First five: [{'month': '2020-01', 'battery_install_total': 2.3167}, {'month': '2020-02', 'battery_install_total': 0.5981000000000001}, {'month': '2020-03', 'battery_install_total': 2.7701}, {'month': '2020-04', 'battery_install_total': 3.5873000000000004}, {'month': '2020-05', 'battery_install_total': 3.5062}]. Last five: [{'month': '2025-10', 'battery_install_total': 84.1}, {'month': '2025-11', 'battery_install_total': 93.5}, {'month': '2025-12', 'battery_install_total': 98.1}, {'month': '2026-01', 'battery_install_total': 42.0}, {'month': '2026-02', 'battery_install_total': 26.3}].

## 7. Inventory

SMM weekly downstream, smelter, other and total lithium-carbonate inventory covers 2023-06-01 to 2025-10-09. Weekly levels and monthly mean/EOM versions are validation-only.

## 8. Cost and margin

Spodumene-route and lepidolite-route estimated production cost and gross margin cover 2022-10-10 to 2025-10-10. Negative margins are valid loss observations. These series are validation-only.

## 9. Supply-route production

Monthly brine, lepidolite and spodumene-route output is retained from 2018-08 to 2025-09. No recycling route is present.

## 10. Lithium trade

China Customs/SMM import, export and net-import quantities extend through 2025-08. The 2025 observations are supplement candidates. They are not silently appended to the public panel.

## 11. Data definitions and units

The formal definitions and transformations are in `data/metadata/industry_series_dictionary.csv`. The derived `spodumene_cny_t` is USD/t concentrate multiplied by CNY/USD and is not lithium-carbonate production cost.

## 12. Missingness and anomalies

No interpolation or seasonal adjustment was used. Duplicate dates/months are rejected by tests. Zero placeholders, changes above 100%, component differences and possible definition mismatches are flagged for review.

## 13. Monthly aggregation

Daily prices use monthly arithmetic mean for the core field, plus median and last valid observation. Weekly inventory uses monthly mean and EOM. Partial final price months are excluded using the previous 12 months' typical quote count.

## 14. Common core sample

`common_start=2020-01`, `common_end=2025-09`, `common_months=69`. `DATA_GATE=GO`.

## 15. Core-series recommendation

All four core industry variables are rated `A_CORE`. They have explicit definitions, source, units and at least 60 common complete months with USD/CNY.

## 16. Remaining data gaps

| variable | last complete month | missing to 2026-06 |
|---|---|---|
| lc_spot | 2025-09 | 2025-10;2025-11;2025-12;2026-01;2026-02;2026-03;2026-04;2026-05;2026-06 |
| lc_output | 2025-09 | 2025-10;2025-11;2025-12;2026-01;2026-02;2026-03;2026-04;2026-05;2026-06 |
| spodumene_price | 2025-09 | 2025-10;2025-11;2025-12;2026-01;2026-02;2026-03;2026-04;2026-05;2026-06 |
| battery_install | 2026-02 | 2026-03;2026-04;2026-05;2026-06 |

Trade reconciliation results: 54 match, 3 minor difference, 1 material difference and 8 supplement-only months. The material difference is the June 2021 export quantity (about 6.32%); source definitions must be checked before any splice. Capacity and operating-rate series were not found.

## 17. Modeling readiness

The data gate is GO for Phase 1 empirical work. This ingestion task did not run any model or stationarity test.
