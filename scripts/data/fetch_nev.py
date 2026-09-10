"""Fetch national monthly NEV production and sales from MIIT reposted reports."""
from __future__ import annotations

import argparse
import html
import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import pandas as pd
import requests

from common import METADATA, PROCESSED, RAW, ensure_layout, save_bytes_once, sha256, timestamp, upsert_manifest

INDEX = "https://www.miit.gov.cn/gxsj/tjfx/zbgy/qc/index.html"
UNIT_API = "https://www.miit.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DSGE-LC research/1.0)"}


def plain_html(payload: bytes) -> str:
    return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", payload.decode("utf-8", errors="ignore"))))


def parse_values(text: str, month_number: int | None = None) -> tuple[float, float] | None:
    # The MIIT wording explicitly orders production before sales.  Restrict to
    # the report's current calendar month when supplied: December reports
    # start with an annual total and later print the true December value.
    prefix = rf"(?<![0-9－—-]){month_number}月，" if month_number else ""
    hit = re.search(prefix + r"新能源汽车产销分别完成([0-9.]+)万辆(?:和|、)([0-9.]+)万辆", text)
    if hit:
        return float(hit.group(1)), float(hit.group(2))
    hit = re.search(prefix + r"新能源汽车产销均完成([0-9.]+)万辆", text)
    if hit:
        return float(hit.group(1)), float(hit.group(1))
    hit = re.search(prefix + r"新能源汽车产销分别完成([0-9.]+)辆(?:和|、)([0-9.]+)辆", text)
    if hit:
        return float(hit.group(1)) / 10000, float(hit.group(2)) / 10000
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2020-01")
    parser.add_argument("--end-date", default="2026-06")
    args = parser.parse_args()
    ensure_layout(); session = requests.Session()
    homepage = session.get(INDEX, headers=HEADERS, timeout=30).content.decode("utf-8")
    query = json.loads(re.search(r'queryData="([^"]+)"', homepage).group(1).replace("'", '"'))
    articles: dict[str, str] = {}
    for page in range(1, 5):
        params = dict(query); params["paramJson"] = json.dumps({"pageNo": page, "pageSize": 24})
        listing = session.get(UNIT_API, params=params, headers=HEADERS, timeout=30).json()["data"]["html"]
        for href, title in re.findall(r'href="([^"]+)"[^>]*title="([^"]+)"', listing):
            match = re.search(r"(20\d{2})年(\d{1,2})月(?:份)?汽车工业经济运行情况", title)
            if match:
                month = f"{match.group(1)}-{int(match.group(2)):02d}"
                if args.start_date <= month <= args.end_date:
                    articles[month] = urljoin(INDEX, href)
    def retrieve(item: tuple[str, str]):
        month, url = item; expected = RAW / "miit" / f"miit_auto_{month.replace('-', '_')}.html"
        try:
            raw = expected if expected.exists() else save_bytes_once(expected, session.get(url, headers=HEADERS, timeout=30).content)
            values = parse_values(plain_html(raw.read_bytes()), int(month[-2:]))
            return month, url, raw, values
        except requests.RequestException:
            return month, url, None, None
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(retrieve, sorted(articles.items())))
    rows, raw_files = [], []
    for month, url, raw, values in results:
        if raw is not None: raw_files.append(raw)
        if values is not None:
            production, sales = values
            rows.append({"month": month, "nev_production": production, "nev_sales": sales, "source_url": url,
                         "original_unit": "10,000 vehicles"})
    result = pd.DataFrame(rows).sort_values("month") if rows else pd.DataFrame(columns=["month", "nev_production", "nev_sales", "source_url", "original_unit"])
    # MIIT's public index omits the standalone August-2020 title.  Its
    # September report states same-definition January--September cumulative
    # values and September's current-month values, so recover only this one
    # documented flow observation by subtraction.
    derived = []
    if "2020-08" not in set(result.month) and (RAW / "miit" / "miit_auto_2020_09.html").exists():
        text = plain_html((RAW / "miit" / "miit_auto_2020_09.html").read_bytes())
        cumulative = re.search(r"1(?:－|-|—)9月，新能源汽车产销分别完成([0-9.]+)万辆(?:和|、)([0-9.]+)万辆", text)
        september = result.loc[result.month.eq("2020-09")]
        prior = result.loc[(result.month >= "2020-01") & (result.month <= "2020-07")]
        if cumulative and len(september) == 1 and len(prior) == 7:
            production = float(cumulative.group(1)) - prior.nev_production.sum() - september.nev_production.iloc[0]
            sales = float(cumulative.group(2)) - prior.nev_sales.sum() - september.nev_sales.iloc[0]
            url = september.source_url.iloc[0]
            result = pd.concat([result, pd.DataFrame([{"month":"2020-08", "nev_production":production, "nev_sales":sales,
                "source_url":url, "original_unit":"10,000 vehicles (derived from MIIT Jan-Sep cumulative)"}])]).sort_values("month")
            derived.append({"month":"2020-08", "current_cumulative":f"{cumulative.group(1)},{cumulative.group(2)}", "previous_cumulative":"sum 2020-01..2020-07",
                "derived_monthly":f"{production},{sales}", "source":url, "method":"2020 Jan-Sep cumulative minus Jan-Jul monthly sum minus Sep current month"})
    result.to_csv(PROCESSED / "nev_monthly.csv", index=False)
    pd.DataFrame(derived, columns=["month", "current_cumulative", "previous_cumulative", "derived_monthly", "source", "method"]).to_csv(METADATA / "nev_derived_months.csv", index=False)
    status = "OK" if len(result) == len(pd.period_range(args.start_date, args.end_date, freq="M")) else "PARTIAL" if len(result) else "FAILED"
    hashes = ";".join(f"{p.name}:SHA256={sha256(p)}" for p in raw_files)
    for name in ("nev_production", "nev_sales"):
        upsert_manifest({"canonical_name": name, "source_name": "MIIT monthly automobile industry economic operation report (CAAM data)",
            "source_url": INDEX, "retrieved_at": timestamp(), "raw_path": "data/raw/public/miit/", "frequency": "monthly",
            "unit": "10,000 vehicles", "coverage_start": result.month.min() if len(result) else "", "coverage_end": result.month.max() if len(result) else "",
            "n_obs": len(result), "status": status, "notes": f"National NEV wording parsed as production then sales. {hashes}"})
    print(f"MIIT NEV: {status}; reports found={len(articles)}, values={len(result)}")
    return 0 if len(result) else 1


if __name__ == "__main__":
    raise SystemExit(main())
