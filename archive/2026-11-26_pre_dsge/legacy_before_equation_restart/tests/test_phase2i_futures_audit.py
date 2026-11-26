import hashlib
from pathlib import Path

import pandas as pd

from src.futures.data_audit import (
    aggregate_contract_daily,
    audit_contract_file,
    discover_contract_directory,
    read_contract_file,
)


def _write_contract(path: Path, contract: str, rows: list[dict]) -> None:
    frame = pd.DataFrame(rows)
    frame.insert(0, "StockID", contract.lower())
    frame.to_csv(path, index=False)


def test_schema_discovery_prefers_smaller_ohlc_directory(tmp_path):
    small = tmp_path / "opaque_a"
    large = tmp_path / "opaque_b"
    small.mkdir(); large.mkdir()
    row = {"date": "2023-07-21 09:05:00", "open": 100, "high": 102, "low": 99,
           "close": 101, "vol": 5, "amount": 500, "cjbs": 2}
    for directory, multiplier in ((small, 1), (large, 200)):
        for contract in ("LC2401", "LC2402"):
            rows = [row] * multiplier
            _write_contract(directory / f"{contract}.csv", contract, rows)
    selected, candidates = discover_contract_directory([tmp_path], minimum_contracts=2)
    assert selected == small
    assert candidates.selected.sum() == 1
    assert set(candidates.schema_status) == {"PASS_5MIN_OHLC"}


def test_contract_audit_and_read_are_non_mutating(tmp_path):
    path = tmp_path / "LC2401.csv"
    rows = [
        {"date": "2023-07-21 09:05:00", "open": 100, "high": 105, "low": 99, "close": 102, "vol": 5, "amount": 500, "cjbs": 2},
        {"date": "2023-07-21 09:10:00", "open": 102, "high": 106, "low": 101, "close": 104, "vol": 7, "amount": 700, "cjbs": 3},
    ]
    _write_contract(path, "LC2401", rows)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    frame = read_contract_file(path)
    audit = audit_contract_file(path)
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert before == after
    assert list(frame.columns) == ["StockID", "date", "open", "high", "low", "close", "vol", "amount", "cjbs"]
    assert audit["schema_status"] == "PASS_5MIN_OHLC"
    assert audit["duplicate_timestamps"] == 0


def test_daily_ohlc_and_volume_aggregation(tmp_path):
    path = tmp_path / "LC2401.csv"
    rows = [
        {"date": "2023-07-21 09:05:00", "open": 100, "high": 105, "low": 99, "close": 102, "vol": 5, "amount": 500, "cjbs": 2},
        {"date": "2023-07-21 09:10:00", "open": 102, "high": 108, "low": 101, "close": 107, "vol": 7, "amount": 700, "cjbs": 3},
    ]
    _write_contract(path, "LC2401", rows)
    daily = aggregate_contract_daily([path]).iloc[0]
    assert daily.daily_open == 100
    assert daily.daily_high == 108
    assert daily.daily_low == 99
    assert daily.daily_close == 107
    assert daily.daily_volume == 12
    assert daily.daily_amount == 1200
    assert daily.daily_trades == 5
    assert bool(daily.ohlc_envelope_valid)
