"""Attempt the official battery-alliance public source; never scrape gated data."""
from __future__ import annotations
import argparse
from common import ensure_layout, timestamp, upsert_manifest

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--start-date", default="2020-01"); parser.add_argument("--end-date", default="2026-06"); parser.parse_args()
    ensure_layout()
    upsert_manifest({"canonical_name":"battery_install","source_name":"China Automotive Power Battery Industry Innovation Alliance",
        "source_url":"https://www.cbea.com/","retrieved_at":timestamp(),"frequency":"monthly","unit":"GWh","status":"MANUAL_REQUIRED",
        "notes":"The alliance publishes dispersed monthly releases; no stable bulk public download endpoint was available without using secondary republishers. No secondary series was promoted to processed data."})
    print("battery_install: MANUAL_REQUIRED (official bulk endpoint unavailable)")
    return 0
if __name__ == "__main__": raise SystemExit(main())
