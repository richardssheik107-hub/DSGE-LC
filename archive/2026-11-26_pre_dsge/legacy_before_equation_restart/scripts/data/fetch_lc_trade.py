"""Retrieve China monthly lithium-carbonate trade from UN Comtrade's public API.

HS 283691 is requested at the six-digit level.  The API reports netWgt in kg;
the canonical series is metric tons (kg / 1,000), while the original kg and
optional USD values are retained in the processed file.
"""
from __future__ import annotations

import argparse
import time

import pandas as pd
import requests

from common import PROCESSED, RAW, ensure_layout, save_bytes_once, sha256, timestamp, upsert_manifest

URL = "https://comtradeapi.un.org/public/v1/preview/C/M/HS"
HEADERS = {"User-Agent": "DSGE-LC research data acquisition/1.0"}


def months(start: str, end: str) -> list[str]:
    return pd.period_range(start, end, freq="M").strftime("%Y%m").tolist()


def retrieve(session: requests.Session, period: str, flow: str) -> requests.Response:
    params = {"period": period, "reporterCode": "156", "flowCode": flow, "partnerCode": "0",
              "cmdCode": "283691", "partner2Code": "0", "customsCode": "C00", "motCode": "0",
              "maxRecords": "500"}
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            response = session.get(URL, params=params, headers=HEADERS, timeout=60)
            if response.status_code == 429:
                raise requests.HTTPError("HTTP 429 rate limit", response=response)
            response.raise_for_status()
            payload = response.json()
            if "data" not in payload:
                raise ValueError("response lacks data field")
            return response
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError(f"{period}/{flow}: {last_error}")


def row_from_payload(month: str, flow: str, payload: dict) -> dict[str, object]:
    data = payload.get("data") or []
    item = data[0] if data else {}
    net_kg = item.get("netWgt")
    value = item.get("primaryValue")
    return {"month": f"{month[:4]}-{month[4:]}", "flow": flow, "netweight_kg": net_kg,
            "value_usd": value, "qty": item.get("qty"), "qty_unit_code": item.get("qtyUnitCode"),
            "is_netweight_estimated": item.get("isNetWgtEstimated"), "api_record_count": len(data)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2020-01")
    parser.add_argument("--end-date", default="2026-06")
    args = parser.parse_args()
    ensure_layout()
    session = requests.Session()
    rows, raw_files, failures = [], [], []
    for period in months(args.start_date, args.end_date):
        for flow, label in (("M", "import"), ("X", "export")):
            expected = RAW / "comtrade" / f"comtrade_cn_hs283691_{label}_{period}.json"
            try:
                if expected.exists():
                    payload = __import__("json").loads(expected.read_text(encoding="utf-8"))
                    rows.append(row_from_payload(period, flow, payload))
                    raw_files.append(expected)
                    continue
                response = retrieve(session, period, flow)
                raw = save_bytes_once(expected, response.content)
                raw_files.append(raw)
                rows.append(row_from_payload(period, flow, response.json()))
            except Exception as exc:
                failures.append(str(exc))
            # Comtrade's public preview endpoint permits one period at a time;
            # a modest pause respects that rate limit.
            time.sleep(1.1)
    long = pd.DataFrame(rows)
    full_months = pd.DataFrame({"month": pd.period_range(args.start_date, args.end_date, freq="M").astype(str)})
    if not long.empty:
        imports = long[long.flow == "M"].set_index("month")
        exports = long[long.flow == "X"].set_index("month")
        result = full_months.copy()
        result["import_netweight_kg"] = result.month.map(imports.netweight_kg if not imports.empty else {})
        result["export_netweight_kg"] = result.month.map(exports.netweight_kg if not exports.empty else {})
        result["lc_import_qty"] = pd.to_numeric(result.import_netweight_kg, errors="coerce") / 1000
        result["lc_export_qty"] = pd.to_numeric(result.export_netweight_kg, errors="coerce") / 1000
        result["lc_import_value_usd"] = result.month.map(imports.value_usd if not imports.empty else {})
        result["lc_export_value_usd"] = result.month.map(exports.value_usd if not exports.empty else {})
        result.to_csv(PROCESSED / "lc_trade_monthly.csv", index=False)
    else:
        result = full_months.assign(import_netweight_kg=pd.NA, export_netweight_kg=pd.NA,
                                    lc_import_qty=pd.NA, lc_export_qty=pd.NA,
                                    lc_import_value_usd=pd.NA, lc_export_value_usd=pd.NA)
    status = "OK" if not failures and len(rows) == len(full_months) * 2 else "PARTIAL" if rows else "FAILED"
    hashes = "; ".join(f"{p.name}:SHA256={sha256(p)}" for p in raw_files)
    for name, raw_col in (("lc_import_qty", "import_netweight_kg"), ("lc_export_qty", "export_netweight_kg")):
        values = result[["month", name]].dropna()
        upsert_manifest({"canonical_name": name, "source_name": "UN Comtrade public API", "source_url": URL,
            "retrieved_at": timestamp(), "raw_path": "data/raw/public/comtrade/", "frequency": "monthly",
            "unit": "metric tons", "coverage_start": values.month.min() if len(values) else "",
            "coverage_end": values.month.max() if len(values) else "", "n_obs": len(values), "status": status,
            "notes": f"China reporter 156, World partner 0, HS 283691, {raw_col} kg / 1000. {len(failures)} failed requests. {hashes}"})
    print(f"UN Comtrade: {status}; records={len(rows)}/expected={len(full_months)*2}; failures={len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
