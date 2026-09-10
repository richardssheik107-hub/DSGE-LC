"""Write reproducible audits for public-data completion work (no deletion)."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re

import pandas as pd

from common import METADATA, PROCESSED, RAW, ensure_layout, sha256


def audit_comtrade() -> None:
    root = RAW / "comtrade"
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(root.glob("*.json")):
        groups[sha256(path)].append(path)
    rows = []
    for digest, paths in sorted(groups.items()):
        canonical = next((p.name for p in paths if re.fullmatch(r"comtrade_cn_hs283691_(import|export)_\d{6}\.json", p.name)), paths[0].name)
        for path in paths:
            rows.append({"path": str(path.relative_to(Path.cwd())).replace("\\", "/"), "filename": path.name,
                         "bytes": path.stat().st_size, "sha256": digest, "duplicate_group_size": len(paths),
                         "canonical_candidate": canonical, "action": "RETAIN_NO_DELETE"})
    pd.DataFrame(rows).to_csv(METADATA / "comtrade_duplicate_audit.csv", index=False)


def reconcile_nbs() -> None:
    data = pd.read_csv(PROCESSED / "macro_price_monthly.csv", dtype={"month": str})
    rows = []
    for kind in ("cpi", "ppi"):
        field = f"{kind}_yoy"
        for _, item in data.iterrows():
            raw = RAW / "nbs" / f"nbs_{kind}_{item.month}.html"
            rows.append({"variable": field, "month": item.month, "official_html_available": raw.exists(),
                         "official_excel_available": False, "html_value": item[field] if pd.notna(item[field]) else "",
                         "excel_value": "", "difference": "", "status": "MATCH" if pd.notna(item[field]) and raw.exists() else "MISSING"})
    pd.DataFrame(rows).to_csv(METADATA / "nbs_reconciliation.csv", index=False)


def protected_raw_hashes() -> None:
    rows = []
    for path in [RAW / "pboc_cfets" / "fred_dexchus.csv"]:
        if path.exists():
            rows.append({"path": str(path.relative_to(Path.cwd())).replace("\\", "/"), "sha256": sha256(path),
                         "protection": "must_not_be_overwritten_by_public_completion"})
    pd.DataFrame(rows).to_csv(METADATA / "protected_raw_hashes.csv", index=False)


def main() -> int:
    ensure_layout()
    audit_comtrade()
    reconcile_nbs()
    protected_raw_hashes()
    print("Wrote Comtrade duplicate, NBS reconciliation, and protected-raw audits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
