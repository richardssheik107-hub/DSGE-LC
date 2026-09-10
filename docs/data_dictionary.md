# Phase 1 data dictionary

| Canonical field | Frequency | Unit | Definition / source rule |
|---|---:|---:|---|
| `battery_install_gwh` | monthly | GWh | China domestic power-battery installation; industry-alliance definition. |
| `nev_sales_units` | monthly | vehicles | CAAM new-energy-vehicle wholesale sales; not passenger retail sales. |
| `nev_production_units` | monthly | vehicles | CAAM new-energy-vehicle production. |
| `usd_cny` | daily | CNY per USD | A value of 7.20 means 1 USD = 7.20 CNY. |
| `usd_cny_mean` / `usd_cny_end` | monthly | CNY per USD | Arithmetic mean / final valid daily observation. |
| `china_gov_3m`, `china_gov_6m`, `china_gov_1y` | daily | percent | China government yield curve at the explicitly named tenor only. |
| `cpi_yoy`, `ppi_yoy` | monthly | percent | National CPI/PPI year-on-year rate; neither is an index level. |
| `lc_import_qty_ton`, `lc_export_qty_ton` | monthly | metric ton | Lithium carbonate physical trade quantity; kilograms must be divided by 1,000. |
| `lc_net_import_ton` | monthly | metric ton | Import quantity minus export quantity. |
| `lc_spot` | daily | CNY/ton | Placeholder: one consistent battery-grade spot series required. |
| `lc_output` | monthly | ton | Placeholder: continuous China lithium-carbonate production required. |
| `spodumene_price` | daily/monthly | source unit | Placeholder: prefer 6% Li2O CIF China concentrate price. |
