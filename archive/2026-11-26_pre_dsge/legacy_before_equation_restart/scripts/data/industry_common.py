"""Shared paths and helpers for the manually supplied industry workbooks."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "commercial" / "manual"
INTERIM_DIR = ROOT / "data" / "interim" / "industry"
PROCESSED_DIR = ROOT / "data" / "processed" / "industry"
METADATA_DIR = ROOT / "data" / "metadata"

LITHIUM_FILE = RAW_DIR / "钴锂小金属行业周度数据库-20251016.xlsx"
BATTERY_FILE = RAW_DIR / "动力电池行业数据库-20260323.xlsx"


def ensure_dirs() -> None:
    for path in (RAW_DIR, INTERIM_DIR, PROCESSED_DIR, METADATA_DIR):
        path.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig", na_rep="NA")


def as_month(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce").dt.to_period("M").astype("string")


def monthly_range(start: str, end: str) -> list[str]:
    return pd.period_range(start, end, freq="M").astype(str).tolist()
