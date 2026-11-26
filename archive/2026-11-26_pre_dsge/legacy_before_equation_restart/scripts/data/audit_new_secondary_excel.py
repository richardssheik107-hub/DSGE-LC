"""Generate the Data Freeze v2 secondary-Excel audit without modifying sources or v1."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.data_audit.secondary_excel import (  # noqa: E402
    BATTERY_SHA256,
    DONGWU_SHA256,
    V1_SHA256,
    AuditPaths,
    battery_auxiliary_catalog,
    build_battery_reconciliation,
    build_gap_status,
    build_quote_calendar_audit,
    build_spot_candidates,
    build_spot_reconciliation,
    read_battery_install,
    read_dongwu_spot,
    search_valid_series,
    sha256,
    workbook_inventory,
)


def main() -> None:
    paths = AuditPaths(ROOT)
    v1 = ROOT / "data/processed/core_monthly_panel.csv"
    before = {paths.dongwu: sha256(paths.dongwu), paths.battery: sha256(paths.battery), v1: sha256(v1)}
    expected = {paths.dongwu: DONGWU_SHA256, paths.battery: BATTERY_SHA256, v1: V1_SHA256}
    if before != expected:
        raise RuntimeError("Protected input hash mismatch")

    inventory = pd.DataFrame([workbook_inventory(paths.dongwu), workbook_inventory(paths.battery)])
    raw_spot, spot_metadata = read_dongwu_spot(paths.dongwu)
    canonical_daily = pd.read_csv(ROOT / "data/interim/industry/lc_spot_daily.csv")
    quote_audit = build_quote_calendar_audit(raw_spot, canonical_daily)
    spot_reconciliation = build_spot_reconciliation(raw_spot, quote_audit, canonical_daily)
    spot_candidates = build_spot_candidates(raw_spot, quote_audit)

    battery = read_battery_install(paths.battery)
    existing_battery = pd.read_csv(ROOT / "data/interim/public_gap_closure/battery_install_tail.csv")
    battery_reconciliation = build_battery_reconciliation(battery, existing_battery)
    auxiliary = battery_auxiliary_catalog(paths.battery)
    sc6_hits, output_hits = search_valid_series([paths.dongwu, paths.battery])
    gap_status = build_gap_status()

    metadata_dir = ROOT / "data/metadata"
    candidate_dir = ROOT / "data/processed/candidates"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(metadata_dir / "new_excel_secondary_audit.csv", index=False, encoding="utf-8-sig")
    quote_audit.to_csv(metadata_dir / "dongwu_smm_quote_calendar_audit.csv", index=False, encoding="utf-8-sig")
    spot_reconciliation.to_csv(metadata_dir / "dongwu_smm_lc_spot_reconciliation.csv", index=False, encoding="utf-8-sig", float_format="%.10g")
    spot_candidates.to_csv(candidate_dir / "lc_spot_dongwu_smm_tail_candidates.csv", index=False, encoding="utf-8-sig", float_format="%.10g")
    battery_reconciliation.to_csv(metadata_dir / "battery_chemistry_tail_reconciliation.csv", index=False, encoding="utf-8-sig", float_format="%.10g")
    gap_status.to_csv(metadata_dir / "data_freeze_v2_gap_status.csv", index=False, encoding="utf-8-sig")

    after = {path: sha256(path) for path in before}
    if before != after:
        raise RuntimeError("Protected inputs changed during read-only audit")
    summary = {
        "dongwu_spot": spot_metadata,
        "full_overlap_match_counts": spot_reconciliation.iloc[:69].match_status.value_counts().to_dict(),
        "battery_auxiliary": auxiliary,
        "sc6_search_result": "NO_MATCHING_SC6_CIF_CHINA_SERIES" if not sc6_hits else sc6_hits,
        "lc_output_search_result": "NO_CANONICAL_OUTPUT_FILL" if not output_hits else output_hits,
        "protected_hashes_unchanged": True,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
