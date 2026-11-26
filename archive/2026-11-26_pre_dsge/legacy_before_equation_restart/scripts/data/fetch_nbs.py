"""Fetch CPI/PPI from public NBS release pages when its bulk API is blocked."""
from __future__ import annotations
import argparse
import html
import re
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
from common import PROCESSED, RAW, ensure_layout, save_bytes_once, sha256, timestamp, upsert_manifest

NBS_URL="https://data.stats.gov.cn/easyquery.htm?m=QueryData&dbcode=hgyd"
SEARCH_URL="https://api.so-gov.cn/query/s"


def search_nbs_release(kind: str, month: str, headers: dict[str, str]) -> tuple[str, str] | None:
    """Use NBS's public site-search index to find an older release omitted by
    the rolling archive.  This is an ordinary public search endpoint, not an
    alternate data provider; the returned document is still fetched from
    stats.gov.cn and retained verbatim."""
    year, mon = month.split("-")
    topic = "居民消费价格同比" if kind == "cpi" else "工业生产者出厂价格同比"
    try:
        response = requests.post(SEARCH_URL, data={
            "siteCode": "bm36000002", "tab": "", "qt": f"{year}年{int(mon)}月份{topic}",
            "page": 1, "pageSize": 20, "ie": "",
        }, headers=headers, timeout=30)
        response.raise_for_status()
        docs = response.json().get("resultDocs", [])
    except (requests.RequestException, ValueError):
        return None
    expected = f"{year}年{int(mon)}月份"
    marker = "居民消费价格" if kind == "cpi" else "工业生产者出厂价格"
    for doc in docs:
        data = doc.get("data", doc)
        title = data.get("titleO", "")
        url = data.get("url", "")
        if expected in title and marker in title and "stats.gov.cn" in url:
            return url.replace("http://", "https://"), title
    return None
def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--start-date",default="2020-01"); parser.add_argument("--end-date",default="2026-06"); args=parser.parse_args()
    ensure_layout()
    headers={"User-Agent":"DSGE-LC public-data audit/1.0"}
    try:
        status=requests.get(NBS_URL,timeout=30,headers=headers).status_code
    except requests.RequestException as exc:
        status=f"network error: {exc}"
    found={}
    # The current NBS archive exposes 66 ordinary public list pages.  We use
    # release-page titles, then retain each original article HTML in raw/.
    listings = [f"https://www.stats.gov.cn/sj/zxfb/index_{page}.html" for page in range(1,67)]
    def fetch_listing(listing: str) -> tuple[str, bytes | None]:
        try:
            return listing, requests.get(listing,timeout=30,headers=headers).content
        except requests.RequestException:
            return listing, None
    # Four simultaneous reads is deliberately modest and turns the public
    # archive index into a bounded, reproducible request set.
    with ThreadPoolExecutor(max_workers=4) as pool:
        listing_results = list(pool.map(fetch_listing, listings))
    for listing, payload in listing_results:
        if payload is None:
            continue
        text=payload.decode("utf-8",errors="ignore")
        for href,label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',text,re.S|re.I):
            title=html.unescape(re.sub(r"<.*?>", "", label)).strip()
            kind="cpi" if "居民消费价格同比" in title else "ppi" if "工业生产者出厂价格同比" in title else ""
            hit=re.search(r"(20\d{2})年(\d{1,2})月份", title)
            if not kind or not hit:
                continue
            month=f"{hit.group(1)}-{int(hit.group(2)):02d}"
            if args.start_date <= month <= args.end_date:
                found[(kind,month)]=(urljoin(listing,href),title)
    # The rolling archive no longer lists older announcements consistently.
    # First retain any existing values, then only query the NBS public search
    # index for the specific missing (series, month) keys.
    existing_path = PROCESSED / "macro_price_monthly.csv"
    existing = pd.read_csv(existing_path, dtype={"month": str}) if existing_path.exists() else pd.DataFrame()
    months = pd.period_range(args.start_date, args.end_date, freq="M").astype(str).tolist()
    for kind in ("cpi", "ppi"):
        field = f"{kind}_yoy"
        available = set(existing.loc[existing.get(field, pd.Series(dtype=float)).notna(), "month"]) if field in existing else set()
        available.update(month for current_kind, month in found if current_kind == kind)
        for month in months:
            if month not in available:
                hit = search_nbs_release(kind, month, headers)
                if hit:
                    found[(kind, month)] = hit
    if not found and existing.empty:
        print(f"NBS archive/search yielded no candidates (API probe={status}); no output written.")
        return 1
    rows=[]; raw_files=[]
    print(f"NBS archive candidates: CPI={sum(kind == 'cpi' for kind, _ in found)}, PPI={sum(kind == 'ppi' for kind, _ in found)}")
    candidates=[]
    for (kind,month),(url,title) in sorted(found.items()):
        # Headlines state the nationwide headline year-on-year rate.  We do not
        # calculate a rate from any lower-level table.
        # NBS has used several headline wordings (including extra month-on-
        # month text).  Read the first numeric rate after the already verified
        # year-on-year marker, without inferring a value when none is printed.
        rate=re.search(r"同比[^0-9]*(\d+(?:\.\d+)?)%", title)
        value=float(rate.group(1)) * (-1 if "同比下降" in title else 1) if rate else None
        candidates.append((kind, month, url, value))
    def fetch_article(item: tuple[str, str, str, float | None]):
        kind, month, url, value = item
        expected = RAW / "nbs" / f"nbs_{kind}_{month}.html"
        if expected.exists():
            raw = expected
        else:
            try:
                article=requests.get(url,timeout=30,headers=headers)
                article.raise_for_status()
                raw=save_bytes_once(expected, article.content)
            except requests.RequestException:
                return None
        if value is None:
            # List-page headings often omit PPI's number.  The official article
            # body names the national headline explicitly; strip markup only,
            # then retain the printed figure and its sign.
            body=html.unescape(re.sub(r"<[^>]+>", "", raw.read_text(encoding="utf-8", errors="ignore")))
            label="全国工业生产者出厂价格" if kind == "ppi" else "全国居民消费价格"
            hit=re.search(label + r"同比(?:上涨|下降)(\d+(?:\.\d+)?)%", body)
            if not hit:
                return None
            value=float(hit.group(1)) * (-1 if "同比下降" in hit.group(0) else 1)
        return kind, month, value, raw
    print(f"NBS parsed headline values: CPI={sum(x[0] == 'cpi' for x in candidates)}, PPI={sum(x[0] == 'ppi' for x in candidates)}")
    # The archive is public but requests are deliberately bounded.  This keeps
    # a full historical run practical without bypassing access controls.
    with ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(fetch_article, candidates):
            if result is None:
                continue
            kind, month, value, raw = result
            raw_files.append(raw)
            rows.append({"month":month, f"{kind}_yoy":value})
    if rows or not existing.empty:
        data=pd.DataFrame(rows).groupby("month",as_index=False).first() if rows else pd.DataFrame(columns=["month","cpi_yoy","ppi_yoy"])
        output=pd.DataFrame({"month":months})
        if not existing.empty:
            output=output.merge(existing[[c for c in ("month", "cpi_yoy", "ppi_yoy") if c in existing]],on="month",how="left")
        output=output.merge(data,on="month",how="left",suffixes=("_existing", ""))
        for field in ("cpi_yoy", "ppi_yoy"):
            old=f"{field}_existing"
            if old in output:
                output[field]=output[field].combine_first(output[old])
                output=output.drop(columns=[old])
        # Ensure both schema fields exist even if one release type was absent.
        for field in ("cpi_yoy","ppi_yoy"):
            if field not in output: output[field]=pd.NA
        output[["month","cpi_yoy","ppi_yoy"]].to_csv(PROCESSED / "macro_price_monthly.csv",index=False)
    else:
        output=pd.DataFrame(columns=["month","cpi_yoy","ppi_yoy"])
    for name in ("cpi_yoy","ppi_yoy"):
        series=output[["month",name]].dropna() if name in output else pd.DataFrame()
        raw_hashes=";".join(sha256(p) for p in raw_files)
        upsert_manifest({"canonical_name":name,"source_name":"National Bureau of Statistics of China (NBS) public release archive","source_url":"https://www.stats.gov.cn/sj/zxfb/",
            "retrieved_at":timestamp(),"raw_path":"data/raw/public/nbs/","frequency":"monthly","unit":"percent, year-on-year",
            "coverage_start":series.month.min() if len(series) else "","coverage_end":series.month.max() if len(series) else "","n_obs":len(series),
            "status":"DOWNLOADED" if len(series)==78 else "PARTIAL" if len(series) else "MANUAL_REQUIRED",
            "notes":f"NBS bulk API probe: {status}. Values parsed from official release headings; {len(raw_files)} article payloads retained; SHA256={raw_hashes}"})
    print(f"NBS archive: {len(output.dropna(how='all'))} monthly rows; CPI={output.cpi_yoy.notna().sum() if 'cpi_yoy' in output else 0}, PPI={output.ppi_yoy.notna().sum() if 'ppi_yoy' in output else 0}; API probe={status}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
