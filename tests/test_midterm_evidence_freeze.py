import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE_HASH = "9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5"


def test_required_midterm_evidence_documents_exist():
    names = (
        "midterm_evidence_matrix.md",
        "midterm_claim_registry.md",
        "midterm_figure_manifest.md",
        "midterm_table_manifest.md",
        "midterm_result_digest.md",
        "midterm_reproducibility_manifest.md",
    )
    for name in names:
        path = ROOT / "docs" / name
        assert path.exists() and path.stat().st_size > 500, name


def test_ten_frozen_main_figures_exist():
    paths = (
        "outputs/phase1/figures/01_lc_spot_level.png",
        "outputs/midterm/figure_02_research_mechanism.png",
        "outputs/midterm/figure_03_data_model_map.png",
        "outputs/midterm/figure_04_posterior_parameter_summary.png",
        "outputs/phase2/phase2e/irf_price_4shocks.png",
        "outputs/phase2/phase2e/fevd_price_posterior_bands.png",
        "outputs/phase2/phase2f/historical_price_decomposition.png",
        "outputs/midterm/figure_08_structural_oos_comparison.png",
        "outputs/midterm/figure_09_external_validation.png",
        "outputs/phase2/phase2i/lead_lag_correlation.png",
    )
    assert len(paths) == 10
    for raw in paths:
        path = ROOT / raw
        assert path.exists() and path.stat().st_size > 0, raw


def test_claim_registry_keeps_required_warning_and_prohibition_boundaries():
    text = (ROOT / "docs/midterm_claim_registry.md").read_text(encoding="utf-8")
    for token in (
        "a_c", "b_n", "b_q", "rho_p", "rho_d", "sigma_d", "N=57",
        "conditional-smoothed HD", "short OOS", "short futures overlap",
        "The structural model forecasts best at all horizons",
        "The price shock measures speculation",
        "Spot and futures are cointegrated",
    ):
        assert token in text


def test_midterm_freeze_and_git_safety_assertions_are_recorded():
    actual = hashlib.sha256((ROOT / "data/processed/core_monthly_panel.csv").read_bytes()).hexdigest()
    assert actual == FREEZE_HASH
    status = (ROOT / "docs/project_status_2026_09_15.md").read_text(encoding="utf-8")
    manifest = (ROOT / "docs/midterm_reproducibility_manifest.md").read_text(encoding="utf-8")
    assert "CORE MIDTERM EXPERIMENTS: FROZEN" in status
    assert "Futures raw files committed: NO" in manifest
    assert "Posterior raw artifacts committed: NO" in manifest
    assert "Credentials committed: NO" in manifest
