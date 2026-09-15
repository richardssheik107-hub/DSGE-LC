"""Generate Phase 1A-1 audits, descriptive tables and figures only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "phase1"))

from build_phase1a1_dataset import build_and_write, load_config  # noqa: E402
from src.diagnostics.descriptive import (  # noqa: E402
    annual_summary,
    contemporaneous_correlations,
    data_audit,
    descriptive_growth,
    descriptive_levels,
    large_changes,
    save_line_figure,
    save_mom_grid,
)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig", float_format="%.10g")


def main() -> None:
    config = load_config()
    data = build_and_write()
    output = ROOT / "outputs" / "phase1"
    audit_dir = output / "data_audit"
    tables = output / "tables"
    figures = output / "figures"
    write_csv(data_audit(data, config, config["units"]), audit_dir / "phase1a1_data_audit.csv")
    write_csv(large_changes(data, config["large_change_threshold_pct"], config["extreme_change_threshold_pct"]), audit_dir / "phase1a1_large_changes.csv")
    write_csv(descriptive_levels(data), tables / "descriptive_statistics_levels.csv")
    write_csv(descriptive_growth(data), tables / "descriptive_statistics_growth.csv")
    write_csv(contemporaneous_correlations(data), tables / "contemporaneous_correlations.csv")
    write_csv(annual_summary(data), tables / "annual_summary.csv")

    start, end = config["sample_start"], config["sample_end"]
    save_line_figure(data, [("lc_spot", "LC spot")], figures / "01_lc_spot_level.png", "Lithium Carbonate Spot Price", "CNY/t", start, end)
    save_line_figure(data, [("lc_spot_log", "Log LC spot")], figures / "02_lc_spot_log.png", "Lithium Carbonate Spot Price: Log Level", "Natural log", start, end)
    save_line_figure(data, [("lc_output", "LC output")], figures / "03_lc_output_level.png", "China Lithium Carbonate Monthly Output", "Metric tons", start, end)
    save_line_figure(data, [("battery_install", "Battery installation")], figures / "04_battery_install_level.png", "China Power-Battery Installation", "GWh", start, end)
    save_line_figure(data, [("battery_install_yoy_pct", "Battery installation YoY")], figures / "05_battery_install_yoy.png", "Power-Battery Installation: Year-on-Year Change", "Percent", start, end)
    save_line_figure(data, [("lc_spot_z", "LC spot"), ("spodumene_price_z", "Spodumene SC6")], figures / "06_spot_vs_spodumene_zscore.png", "LC Spot and Spodumene Price", "Sample z-score", start, end, "Standardized levels; contemporaneous visual comparison only")
    save_line_figure(data, [("spodumene_cny_t", "Spodumene CNY proxy")], figures / "07_spodumene_cny_proxy.png", "RMB-Denominated Spodumene Price Proxy", "CNY/t concentrate", start, end, "Not lithium-carbonate production cost")
    save_line_figure(data, [("lc_spot_z", "LC spot"), ("lc_output_z", "LC output"), ("spodumene_cny_z", "Spodumene CNY proxy"), ("battery_install_z", "Battery installation")], figures / "08_core_variables_zscore.png", "Standardized Core Economic Variables", "Sample z-score", start, end, "Price, supply, ore-cost proxy and demand; descriptive only")
    save_mom_grid(data, figures / "09_core_mom_changes.png", start, end)
    window = config["rolling_window"]
    save_line_figure(data, [
        (f"lc_spot_dlog_rolling_std_{window}m", "LC spot"),
        (f"spodumene_price_dlog_rolling_std_{window}m", "Spodumene SC6"),
        (f"lc_output_dlog_rolling_std_{window}m", "LC output"),
        (f"battery_install_dlog_rolling_std_{window}m", "Battery installation"),
    ], figures / "10_rolling_volatility.png", "Rolling Monthly Volatility", "12-month std of log difference", start, end, "Comparable growth-rate volatility; no structural-break inference")

    summary = {
        "rows": len(data),
        "start": data.month.iloc[0],
        "end": data.month.iloc[-1],
        "large_change_flags": len(large_changes(data, config["large_change_threshold_pct"], config["extreme_change_threshold_pct"])),
        "figures": len(list(figures.glob("*.png"))),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
