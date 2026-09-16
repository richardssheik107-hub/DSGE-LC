import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "midterm_report_2026.md"


def _text() -> str:
    return REPORT.read_text(encoding="utf-8")


def test_midterm_report_has_required_title_length_and_sections():
    text = _text()
    assert text.startswith("# 碳酸锂价格波动的影响因素与定价机制研究")
    assert 15_000 <= len(re.sub(r"\s", "", text)) <= 25_000
    headings = re.findall(r"^## (\d+) (.+)$", text, flags=re.MULTILINE)
    assert [int(number) for number, _ in headings] == list(range(1, 20))


def test_midterm_report_keeps_model_and_sample_boundaries():
    text = _text()
    for token in (
        "半结构线性状态空间",
        "不是由代表性家庭和企业最优化",
        "2020年1月至2025年9月",
        "2021年1月至2025年9月",
        "57个月",
        "9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5",
    ):
        assert token in text


def test_midterm_report_preserves_mandatory_warnings_and_claim_limits():
    text = _text()
    for token in (
        "a_c", "b_n/b_q/rho_p", "rho_d", "sigma_d", "价格残差",
        "条件平滑", "短评价窗", "短期货样本", "不能直接命名为投机",
        "不可写“结构模型在所有期限预测最好”", "不能写“期货总是领先现货”",
        "[CITATION TO VERIFY]",
    ):
        assert token in text


def test_midterm_report_references_all_frozen_figures_and_tables():
    text = _text()
    for number in range(1, 11):
        assert f"图{number}" in text
    for number in range(1, 12):
        assert f"表{number}" in text
