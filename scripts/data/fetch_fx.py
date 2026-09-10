"""Download daily USD/CNY into the Phase 1 raw and processed layers.

Primary Chinese official sources are CFETS/PBOC. When their historical endpoint
is access-controlled, the script uses the Federal Reserve's public DEXCHUS
download as a documented fallback, not an unnamed republisher. DEXCHUS is
already quoted as CNY per USD.
"""
from __future__ import annotations

import argparse
import io
import sys

import pandas as pd
import requests

from common import PROCESSED, RAW, ensure_layout, save_bytes_once, sha256, timestamp, upsert_manifest

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXCHUS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2020-01-01")
    parser.add_argument("--end-date", default="2026-06-30")
    args = parser.parse_args()
    ensure_layout()
    try:
        response = requests.get(FRED_URL, timeout=60, headers={"User-Agent": "DSGE-LC public-data audit/1.0"})
        response.raise_for_status()
    except requests.RequestException as exc:
        upsert_manifest({"canonical_name": "usd_cny", "source_name": "Federal Reserve Economic Data (fallback)",
                         "source_url": FRED_URL, "retrieved_at": timestamp(), "frequency": "daily", "unit": "CNY per USD",
                         "status": "FAILED", "notes": f"Download failed: {exc}"})
        print(f"FX download failed: {exc}", file=sys.stderr)
        return 1
    raw = save_bytes_once(RAW / "pboc_cfets" / "fred_dexchus.csv", response.content)
    frame = pd.read_csv(io.BytesIO(response.content))
    frame.columns = ["date", "usd_cny"]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["usd_cny"] = pd.to_numeric(frame["usd_cny"], errors="coerce")
    frame = frame[(frame.date >= args.start_date) & (frame.date <= args.end_date)].dropna().drop_duplicates("date").sort_values("date")
    frame["date"] = frame["date"].dt.strftime("%Y-%m-%d")
    frame.to_csv(PROCESSED / "usd_cny_daily.csv", index=False)
    monthly = frame.assign(month=pd.to_datetime(frame.date).dt.to_period("M").astype(str)).groupby("month", as_index=False).agg(
        usd_cny_mean=("usd_cny", "mean"), usd_cny_end=("usd_cny", "last")
    )
    monthly.to_csv(PROCESSED / "usd_cny_monthly.csv", index=False)
    upsert_manifest({"canonical_name": "usd_cny", "source_name": "Federal Reserve Economic Data, DEXCHUS (documented fallback after CFETS access control)",
                     "source_url": FRED_URL, "retrieved_at": timestamp(), "raw_path": str(raw.relative_to(raw.parents[4])),
                     "frequency": "daily", "unit": "CNY per USD", "coverage_start": frame.date.min(), "coverage_end": frame.date.max(),
                     "n_obs": len(frame), "status": "DOWNLOADED", "notes": f"SHA256={sha256(raw)}; source direction retained as CNY per USD."})
    print(f"Downloaded {len(frame)} daily USD/CNY observations ({frame.date.min()} to {frame.date.max()}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
