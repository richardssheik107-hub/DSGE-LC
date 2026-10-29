"""Check repository consistency only; this is not an economic-model solver."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors = []
    status = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'model/registry.json').read_text(encoding='utf-8'))
    library = json.loads((ROOT / 'references/library.json').read_text(encoding='utf-8'))
    symbols = json.loads((ROOT / 'model/symbols.json').read_text(encoding='utf-8'))
    equations = (ROOT / status['canonical_equations']).read_text(encoding='utf-8')
    expected = [f'E{i:02d}' for i in range(1, 32)]
    found = re.findall(r'^### (E\d{2})$', equations, flags=re.M)
    if found != expected:
        errors.append('Canonical equation headings must be exactly E01--E31, once each.')
    rows = registry['equations']
    if [row['id'] for row in rows] != expected:
        errors.append('Equation registry does not match canonical headings.')
    ids = {row['id'] for row in library['items']}
    if len(ids) != len(library['items']):
        errors.append('Duplicate reference id.')
    for row in rows:
        if not set(row['source_ids']) <= ids:
            errors.append(f"Unknown reference for {row['id']}")
        if not set(row['depends_on']) <= set(expected):
            errors.append(f"Unknown equation dependency for {row['id']}")
        if row['canonical'] != f"docs/03_equations.md#{row['id'].lower()}":
            errors.append(f"Wrong canonical pointer for {row['id']}")
    for record in library['items']:
        for field in ('authors', 'year', 'title', 'publication', 'url', 'verification', 'locator', 'supports', 'does_not_support', 'checked_on'):
            if not record.get(field):
                errors.append(f"Missing {field} in {record['id']}")
    for obj in (registry, symbols):
        if obj['model_id'] != status['model_id']:
            errors.append('Model version mismatch.')
    for flag in ('approved_by_supervisor', 'full_equilibrium_solved', 'real_data_validated', 'parameters_identified', 'real_data_estimated', 'old_tests_inherited'):
        if status.get(flag) is not False:
            errors.append(f'Review gate unexpectedly changed: {flag}')
    for forbidden in ('src/structural', 'src/rebuild_theory', 'configs/phase2a.yaml', 'data/processed'):
        if (ROOT / forbidden).exists():
            errors.append(f'Legacy execution path restored: {forbidden}')
    if symbols['industry_parameter_values']:
        errors.append('Unreviewed industry parameter values are not allowed in this candidate.')
    checked_links = 0
    markdown_files = sorted(ROOT.rglob('*.md'))
    for path in markdown_files:
        text = path.read_text(encoding='utf-8')
        if text.count('$$') % 2:
            errors.append(f'Unpaired display math delimiter in {path.relative_to(ROOT)}')
        if re.search(r'turn\d+(?:file|search|view)\d+', text):
            errors.append(f'Chat-only citation token in {path.relative_to(ROOT)}')
        # Ignore code fences; inspect local Markdown links only.
        prose = re.sub(r'```.*?```', '', text, flags=re.S)
        for target in re.findall(r'\]\(([^\s)]+)\)', prose):
            if target.startswith(('https://', 'http://', 'mailto:', '#')):
                continue
            target_path = target.split('#', 1)[0]
            if not (path.parent / target_path).resolve().exists():
                errors.append(f'Broken local link in {path.relative_to(ROOT)}: {target}')
            checked_links += 1
    result = {
        'scope': 'documentation and registry consistency, not equilibrium or source validation',
        'model_id': status['model_id'],
        'equation_groups': len(rows),
        'reference_records': len(ids),
        'markdown_files': len(markdown_files),
        'local_links_checked': checked_links,
        'errors': errors,
        'passed': not errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())
