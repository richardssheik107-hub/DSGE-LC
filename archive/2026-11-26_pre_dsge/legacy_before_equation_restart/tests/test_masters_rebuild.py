"""New workflow guards and C0 boundary probes; no empirical estimation."""
from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("masters_audit", ROOT / "scripts/audit_masters_rebuild.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
from src.theory_audit.c0_state_space import C0StateParams, one_step, transition_matrices, output_matrices


def payloads():
    def load(name):
        return json.loads((ROOT / "configs" / name).read_text(encoding="utf-8"))
    return load("masters_rebuild_plan_v1.json"), load("equation_roadmap_v1.json"), load("repository_lifecycle_20260919.json")


def test_current_plan_and_actual_deliverables():
    p, r, l = payloads()
    assert audit.validate(p, r, l) == []
    assert audit.check_files(ROOT, p) == []


@pytest.mark.parametrize("mutation,expected", [
    ("old_required", "OLD_MODEL_FORCED_INTO_NEW_THESIS"),
    ("old_draws", "LEGACY_RESULT_REUSE"),
    ("legacy_active", "LEGACY_REGISTRY_STILL_ACTIVE"),
    ("legacy_queue", "LEGACY_QUEUE_NOT_RETIRED"),
    ("legacy_autorun", "LEGACY_AUTORUN"),
    ("copy_chapters", "WRONG_THESIS_SCOPE"),
    ("fixed_chapters", "WRONG_THESIS_SCOPE"),
    ("forced_equations", "FORCED_COMPLEXITY"),
    ("all_relations", "ALL_RELATIONS_FORCED"),
    ("duplicate_relation", "RELATION_COVERAGE"),
    ("storage", "STORAGE_CLOSURE_CONFLICT"),
    ("production", "DYNAMIC_PRODUCTION_NOT_REPLACED"),
    ("estimate_early", "ESTIMATION_BEFORE_TWO_GATES"),
    ("fake_approval", "APPROVAL_WITHOUT_RECORD"),
    ("freeze_early", "PREMATURE_MODEL_FREEZE"),
    ("duplicate_phase", "PHASE_IDS"),
    ("bad_dependency", "UNKNOWN_DEPENDENCY"),
    ("cycle", "DEPENDENCY_CYCLE"),
    ("no_evidence", "COMPLETE_WITHOUT_EVIDENCE"),
    ("completed_early", "CLOSED_BEFORE_DEPENDENCY"),
    ("fake_submission", "SUBMISSION_WITHOUT_EVIDENCE"),
    ("snapshot", "SNAPSHOT_MISMATCH"),
])
def test_false_progress_and_scope_changes_fail(mutation, expected):
    p, r, l = payloads()
    if mutation == "old_required": p["legacy_model_required_in_new_thesis"] = True
    elif mutation == "old_draws": p["old_draws_reused_as_new_posterior"] = True
    elif mutation == "legacy_active": l["legacy_registries"][0]["execution_authority"] = True
    elif mutation == "legacy_queue": p["legacy_experiments"]["CMP_NOINV4"] = "RUNNING"
    elif mutation == "legacy_autorun": p["execution"]["legacy_experiments_auto_run"] = True
    elif mutation == "copy_chapters": p["thesis"]["copy_hog_chapter_structure"] = True
    elif mutation == "fixed_chapters": p["thesis"]["fixed_chapter_count"] = 5
    elif mutation == "forced_equations": p["equation_count_target"] = 28
    elif mutation == "all_relations": r["all_relations_jointly_active"] = True
    elif mutation == "duplicate_relation": r["relations"][0] = deepcopy(r["relations"][1])
    elif mutation == "storage": r["mutual_exclusion"] = []
    elif mutation == "production": r["replacement_rules"] = []
    elif mutation == "estimate_early": p["execution"]["allow_real_estimation"] = True
    elif mutation == "fake_approval": p["supervisor_gate"]["status"] = "CONFIRMED"
    elif mutation == "freeze_early": p["final_state_count"] = 4
    elif mutation == "duplicate_phase": p["phases"].append(deepcopy(p["phases"][0]))
    elif mutation == "bad_dependency": p["phases"][1]["depends_on"] = ["NOT_HERE"]
    elif mutation == "cycle": p["phases"][0]["depends_on"] = ["RB11"]
    elif mutation == "no_evidence": p["phases"][0]["evidence"] = []
    elif mutation == "completed_early": p["phases"][2]["status"] = "COMPLETE"
    elif mutation == "fake_submission": p["thesis"]["submission_ready"] = True
    elif mutation == "snapshot": l["snapshot_commit"] = "0" * 40
    assert expected in audit.validate(p, r, l)


def test_valid_gate_metadata_is_not_permanently_blocked():
    p, r, l = payloads()
    p["supervisor_gate"].update(status="CONFIRMED", approval_evidence="actual_note.md",
                                approved_model_id="EXAMPLE", approved_spec_commit="a" * 40)
    p["estimation_gate"]["status"] = "PASSED"
    p["estimation_gate"]["passed_checks"] = list(p["estimation_gate"]["required_checks"])
    p["execution"]["allow_real_estimation"] = True
    assert "ESTIMATION_BEFORE_TWO_GATES" not in audit.validate(p, r, l)
    # Metadata validity does not certify a document, so file existence is separate.
    assert "MISSING_FILE:actual_note.md" in audit.check_files(ROOT, p)


def test_required_paths_cannot_escape_workspace(tmp_path):
    assert audit.check_files(tmp_path, {"required_files": ["../secret.md"]}) == ["UNSAFE_PATH:../secret.md"]


def test_retired_paths_are_short_redirects_not_lost_history():
    _, _, life = payloads()
    for entry in life["retired_operational_documents"]:
        text = (ROOT / entry["path"]).read_text(encoding="utf-8")
        assert "历史计划入口已退役" in text
        assert life["snapshot_commit"] in text and "MASTER_PLAN.md" in text
        assert len(text) < 1500


def params():
    return C0StateParams(g=2., kappa=1., b=3., a=1.2, rho_d=.7,
                         rho_c=.6, sigma_d=.1, sigma_c=.2, inventory_loss=0.)


def test_zero_loss_inventory_has_unit_root_not_global_stationarity():
    A, _, _ = transition_matrices(params())
    assert A[3, 3] == 1.
    assert np.max(np.abs(np.linalg.eigvals(A))) == pytest.approx(1.)
    assert np.max(np.abs(np.linalg.eigvals(A[:3, :3]))) < 1.


def test_inventory_level_is_not_a_price_channel_under_E24():
    p = params()
    _, base_out = one_step(p, np.zeros(4), np.zeros(2), np.zeros(5))
    _, changed_out = one_step(p, np.array([0., 0., 0., 100.]), np.zeros(2), np.zeros(5))
    assert changed_out == pytest.approx(base_out)
    H, _, _ = output_matrices(p)
    assert np.all(H[:, 3] == 0)


def test_no_adjustment_removes_output_memory():
    A, _, _ = transition_matrices(replace(params(), kappa=0.))
    assert np.all(A[:, 2] == 0)


def test_deviation_mapping_and_three_primitive_residuals():
    p = params()
    lag = np.array([.2, -.1, .5, 2.])
    shock = np.array([.3, -.2])
    u = np.array([.1, .2, .05, .07, .03])
    x, out = one_step(p, lag, shock, u)
    z, c, q, inv = x
    price, y = out
    v, other, j, n, r = u
    assert (p.g+p.kappa)*q-price+c-p.kappa*lag[2] == pytest.approx(0, abs=1e-12)
    assert p.b*y-z+v+p.a*price == pytest.approx(0, abs=1e-12)
    assert q+r+n-p.a*y-other-j == pytest.approx(0, abs=1e-12)
    assert inv == pytest.approx(lag[3]+j)
