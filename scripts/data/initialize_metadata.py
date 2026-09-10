"""Register Phase 1 variables intentionally outside this public-data round."""
from __future__ import annotations
from common import ensure_layout, timestamp, upsert_manifest

def main() -> int:
    ensure_layout()
    items = [
        ("lc_spot", "Mysteel", "SMM / Wind / Baiinfo", "daily", "Need one consistent battery-grade lithium carbonate spot series."),
        ("lc_output", "Mysteel", "SMM / Baiinfo / Wind", "monthly", "Need continuous China lithium carbonate monthly production."),
        ("spodumene_price", "Mysteel", "SMM / Baiinfo", "daily_or_monthly", "Prefer 6% Li2O CIF China concentrate price."),
        ("lc_futures", "Existing repository raw files", "GFEX", "daily/minute/tick", "NOT_NEEDED: instructed read-only and not present in this checkout."),
        ("lc_options", "Existing repository raw files", "GFEX", "daily/minute/tick", "NOT_NEEDED: instructed read-only and not present in this checkout."),
    ]
    for name, preferred, alternative, frequency, note in items:
        status = "NOT_NEEDED" if name in {"lc_futures", "lc_options"} else "MANUAL_REQUIRED"
        upsert_manifest({"canonical_name": name, "source_name": preferred, "source_url": "",
                         "retrieved_at": timestamp(), "frequency": frequency, "unit": "see data dictionary",
                         "coverage_start": "2020-01-01", "coverage_end": "2026-06-30", "n_obs": "0",
                         "status": status, "notes": f"Preferred: {preferred}; alternative: {alternative}. {note}"})
    print("Registered manual-source placeholders and protected-market-data records.")
    return 0
if __name__ == "__main__": raise SystemExit(main())
