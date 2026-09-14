"""Download public ChinaBond government-curve 3M and 6M yields.

Uses ChinaBond's public historical government-bond yield-to-maturity query,
selecting its published 0.25- and 0.50-year curve nodes.  No Shibor proxy is
used.
"""
from __future__ import annotations

import argparse
import calendar
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd
import requests

from common import PROCESSED, RAW, ensure_layout, save_bytes_once, sha256, timestamp, upsert_manifest

BASE = "https://yield.chinabond.com.cn/cbweb-mn"
CURVE_ID = "2c9081e50a2f9606010a3068cae70001"
QUERY_URL = f"{BASE}/yc/queryXyz"


def years_between(start: str, end: str) -> list[tuple[str, str]]:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    return [(max(first, date(y, 1, 1)).isoformat(), min(last, date(y, 12, 31)).isoformat())
            for y in range(first.year, last.year + 1)]


def months_between(start: str, end: str) -> list[tuple[str, str]]:
    """Use bounded month requests; ChinaBond's multi-year response can time out."""
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    periods: list[tuple[str, str]] = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        begin = max(first, date(year, month, 1))
        finish = min(last, date(year, month, calendar.monthrange(year, month)[1]))
        periods.append((begin.isoformat(), finish.isoformat()))
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return periods


def request_period(session: requests.Session, start: str, end: str) -> requests.Response:
    params = {"startTime": start, "endTime": end, "qxlx": "0,", "yqqxN": "N", "yqqxK": "K",
              "ycDefIds": f"{CURVE_ID},", "locale": "zh_CN"}
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = session.post(QUERY_URL, params=params, timeout=30)
            response.raise_for_status()
            if not response.content.startswith(b"["):
                raise ValueError("response was not a JSON array")
            return response
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{start} to {end}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2020-01-01")
    parser.add_argument("--end-date", default="2026-06-30")
    args = parser.parse_args()
    ensure_layout()
    observations, raw_files, failures = [], [], []
    def fetch(period: tuple[str, str]):
        session = requests.Session()
        session.headers["User-Agent"] = "Mozilla/5.0 (compatible; DSGE-LC public-data audit/1.0)"
        return period, request_period(session, *period)

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(fetch, period) for period in months_between(args.start_date, args.end_date)]
        for future in as_completed(futures):
            try:
                (start, end), response = future.result()
            except Exception as exc:
                failures.append(str(exc))
                continue
            raw = save_bytes_once(RAW / "chinabond" / f"chinabond_gov_ytm_{start}_{end}.json", response.content)
            raw_files.append(raw)
            for curve in response.json():
                values = dict(zip(curve.get("bzqx", []), curve.get("syl", [])))
                if curve.get("workTime"):
                    observations.append({"date": curve["workTime"], "china_gov_3m": values.get(0.25),
                                         "china_gov_6m": values.get(0.5)})
    frame = pd.DataFrame(observations)
    if not frame.empty:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
        for column in ("china_gov_3m", "china_gov_6m"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame["date"] = frame["date"].dt.strftime("%Y-%m-%d")
        frame.to_csv(PROCESSED / "china_gov_yields_daily.csv", index=False)
    status = "DOWNLOADED" if not failures and not frame.empty else "PARTIAL" if not frame.empty else "FAILED"
    note = "; ".join(failures) if failures else "Public historical response; 3M=0.25Y and 6M=0.50Y."
    hashes = ", ".join(f"{raw.name}:SHA256={sha256(raw)}" for raw in raw_files)
    for name, tenor in (("china_gov_3m", "0.25Y"), ("china_gov_6m", "0.50Y")):
        upsert_manifest({"canonical_name": name, "source_name": "ChinaBond government bond yield curve",
            "source_url": QUERY_URL, "retrieved_at": timestamp(), "raw_path": "data/raw/public/chinabond/",
            "frequency": "daily", "unit": "percent", "coverage_start": frame.date.min() if not frame.empty else "",
            "coverage_end": frame.date.max() if not frame.empty else "", "n_obs": len(frame), "status": status,
            "notes": f"{tenor}; {note} {hashes}".strip()})
    print(f"ChinaBond: {status}; {len(frame)} daily curve observations; failures={len(failures)}")
    return 0 if not frame.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
