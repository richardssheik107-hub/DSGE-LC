"""Audit the active master's workflow, never estimate or certify a thesis.

Standard library only. Legacy ledgers are classified by the lifecycle registry;
they remain intact for historical tests. This command is the active entry point.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

SHA = re.compile(r"[0-9a-f]{40}\Z")
PHASE = re.compile(r"RB\d{2}\Z")
STATUSES = {"PLANNED", "IN_PROGRESS", "COMPLETE", "BLOCKED", "DEFERRED_WITH_REASON"}
CLOSED = {"COMPLETE", "DEFERRED_WITH_REASON"}
LEGACY = {"CMP_NOINV4", "CMP_COSTFEEDBACK15", "ROB_COMMON57", "FUT_DAILY_INCREMENT"}


def validate(plan: dict, roadmap: dict, life: dict) -> list[str]:
    """Check metadata consistency only; cannot attest actual approval or research."""
    errors: list[str] = []
    if plan.get("workflow_id") != "MASTERS_REBUILD_20260919" or plan.get("active") is not True:
        errors.append("WRONG_ACTIVE_WORKFLOW")
    if not SHA.fullmatch(str(plan.get("reviewed_commit", ""))):
        errors.append("INVALID_SNAPSHOT")
    if life.get("snapshot_commit") != plan.get("reviewed_commit"):
        errors.append("SNAPSHOT_MISMATCH")
    if life.get("authority") != "configs/masters_rebuild_plan_v1.json":
        errors.append("WRONG_AUTHORITY")
    if any(v.get("execution_authority") is not False for v in life.get("legacy_registries", [])):
        errors.append("LEGACY_REGISTRY_STILL_ACTIVE")
    if {v.get("path") for v in life.get("legacy_registries", [])} != {"configs/thesis_workplan.json", "configs/finalization_tasks.json"}:
        errors.append("LEGACY_REGISTRY_COVERAGE")
    if any(not SHA.fullmatch(str(v)) for v in life.get("protected_trees", {}).values()):
        errors.append("INVALID_PROTECTED_OBJECT")
    if life.get("private_data_deleted") is not False or life.get("history_rewritten") is not False:
        errors.append("DESTRUCTIVE_REBUILD")
    if set(plan.get("legacy_experiments", {})) != LEGACY or any(v != "RETIRED_FROM_ACTIVE_QUEUE_NOT_RUN" for v in plan.get("legacy_experiments", {}).values()):
        errors.append("LEGACY_QUEUE_NOT_RETIRED")
    if plan.get("legacy_model_required_in_new_thesis") is not False:
        errors.append("OLD_MODEL_FORCED_INTO_NEW_THESIS")
    if plan.get("old_results_relabelled") or plan.get("old_draws_reused_as_new_posterior"):
        errors.append("LEGACY_RESULT_REUSE")
    if plan.get("equation_count_target") is not None or plan.get("forced_extensions"):
        errors.append("FORCED_COMPLEXITY")
    thesis = plan.get("thesis", {})
    if thesis.get("kind") != "MASTERS_DISSERTATION" or thesis.get("copy_hog_chapter_structure") is not False or thesis.get("fixed_chapter_count") is not None:
        errors.append("WRONG_THESIS_SCOPE")
    phases = plan.get("phases", [])
    ids = [p.get("id") for p in phases]
    if not ids or any(not PHASE.fullmatch(str(i)) for i in ids) or len(ids) != len(set(ids)):
        return errors + ["PHASE_IDS"]
    by_id = {p["id"]: p for p in phases}
    for p in phases:
        if p.get("status") not in STATUSES:
            errors.append("UNKNOWN_PHASE_STATUS")
        if p.get("status") in CLOSED and not p.get("evidence"):
            errors.append("COMPLETE_WITHOUT_EVIDENCE")
        if p.get("status") == "DEFERRED_WITH_REASON" and not p.get("reason"):
            errors.append("DEFERRED_WITHOUT_REASON")
        for dep in p.get("depends_on", []):
            if dep not in by_id:
                errors.append("UNKNOWN_DEPENDENCY")
            elif p.get("status") in CLOSED and by_id[dep].get("status") not in CLOSED:
                errors.append("CLOSED_BEFORE_DEPENDENCY")
    visiting, done = set(), set()
    def visit(node: str) -> None:
        if node in visiting:
            errors.append("DEPENDENCY_CYCLE")
            return
        if node in done or node not in by_id:
            return
        visiting.add(node)
        for dep in by_id[node].get("depends_on", []):
            visit(dep)
        visiting.remove(node)
        done.add(node)
    for node in by_id:
        visit(node)
    if not set(plan.get("current_focus", [])).issubset(by_id):
        errors.append("UNKNOWN_CURRENT_FOCUS")
    sg, eg = plan.get("supervisor_gate", {}), plan.get("estimation_gate", {})
    approved = sg.get("status") == "CONFIRMED" and bool(sg.get("approval_evidence")) and bool(sg.get("approved_model_id")) and bool(SHA.fullmatch(str(sg.get("approved_spec_commit", ""))))
    technical = eg.get("status") == "PASSED" and bool(eg.get("required_checks")) and set(eg.get("required_checks", [])).issubset(eg.get("passed_checks", []))
    exe = plan.get("execution", {})
    if sg.get("status") == "CONFIRMED" and not approved:
        errors.append("APPROVAL_WITHOUT_RECORD")
    if exe.get("legacy_experiments_auto_run") is not False:
        errors.append("LEGACY_AUTORUN")
    if exe.get("allow_real_estimation") or plan.get("new_empirical_estimation") or by_id.get("RB07", {}).get("status") in {"IN_PROGRESS", "COMPLETE"}:
        if not approved or not technical:
            errors.append("ESTIMATION_BEFORE_TWO_GATES")
    if not approved and (plan.get("final_state_count") is not None or plan.get("free_parameter_count") is not None or plan.get("final_model_id") is not None):
        errors.append("PREMATURE_MODEL_FREEZE")
    if thesis.get("submission_ready") is True and not (thesis.get("school_rules_verified") and thesis.get("final_approval_evidence")):
        errors.append("SUBMISSION_WITHOUT_EVIDENCE")
    equations = [r.get("id") for r in roadmap.get("relations", [])]
    if len(equations) != 28 or set(equations) != {f"E{i:02}" for i in range(1, 29)}:
        errors.append("RELATION_COVERAGE")
    if roadmap.get("all_relations_jointly_active") is not False:
        errors.append("ALL_RELATIONS_FORCED")
    if ["E23", "E24"] not in roadmap.get("mutual_exclusion", []):
        errors.append("STORAGE_CLOSURE_CONFLICT")
    if {"when": "E14", "replaces": ["E10", "E11"]} not in roadmap.get("replacement_rules", []):
        errors.append("DYNAMIC_PRODUCTION_NOT_REPLACED")
    if not plan.get("required_files"):
        errors.append("EMPTY_DELIVERABLES")
    return sorted(set(errors))


def check_files(root: Path, plan: dict) -> list[str]:
    root = root.resolve()
    paths = list(plan.get("required_files", []))
    for phase in plan.get("phases", []):
        paths.extend(phase.get("evidence", []))
    evidence = plan.get("supervisor_gate", {}).get("approval_evidence")
    if evidence:
        paths.append(evidence)
    errors = []
    for relative in sorted(set(paths)):
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            errors.append("UNSAFE_PATH:" + relative)
        elif not target.is_file():
            errors.append("MISSING_FILE:" + relative)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        def load(name):
            return json.loads((root / "configs" / name).read_text(encoding="utf-8"))
        plan = load("masters_rebuild_plan_v1.json")
        errors = validate(plan, load("equation_roadmap_v1.json"), load("repository_lifecycle_20260919.json"))
        errors += check_files(root, plan)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors = ["READ_OR_SCHEMA_ERROR:" + str(exc)]
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors,
                      "scope": "ACTIVE_WORKFLOW_METADATA_AND_DELIVERABLE_EXISTENCE",
                      "new_estimation_run": False, "supervisor_approval_certified": False,
                      "private_hashes_recomputed": False}, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
