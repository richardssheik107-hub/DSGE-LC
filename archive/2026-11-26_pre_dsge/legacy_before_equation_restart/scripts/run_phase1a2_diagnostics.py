"""Run Phase 1A-2 diagnostics on the protected 2020-01 to 2025-09 sample."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.diagnostics.break_tests import break_screening_table  # noqa: E402
from src.diagnostics.lag_screening import candidate_regions, hac_confirmation, lead_lag_table  # noqa: E402
from src.diagnostics.phase1a2 import margin_proxy_table, mechanism_evidence  # noqa: E402
from src.diagnostics.phase1a2_figures import (  # noqa: E402
    save_break_overview, save_heatmap, save_lag_profile, save_rolling_corr,
)
from src.diagnostics.stationarity import stationarity_table, zivot_andrews_table  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    config = json.loads((ROOT / "configs" / "phase1.yaml").read_text(encoding="utf-8"))
    freeze = ROOT / "data" / "processed" / "core_monthly_panel.csv"
    dataset_path = ROOT / "data" / "processed" / "phase1" / "monthly_structural_v1.csv"
    if sha256(freeze) != config["data_freeze_sha256"]:
        raise RuntimeError("Data Freeze v1 hash mismatch")
    data = pd.read_csv(dataset_path)
    if (len(data), data.month.iloc[0], data.month.iloc[-1]) != (69, "2020-01", "2025-09"):
        raise RuntimeError("Phase 1A-2 requires exactly the frozen 69-month sample")

    table_dir = ROOT / "outputs" / "phase1" / "tables"
    figure_dir = ROOT / "outputs" / "phase1" / "figures"
    local_dir = ROOT / "data" / "processed" / "phase1"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    margin = margin_proxy_table(data)
    stationarity = stationarity_table(data)
    za = zivot_andrews_table(data)
    correlations = lead_lag_table(data, margin)
    candidates = candidate_regions(correlations)
    hac = hac_confirmation(data, margin, candidates)
    breaks = break_screening_table(data, za, min_segment=18)
    evidence = mechanism_evidence(correlations, candidates, breaks)

    outputs = {
        local_dir / "margin_proxy_diagnostics.csv": margin,
        table_dir / "stationarity_results.csv": stationarity,
        table_dir / "zivot_andrews_results.csv": za,
        table_dir / "lead_lag_correlations.csv": correlations,
        table_dir / "lead_lag_candidate_regions.csv": candidates,
        table_dir / "lead_lag_hac_confirmation.csv": hac,
        table_dir / "structural_break_screening.csv": breaks,
        table_dir / "mechanism_evidence_table.csv": evidence,
    }
    for path, frame in outputs.items():
        frame.to_csv(path, index=False, encoding="utf-8-sig", float_format="%.8g")

    start, end = config["sample_start"], config["sample_end"]
    save_rolling_corr(data, "lc_spot_dlog", "spodumene_cny_dlog", figure_dir / "11_rolling_corr_spot_ore.png", "Spot–Ore Relationship Stability", start, end)
    save_rolling_corr(data, "lc_spot_dlog", "battery_install_dlog", figure_dir / "12_rolling_corr_spot_battery.png", "Spot–Battery Relationship Stability", start, end)
    save_rolling_corr(data, "lc_spot_dlog", "lc_output_dlog", figure_dir / "13_rolling_corr_spot_output.png", "Spot–Output Relationship Stability", start, end)
    save_heatmap(correlations, figure_dir / "14_lead_lag_heatmap_dlog.png", start, end)
    save_lag_profile(correlations, "Cost → Price", figure_dir / "15_cost_to_price_lag_profile.png", start, end)
    save_lag_profile(correlations, "Price → Future Supply", figure_dir / "16_price_to_output_lag_profile.png", start, end)
    save_lag_profile(correlations, "Margin → Future Supply", figure_dir / "17_margin_to_output_lag_profile.png", start, end, margin=True)
    save_break_overview(data, breaks, figure_dir / "18_break_candidates_overview.png", start, end)
    print(f"Phase 1A-2 complete: {len(outputs)} tables and 8 figures; sample {start} to {end}")


if __name__ == "__main__":
    main()
