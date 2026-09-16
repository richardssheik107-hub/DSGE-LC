"""R1-6 machine-readable evidence registry integrity checks."""
import json
from pathlib import Path

import pytest

from scripts.build_r1_result_registry import REQUIRED, REV, build, claim_revisions


def test_claim_revision_taxonomy_and_unique_ids():
    rows = claim_revisions()
    allowed = {"UNCHANGED", "NUMERICALLY_REVISED", "WEAKENED", "REVERSED",
               "NOT_EVALUATED", "WITHDRAWN_PENDING_VALIDATION"}
    assert len(rows) >= 10
    assert len({row["claim_id"] for row in rows}) == len(rows)
    assert all(row["revision"] in allowed for row in rows)
    assert any(row["revision"] == "WEAKENED" for row in rows)


def test_private_registry_entries_have_required_provenance_and_distinct_stats():
    if not (REV / "preflight/inputs_before.json").exists():
        pytest.skip("private R1 revision outputs are unavailable in portable checkout")
    data = build()
    assert data["schema"] == "r1_result_registry_v1"
    assert data["result_count"] == len(data["results"])
    assert data["result_count"] >= 50
    for row in data["results"]:
        assert set(REQUIRED).issubset(row)
        assert row["n"] > 0
        assert len(row["data_hash"]) == 64
        assert len(row["source_file_sha256"]) == 64
        assert len(row["source_commit"]) == 40
        assert row["technical_status"]
        assert row["interpretation_status"]
        assert row["sample_start"] <= row["sample_end"]
        assert not Path(row["source_file"]).is_absolute()
    assert {row["claim_id"] for row in data["results"]}.issuperset(
        {"POSTERIOR_CONVERGENCE", "FEVD_PRICE_12M", "HISTORICAL_EPISODES",
         "HISTORICAL_RAW_LOG_UNIT", "MEASUREMENT_SCALER", "FUTURES_LEADING",
         "STRUCTURAL_OOS", "INVENTORY_EXTERNAL", "EXTERNAL_COST_INDEPENDENCE"})
    assert all(row["evidence_result_keys"] or row["archived_evidence"]
               for row in data["claim_revisions"])
    sensitivity = next(row for row in data["results"] if row["claim_id"] == "HISTORICAL_HIGH_SENSITIVITY")
    assert sensitivity["posterior_artifact_hash"] is None
    assert len(sensitivity["posterior_artifact_hashes"]) == 7
    for row in data["results"]:
        if row["claim_id"] in {"INVENTORY_EXTERNAL", "EXTERNAL_COST_INDEPENDENCE"}:
            assert any("industry/" in path for path in row["input_hashes"])
        if row["claim_id"] == "STRUCTURAL_OOS":
            assert row["sample_start"] == row["target_start"]
            assert row["sample_end"] == row["target_end"]
            assert row["origin_start"] <= row["origin_end"]
            assert len(row["input_hashes"]) >= 6
        if row["claim_id"] == "FUTURES_LEADING":
            assert row["source_row_or_key"]["column"] in (
                "matched_ex_post_pearson", "matched_lagged_main_pearson")
    final = REV / "result_registry_final/result_registry.json"
    if final.exists():
        assert json.loads(final.read_text(encoding="utf-8")) == data
