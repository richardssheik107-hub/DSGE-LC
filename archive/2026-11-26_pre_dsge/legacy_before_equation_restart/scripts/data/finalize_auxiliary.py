"""Audit round-three auxiliary data without modifying the main public panel."""
from __future__ import annotations
import hashlib
from pathlib import Path
import pandas as pd
from common import METADATA, PROCESSED, RAW, ensure_layout

FIELDS=["manufacturing_pmi","industrial_production_yoy","m2_yoy","lpr_1y","lpr_5y","dr007","reverse_repo_7d_rate","mlf_1y_rate","auto_sales","auto_production","nev_penetration","brent_price"]
STATUS={"manufacturing_pmi":"FAILED","industrial_production_yoy":"FAILED","m2_yoy":"FAILED","lpr_1y":"OK","lpr_5y":"OK","dr007":"MANUAL_REQUIRED","reverse_repo_7d_rate":"MANUAL_REQUIRED","mlf_1y_rate":"MANUAL_REQUIRED","auto_sales":"PARTIAL","auto_production":"PARTIAL","nev_penetration":"PARTIAL","brent_price":"NOT_RECOMMENDED"}
def main() -> int:
    ensure_layout(); path=PROCESSED.parent/"auxiliary_macro_monthly.csv"; panel=pd.read_csv(path,dtype={"month":str})
    for f in FIELDS:
        if f not in panel: panel[f]=pd.NA
    panel=panel[["month"]+FIELDS]; panel.to_csv(path,index=False)
    audit=[]; anomalies=[]
    for f in FIELDS:
        values=pd.to_numeric(panel[f],errors="coerce"); valid=values.dropna(); months=panel.loc[values.notna(),"month"]
        audit.append({"variable":f,"start":months.min() if len(months) else "","end":months.max() if len(months) else "","expected_obs":78,"actual_obs":len(valid),"missing_obs":78-len(valid),"missing_ratio":round((78-len(valid))/78,6),"duplicates":int(months.duplicated().sum()),"min":valid.min() if len(valid) else "","max":valid.max() if len(valid) else "","mean":valid.mean() if len(valid) else "","status":STATUS[f]})
        if len(valid) and (valid < 0).any():
            for idx in values[values<0].index: anomalies.append({"variable":f,"date":panel.month.iloc[idx],"value":values.iloc[idx],"reason":"negative value requires review","action":"REVIEW"})
    pd.DataFrame(audit).to_csv(METADATA/"auxiliary_data_audit.csv",index=False)
    pd.DataFrame(anomalies,columns=["variable","date","value","reason","action"]).to_csv(METADATA/"auxiliary_data_anomalies.csv",index=False)
    protected=[]
    for name in ("lc_spot","lc_output","spodumene_price","battery_install"):
        candidates=list((RAW).rglob(f"*{name}*"))
        for p in candidates:
            if p.is_file(): protected.append({"category":"core_industry","path":str(p.relative_to(Path.cwd())).replace("\\","/"),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
    for root in (RAW/"futures", RAW/"options"):
        if root.exists():
            for p in root.rglob("*"):
                if p.is_file(): protected.append({"category":"futures_or_options","path":str(p.relative_to(Path.cwd())).replace("\\","/"),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
    pd.DataFrame(protected,columns=["category","path","sha256"]).to_csv(METADATA/"round3_protected_raw_hashes.csv",index=False)
    source_path=METADATA/"public_data_sources.csv"
    sources=pd.read_csv(source_path,dtype=str).fillna("") if source_path.exists() else pd.DataFrame()
    source_rows=[]
    for item in audit:
        variable=item["variable"]
        source_rows.append({"variable":variable,"canonical_name":variable,"source_name":"NBS official release archive" if variable in ("manufacturing_pmi","industrial_production_yoy") else "ChinaMoney / National Interbank Funding Center" if variable.startswith("lpr") else "MIIT monthly automobile report" if variable.startswith(("auto_","nev_")) else "Not acquired","source_type":"official public release","source_url":"https://www.stats.gov.cn/" if variable in ("manufacturing_pmi","industrial_production_yoy") else "https://www.chinamoney.com.cn/chinese/bklpr/" if variable.startswith("lpr") else "https://www.miit.gov.cn/gxsj/tjfx/zbgy/qc/index.html" if variable.startswith(("auto_","nev_")) else "","source_series_name":variable,"frequency":"monthly","original_unit":"percent" if variable.startswith(("lpr","nev_")) or variable.endswith("yoy") else "10,000 vehicles" if variable.startswith("auto_") else "index","processed_unit":"same as original","start_date":item["start"],"end_date":item["end"],"retrieval_date":"","retrieval_method":"Prevailing policy quote by month" if variable.startswith("lpr") else "Official retained report/raw" if item["actual_obs"] else "Not acquired","transformation":"Policy-state carry-forward only" if variable.startswith("lpr") else "NEV sales / auto sales * 100 where report does not state penetration" if variable=="nev_penetration" else "None","license_note":"Retain source attribution; consult provider terms.","status":item["status"],"notes":"Round 3 auxiliary variable."})
    additions=pd.DataFrame(source_rows)
    if not sources.empty: sources=sources.loc[~sources.variable.isin(additions.variable)]
    pd.concat([sources, additions],ignore_index=True).to_csv(source_path,index=False)
    print("Wrote auxiliary audit, anomalies, and raw protection ledger.")
    return 0
if __name__ == "__main__": raise SystemExit(main())
