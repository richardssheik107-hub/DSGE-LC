"""Build the local-only Phase 1A-1 structural dataset from Data Freeze v1."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.diagnostics.transformations import build_structural_dataset  # noqa: E402


def load_config() -> dict:
    # JSON syntax is valid YAML and keeps this project dependency-free.
    return json.loads((ROOT / "configs" / "phase1.yaml").read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_and_write() -> pd.DataFrame:
    config = load_config()
    source = ROOT / "data" / "processed" / "core_monthly_panel.csv"
    if not source.exists():
        raise FileNotFoundError("Data Freeze v1 is unavailable; commercial data must not be reconstructed")
    if sha256(source) != config["data_freeze_sha256"]:
        raise RuntimeError("Data Freeze v1 SHA256 does not match the protected configuration")
    core = pd.read_csv(source)
    data = build_structural_dataset(core, rolling_window=int(config["rolling_window"]))
    if len(data) != config["expected_months"] or data.month.iloc[0] != config["sample_start"] or data.month.iloc[-1] != config["sample_end"]:
        raise RuntimeError("Frozen sample boundaries do not match Phase 1 configuration")
    output = ROOT / "data" / "processed" / "phase1" / "monthly_structural_v1.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False, encoding="utf-8-sig", float_format="%.10g")
    return data


if __name__ == "__main__":
    result = build_and_write()
    print(f"Wrote {len(result)} frozen observations: {result.month.iloc[0]} to {result.month.iloc[-1]}")
