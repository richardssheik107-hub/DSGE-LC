"""Validate thesis planning metadata; never estimate or certify scientific results.

Standard-library only. --check-git-baseline checks objects at the recorded commit,
not private data SHA256s, the current working tree or local visual acceptance.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path

SHA1 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMPLETED = {"COMPLETE", "OMITTED_WITH_REASON"}


def validate(baseline: dict, plan: dict) -> list[str]:
    errors: list[str] = []
    if not SHA1.fullmatch(str(baseline.get('source_commit', ''))):
        errors.append('INVALID_BASE_COMMIT')
    if baseline.get('source_commit') != plan.get('baseline_commit'):
        errors.append('BASELINE_COMMIT_MISMATCH')
    if baseline.get('baseline_id') != plan.get('baseline_id'):
        errors.append('BASELINE_ID_MISMATCH')
    if not SHA256.fullmatch(str(baseline.get('private_core_sha256_recorded', ''))):
        errors.append('INVALID_RECORDED_CORE_HASH')
    for path, obj in baseline.get('protected_git_objects', {}).items():
        if obj.get('type') not in {'tree', 'blob'} or not SHA1.fullmatch(str(obj.get('sha', ''))):
            errors.append(f'INVALID_GIT_OBJECT:{path}')
    tasks = plan.get('tasks', [])
    ids = [t.get('id') for t in tasks]
    if not ids or None in ids or len(ids) != len(set(ids)):
        errors.append('EMPTY_OR_DUPLICATE_TASK_IDS')
        return errors
    by_id = {t['id']: t for t in tasks}
    for t in tasks:
        if t.get('status') not in plan.get('status_definitions', {}):
            errors.append(f'UNKNOWN_TASK_STATUS:{t["id"]}')
        for dep in t.get('depends_on', []):
            if dep not in by_id:
                errors.append(f'UNKNOWN_DEPENDENCY:{t["id"]}:{dep}')
            elif t.get('status') in COMPLETED and by_id[dep].get('status') not in COMPLETED:
                errors.append(f'COMPLETED_WITH_OPEN_DEPENDENCY:{t["id"]}:{dep}')
        if t.get('status') in COMPLETED and not t.get('evidence'):
            errors.append(f'COMPLETED_WITHOUT_EVIDENCE:{t["id"]}')
        if t.get('status') == 'OMITTED_WITH_REASON' and not t.get('reason'):
            errors.append(f'OMITTED_WITHOUT_REASON:{t["id"]}')
    visiting, done = set(), set()
    def visit(node: str):
        if node in visiting:
            errors.append(f'CYCLIC_DEPENDENCY:{node}')
            return
        if node in done or node not in by_id:
            return
        visiting.add(node)
        for dep in by_id[node].get('depends_on', []):
            visit(dep)
        visiting.remove(node)
        done.add(node)
    for node in by_id:
        visit(node)
    experiments = plan.get('planned_experiments', [])
    names = [e.get('id') for e in experiments]
    if not names or len(names) != len(set(names)):
        errors.append('EMPTY_OR_DUPLICATE_EXPERIMENTS')
    for e in experiments:
        if e.get('task') not in by_id:
            errors.append(f'EXPERIMENT_WITHOUT_TASK:{e.get("id")}')
        status = e.get('status')
        if status in {'PROTOCOL_DRAFT_NOT_RUN', 'PROTOCOL_FROZEN_NOT_RUN'} and e.get('result_evidence'):
            errors.append(f'UNRUN_EXPERIMENT_HAS_RESULTS:{e.get("id")}')
        elif status in {'EMPIRICAL_COMPLETE', 'EMPIRICAL_COMPLETE_WITH_LIMITS'}:
            if not e.get('result_evidence'):
                errors.append(f'EXPERIMENT_COMPLETE_WITHOUT_RESULTS:{e.get("id")}')
        elif status not in {'PROTOCOL_DRAFT_NOT_RUN', 'PROTOCOL_FROZEN_NOT_RUN', 'RUNNING', 'BLOCKED', 'OMITTED_WITH_REASON'}:
            errors.append(f'UNKNOWN_EXPERIMENT_STATUS:{e.get("id")}')
    if plan.get('thesis_submission_ready') is True:
        for key in ('advisor_approval_evidence', 'institutional_requirements_evidence', 'final_submission_audit'):
            if not plan.get(key):
                errors.append(f'SUBMISSION_WITHOUT:{key}')
    return errors


def evidence_paths(baseline: dict, plan: dict) -> list[str]:
    paths = [plan['plan'], plan['protocol'], plan['degree_thesis_blueprint'],
             plan['short_paper_source'], plan['historical_long_draft']]
    if plan.get('degree_thesis_source_created'):
        paths.append(plan['degree_thesis_source_after_initialization'])
    for t in plan.get('tasks', []):
        paths.extend(t.get('evidence', []))
    for e in plan.get('planned_experiments', []):
        paths.extend(e.get('result_evidence', []))
    for r in baseline.get('reported_acceptance', {}).values():
        paths.append(r['evidence'])
    return sorted(set(paths))


def check_files(root: Path, paths: list[str]) -> list[str]:
    root = root.resolve()
    errors = []
    for relative in paths:
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            errors.append(f'UNSAFE_EVIDENCE_PATH:{relative}')
        elif not target.is_file():
            errors.append(f'MISSING_EVIDENCE_FILE:{relative}')
    return errors


def check_git(root: Path, baseline: dict) -> list[str]:
    errors = []
    for path, item in baseline['protected_git_objects'].items():
        result = subprocess.run(['git', 'rev-parse', f'{baseline["source_commit"]}:{path}'],
                                cwd=root, text=True, capture_output=True, check=False)
        if result.returncode or result.stdout.strip() != item['sha']:
            errors.append(f'BASELINE_GIT_OBJECT_MISMATCH:{path}')
    return errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--check-git-baseline', action='store_true')
    args = p.parse_args()
    root = args.root.resolve()
    try:
        baseline = json.loads((root/'configs/research_baseline_20260917.json').read_text(encoding='utf-8-sig'))
        plan = json.loads((root/'configs/thesis_workplan.json').read_text(encoding='utf-8-sig'))
        errors = validate(baseline, plan)
        errors += check_files(root, evidence_paths(baseline, plan))
        if args.check_git_baseline:
            errors += check_git(root, baseline)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors = [f'READ_OR_SCHEMA_ERROR:{exc}']
    print(json.dumps({'status':'PASS' if not errors else 'FAIL', 'errors':errors,
                      'scope':'PLAN_METADATA_AND_EVIDENCE_EXISTENCE_ONLY',
                      'scientific_results_recomputed':False, 'private_hashes_recomputed':False,
                      'thesis_readiness_certified':False}, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == '__main__':
    raise SystemExit(main())
