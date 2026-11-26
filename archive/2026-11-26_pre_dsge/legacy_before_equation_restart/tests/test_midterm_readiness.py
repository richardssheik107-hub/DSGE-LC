import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMO = ROOT / "docs" / "midterm_readiness_2026.md"
FREEZE_HASH = "9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5"


def test_readiness_memo_records_final_decision_and_required_audits():
    text = MEMO.read_text(encoding="utf-8")
    for token in (
        "MIDTERM_READY_WITH_WARNINGS", "Completed phases", "Data Freeze",
        "Main empirical findings", "Main warnings", "Reproducibility audit",
        "Git and safety audit", "Post-midterm plan",
    ):
        assert token in text


def test_readiness_memo_preserves_freeze_and_claim_boundaries():
    actual = hashlib.sha256((ROOT / "data/processed/core_monthly_panel.csv").read_bytes()).hexdigest()
    assert actual == FREEZE_HASH
    text = MEMO.read_text(encoding="utf-8")
    for token in (
        FREEZE_HASH, "N=57", "a_c", "b_n / b_q / rho_p",
        "不能命名为投机", "不是因果证明", "BVAR",
        "短样本不支持协整", "611 passed",
    ):
        assert token in text


def test_readiness_memo_lists_all_midterm_deliverables():
    text = MEMO.read_text(encoding="utf-8")
    for name in (
        "midterm_evidence_matrix.md", "midterm_report_2026.md",
        "midterm_slides_2026.md", "midterm_speaker_notes_2026.md",
        "midterm_defense_qa.md", "midterm_one_minute_summary.md",
        "midterm_three_minute_summary.md", "midterm_defense_checklist.md",
        "midterm_readiness_2026.md",
    ):
        assert name in text
