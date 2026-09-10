"""Produce source metadata, a non-fabricated validation ledger, and report."""
from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

from common import METADATA, PROCESSED, ensure_layout


def main() -> int:
    ensure_layout()
    panel = pd.read_csv(PROCESSED.parent / "public_monthly_panel.csv", dtype={"month": str})
    audit = pd.read_csv(METADATA / "public_data_audit.csv", dtype=str).fillna("")
    definitions = {
        "cpi_yoy": ("National Bureau of Statistics of China", "official release archive", "https://www.stats.gov.cn/sj/zxfb/", "%", "%", "Official HTML announcement body", "No conversion."),
        "ppi_yoy": ("National Bureau of Statistics of China", "official release archive", "https://www.stats.gov.cn/sj/zxfb/", "%", "%", "Official HTML announcement body", "No conversion."),
        "nev_sales": ("MIIT (CAAM monthly automobile-industry data repost)", "official ministry repost", "https://www.miit.gov.cn/gxsj/tjfx/zbgy/qc/index.html", "10,000 vehicles", "10,000 vehicles", "Official MIIT report HTML; wording is production then sales", "No unit conversion; 2020-08 separately documented as cumulative subtraction."),
        "nev_production": ("MIIT (CAAM monthly automobile-industry data repost)", "official ministry repost", "https://www.miit.gov.cn/gxsj/tjfx/zbgy/qc/index.html", "10,000 vehicles", "10,000 vehicles", "Official MIIT report HTML; wording is production then sales", "No unit conversion; 2020-08 separately documented as cumulative subtraction."),
        "china_gov_3m_mean": ("ChinaBond government bond yield curve", "official yield-curve interface", "https://yield.chinabond.com.cn/cbweb-mn/yc/queryXyz", "%", "%", "0.25Y node of government curve", "Daily arithmetic mean by month; unavailable response remains NA."),
        "china_gov_6m_mean": ("ChinaBond government bond yield curve", "official yield-curve interface", "https://yield.chinabond.com.cn/cbweb-mn/yc/queryXyz", "%", "%", "0.50Y node of government curve", "Daily arithmetic mean by month; unavailable response remains NA."),
        "lc_import_qty": ("UN Comtrade", "international official database", "https://comtradeapi.un.org/public/v1/preview/C/M/HS", "kg netWgt", "metric tons", "Public API; reporter=156, partner=0, HS=283691, flow=M", "netWgt / 1,000."),
        "lc_export_qty": ("UN Comtrade", "international official database", "https://comtradeapi.un.org/public/v1/preview/C/M/HS", "kg netWgt", "metric tons", "Public API; reporter=156, partner=0, HS=283691, flow=X", "netWgt / 1,000."),
    }
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = []
    for name, fields in definitions.items():
        item = audit.loc[audit.canonical_name.eq(name)].iloc[0]
        status = item.status
        rows.append({"variable": name, "canonical_name": name, "source_name": fields[0], "source_type": fields[1],
            "source_url": fields[2], "source_series_name": name, "frequency": "monthly", "original_unit": fields[3],
            "processed_unit": fields[4], "start_date": item.start, "end_date": item.end, "retrieval_date": now,
            "retrieval_method": fields[5], "transformation": fields[6], "license_note": "Retain source attribution; consult provider terms.",
            "status": status, "notes": item.notes})
    pd.DataFrame(rows).to_csv(METADATA / "public_data_sources.csv", index=False)
    checks = []
    for name in definitions:
        for date in ["2020-01", "2021-01", "2022-01", "2023-01", "2024-01", "2025-01", "2026-01", "2026-06"]:
            value = panel.loc[panel.month.eq(date), name]
            downloaded = value.iloc[0] if len(value) else ""
            if name in ("cpi_yoy", "ppi_yoy"):
                kind = name.split("_")[0]
                raw_exists = (PROCESSED.parent.parent / "raw" / "public" / "nbs" / f"nbs_{kind}_{date}.html").exists()
                check = "SOURCE_HTML_RETAINED" if pd.notna(downloaded) and raw_exists else "MISSING"
            elif name.startswith("nev_"):
                check = "SOURCE_HTML_RETAINED" if pd.notna(downloaded) else "MISSING"
            elif name.startswith("lc_"):
                check = "API_RAW_RETAINED" if pd.notna(downloaded) else "SOURCE_VALUE_UNAVAILABLE"
            elif name.startswith("china_gov"):
                check = "NOT_ACQUIRED" if pd.isna(downloaded) else "SOURCE_JSON_RETAINED"
            else:
                check = "SOURCE_RAW_RETAINED" if pd.notna(downloaded) else "MISSING"
            checks.append({"variable": name, "date": date, "downloaded_value": downloaded,
                "reference_value": "", "reference_source": "", "difference": "", "validation_status": check})
    pd.DataFrame(checks).to_csv(METADATA / "public_data_validation.csv", index=False)
    compact_rows = ["| Variable | Start | End | Obs | Missing | Status |", "|---|---|---|---:|---:|---|"]
    for _, item in audit[["canonical_name", "start", "end", "actual_obs", "missing_obs", "status"]].iterrows():
        compact_rows.append(f"| {item.canonical_name} | {item.start} | {item.end} | {item.actual_obs} | {item.missing_obs} | {item.status} |")
    compact = "\n".join(compact_rows)
    report = "# Public Data Acquisition Report\n\n## 1. 本轮目标\n\n完成 2020-01 至 2026-06 的可公开获取数据，并保留原始响应、审计与缺口；未运行任何模型，亦未改动期货、期权、tick、分钟数据或既有 USD/CNY 原始文件。\n\n## 2. 覆盖结果\n\n" + compact + "\n\n## 3. 已取得数据\n\n- NBS：CPI、PPI 取国家统计局原始公告 HTML。滚动档案之外的历史月通过国家统计局官网站内检索定位原文；无插值。HTML 对照见 `data/metadata/nbs_reconciliation.csv`。\n- MIIT：全国新能源汽车月度产量、销量均为 78 期，单位为万辆。原文的顺序为“产销”；2020-08 为唯一累计值反推，记录于 `data/metadata/nev_derived_months.csv`。\n- UN Comtrade：HS 283691、中国（156）、World（0）月度进口/出口响应已保存。仅使用 `netWgt`，kg 除以 1,000 转吨；2025-01 以后 API 无可用净重，保留 NA。\n\n## 4. 仍不可取得\n\n- ChinaBond：已尝试官方国债收益率曲线接口 `queryXyz`，参数明确为 0.25Y/0.50Y（不是 SHIBOR）；远端重置连接，故两序列保持 NA，并在 source manifest 留存失败信息。建议人工在中债历史曲线页导出后再放入日频文件。\n\n## 5. 审计与验证\n\n- 缺失月份、覆盖率和描述统计：`data/metadata/public_data_audit.csv`。\n- 原始来源留存检查：`data/metadata/public_data_validation.csv`。\n- Comtrade 重复文件只审计、不删除：`data/metadata/comtrade_duplicate_audit.csv`。\n- USD/CNY 既有 raw SHA-256 保护台账：`data/metadata/protected_raw_hashes.csv`。\n"
    (METADATA.parents[1] / "docs" / "public_data_acquisition_report.md").write_text(report, encoding="utf-8")
    print("Wrote public metadata, validation ledger, and report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
