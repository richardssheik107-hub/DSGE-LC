"""Read-only discovery, integrity audit and daily aggregation of GFEX LC files."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


CONTRACT_PATTERN = re.compile(r"^LC\d{4}\.csv$", re.IGNORECASE)
EXPECTED_5MIN_COLUMNS = (
    "StockID", "date", "open", "high", "low", "close", "vol", "amount", "cjbs",
)
PRICE_COLUMNS = ("open", "high", "low", "close")
NUMERIC_COLUMNS = PRICE_COLUMNS + ("vol", "amount", "cjbs")


def sha256_file(path: str | Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def path_fingerprint(path: str | Path) -> str:
    normalized = str(Path(path).resolve()).replace("\\", "/").casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _contract_files(root: Path) -> Iterable[Path]:
    try:
        for path in root.rglob("*.csv"):
            if CONTRACT_PATTERN.fullmatch(path.name):
                yield path
    except (OSError, PermissionError):
        return


def _schema_status(path: Path, expected_columns: Sequence[str]) -> tuple[str, str]:
    try:
        columns = tuple(pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        return "READ_ERROR", type(exc).__name__
    missing = [column for column in expected_columns if column not in columns]
    if missing:
        return "SCHEMA_MISMATCH", ";".join(missing)
    return "PASS_5MIN_OHLC", ""


def discover_contract_directory(
    roots: Sequence[str | Path],
    *,
    minimum_contracts: int = 30,
    expected_columns: Sequence[str] = EXPECTED_5MIN_COLUMNS,
) -> tuple[Path, pd.DataFrame]:
    """Select the smallest complete OHLC directory without relying on folder names."""
    groups: dict[Path, list[Path]] = {}
    for raw_root in roots:
        root = Path(raw_root).expanduser()
        if not root.exists():
            continue
        for path in _contract_files(root):
            groups.setdefault(path.parent, []).append(path)

    rows: list[dict[str, object]] = []
    for directory, paths in groups.items():
        distinct = sorted({path.name.upper(): path for path in paths}.values())
        if len(distinct) < minimum_contracts:
            continue
        status, detail = _schema_status(distinct[0], expected_columns)
        rows.append({
            "source_directory": str(directory.resolve()),
            "source_directory_fingerprint": path_fingerprint(directory),
            "contract_count": len(distinct),
            "total_bytes": int(sum(path.stat().st_size for path in distinct)),
            "first_contract": min(path.stem.upper() for path in distinct),
            "last_contract": max(path.stem.upper() for path in distinct),
            "schema_status": status,
            "schema_detail": detail,
        })
    if not rows:
        raise FileNotFoundError(f"no directory with at least {minimum_contracts} LCYYMM files")
    candidates = pd.DataFrame(rows)
    eligible = candidates.loc[candidates.schema_status.eq("PASS_5MIN_OHLC")].copy()
    if eligible.empty:
        raise ValueError("LC directories were found, but no 5-minute OHLC schema passed")
    eligible = eligible.sort_values(
        ["total_bytes", "contract_count", "source_directory_fingerprint"],
        ascending=[True, False, True],
        kind="mergesort",
    )
    selected_path = Path(eligible.iloc[0].source_directory)
    candidates["selected"] = candidates.source_directory.eq(str(selected_path))
    candidates = candidates.sort_values(
        ["selected", "schema_status", "total_bytes"], ascending=[False, True, True]
    ).reset_index(drop=True)
    return selected_path, candidates


def list_contract_files(directory: str | Path) -> list[Path]:
    files = [path for path in Path(directory).glob("*.csv") if CONTRACT_PATTERN.fullmatch(path.name)]
    return sorted(files, key=lambda path: path.name.upper())


def read_contract_file(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    frame = pd.read_csv(path, encoding="utf-8-sig")
    missing = [column for column in EXPECTED_5MIN_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{path.name}: missing 5-minute columns {missing}")
    frame = frame.loc[:, EXPECTED_5MIN_COLUMNS].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["StockID"] = frame["StockID"].astype(str).str.upper().str.strip()
    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def audit_contract_file(path: str | Path) -> dict[str, object]:
    path = Path(path)
    try:
        frame = read_contract_file(path)
        timestamps = frame.date
        valid_timestamps = timestamps.dropna()
        prices = frame.loc[:, PRICE_COLUMNS]
        negative_price = (prices < 0).any(axis=1)
        nonpositive_price = (prices <= 0).any(axis=1)
        return {
            "contract": path.stem.upper(),
            "path_fingerprint": path_fingerprint(path),
            "rows": int(len(frame)),
            "first_timestamp": valid_timestamps.min(),
            "last_timestamp": valid_timestamps.max(),
            "first_trading_day": valid_timestamps.min().date() if len(valid_timestamps) else pd.NaT,
            "last_trading_day": valid_timestamps.max().date() if len(valid_timestamps) else pd.NaT,
            "price_min": float(prices.min().min()),
            "price_max": float(prices.max().max()),
            "volume_sum": float(frame.vol.sum(min_count=1)),
            "duplicate_timestamps": int(timestamps.duplicated(keep=False).sum()),
            "non_monotonic_timestamp_count": int((timestamps.diff().dropna() < pd.Timedelta(0)).sum()),
            "missing_timestamp": int(timestamps.isna().sum()),
            "missing_ohlc": int(prices.isna().any(axis=1).sum()),
            "negative_price": int(negative_price.sum()),
            "nonpositive_price": int(nonpositive_price.sum()),
            "negative_volume": int((frame.vol < 0).sum()),
            "zero_volume_rows": int(frame.vol.eq(0).sum()),
            "schema_status": "PASS_5MIN_OHLC",
        }
    except (OSError, ValueError, UnicodeError, pd.errors.ParserError) as exc:
        return {
            "contract": path.stem.upper(),
            "path_fingerprint": path_fingerprint(path),
            "rows": 0,
            "schema_status": f"FAIL:{type(exc).__name__}:{exc}",
        }


def build_raw_manifest(files: Sequence[str | Path]) -> pd.DataFrame:
    rows = []
    for raw_path in files:
        path = Path(raw_path)
        stat = path.stat()
        rows.append({
            "contract": path.stem.upper(),
            "file_name": path.name,
            "path_fingerprint": path_fingerprint(path),
            "bytes": int(stat.st_size),
            "modified_time_utc": pd.Timestamp(stat.st_mtime, unit="s", tz="UTC"),
            "sha256": sha256_file(path),
        })
    return pd.DataFrame(rows).sort_values("contract").reset_index(drop=True)


def aggregate_contract_daily(files: Sequence[str | Path]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for raw_path in files:
        path = Path(raw_path)
        frame = read_contract_file(path)
        frame = frame.loc[frame.date.notna()].sort_values("date", kind="mergesort")
        frame["trading_day"] = frame.date.dt.normalize()
        contract = path.stem.upper()
        observed = frame.StockID.dropna().unique()
        if len(observed) and set(observed) != {contract}:
            raise ValueError(f"{path.name}: StockID does not match file contract")
        daily = frame.groupby("trading_day", sort=True).agg(
            daily_open=("open", "first"),
            daily_high=("high", "max"),
            daily_low=("low", "min"),
            daily_close=("close", "last"),
            daily_volume=("vol", "sum"),
            daily_amount=("amount", "sum"),
            daily_trades=("cjbs", "sum"),
            intraday_rows=("date", "size"),
        ).reset_index().rename(columns={"trading_day": "date"})
        daily.insert(1, "contract", contract)
        daily["ohlc_envelope_valid"] = (
            daily.daily_high.ge(daily[["daily_open", "daily_close"]].max(axis=1))
            & daily.daily_low.le(daily[["daily_open", "daily_close"]].min(axis=1))
        )
        daily["prices_positive"] = daily.loc[:, ["daily_open", "daily_high", "daily_low", "daily_close"]].gt(0).all(axis=1)
        rows.append(daily)
    if not rows:
        raise ValueError("no contract files supplied")
    result = pd.concat(rows, ignore_index=True)
    result = result.sort_values(["date", "contract"], kind="mergesort").reset_index(drop=True)
    if result.duplicated(["date", "contract"]).any():
        raise ValueError("daily contract aggregation contains duplicate contract-days")
    return result
