"""Portable governance tests; no private data or original research rerun."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('governance',ROOT/'scripts/audit_thesis_governance.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def payloads():
    return (json.loads((ROOT/'configs/research_baseline_20260917.json').read_text(encoding="utf-8")),
            json.loads((ROOT/'configs/thesis_workplan.json').read_text(encoding="utf-8")))

def test_current_payloads():
    assert g.validate(*payloads()) == []

def test_bad_baseline_reference():
    b,p=payloads();p['baseline_commit']='0'*40
    assert 'BASELINE_COMMIT_MISMATCH' in g.validate(b,p)

def test_bad_hash_type():
    b,p=payloads();b['private_core_sha256_recorded']='0'*40
    assert 'INVALID_RECORDED_CORE_HASH' in g.validate(b,p)

def test_duplicate_task():
    b,p=payloads();p['tasks'].append(copy.deepcopy(p['tasks'][0]))
    assert 'EMPTY_OR_DUPLICATE_TASK_IDS' in g.validate(b,p)

def test_cycle():
    b,p=payloads();p['tasks'][0]['depends_on']=['D08']
    assert any('CYCLIC_DEPENDENCY' in e for e in g.validate(b,p))

def test_unknown_dependency():
    b,p=payloads();p['tasks'][1]['depends_on']=['ABSENT']
    assert any('UNKNOWN_DEPENDENCY' in e for e in g.validate(b,p))

def test_completed_without_evidence():
    b,p=payloads();p['tasks'][0]['evidence']=[]
    assert any('COMPLETED_WITHOUT_EVIDENCE' in e for e in g.validate(b,p))

def test_completed_with_pending_prerequisite():
    b,p=payloads();p['tasks'][2]['status']='COMPLETE';p['tasks'][2]['evidence']=['report.md']
    assert any('COMPLETED_WITH_OPEN_DEPENDENCY' in e for e in g.validate(b,p))

def test_omission_needs_reason():
    b,p=payloads();p['tasks'][1]['status']='OMITTED_WITH_REASON';p['tasks'][1]['evidence']=['decision.md']
    assert any('OMITTED_WITHOUT_REASON' in e for e in g.validate(b,p))

def test_unrun_experiment_cannot_claim_results():
    for status in ('PROTOCOL_DRAFT_NOT_RUN', 'PROTOCOL_FROZEN_NOT_RUN'):
        b,p=payloads();p['planned_experiments'][0]['status']=status
        p['planned_experiments'][0]['result_evidence']=['fake.csv']
        assert any('UNRUN_EXPERIMENT_HAS_RESULTS' in e for e in g.validate(b,p))

def test_done_experiment_needs_results():
    b,p=payloads();p['planned_experiments'][0]['status']='EMPIRICAL_COMPLETE'
    assert any('EXPERIMENT_COMPLETE_WITHOUT_RESULTS' in e for e in g.validate(b,p))

def test_empty_result_does_not_mean_submission_ready():
    b,p=payloads();p['thesis_submission_ready']=True
    assert sum(e.startswith('SUBMISSION_WITHOUT') for e in g.validate(b,p))==3

def test_path_traversal_rejected(tmp_path):
    assert g.check_files(tmp_path,['../other.txt']) == ['UNSAFE_EVIDENCE_PATH:../other.txt']

def test_missing_evidence(tmp_path):
    assert g.check_files(tmp_path,['missing.md']) == ['MISSING_EVIDENCE_FILE:missing.md']

def test_existing_evidence(tmp_path):
    (tmp_path/'actual.md').write_text('actual report')
    assert not g.check_files(tmp_path,['actual.md'])

def test_future_uncreated_thesis_not_required():
    b,p=payloads()
    assert p['degree_thesis_source_after_initialization'] not in g.evidence_paths(b,p)
