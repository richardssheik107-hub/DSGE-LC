"""Shared, conservative utilities for Phase 1 public-data acquisition.

Fetchers never overwrite existing raw files.  They return a non-zero exit code
on network/access failures so that an unsuccessful source is not mistaken for
data coverage.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "public"
PROCESSED = ROOT / "data" / "processed" / "phase1"
METADATA = ROOT / "data" / "metadata"


def ensure_layout() -> None:
    for part in ("battery", "caam", "pboc_cfets", "chinabond", "nbs", "customs"):
        (RAW / part).mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "interim" / "public").mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    METADATA.mkdir(parents=True, exist_ok=True)


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_bytes_once(path: Path, content: bytes) -> Path:
    """Save a raw response once; make the filename collision-safe."""
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = path
    suffix = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{suffix}{path.suffix}")
        suffix += 1
    candidate.write_bytes(content)
    return candidate


def upsert_manifest(row: dict[str, object]) -> None:
    """Replace the row for one canonical variable without touching raw data."""
    ensure_layout()
    path = METADATA / "source_manifest.csv"
    fields = [
        "canonical_name", "source_name", "source_url", "retrieved_at", "raw_path",
        "frequency", "unit", "coverage_start", "coverage_end", "n_obs", "status", "notes",
    ]
    existing: list[dict[str, str]] = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            existing = list(csv.DictReader(handle))
    clean = {name: str(row.get(name, "")) for name in fields}
    existing = [item for item in existing if item.get("canonical_name") != clean["canonical_name"]]
    existing.append(clean)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(existing)
