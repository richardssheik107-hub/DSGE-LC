"""Recover bounded NBS auxiliary observations already retained during attempts."""
from __future__ import annotations
import html, json, re
import pandas as pd
from common import PROCESSED, RAW
def main() -> int:
    out=PROCESSED.parent/"auxiliary_macro_monthly.csv"; panel=pd.read_csv(out,dtype={"month":str})
    for kind, field in [("pmi","manufacturing_pmi"),("industrial","industrial_production_yoy")]:
        values={}
        for raw in (RAW/"nbs").glob(f"nbs_{kind}_????_??.html"):
            month=raw.name.split("_")[2]+"-"+raw.name.split("_")[3].split(".")[0]
            text=re.sub(r"\s+","",html.unescape(re.sub(r"<[^>]+>","",raw.read_text(encoding="utf-8",errors="ignore"))))
            if kind=="pmi": match=re.search(r"制造业采购经理指数（PMI）为([0-9.]+)",text)
            else: match=re.search(r"规模以上工业增加值(?:同比)?增长([0-9.]+)%",text)
            if match: values[month]=float(match.group(1))
        panel[field]=panel.month.map(values)
    panel.to_csv(out,index=False); print(f"Recovered PMI={panel.manufacturing_pmi.notna().sum()}, IP={panel.industrial_production_yoy.notna().sum()}")
    return 0
if __name__=="__main__": raise SystemExit(main())
