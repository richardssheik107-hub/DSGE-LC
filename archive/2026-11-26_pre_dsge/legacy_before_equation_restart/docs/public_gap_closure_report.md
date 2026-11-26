# Public Gap Closure Report

## 1. Scope

This round searched, fetched, verified and reconciled publicly available tail observations through 2026-06. It did not run models, interpolate missing values, infer chart values or convert forecasts into actuals. `data/processed/core_monthly_panel.csv` remains Data Freeze v1 and was not modified.

## 2. Core v1 status

Data Freeze v1 has a complete common sample from 2020-01 through 2025-09 (69 months). The four industry series and USD/CNY have no internal missing observations over that window.

## 3. Battery installation tail

| Month | Total GWh | LFP GWh | NCM GWh | Source status |
|---|---:|---:|---:|---|
| 2026-03 | 56.5 | 45.8 | 10.7 | ACTUAL_OFFICIAL_REPRINT |
| 2026-04 | 62.4 | 50.8 | 11.5 | ACTUAL_OFFICIAL_REPRINT |
| 2026-05 | 71.9 | 58.4 | 13.4 | ACTUAL_OFFICIAL_REPRINT |
| 2026-06 | 76.5 | 63.7 | 12.7 | ACTUAL_OFFICIAL_REPRINT |

All four observations are monthly, not cumulative. Public values for 2026-01 and 2026-02 exactly match the commercial workbook, so the SOURCE_B tail is accepted. The v2 candidate also carries forward the read-only commercial monthly observations for 2025-10 through 2026-02.

## 4. Lithium carbonate output tail

| Month | Value t | Type | Grade | Decision |
|---|---:|---|---|---|
| 2025-10 | 92,260 | ACTUAL | SOURCE_C | REVIEW_REQUIRED |
| 2025-11 | 95,350 | ACTUAL | SOURCE_C | REVIEW_REQUIRED |
| 2025-12 | 99,200 | ACTUAL | SOURCE_C | REVIEW_REQUIRED |
| 2026-01 | 97,900 | ACTUAL | SOURCE_A | ACCEPTED_PUBLIC_PATCH |
| 2026-02 | 83,090 | ACTUAL | SOURCE_A | ACCEPTED_PUBLIC_PATCH |
| 2026-03 | 106,620 | ACTUAL | SOURCE_C | REVIEW_REQUIRED |
| 2026-04 | 110,030 | ACTUAL | SOURCE_C | REVIEW_REQUIRED |
| 2026-05 | 113,295 | ACTUAL | SOURCE_C | REVIEW_REQUIRED |
| 2026-06 | 115,320 | ACTUAL | SOURCE_C | REVIEW_REQUIRED |

The public research table used for 2025-10 through 2025-12 reproduces the commercial 2025-07, 2025-08 and 2025-09 values exactly. This supports its transcription quality, but SOURCE_C observations remain review candidates under the stated patch rule. Forecasts found in contemporaneous reports were not used.

## 5. Lithium carbonate spot tail

SMM public pages explicitly reported matching monthly means for 2025-10 (75,291.18 CNY/t), 2025-11 (86,457.5), 2026-01 (156,000), 2026-02 (149,600) and 2026-03 (156,700). These are accepted as `PUBLIC_REPORTED_MONTHLY_MEAN` and remain distinguishable from historical `DAILY_AGGREGATED` values.

For 2025-12 and 2026-04 through 2026-06, public pages only exposed end-of-month points, ranges or percentage changes. They remain NA in the core candidate. No monthly mean was reverse-calculated.

## 6. Spodumene tail

Only 2026-03 supplied an explicit SMM SC6, CIF China, USD/t monthly mean (2,081.4 USD/t), so it is accepted. October and November 2025 and April and June 2026 are end-of-month or daily points; February 2026 is a daily point; January 2026 is only an approximate monthly mean; May 2026 is a range. These observations are retained for validation or review and do not construct monthly means. The unresolved months require an authorized SMM export.

## 7. Lithium trade

SMM public pages explicitly citing China Customs provide monthly lithium-carbonate import and export quantities for every month from 2025-09 through 2026-06. Units are metric tons. The complete tail is accepted in `public_monthly_panel_v2_candidate.csv`.

The same pages report monthly physical volumes labelled 锂辉石进口量. Because these totals can include concentrate and lower-grade ore, they are stored as `lithium_concentrate_import` review candidates with `definition_match=FALSE`; they are not renamed `spodumene_import` and do not overwrite the commercial series.

## 8. CPI/PPI completion

The seven requested gaps were filled from National Bureau of Statistics releases: CPI 2023-06=0.0%, 2023-09=0.0%, 2025-07=0.0%; PPI 2024-12=-2.3%, 2025-01=-2.3%, 2025-07=-3.6%, 2026-03=+0.5%. Both series now cover all 78 months. Official HTML copies are retained under `data/raw/public/gap_closure/nbs/`.

## 9. China government yield

The ChinaBond official endpoint became reachable. It returned 1,618 daily government-bond curve observations from 2020-01-02 through 2026-06-30 with explicit 0.25Y and 0.50Y nodes and no missing yield values. Monthly arithmetic means cover all 78 months. These are government-bond curve yields, not SHIBOR, DR007, LPR or policy-bank bonds.

## 10. Inventory / margin public supplements

No systematic post-2025-10 inventory, spodumene-route cost or SMM margin series with explicit text/table values and matching definitions was found within this round's limited budget. They remain validation-only and unchanged. No cost or margin was reverse-engineered from spot and ore prices.

## 11. Source quality

SOURCE_A contains NBS releases, ChinaBond responses and SMM public pages. SOURCE_B contains authoritative reproductions of China Automotive Power Battery Industry Innovation Alliance monthly data. SOURCE_C contains formal research reports citing SMM where the original exact public value was not directly accessible. SOURCE_D material was excluded.

Copyright-restricted SMM and media pages were not copied into the repository; their URLs, publication dates, exact references and decisions are preserved in `public_gap_source_manifest.csv`.

## 12. Reconciliation with canonical data

Public SMM-cited output values exactly match canonical values for 2025-07, 2025-08 and 2025-09. Public alliance-cited battery totals exactly match the commercial workbook for 2026-01 and 2026-02. No overlap comparison shows a material difference. Exact overlap does not automatically upgrade SOURCE_C to an accepted patch.

## 13. V2 candidate coverage

The v2 candidate has 78 calendar rows from 2020-01 through 2026-06. Complete five-variable core coverage remains 2020-01 through 2025-09 (69 months), because strict monthly-mean gaps remain in spot and spodumene and SOURCE_C output months remain under review. USD/CNY and battery installation each cover all 78 months; CPI, PPI and both ChinaBond tenors also cover all 78 months in the public candidate.

## 14. Remaining gaps

- `lc_spot`: 2025-12 and 2026-04 through 2026-06.
- `lc_output_total`: 2025-10 through 2025-12 and 2026-03 through 2026-06 remain review candidates; only 2026-01 and 2026-02 are accepted.
- `spodumene_price`: 2025-10 through 2026-02 and 2026-04 through 2026-06.
- `battery_install`: no remaining month through 2026-06.

## 15. Manual / authenticated data still needed

An authorized SMM export is still needed for the unresolved daily-to-monthly spot and SC6 CIF China means. A direct SMM output export or source-owner confirmation is needed before the SOURCE_C output candidates can be promoted. No manual ChinaBond export is now needed.
