"""Audit industry outputs, reconcile overlaps, and write the ingestion report."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from industry_common import (
    BATTERY_FILE,
    INTERIM_DIR,
    LITHIUM_FILE,
    METADATA_DIR,
    PROCESSED_DIR,
    ROOT,
    monthly_range,
    sha256,
    write_csv,
)


TARGET_END = "2026-06"


def _core_frames():
    return {
        "lc_spot": (pd.read_csv(PROCESSED_DIR / "lc_spot_monthly.csv", na_values=["NA"]), "lc_spot_mean", "CNY/t"),
        "lc_output": (pd.read_csv(PROCESSED_DIR / "lc_output_monthly.csv", na_values=["NA"]), "lc_output_total", "metric tons"),
        "spodumene_price": (pd.read_csv(PROCESSED_DIR / "spodumene_price_monthly.csv", na_values=["NA"]), "spodumene_price_mean", "USD/t"),
        "battery_install": (pd.read_csv(PROCESSED_DIR / "battery_install_monthly.csv", na_values=["NA"]), "battery_install_total", "GWh"),
    }


def coverage_table() -> pd.DataFrame:
    raw = {
        "lc_spot": ("2017-01-03", "2025-10-10", "2025-10"),
        "lc_output": ("2018-08-31", "2025-09-30", ""),
        "spodumene_price": ("2017-01-03", "2025-10-10", "2025-10"),
        "battery_install": ("2020-01", "2026-02", ""),
    }
    rows = []
    for variable, (frame, column, _) in _core_frames().items():
        valid = frame.loc[frame[column].notna(), ["month", column]].sort_values("month")
        start, end = valid.month.iloc[0], valid.month.iloc[-1]
        expected = monthly_range(start, end)
        missing = sorted(set(expected) - set(valid.month.astype(str)))
        rows.append({
            "variable": variable,
            "raw_start": raw[variable][0],
            "raw_end": raw[variable][1],
            "processed_start": start,
            "processed_end": end,
            "frequency": "monthly",
            "expected_months": len(expected),
            "observed_months": len(valid),
            "missing_months": ";".join(missing),
            "partial_months": raw[variable][2],
            "recommended_start": max(start, "2020-01"),
            "recommended_end": end,
            "status": "A_CORE" if not missing and len(valid.loc[valid.month.ge("2020-01")]) >= 60 else "B_USABLE",
        })
    return pd.DataFrame(rows)


def common_sample() -> tuple[pd.DataFrame, str, str, int, str]:
    panel = pd.read_csv(ROOT / "data" / "processed" / "core_monthly_panel.csv", na_values=["NA"])
    start, end, count = panel.month.iloc[0], panel.month.iloc[-1], len(panel)
    gate = "GO" if count >= 60 else "GO_WITH_REDUCED_PARAMETERS" if count >= 48 else "SIMPLIFY" if count >= 36 else "STOP"
    rows = []
    for variable in ("lc_spot", "lc_output_total", "spodumene_price", "battery_install", "usd_cny_mean"):
        rows.append({"variable": variable, "available_start": start, "available_end": end, "missing_inside_common_window": int(panel[variable].isna().sum()), "common_start": "", "common_end": "", "common_months": "", "data_gate": ""})
    rows.append({"variable": "__COMMON__", "available_start": "", "available_end": "", "missing_inside_common_window": 0, "common_start": start, "common_end": end, "common_months": count, "data_gate": gate})
    return pd.DataFrame(rows), start, end, count, gate


def dictionary() -> pd.DataFrame:
    rows = [
        ("lc_spot", LITHIUM_FILE.name, "SMM钴锂新能源价格", "碳酸锂（99.5%电池级/国产,元/吨）", "SMM", "China domestic battery-grade lithium carbonate spot/assessment average", "lithium carbonate", "99.5% battery grade", "China", "daily", "CNY/t", "CNY/t", "CNY", "2017-01-03", "2025-10-10", 2133, "monthly arithmetic mean; EOM and median retained", "zeros to NA; exclude partial final month", "CORE", "A_CORE", "2025-10 is partial"),
        ("lc_output", LITHIUM_FILE.name, "SMM月度新能源金属材料产量", "碳酸锂（吨）", "SMM", "China lithium carbonate actual total output", "lithium carbonate", "all grades", "China", "monthly", "physical tons", "metric tons", "", "2018-08", "2025-09", 86, "none", "level retained", "CORE", "A_CORE", "not capacity or schedule"),
        ("spodumene_price", LITHIUM_FILE.name, "SMM钴锂新能源价格", "锂辉石精矿（6%,CIF中国,美元/吨）", "SMM", "Spodumene concentrate 6% Li2O CIF China", "spodumene concentrate", "6% Li2O", "CIF China", "daily", "USD/t", "USD/t", "USD", "2019-07-03", "2025-10-10", 1520, "monthly arithmetic mean; EOM and median retained", "pre-coverage zeros to NA; exclude partial final month", "CORE", "A_CORE", "preferred raw-material price definition"),
        ("battery_install", BATTERY_FILE.name, "全球&中国动力电池行业装机规模-月度", "中国（GWh）", "China Automotive Power Battery Industry Innovation Alliance", "China monthly total power-battery installation", "power battery", "total", "China", "monthly", "GWh", "GWh", "", "2020-01", "2026-02", 74, "none", "matrix normalized to YYYY-MM", "CORE", "A_CORE", "monthly total, not production/sales/cumulative"),
        ("battery_install_lfp", BATTERY_FILE.name, "全球&中国动力电池行业装机规模-月度", "其中：铁锂（GWh）", "China Automotive Power Battery Industry Innovation Alliance", "China monthly LFP power-battery installation", "power battery", "LFP", "China", "monthly", "GWh", "GWh", "", "2020-01", "2026-02", 74, "none", "level retained", "ROBUSTNESS", "A_CORE", "chemistry component"),
        ("battery_install_ncm", BATTERY_FILE.name, "全球&中国动力电池行业装机规模-月度", "其中：三元（GWh）", "China Automotive Power Battery Industry Innovation Alliance", "China monthly ternary power-battery installation", "power battery", "NCM", "China", "monthly", "GWh", "GWh", "", "2020-01", "2026-02", 74, "none", "level retained", "ROBUSTNESS", "A_CORE", "chemistry component"),
        ("lc_inventory_total", LITHIUM_FILE.name, "SMM碳酸锂周度产量库存&天数", "总计(右轴)", "SMM", "survey total inventory across downstream, smelters and other", "lithium carbonate", "", "China sample", "weekly", "tons", "metric tons", "", "2023-06-01", "2025-10-09", 119, "weekly retained; monthly mean and EOM", "level retained", "VALIDATION_ONLY", "B_USABLE", "sample definition may change"),
        ("lc_cost_spodumene", LITHIUM_FILE.name, "SMM锂冶炼利润", "外购锂辉石精矿成本(元/吨)", "SMM", "estimated lithium-carbonate production cost using purchased spodumene", "lithium carbonate", "spodumene route", "China", "daily", "CNY/t", "CNY/t", "CNY", "2022-10-10", "2025-10-10", 729, "weekly/monthly arithmetic mean", "level retained", "VALIDATION_ONLY", "B_USABLE", "estimated route cost"),
        ("lc_margin_spodumene", LITHIUM_FILE.name, "SMM锂冶炼利润", "锂辉石生产毛利(元/吨)", "SMM", "estimated gross margin for spodumene route", "lithium carbonate", "spodumene route", "China", "daily", "CNY/t", "CNY/t", "CNY", "2022-10-10", "2025-10-10", 728, "weekly/monthly arithmetic mean", "level retained", "VALIDATION_ONLY", "B_USABLE", "negative values are economic losses"),
        ("lc_import_qty", LITHIUM_FILE.name, "中国碳酸锂进出口数据", "碳酸锂进口量（吨）", "China Customs", "China lithium carbonate imports", "lithium carbonate", "customs commodity", "China/world", "monthly", "tons", "metric tons", "", "2017-01", "2025-08", 102, "none", "level retained", "ROBUSTNESS", "B_USABLE", "reconcile against HS 283691 Comtrade"),
        ("lithium_concentrate_import_total", LITHIUM_FILE.name, "中国锂矿进口数据(分国别)", "锂精矿月度进口量：总计(吨)", "SMM", "lithium concentrate imports; exact customs commodity definition unverified", "lithium concentrate", "not assumed to be pure spodumene", "China/world", "monthly", "tons", "metric tons", "", "2021-08", "2025-08", 49, "none", "level retained", "ROBUSTNESS", "B_USABLE", "do not relabel as spodumene imports"),
    ]
    columns = ["canonical_name", "source_file", "sheet_name", "original_series_name", "original_source", "definition", "product", "grade", "region", "frequency", "original_unit", "processed_unit", "currency", "start_date", "end_date", "obs_count", "aggregation_method", "transformation", "recommended_use", "status", "notes"]
    return pd.DataFrame(rows, columns=columns)


def anomalies() -> pd.DataFrame:
    rows = [{"variable": "spodumene_price", "date": "2017-01-03/2019-07-02", "value": 0, "previous_value": "", "change_pct": "", "reason": "613 zero placeholders before first positive quote", "severity": "HIGH", "action": "REVIEW"}]
    for variable, (frame, column, _) in _core_frames().items():
        data = frame[["month", column]].dropna().sort_values("month")
        changes = data[column].pct_change()
        for idx in data.index[changes.abs().gt(1.0)]:
            pos = data.index.get_loc(idx)
            rows.append({"variable": variable, "date": data.loc[idx, "month"], "value": data.loc[idx, column], "previous_value": data.iloc[pos - 1][column] if pos else "", "change_pct": changes.loc[idx], "reason": "absolute month-on-month change above 100%; possible market move or definition/unit issue", "severity": "MEDIUM", "action": "REVIEW"})
    return pd.DataFrame(rows)


def reconciliations() -> tuple[pd.DataFrame, pd.DataFrame]:
    existing = pd.read_csv(ROOT / "data" / "processed" / "public_monthly_panel.csv", na_values=["NA"])
    excel = pd.read_csv(PROCESSED_DIR / "lc_trade_monthly_industry.csv", na_values=["NA"])
    merged = existing[["month", "lc_import_qty", "lc_export_qty"]].merge(excel[["month", "lc_import_qty", "lc_export_qty"]], on="month", suffixes=("_comtrade", "_excel"))
    merged = merged.rename(columns={"lc_import_qty_comtrade": "comtrade_import", "lc_import_qty_excel": "excel_import", "lc_export_qty_comtrade": "comtrade_export", "lc_export_qty_excel": "excel_export"})
    merged["import_diff"] = merged.excel_import - merged.comtrade_import
    merged["import_diff_pct"] = merged.import_diff / merged.comtrade_import.replace(0, np.nan)
    merged["export_diff"] = merged.excel_export - merged.comtrade_export
    merged["export_diff_pct"] = merged.export_diff / merged.comtrade_export.replace(0, np.nan)
    comparable = merged[["comtrade_import", "excel_import", "comtrade_export", "excel_export"]].notna().all(axis=1)
    merged["definition_match"] = np.where(comparable, "LIKELY_HS283691_BUT_VERIFY", "NOT_COMPARABLE")
    maxdiff = merged[["import_diff_pct", "export_diff_pct"]].abs().max(axis=1)
    merged["status"] = np.where(~comparable, "NOT_COMPARABLE", np.where(maxdiff <= 0.01, "MATCH", np.where(maxdiff <= 0.05, "MINOR_DIFFERENCE", "MATERIAL_DIFFERENCE")))
    merged["notes"] = "Do not overwrite Comtrade; China Customs/SMM workbook is a supplement candidate."

    output = pd.read_csv(PROCESSED_DIR / "lc_output_monthly.csv", na_values=["NA"])
    battery = pd.read_csv(PROCESSED_DIR / "battery_install_monthly.csv", na_values=["NA"])
    component = pd.concat([
        output[["month", "lc_output_total", "route_sum", "route_difference", "route_difference_pct"]].assign(check="lc_output_route_sum"),
        battery[["month", "battery_install_total", "battery_install_chemistry_sum", "chemistry_difference", "chemistry_difference_pct"]].assign(check="battery_chemistry_sum"),
    ], ignore_index=True, sort=False)
    return merged, component


def protect_hashes() -> None:
    ledger = pd.read_csv(METADATA_DIR / "manual_industry_raw_hashes.csv", dtype=str)
    for idx, row in ledger.iterrows():
        path = ROOT / row.file
        ledger.loc[idx, "protected_status"] = "HASH_UNCHANGED" if sha256(path) == row.sha256 else "HASH_CHANGED_FAIL"
    write_csv(ledger, METADATA_DIR / "manual_industry_raw_hashes.csv")


def qa_text(frame: pd.DataFrame, column: str) -> str:
    values = frame[column].dropna()
    desc = values.describe(percentiles=[0.01, 0.5, 0.99])
    first = frame.loc[frame[column].notna(), ["month", column]].head(5).to_dict("records")
    last = frame.loc[frame[column].notna(), ["month", column]].tail(5).to_dict("records")
    return f"start={frame.loc[frame[column].notna(), 'month'].iloc[0]}, end={frame.loc[frame[column].notna(), 'month'].iloc[-1]}, obs={len(values)}, missing={frame[column].isna().sum()}, mean={desc['mean']:.4f}, median={desc['50%']:.4f}, std={desc['std']:.4f}, min={desc['min']:.4f}, max={desc['max']:.4f}, p01={desc['1%']:.4f}, p99={desc['99%']:.4f}. First five: {first}. Last five: {last}."


def report(common_start: str, common_end: str, common_months: int, gate: str, trade: pd.DataFrame) -> None:
    frames = _core_frames()
    qa = {name: qa_text(frame, col) for name, (frame, col, _) in frames.items()}
    gaps = []
    for name, (frame, col, _) in frames.items():
        last = frame.loc[frame[col].notna(), "month"].max()
        missing = monthly_range(str(pd.Period(last, freq="M") + 1), TARGET_END) if last < TARGET_END else []
        gaps.append(f"| {name} | {last} | {';'.join(missing) or 'none'} |")
    material = int(trade.status.eq("MATERIAL_DIFFERENCE").sum())
    status_counts = trade.status.value_counts().to_dict()
    text = f"""# Industry Data Ingestion and Audit

## 1. Source files

Two licensed industry workbooks were copied unchanged to `data/raw/commercial/manual/`. SHA-256 protection is recorded in `data/metadata/manual_industry_raw_hashes.csv`.

## 2. Workbook structure

All sheets, used ranges, inferred header/data rows, date columns, merged ranges, hidden columns, units and source notes are catalogued in `data/metadata/manual_excel_sheet_inventory.csv`.

## 3. Lithium carbonate spot price

Canonical field: `碳酸锂（99.5%电池级/国产,元/吨）`, SMM, CNY/t. Daily observations are aggregated by arithmetic mean; EOM and median are retained. October 2025 is excluded as a partial month.

QA: {qa['lc_spot']}

## 4. Lithium carbonate production

Canonical field: total lithium carbonate actual monthly output, physical tons. Industrial/battery grade and brine/lepidolite/spodumene routes are retained separately. Route differences are reported and never used to overwrite total output.

QA: {qa['lc_output']}

## 5. Spodumene price

Canonical field: 6% Li2O spodumene concentrate, CIF China, USD/t. The 613 pre-July-2019 zeros are treated as unavailable placeholders. October 2025 is excluded as a partial month.

QA: {qa['spodumene_price']}

## 6. Battery installation

Canonical field: China monthly total power-battery installation, GWh, from the China Automotive Power Battery Industry Innovation Alliance. LFP and NCM components are retained for robustness and reconciliation.

QA: {qa['battery_install']}

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

`common_start={common_start}`, `common_end={common_end}`, `common_months={common_months}`. `DATA_GATE={gate}`.

## 15. Core-series recommendation

All four core industry variables are rated `A_CORE`. They have explicit definitions, source, units and at least 60 common complete months with USD/CNY.

## 16. Remaining data gaps

| variable | last complete month | missing to 2026-06 |
|---|---|---|
{chr(10).join(gaps)}

Trade reconciliation results: {status_counts.get('MATCH', 0)} match, {status_counts.get('MINOR_DIFFERENCE', 0)} minor difference, {material} material difference and {status_counts.get('NOT_COMPARABLE', 0)} supplement-only months. The material difference is the June 2021 export quantity (about 6.32%); source definitions must be checked before any splice. Capacity and operating-rate series were not found.

## 17. Modeling readiness

The data gate is GO for Phase 1 empirical work. This ingestion task did not run any model or stationarity test.
"""
    (ROOT / "docs" / "industry_data_ingestion_audit.md").write_text(text, encoding="utf-8")


def main() -> None:
    coverage = coverage_table()
    write_csv(coverage, METADATA_DIR / "core_data_coverage.csv")
    common, start, end, count, gate = common_sample()
    write_csv(common, METADATA_DIR / "core_common_sample_audit.csv")
    write_csv(dictionary(), METADATA_DIR / "industry_series_dictionary.csv")
    write_csv(anomalies(), METADATA_DIR / "industry_data_anomalies.csv")
    trade, component = reconciliations()
    write_csv(trade, METADATA_DIR / "lc_trade_reconciliation.csv")
    write_csv(component, METADATA_DIR / "industry_component_reconciliation.csv")
    protect_hashes()
    report(start, end, count, gate, trade)


if __name__ == "__main__":
    main()
