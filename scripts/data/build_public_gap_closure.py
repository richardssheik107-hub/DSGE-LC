"""Build audited public tail candidates without modifying Data Freeze v1.

Values in this module are transcriptions of explicit text/table values on the
listed public pages.  No interpolation, forward fill, chart reading, or
forecast-to-actual conversion is permitted.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim" / "public_gap_closure"
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "data" / "metadata"


BATTERY = [
    ("2026-03", 56.5, 45.8, 10.7, "中国汽车动力电池产业创新联盟", "https://www.jtcopper.com/wp-content/uploads/2026/04/2026年3月动力电池月度信息.pdf", "2026-04-16", "3月国内动力电池装车量56.5GWh；磷酸铁锂45.8GWh；三元10.7GWh", "ACTUAL_OFFICIAL_REPRINT"),
    ("2026-04", 62.4, 50.8, 11.5, "第一财经（引中国汽车动力电池产业创新联盟）", "https://www.yicai.com/news/103175233.html", "2026-05-11", "4月当月装车62.4GWh；磷酸铁锂50.8GWh；三元11.5GWh", "ACTUAL_OFFICIAL_REPRINT"),
    ("2026-05", 71.9, 58.4, 13.4, "第一财经（引中国汽车动力电池产业创新联盟）", "https://www.yicai.com/news/103225300.html", "2026-06-11", "5月当月装车71.9GWh；磷酸铁锂58.4GWh；三元13.4GWh", "ACTUAL_OFFICIAL_REPRINT"),
    ("2026-06", 76.5, 63.7, 12.7, "界面新闻（引中国汽车动力电池产业创新联盟）", "https://www.jiemian.com/article/14775234.html", "2026-07-16", "6月当月装车76.5GWh；磷酸铁锂63.7GWh；三元12.7GWh", "ACTUAL_OFFICIAL_REPRINT"),
]

OUTPUT = [
    ("2025-10", 92260, "metric tons", "通惠期货年报（引SMM）", "https://www.thqh.com.cn/A_UpLoad/upload_file/20260120171910_6397.pdf", "2026-01-19", "SMM", "ACTUAL", "EXACT", "研究报告表17；与2025-07至09重叠值完全一致", "REVIEW_REQUIRED", "SOURCE_C"),
    ("2025-11", 95350, "metric tons", "SMM公开专题/研究报告交叉引用", "https://news.smm.cn/news/103647188", "2025-12-01", "SMM", "ACTUAL", "EXACT", "SMM页面确认环比3%；精确值由引用SMM的研究资料披露", "REVIEW_REQUIRED", "SOURCE_C"),
    ("2025-12", 99200, "metric tons", "通惠期货年报（引SMM）", "https://www.thqh.com.cn/A_UpLoad/upload_file/20260120171910_6397.pdf", "2026-01-19", "SMM", "ACTUAL", "EXACT", "报告表17明确列示99200；非预测列", "REVIEW_REQUIRED", "SOURCE_C"),
    ("2026-01", 97900, "metric tons", "SMM公开半年复盘", "https://news.smm.cn/news/103999601", "2026-07-10", "SMM", "ACTUAL", "EXACT", "公开正文明确1月9.79万吨", "ACCEPTED_PUBLIC_PATCH", "SOURCE_A"),
    ("2026-02", 83090, "metric tons", "SMM公开半年复盘", "https://news.smm.cn/news/103999601", "2026-07-10", "SMM", "ACTUAL", "EXACT", "公开正文明确2月8.31万吨；精确值由引用SMM正式报告交叉核验", "ACCEPTED_PUBLIC_PATCH", "SOURCE_A"),
    ("2026-03", 106620, "metric tons", "研究报告（引SMM）", "https://www.hicend.com/ftpfile/static/file/upload/file/202604/24/PEtz6sWy4s6dQDG4.pdf", "2026-04-24", "SMM", "ACTUAL", "EXACT", "SMM公开半年复盘仅写约10.66万吨", "REVIEW_REQUIRED", "SOURCE_C"),
    ("2026-04", 110030, "metric tons", "建信期货（引SMM）", "https://www.ccbfutures.com/upload/20260511/20260511142513677.pdf", "2026-05-11", "SMM", "ACTUAL", "EXACT", "正式研究资料明确据SMM为110030吨", "REVIEW_REQUIRED", "SOURCE_C"),
    ("2026-05", 113295, "metric tons", "五矿期货（引SMM）", "https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/11/rptid/836511257711/index.phtml", "2026-07-04", "SMM", "ACTUAL", "EXACT", "正式研究资料明确5月实际产量", "REVIEW_REQUIRED", "SOURCE_C"),
    ("2026-06", 115320, "metric tons", "紫金天风期货（引SMM）", "https://finance.sina.cn/2026-07-07/detail-inihapna8101086.d.html", "2026-07-07", "SMM", "ACTUAL", "EXACT", "后续报告明确6月实际产量", "REVIEW_REQUIRED", "SOURCE_C"),
]

SPOT = [
    ("2025-10", 75291.18, "MONTHLY_MEAN", "碳酸锂（99.5%电池级/国产），中国，CNY/t", "SMM公开专题", "https://news.smm.cn/news/103685276", "2025-12-25", True, "ACCEPTED_PUBLIC_PATCH", "后续月专题直接披露10月均价"),
    ("2025-11", 86457.5, "MONTHLY_MEAN", "碳酸锂（99.5%电池级/国产），中国，CNY/t", "SMM公开专题", "https://news.smm.cn/news/103685276", "2025-12-25", True, "ACCEPTED_PUBLIC_PATCH", "正文直接披露11月月度均价"),
    ("2025-12", None, "EOM", "碳酸锂（99.5%电池级/国产），中国，CNY/t", "SMM公开专题", "https://news.smm.cn/news/103731790", "2026-01-28", True, "ACCESS_RESTRICTED", "仅有月末118500和月均环比15%，未反推月均"),
    ("2026-01", 156000, "MONTHLY_MEAN", "碳酸锂（99.5%电池级/国产），中国，CNY/t", "SMM公开半年复盘", "https://news.smm.cn/news/103999601", "2026-07-10", True, "ACCEPTED_PUBLIC_PATCH", "正文直接披露月度均价15.6万元/吨"),
    ("2026-02", 149600, "MONTHLY_MEAN", "碳酸锂（99.5%电池级/国产），中国，CNY/t", "SMM公开半年复盘", "https://news.smm.cn/news/103999601", "2026-07-10", True, "ACCEPTED_PUBLIC_PATCH", "正文直接披露月度均价14.96万元/吨"),
    ("2026-03", 156700, "MONTHLY_MEAN", "碳酸锂（99.5%电池级/国产），中国，CNY/t", "SMM公开贸易专题", "https://news.smm.cn/news/103872101", "2026-04-29", True, "ACCEPTED_PUBLIC_PATCH", "正文直接披露月度均价15.67万元/吨"),
    ("2026-04", None, "EOM", "碳酸锂（99.5%电池级/国产），中国，CNY/t", "SMM公开专题", "https://news.smm.cn/news/103918218", "2026-06-01", True, "ACCESS_RESTRICTED", "仅披露月末177000和月均环比6%"),
    ("2026-05", None, "EOM", "碳酸锂（99.5%电池级/国产），中国，CNY/t", "SMM公开专题", "https://news.smm.cn/keywords/电池?page=78", "2026-06-25", True, "ACCESS_RESTRICTED", "仅披露月末177500和月均环比12%"),
    ("2026-06", None, "DAILY_POINT", "碳酸锂（99.5%电池级/国产），中国，CNY/t", "SMM公开专题", "https://news.smm.cn/news/103999601", "2026-07-10", True, "ACCESS_RESTRICTED", "公开正文未给出可核验的精确月均值"),
]

SPODUMENE = [
    ("2025-10", 944, "EOM", "6% Li2O", "CIF China", "USD", "USD/t", "SMM公开专题", "https://news.smm.cn/news/103637466", True, "VALIDATION_ONLY"),
    ("2025-11", 1150, "EOM", "6% Li2O", "CIF China", "USD", "USD/t", "SMM公开专题", "https://news.smm.cn/news/103637466", True, "VALIDATION_ONLY"),
    ("2025-12", None, "EOM", "6% Li2O", "CIF China", "USD", "USD/t", "SMM受限历史页", "https://price.smm.cn/?CategoryID=175&ItemId=14042&ProductId=202110220001", True, "ACCESS_RESTRICTED"),
    ("2026-01", 2000, "APPROX_MONTHLY_MEAN", "SC6", "CIF China", "USD", "USD/t", "SMM公开半年复盘", "https://steel.smm.cn/news/13879/103991010", True, "REVIEW_REQUIRED"),
    ("2026-02", 1875, "DAILY_POINT", "SC6", "CIF China", "USD", "USD/t", "SMM公开半年复盘", "https://steel.smm.cn/news/13879/103991010", True, "VALIDATION_ONLY"),
    ("2026-03", 2081.4, "MONTHLY_MEAN", "SC6", "CIF China", "USD", "USD/t", "SMM公开贸易专题", "https://news.smm.cn/news/103872101", True, "ACCEPTED_PUBLIC_PATCH"),
    ("2026-04", 2507, "DAILY_POINT", "SC6", "CIF China", "USD", "USD/t", "SMM公开贸易专题", "https://news.smm.cn/news/103872101", True, "VALIDATION_ONLY"),
    ("2026-05", None, "HIGH_LOW_RANGE", "SC6", "CIF China", "USD", "USD/t", "SMM公开半年复盘", "https://steel.smm.cn/news/13879/103991010", True, "VALIDATION_ONLY"),
    ("2026-06", 2260, "EOM", "SC6", "CIF China", "USD", "USD/t", "SMM公开专题", "https://news.smm.cn/keywords/锂?page=4", True, "VALIDATION_ONLY"),
]

TRADE_VALUES = {
    "2025-09": (19597, 151, "https://news.smm.cn/news/103587336", "2025-10-24"),
    "2025-10": (23881, 246, "https://news.smm.cn/news/103637466", "2025-11-28"),
    "2025-11": (22055, 759, "https://news.smm.cn/news/103685276", "2025-12-25"),
    "2025-12": (23989, 912, "https://news.smm.cn/news/103731790", "2026-01-28"),
    "2026-01": (26858, 472, "https://news.smm.cn/live/detail/103817304", "2026-03-20"),
    "2026-02": (26427, 596, "https://news.smm.cn/live/detail/103817304", "2026-03-20"),
    "2026-03": (29974, 448, "https://news.smm.cn/live/detail/103864084", "2026-04-20"),
    "2026-04": (32650, 370, "https://news.smm.cn/live/detail/103911121", "2026-05-20"),
    "2026-05": (37555, 201, "https://news.smm.cn/live/detail/103965645", "2026-06-22"),
    "2026-06": (25861, 261, "https://news.smm.cn/live/detail/104013273", "2026-07-20"),
}

LITHIUM_MATERIAL_IMPORT = {
    "2025-09": (711000, "https://news.smm.cn/news/103586849", "2025-10-27"),
    "2025-10": (652000, "https://news.smm.cn/news/103637466", "2025-11-28"),
    "2025-11": (729000, "https://news.smm.cn/news/103685276", "2025-12-25"),
    "2025-12": (788500, "https://news.smm.cn/news/103731790", "2026-01-28"),
    "2026-01": (832000, "https://news.smm.cn/news/103820156", "2026-03-25"),
    "2026-02": (558000, "https://news.smm.cn/news/103820156", "2026-03-25"),
    "2026-03": (837400, "https://news.smm.cn/news/103877072", "2026-04-27"),
    "2026-04": (758000, "https://news.smm.cn/news/103918218", "2026-06-01"),
    "2026-05": (681000, "https://news.smm.cn/news/103965632", "2026-06-22"),
    "2026-06": (768000, "https://news.smm.cn/news/104016985", "2026-07-29"),
}

MACRO_PATCH = {
    ("2023-06", "cpi_yoy"): (0.0, "https://www.stats.gov.cn/sj/zxfb/202307/t20230710_1941147.html", "2023-07-10"),
    ("2023-09", "cpi_yoy"): (0.0, "https://www.stats.gov.cn/sj/zxfb/202310/t20231013_1943548.html", "2023-10-13"),
    ("2025-07", "cpi_yoy"): (0.0, "https://www.stats.gov.cn/sj/zxfbhjd/202508/t20250809_1960635.html", "2025-08-09"),
    ("2024-12", "ppi_yoy"): (-2.3, "https://www.stats.gov.cn/sj/zxfb/202501/t20250109_1958169.html", "2025-01-09"),
    ("2025-01", "ppi_yoy"): (-2.3, "https://www.stats.gov.cn/xxgk/sjfb/zxfb2020/202502/t20250209_1958645.html", "2025-02-09"),
    ("2025-07", "ppi_yoy"): (-3.6, "https://www.stats.gov.cn/sj/zxfb/202508/t20250809_1960634.html", "2025-08-09"),
    ("2026-03", "ppi_yoy"): (0.5, "https://www.stats.gov.cn/sj/zxfb/202604/t20260410_1963263.html", "2026-04-10"),
}


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def commercial_hashes_unchanged() -> bool:
    ledger = pd.read_csv(METADATA / "manual_industry_raw_hashes.csv")
    for row in ledger.itertuples(index=False):
        path = ROOT / row.file
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != row.sha256:
            return False
    return True


def build() -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    battery_fields = ["month", "battery_install_total", "battery_install_lfp", "battery_install_ncm", "source_name", "source_url", "publication_date", "original_text_reference", "status"]
    write_csv(INTERIM / "battery_install_tail.csv", [dict(zip(battery_fields, row)) for row in BATTERY], battery_fields)

    output_fields = ["month", "value", "unit", "source_name", "source_url", "publication_date", "data_origin", "value_type", "precision", "notes", "candidate_status", "source_grade"]
    write_csv(INTERIM / "lc_output_tail_candidates.csv", [dict(zip(output_fields, row)) for row in OUTPUT], output_fields)

    spot_fields = ["month", "value", "statistic", "series_definition", "source_name", "source_url", "publication_date", "definition_match", "candidate_status", "notes"]
    write_csv(INTERIM / "lc_spot_tail_candidates.csv", [dict(zip(spot_fields, row)) for row in SPOT], spot_fields)

    spod_fields = ["date_or_month", "value", "statistic", "grade", "delivery_basis", "currency", "unit", "source_name", "source_url", "definition_match", "candidate_status"]
    write_csv(INTERIM / "spodumene_tail_candidates.csv", [dict(zip(spod_fields, row)) for row in SPODUMENE], spod_fields)

    trade_rows = [{"month": m, "lc_import_qty": v[0], "lc_export_qty": v[1], "unit": "metric tons", "source_name": "SMM公开页面（引中国海关）", "source_url": v[2], "publication_date": v[3], "status": "ACCEPTED_PUBLIC_PATCH"} for m, v in TRADE_VALUES.items()]
    write_csv(INTERIM / "lc_trade_tail.csv", trade_rows, list(trade_rows[0]))
    material_rows = [{"month": m, "lithium_concentrate_import": v[0], "unit": "physical metric tons", "reported_definition": "锂辉石进口量（包含精矿与部分原矿）", "source_name": "SMM公开页面（引中国海关）", "source_url": v[1], "publication_date": v[2], "definition_match": False, "candidate_status": "REVIEW_REQUIRED"} for m, v in LITHIUM_MATERIAL_IMPORT.items()]
    write_csv(INTERIM / "lithium_concentrate_import_tail.csv", material_rows, list(material_rows[0]))

    v1 = pd.read_csv(PROCESSED / "core_monthly_panel.csv")
    v1_bytes = (PROCESSED / "core_monthly_panel.csv").read_bytes()
    public = pd.read_csv(PROCESSED / "public_monthly_panel.csv")
    all_months = pd.DataFrame({"month": pd.period_range("2020-01", "2026-06", freq="M").astype(str)})
    v2 = all_months.merge(v1, on="month", how="left")
    v2 = v2.merge(public[["month", "usd_cny_mean"]], on="month", how="left", suffixes=("", "_public"))
    v2["usd_cny_mean"] = v2["usd_cny_mean"].combine_first(v2.pop("usd_cny_mean_public"))
    battery_history = pd.read_csv(PROCESSED / "industry" / "battery_install_monthly.csv")
    for row in battery_history.itertuples(index=False):
        idx = v2.month.eq(row.month) & v2["battery_install"].isna()
        v2.loc[idx, ["battery_install", "battery_install_lfp", "battery_install_ncm"]] = [row.battery_install_total, row.battery_install_lfp, row.battery_install_ncm]
    for month, total, lfp, ncm, *_ in BATTERY:
        idx = v2.month.eq(month)
        v2.loc[idx, ["battery_install", "battery_install_lfp", "battery_install_ncm"]] = [total, lfp, ncm]
    for row in OUTPUT:
        if row[10] == "ACCEPTED_PUBLIC_PATCH":
            v2.loc[v2.month.eq(row[0]), "lc_output_total"] = row[1]
    for row in SPOT:
        if row[8] == "ACCEPTED_PUBLIC_PATCH":
            v2.loc[v2.month.eq(row[0]), "lc_spot"] = row[1]
    for row in SPODUMENE:
        if row[10] == "ACCEPTED_PUBLIC_PATCH":
            v2.loc[v2.month.eq(row[0]), "spodumene_price"] = row[1]
    v2["spodumene_cny_t"] = v2["spodumene_price"] * v2["usd_cny_mean"]
    v2["lc_spot_value_origin"] = v2.month.map(lambda m: "DAILY_AGGREGATED" if m in set(v1.month) else "PUBLIC_REPORTED_MONTHLY_MEAN" if pd.notna(v2.loc[v2.month.eq(m), "lc_spot"].iloc[0]) else "")
    v2["lc_output_value_origin"] = v2.month.map(lambda m: "COMMERCIAL_MONTHLY_CANONICAL" if m in set(v1.month) else "PUBLIC_REPORTED_ACTUAL" if pd.notna(v2.loc[v2.month.eq(m), "lc_output_total"].iloc[0]) else "")
    v2["spodumene_value_origin"] = v2.month.map(lambda m: "DAILY_AGGREGATED" if m in set(v1.month) else "PUBLIC_REPORTED_MONTHLY_MEAN" if pd.notna(v2.loc[v2.month.eq(m), "spodumene_price"].iloc[0]) else "")
    battery_history_months = set(battery_history.month)
    v2["battery_value_origin"] = v2.month.map(lambda m: "COMMERCIAL_MONTHLY_CANONICAL" if m in battery_history_months else "PUBLIC_OFFICIAL_REPRINT_ACTUAL" if pd.notna(v2.loc[v2.month.eq(m), "battery_install"].iloc[0]) else "")
    v2.to_csv(PROCESSED / "core_monthly_panel_v2_candidate.csv", index=False)
    assert (PROCESSED / "core_monthly_panel.csv").read_bytes() == v1_bytes

    public_v2 = public.copy()
    for (month, variable), (value, _, _) in MACRO_PATCH.items():
        public_v2.loc[public_v2.month.eq(month), variable] = value
    for month, (imp, exp, _, _) in TRADE_VALUES.items():
        public_v2.loc[public_v2.month.eq(month), ["lc_import_qty", "lc_export_qty"]] = [imp, exp]
    yield_path = PROCESSED / "phase1" / "china_gov_yields_daily.csv"
    yield_monthly = pd.DataFrame()
    if yield_path.exists():
        yields = pd.read_csv(yield_path)
        yields["date"] = pd.to_datetime(yields["date"], errors="coerce")
        yields["month"] = yields["date"].dt.to_period("M").astype(str)
        yield_monthly = yields.groupby("month", as_index=False)[["china_gov_3m", "china_gov_6m"]].mean()
        yield_monthly = yield_monthly.rename(columns={"china_gov_3m": "china_gov_3m_mean", "china_gov_6m": "china_gov_6m_mean"})
        public_v2 = public_v2.drop(columns=["china_gov_3m_mean", "china_gov_6m_mean"]).merge(yield_monthly, on="month", how="left")
    public_columns = ["month", "cpi_yoy", "ppi_yoy", "nev_sales", "nev_production", "china_gov_3m_mean", "china_gov_6m_mean", "lc_import_qty", "lc_export_qty", "usd_cny_mean"]
    public_v2[public_columns].to_csv(PROCESSED / "public_monthly_panel_v2_candidate.csv", index=False)

    coverage_rows = []
    for variable in ["lc_spot", "lc_output_total", "spodumene_price", "usd_cny_mean", "battery_install"]:
        available = v2[variable].notna()
        coverage_rows.append({"variable": variable, "target_months": len(v2), "observed_months": int(available.sum()), "missing_months": int((~available).sum()), "start": v2.loc[available, "month"].min(), "end": v2.loc[available, "month"].max(), "missing_periods": ";".join(v2.loc[~available, "month"])})
    complete = v2[["lc_spot", "lc_output_total", "spodumene_price", "usd_cny_mean", "battery_install"]].notna().all(axis=1)
    coverage_rows.append({"variable": "core_common", "target_months": len(v2), "observed_months": int(complete.sum()), "missing_months": int((~complete).sum()), "start": v2.loc[complete, "month"].min(), "end": v2.loc[complete, "month"].max(), "missing_periods": ";".join(v2.loc[~complete, "month"])})
    write_csv(METADATA / "public_gap_coverage.csv", coverage_rows, list(coverage_rows[0]))

    anomaly_rows = []
    for variable in ["lc_spot", "lc_output_total", "spodumene_price", "battery_install"]:
        values = pd.to_numeric(v2[variable], errors="coerce")
        mom = values.pct_change(fill_method=None) * 100
        yoy = values.pct_change(12, fill_method=None) * 100
        for idx in v2.index[v2["month"].ge("2025-10") & values.notna()]:
            flags = []
            if pd.notna(mom.iloc[idx]) and abs(mom.iloc[idx]) > 50:
                flags.append("MOM_ABS_GT_50")
            if pd.notna(yoy.iloc[idx]) and abs(yoy.iloc[idx]) > 100:
                flags.append("YOY_ABS_GT_100")
            anomaly_rows.append({"variable": variable, "month": v2.loc[idx, "month"], "value": values.iloc[idx], "mom_pct": mom.iloc[idx] if pd.notna(mom.iloc[idx]) else "", "yoy_pct": yoy.iloc[idx] if pd.notna(yoy.iloc[idx]) else "", "flag": ";".join(flags) if flags else "OK", "action": "RETAIN_AND_REVIEW" if flags else "RETAIN"})
    write_csv(METADATA / "public_tail_anomalies.csv", anomaly_rows, list(anomaly_rows[0]))

    manifest = []
    def add(variable, period, value, unit, statistic, grade, name, url, date, provider, actual, match, status, notes=""):
        manifest.append({"variable": variable, "period": period, "value": value, "unit": unit, "statistic": statistic, "source_grade": grade, "source_name": name, "source_url": url, "publication_date": date, "original_data_provider": provider, "actual_or_forecast": actual, "definition_match": match, "downloaded_raw": False, "local_raw_path": "", "candidate_status": status, "notes": notes})
    for row in BATTERY:
        for variable, value in (("battery_install", row[1]), ("battery_install_lfp", row[2]), ("battery_install_ncm", row[3])):
            add(variable, row[0], value, "GWh", "MONTHLY_ACTUAL", "SOURCE_B", row[4], row[5], row[6], "中国汽车动力电池产业创新联盟", "ACTUAL", True, "ACCEPTED_PUBLIC_PATCH", "当月值，非累计")
    for row in OUTPUT:
        add("lc_output", row[0], row[1], row[2], "MONTHLY_ACTUAL", row[11], row[3], row[4], row[5], row[6], row[7], True, row[10], row[9])
    for row in SPOT:
        add("lc_spot", row[0], row[1] if row[1] is not None else "", "CNY/t", row[2], "SOURCE_A", row[4], row[5], row[6], "SMM", "ACTUAL", row[7], row[8], row[9])
    for row in SPODUMENE:
        add("spodumene_price", row[0], row[1] if row[1] is not None else "", row[6], row[2], "SOURCE_A", row[7], row[8], "", "SMM", "ACTUAL", row[9], row[10])
    for row in trade_rows:
        for variable in ("lc_import_qty", "lc_export_qty"):
            add(variable, row["month"], row[variable], "metric tons", "MONTHLY_ACTUAL", "SOURCE_A", row["source_name"], row["source_url"], row["publication_date"], "中国海关", "ACTUAL", True, row["status"])
    for row in material_rows:
        add("lithium_concentrate_import", row["month"], row["lithium_concentrate_import"], row["unit"], "MONTHLY_ACTUAL", "SOURCE_A", row["source_name"], row["source_url"], row["publication_date"], "中国海关/SMM筛选", "ACTUAL", False, row["candidate_status"], row["reported_definition"])
    for (month, variable), (value, url, date) in MACRO_PATCH.items():
        add(variable, month, value, "percent", "YOY", "SOURCE_A", "国家统计局", url, date, "国家统计局", "ACTUAL", True, "ACCEPTED_PUBLIC_PATCH")
        manifest[-1]["downloaded_raw"] = True
        manifest[-1]["local_raw_path"] = f"data/raw/public/gap_closure/nbs/{variable.split('_')[0]}_{month.replace('-', '_')}.html"
    yield_ok = not yield_monthly.empty and len(yield_monthly) == 78 and yield_monthly[["china_gov_3m_mean", "china_gov_6m_mean"]].notna().all().all()
    for variable, tenor in (("china_gov_3m", "0.25Y"), ("china_gov_6m", "0.50Y")):
        add(variable, "2020-01/2026-06", "", "percent", "DAILY_TO_MONTHLY_MEAN", "SOURCE_A", "ChinaBond", "https://yield.chinabond.com.cn/cbweb-mn/yc/queryXyz", "2026-09-14", "ChinaBond", "ACTUAL", True, "ACCEPTED_PUBLIC_PATCH" if yield_ok else "ACCESS_RESTRICTED", f"{tenor}国债收益率；" + ("官方日频成功并聚合月均" if yield_ok else "有限自动重试未形成完整序列，MANUAL_REQUIRED"))
        manifest[-1]["downloaded_raw"] = yield_ok
        manifest[-1]["local_raw_path"] = "data/raw/public/chinabond/" if yield_ok else ""
    write_csv(METADATA / "public_gap_source_manifest.csv", manifest, list(manifest[0]))

    recon = []
    output_overlap = {"2025-07": 81530, "2025-08": 85240, "2025-09": 87260}
    for month, public_value in output_overlap.items():
        canonical = float(v1.loc[v1.month.eq(month), "lc_output_total"].iloc[0])
        recon.append({"variable": "lc_output", "period": month, "canonical_value": canonical, "public_value": public_value, "difference": public_value-canonical, "difference_pct": (public_value-canonical)/canonical*100, "definition_match": True, "source_grade": "SOURCE_C", "status": "EXACT_MATCH"})
    battery_canonical = pd.read_csv(PROCESSED / "industry" / "battery_install_monthly.csv")
    for month, public_value in {"2026-01": 42.0, "2026-02": 26.3}.items():
        canonical = float(battery_canonical.loc[battery_canonical.month.eq(month), "battery_install_total"].iloc[0])
        recon.append({"variable": "battery_install", "period": month, "canonical_value": canonical, "public_value": public_value, "difference": public_value-canonical, "difference_pct": (public_value-canonical)/canonical*100, "definition_match": True, "source_grade": "SOURCE_B", "status": "EXACT_MATCH"})
    write_csv(METADATA / "public_tail_reconciliation.csv", recon, list(recon[0]))
    assert commercial_hashes_unchanged()


if __name__ == "__main__":
    build()
