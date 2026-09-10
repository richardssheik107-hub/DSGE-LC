"""Acquire a bounded set of public auxiliary series; never touches the core panel."""
from __future__ import annotations
import argparse
import html
import json
import re
from pathlib import Path
import pandas as pd
import requests
from common import PROCESSED, RAW, ensure_layout, save_bytes_once, sha256, timestamp, upsert_manifest

START, END = "2020-01", "2026-06"
MONTHS = pd.period_range(START, END, freq="M").astype(str).tolist()
NBS_SEARCH = "https://api.so-gov.cn/query/s"
LPR_API = "https://www.chinamoney.com.cn/ags/ms/cm-u-bk-currency/LprHis?lang=CN"

def text_of(payload: bytes) -> str:
    return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", payload.decode("utf-8", errors="ignore"))))

def nbs_search(query: str, expected: str) -> dict | None:
    try:
        r = requests.post(NBS_SEARCH, data={"siteCode":"bm36000002","tab":"","qt":query,"page":1,"pageSize":30,"ie":""}, timeout=30)
        r.raise_for_status()
        payload = json.loads(r.content.decode("utf-8"))
        for item in payload.get("resultDocs", []):
            data = item.get("data", item); title, url = data.get("titleO", ""), data.get("url", "")
            if expected in title and "stats.gov.cn" in url:
                return {"url":url.replace("http://", "https://"), "title":title, "summary":data.get("summary", "")}
    except (requests.RequestException, ValueError):
        pass
    return None

def fetch_nbs() -> tuple[pd.DataFrame, pd.DataFrame]:
    pmi_rows, ip_rows = [], []
    for month in MONTHS:
        year, mon = month.split("-"); m = int(mon)
        hit = nbs_search(f"{year}年{m}月中国采购经理指数运行情况", f"{year}年{m}月中国采购经理指数")
        if hit:
            # NBS's official search index includes the release summary. Retain
            # that response instead of making a second request to a page that
            # may be intermittently throttled.
            raw = save_bytes_once(RAW/"nbs"/f"nbs_pmi_{year}_{mon}_search.json", json.dumps(hit, ensure_ascii=False).encode())
            body = re.sub(r"<[^>]+>", "", hit["summary"])
            match = re.search(r"制造业采购经理指数.*?为([0-9]+(?:\.[0-9]+|\s+[0-9]+)?)", body)
            value = float(match.group(1).replace(" ", ".")) if match else pd.NA
            pmi_rows.append({"month":month,"manufacturing_pmi":value,"source_url":hit["url"]})
        # January is intentionally not assigned a Jan--Feb combined observation.
        query = f"{year}年{m}月份规模以上工业增加值" if m != 2 else f"{year}年1—2月份规模以上工业增加值"
        expected = f"{year}年{m}月份" if m != 2 else f"{year}年1—2月份"
        hit = nbs_search(query, expected)
        if hit:
            save_bytes_once(RAW/"nbs"/f"nbs_industrial_{year}_{mon}_search.json", json.dumps(hit, ensure_ascii=False).encode())
            match = re.search(r"规模以上工业增加值(?:同比)?增长([0-9.]+)%", hit["title"]) or re.search(r"规模以上工业增加值(?:同比)?增长([0-9.]+)%", re.sub(r"<[^>]+>", "", hit["summary"]))
            ip_rows.append({"month":month,"industrial_production_yoy":float(match.group(1)) if match else pd.NA,"period_definition":"Jan-Feb combined" if m == 2 else "calendar month","source_url":hit["url"]})
    return pd.DataFrame(pmi_rows), pd.DataFrame(ip_rows)

def fetch_lpr() -> pd.DataFrame:
    records, raws = [], []
    for year in range(2020, 2027):
        end = f"{year}-12-31" if year < 2026 else "2026-06-30"
        try:
            r = requests.post(f"{LPR_API}&strStartDate={year}-01-01&strEndDate={end}", timeout=30); r.raise_for_status()
            raw = save_bytes_once(RAW/"external_macro"/f"chinamoney_lpr_{year}.json", r.content); raws.append(raw)
            records.extend(r.json().get("records", []))
        except (requests.RequestException, ValueError):
            continue
    data = pd.DataFrame(records)
    if data.empty: return pd.DataFrame(columns=["date","lpr_1y","lpr_5y"])
    date_col = next((c for c in data if c.lower() in ("showdate", "date", "showdatecn")), "showDateCN")
    data["date"] = pd.to_datetime(data[date_col], errors="coerce")
    data["lpr_1y"] = pd.to_numeric(data.get("1Y"), errors="coerce")
    data["lpr_5y"] = pd.to_numeric(data.get("5Y"), errors="coerce")
    data = data.dropna(subset=["date"]).sort_values("date")[["date","lpr_1y","lpr_5y"]]
    data["date"] = data.date.dt.strftime("%Y-%m-%d")
    data.to_csv(PROCESSED/"lpr_quotes_daily.csv", index=False)
    return data

def miit_extras() -> pd.DataFrame:
    rows=[]
    for month in MONTHS:
        raw=RAW/"miit"/f"miit_auto_{month.replace('-', '_')}.html"
        if not raw.exists(): continue
        body=text_of(raw.read_bytes()); m=int(month[-2:])
        total=re.search(rf"(?<![0-9－—-]){m}月，(?:我国)?汽车产销分别完成([0-9.]+)万辆和([0-9.]+)万辆",body)
        pen=(re.search(rf"(?<![0-9－—-]){m}月，新能源汽车.*?市场(?:占有率|渗透率)为([0-9.]+)%",body)
             or re.search(rf"(?<![0-9－—-]){m}月，新能源汽车新车销量达到汽车新车总销量的([0-9.]+)%",body))
        rows.append({"month":month,"auto_production":float(total.group(1)) if total else pd.NA,"auto_sales":float(total.group(2)) if total else pd.NA,"nev_penetration":float(pen.group(1)) if pen else pd.NA})
    return pd.DataFrame(rows)

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--skip-nbs", action="store_true"); args=parser.parse_args()
    ensure_layout(); pmi, industrial=(pd.DataFrame(columns=["month","manufacturing_pmi"]),pd.DataFrame(columns=["month","industrial_production_yoy","period_definition"])) if args.skip_nbs else fetch_nbs(); lpr=fetch_lpr(); extras=miit_extras()
    monthly=pd.DataFrame({"month":MONTHS}).merge(pmi[[c for c in ["month","manufacturing_pmi"] if c in pmi]],on="month",how="left").merge(industrial[[c for c in ["month","industrial_production_yoy"] if c in industrial]],on="month",how="left").merge(extras,on="month",how="left")
    if not lpr.empty:
        lpr["month"]=pd.to_datetime(lpr.date).dt.to_period("M").astype(str)
        # A policy quote remains effective until replaced: this is a policy-state
        # construction, not forward-fill of a statistical observation.
        quote=lpr.set_index("month")[["lpr_1y","lpr_5y"]].reindex(MONTHS).ffill().reset_index(names="month")
        monthly=monthly.merge(quote,on="month",how="left")
    # Where the report does not print a penetration percentage, use only the
    # same-report national NEV and total-auto sales ratio; no value is filled
    # when either underlying current-month flow is absent.
    nev_path = PROCESSED / "nev_monthly.csv"
    if nev_path.exists():
        nev = pd.read_csv(nev_path, dtype={"month":str})[["month","nev_sales"]]
        monthly = monthly.merge(nev, on="month", how="left")
        derived = monthly.nev_sales / monthly.auto_sales * 100
        monthly["nev_penetration"] = monthly.nev_penetration.combine_first(derived)
        monthly = monthly.drop(columns=["nev_sales"])
    for col in ("lpr_1y","lpr_5y"):
        if col not in monthly: monthly[col]=pd.NA
    monthly.to_csv(PROCESSED.parent/"auxiliary_macro_monthly.csv",index=False)
    industrial.to_csv(PROCESSED/"industrial_production_monthly.csv",index=False)
    for name, source, unit, data in [("manufacturing_pmi","NBS China PMI","index",pmi),("industrial_production_yoy","NBS industrial production release","percent",industrial),("lpr_1y","ChinaMoney LPR history","percent",monthly),("lpr_5y","ChinaMoney LPR history","percent",monthly),("auto_sales","MIIT monthly automobile report","10,000 vehicles",extras),("auto_production","MIIT monthly automobile report","10,000 vehicles",extras),("nev_penetration","MIIT monthly automobile report","percent",extras)]:
        field=name if name in data else name
        series=data[field].dropna() if field in data else pd.Series(dtype=float)
        upsert_manifest({"canonical_name":name,"source_name":source,"source_url":"https://www.stats.gov.cn/" if name.startswith(("manufacturing","industrial")) else "https://www.chinamoney.com.cn/chinese/bklpr/" if name.startswith("lpr") else "https://www.miit.gov.cn/gxsj/tjfx/zbgy/qc/index.html","retrieved_at":timestamp(),"raw_path":"data/raw/public/nbs/" if name.startswith(("manufacturing","industrial")) else "data/raw/public/external_macro/" if name.startswith("lpr") else "data/raw/public/miit/","frequency":"monthly","unit":unit,"coverage_start":MONTHS[0] if len(series) else "","coverage_end":MONTHS[-1] if len(series) else "","n_obs":len(series),"status":"OK" if len(series)==78 else "PARTIAL" if len(series) else "FAILED","notes":"LPR monthly values are prevailing policy quotes; no statistical interpolation." if name.startswith("lpr") else "Official raw responses retained."})
    print(f"Auxiliary: PMI={monthly.manufacturing_pmi.notna().sum()}, IP={monthly.industrial_production_yoy.notna().sum()}, LPR={monthly.lpr_1y.notna().sum()}, auto={monthly.auto_sales.notna().sum()}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
