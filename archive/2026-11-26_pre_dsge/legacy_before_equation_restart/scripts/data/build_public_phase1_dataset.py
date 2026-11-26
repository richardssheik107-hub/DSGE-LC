"""Build the requested 2020-01--2026-06 public monthly panel and audit."""
from __future__ import annotations

import csv
import pandas as pd

from common import METADATA, PROCESSED, ensure_layout

START, END = "2020-01", "2026-06"
MONTHS = pd.DataFrame({"month": pd.period_range(START, END, freq="M").astype(str)})
FIELDS = ["cpi_yoy", "ppi_yoy", "nev_sales", "nev_production", "china_gov_3m_mean",
          "china_gov_6m_mean", "lc_import_qty", "lc_export_qty", "usd_cny_mean"]


def source_monthly(path: str, columns: list[str]) -> pd.DataFrame:
    file = PROCESSED / path
    if not file.exists():
        return pd.DataFrame(columns=["month"] + columns)
    data = pd.read_csv(file, dtype={"month": str})
    return data[["month"] + [c for c in columns if c in data.columns]].copy()


def rate_monthly() -> pd.DataFrame:
    file = PROCESSED / "china_gov_yields_daily.csv"
    if not file.exists():
        return pd.DataFrame(columns=["month", "china_gov_3m_mean", "china_gov_6m_mean"])
    data = pd.read_csv(file)
    data["month"] = pd.to_datetime(data["date"], errors="coerce").dt.to_period("M").astype(str)
    return data.groupby("month", as_index=False).agg(china_gov_3m_mean=("china_gov_3m", "mean"),
                                                       china_gov_6m_mean=("china_gov_6m", "mean"))


def main() -> int:
    ensure_layout()
    panel = MONTHS.copy()
    sources = [
        source_monthly("macro_price_monthly.csv", ["cpi_yoy", "ppi_yoy"]),
        source_monthly("nev_monthly.csv", ["nev_sales", "nev_production"]),
        rate_monthly(),
        source_monthly("lc_trade_monthly.csv", ["lc_import_qty", "lc_export_qty"]),
        source_monthly("usd_cny_monthly.csv", ["usd_cny_mean"]),
    ]
    for source in sources:
        panel = panel.merge(source, on="month", how="left")
    for field in FIELDS:
        if field not in panel:
            panel[field] = pd.NA
        panel[field] = pd.to_numeric(panel[field], errors="coerce")
    panel = panel[["month"] + FIELDS]
    # New required location plus the prior phase1 location for backward compatibility.
    panel.to_csv(PROCESSED.parent / "public_monthly_panel.csv", index=False)
    panel.to_csv(PROCESSED / "public_monthly_panel.csv", index=False)

    audits = []
    for field in FIELDS:
        values = panel[field].dropna()
        actual_months = panel.loc[panel[field].notna(), "month"]
        missing_months = panel.loc[panel[field].isna(), "month"].tolist()
        audits.append({"canonical_name": field, "start": actual_months.min() if len(actual_months) else "",
            "end": actual_months.max() if len(actual_months) else "", "expected_obs": len(panel),
            "actual_obs": len(values), "missing_obs": len(missing_months),
            "missing_ratio": round(len(missing_months) / len(panel), 6),
            "duplicate_obs": int(actual_months.duplicated().sum()), "min": values.min() if len(values) else "",
            "max": values.max() if len(values) else "", "mean": values.mean() if len(values) else "",
            "status": "OK" if len(values) == len(panel) else "PARTIAL" if len(values) else "MANUAL_REQUIRED",
            "missing_months": ";".join(missing_months), "notes": "No interpolation, fill, or inferred observations."})
    with (METADATA / "public_data_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audits[0]))
        writer.writeheader(); writer.writerows(audits)
    print(f"Built {len(panel)}-month public panel at data/processed/public_monthly_panel.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
