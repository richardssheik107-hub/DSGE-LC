import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _read(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def test_slide_source_has_exactly_eighteen_ordered_slides():
    text = _read("midterm_slides_2026.md")
    slides = re.findall(r"^## Slide (\d+) — (.+)$", text, flags=re.MULTILINE)
    assert [int(number) for number, _ in slides] == list(range(1, 19))
    for token in (
        "12—15 分钟", "semi-structural linear state-space MVP",
        "MIDTERM_READY_WITH_WARNINGS", "Figure 10", "N=57",
    ):
        assert token in text


def test_speaker_notes_cover_every_slide_and_target_duration():
    text = _read("midterm_speaker_notes_2026.md")
    slides = re.findall(r"^## Slide (\d+) —", text, flags=re.MULTILINE)
    assert [int(number) for number in slides] == list(range(1, 19))
    assert "13—14 分钟" in text
    assert len(text) > 3_000


def test_defense_qa_has_at_least_thirty_bounded_answers():
    text = _read("midterm_defense_qa.md")
    questions = re.findall(r"^### Q(\d+) ", text, flags=re.MULTILINE)
    assert len(questions) >= 30
    assert [int(number) for number in questions] == list(range(1, len(questions) + 1))
    assert text.count("**直接回答：**") == len(questions)
    assert text.count("限制是") >= 30


def test_summaries_and_checklist_preserve_core_boundaries():
    one = _read("midterm_one_minute_summary.md")
    three = _read("midterm_three_minute_summary.md")
    checklist = _read("midterm_defense_checklist.md")
    assert 300 <= len(one) <= 1_200
    assert 1_000 <= len(three) <= 4_000
    for token in (
        "57个月", "价格残差", "Data Freeze", "MCMC", "期货",
        "不写“结构模型所有期限预测最好”", "midterm_readiness_2026.md",
    ):
        assert token in one + three + checklist
