"""Check active design metadata and frozen archive bytes; never run economic code."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def main():
    errors = []
    status = read_json('project.json')
    spec = read_json(status['model_specification'])
    refs = read_json(status['reference_registry'])
    manifest = read_json(status['archive_manifest'])
    validation = read_json(status['validation_document'])

    if status['model_id'] != spec['model_id'] or validation['model_id'] != spec['model_id']:
        errors.append('Active model identifiers disagree.')
    if status['canonical_equations'] != spec['canonical_document']:
        errors.append('Active canonical design paths disagree.')
    if status['stage'] != 'DESIGN_AND_CLOSURE_REVIEW' or spec['status'] != 'DESIGN_NOT_IMPLEMENTED':
        errors.append('Design status changed without revising this gate and its evidence.')
    false_flags = (
        'approved_by_supervisor', 'full_dsge_solver_implemented',
        'dsge_steady_state_solved', 'full_dsge_equilibrium_solved',
        'real_data_validated', 'parameters_identified',
        'real_data_estimated', 'old_tests_inherited',
        'archive_is_default_reference', 'archive_in_default_test_discovery',
    )
    for key in false_flags:
        if status.get(key) is not False:
            errors.append(f'Unsupported completed/inherited gate: {key}')
    for key in ('closed_form_pe_E27_inherited', 'legacy_tests_inherited',
                'nonlinear_policy_solved', 'calibrated', 'estimated',
                'independent_condition_count_verified'):
        if spec.get(key) is not False:
            errors.append(f'Unsupported model-specification gate: {key}')
    if spec['independent_condition_count'] is not None:
        errors.append('An unverified independent equation count was declared.')
    if validation.get('dsge_results_inherited') is not False:
        errors.append('Validation record inherits legacy DSGE results.')
    if status['checks'] != ['python scripts/check_repository.py']:
        errors.append('Default checks unexpectedly execute or discover historical work.')

    canonical = (ROOT / spec['canonical_document']).read_text(encoding='utf-8')
    headings = re.findall(r'^### (G\d{2})｜(.+)$', canonical, re.M)
    groups = spec['equation_groups']
    if headings != [(g['id'], g['title']) for g in groups]:
        errors.append('Design headings do not match the machine index.')
    if [g['id'] for g in groups] != [f'G{i:02}' for i in range(1, 27)]:
        errors.append('Expected G01--G26 design modules exactly once (not scalar equation count).')
    ids = {item['id'] for item in refs['items']}
    if len(ids) != len(refs['items']):
        errors.append('Duplicate reference IDs.')
    if status['primary_reference_id'] != 'HOG-REF' or spec['primary_structure_source'] != 'HOG-REF':
        errors.append('The main group reference was displaced.')
    for item in refs['items']:
        for field in ('authors', 'year', 'title', 'publication', 'url', 'verification',
                      'locator', 'supports', 'does_not_support', 'checked_on'):
            if not item.get(field):
                errors.append(f'Missing source field {item["id"]}: {field}')
    for group in groups:
        if not set(group['source_ids']) <= ids:
            errors.append(f'Unknown source in {group["id"]}')
        if group['implementation_status'] != 'NOT_IMPLEMENTED':
            errors.append(f'Implementation gate changed for {group["id"]}')

    archive_root = (ROOT / status['archive_root']).resolve()
    if manifest['archive_root'] != status['archive_root'] or manifest['active_reference'] is not False:
        errors.append('Archive root or reference scope disagrees.')
    archived_paths = set()
    archived_bytes = 0
    by_commit = {}
    for row in manifest['files']:
        path = (ROOT / row['archived_path']).resolve()
        if not path.is_relative_to(archive_root):
            errors.append(f'Archive path escapes scope: {row["archived_path"]}')
            continue
        if row['archived_path'] in archived_paths:
            errors.append(f'Duplicate archived path: {row["archived_path"]}')
        archived_paths.add(row['archived_path'])
        if not path.is_file():
            errors.append(f'Missing frozen file: {row["archived_path"]}')
            continue
        data = path.read_bytes()
        archived_bytes += len(data)
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if (len(data), hashlib.sha256(data).hexdigest(), blob) != (
                row['bytes'], row['sha256'], row['git_blob_sha1']):
            errors.append(f'Frozen bytes changed: {row["archived_path"]}')
        if path.name == 'AGENTS.md':
            errors.append(f'Executable historical instruction file: {row["archived_path"]}')
        count, size = by_commit.get(row['source_commit'], (0, 0))
        by_commit[row['source_commit']] = (count + 1, size + len(data))
    snapshots = {s['source_commit']: s for s in manifest['snapshots']}
    for commit, snap in snapshots.items():
        if by_commit.get(commit) != (snap['archived_file_count'], snap['archived_bytes']):
            errors.append(f'Snapshot totals disagree: {snap["directory"]}')
        excluded = [x for x in manifest['excluded'] if x['source_commit'] == commit]
        if len(excluded) != snap['excluded_file_count']:
            errors.append(f'Excluded totals disagree: {snap["directory"]}')
        if snap['source_file_count'] != snap['archived_file_count'] + len(excluded):
            errors.append(f'Source coverage incomplete: {snap["directory"]}')
        for row in excluded:
            if (archive_root / snap['directory'] / row['source_path']).exists():
                errors.append(f'Excluded source was republished: {row["source_path"]}')
    if len(archived_paths) != 505 or archived_bytes != 5185051 or len(manifest['excluded']) != 508:
        errors.append('Reviewed archive totals changed without a new migration review.')

    active_md = [ROOT / p for p in status['current_documents']]
    active_md += [ROOT / p for p in ('README.md', 'AGENTS.md', 'CHANGELOG.md',
                  'data/README.md', 'model/README.md', 'references/README.md')]
    active_md += [archive_root / 'README.md']
    links = 0
    for path in active_md:
        if not path.is_file():
            errors.append(f'Missing active document: {path.relative_to(ROOT)}')
            continue
        text = path.read_text(encoding='utf-8')
        if any(ord(ch) < 32 and ch not in '\n\r\t' for ch in text):
            errors.append(f'Control character: {path.relative_to(ROOT)}')
        if re.search(r'turn\d+(?:file|search|view)\d+', text):
            errors.append(f'Chat-only citation token: {path.relative_to(ROOT)}')
        prose = re.sub(r'```.*?```', '', text, flags=re.S)
        if prose.count('$$') % 2:
            errors.append(f'Unpaired display math: {path.relative_to(ROOT)}')
        without_display = re.sub(r'\$\$.*?\$\$', '', prose, flags=re.S)
        if len(re.findall(r'(?<!\\)\$', without_display)) % 2:
            errors.append(f'Unpaired inline math: {path.relative_to(ROOT)}')
        for target in re.findall(r'\]\(([^\s)]+)\)', prose):
            if target.startswith(('https://', 'http://', 'mailto:', '#')):
                continue
            local = target.split('#', 1)[0]
            if not (path.parent / local).resolve().exists():
                errors.append(f'Broken current link: {path.relative_to(ROOT)} -> {target}')
            links += 1
    for old in ('src/structural', 'src/rebuild_theory', 'model/conditional_market.py',
                'model/full_conditions.py', 'configs/phase2a.yaml',
                'docs/03_equations.md', 'scripts/check_project.py'):
        if (ROOT / old).exists():
            errors.append(f'Legacy active path remains: {old}')
    for run in validation['frozen_pe_checks']['commands']:
        if run['exit_code'] != 0 or run['passed'] is not True:
            errors.append(f'Frozen baseline check was not successful: {run["command"]}')

    report = {
        'scope': 'active design consistency and archive byte integrity only; no economic solver invoked',
        'model_id': status['model_id'], 'design_modules': len(groups),
        'independent_equation_count_verified': False,
        'reference_records': len(ids), 'primary_reference': status['primary_reference_id'],
        'active_markdown_files': len(active_md), 'local_links_checked': links,
        'archive_files_verified': len(archived_paths), 'archive_bytes_verified': archived_bytes,
        'excluded_metadata_records': len(manifest['excluded']),
        'historical_tests_executed_by_this_check': False,
        'new_dsge_equilibrium_solved': False, 'errors': errors, 'passed': not errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())
