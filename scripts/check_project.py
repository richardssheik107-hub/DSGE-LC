"""Check repository consistency only; this is not an economic-model solver."""
from pathlib import Path
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors = []
    status = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'model/registry.json').read_text(encoding='utf-8'))
    library = json.loads((ROOT / 'references/library.json').read_text(encoding='utf-8'))
    symbols = json.loads((ROOT / 'model/symbols.json').read_text(encoding='utf-8'))
    closure = json.loads((ROOT / 'model/closure_spec.json').read_text(encoding='utf-8'))
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
    for obj in (registry, symbols, closure):
        if obj['model_id'] != status['model_id']:
            errors.append('Model version mismatch.')
        if obj.get('revision') != status.get('revision'):
            errors.append('Closure revision mismatch.')
    if closure['state_dimension'] != status['state_dimension']:
        errors.append('Closure and project state dimensions differ.')
    if closure['reduced_unknowns'] != ['Q', 'J', 'D_s', 'C', 'I', 'P', 'F']:
        errors.append('Reduced current unknowns changed without updating this review.')
    conditions = closure['independent_conditions']
    if [row['id'] for row in conditions] != [f'R{i}' for i in range(1, 8)]:
        errors.append('Reduced conditions must be R1--R7, once each.')
    reduced_ids = [eid for row in conditions for eid in row['canonical']]
    if len(set(reduced_ids)) != 7 or not set(reduced_ids) <= set(expected):
        errors.append('Reduced system has duplicated or unknown canonical conditions.')
    derived = closure['derived_checks_by_representation']
    if set(reduced_ids) & set(derived['reduced_seven_unknowns']):
        errors.append('A reduced condition is also marked as an additional derived check.')
    if set(closure['alternative_original_conditions']) & set(derived['original_ten_unknowns_with_positions']):
        errors.append('An original condition is also marked as an additional derived check.')
    if 'E27' not in reduced_ids or 'E27' not in derived['original_ten_unknowns_with_positions']:
        errors.append('E27 must replace, not duplicate, original position clearing.')
    if closure.get('full_equilibrium_solved') or closure['conditional_subproblem'].get('dynamic_equilibrium_claim'):
        errors.append('Conditional closure was incorrectly marked as a full equilibrium.')
    if status.get('dynamic_fixed_point_implemented') is not False:
        errors.append('Dynamic fixed point implementation gate unexpectedly changed.')
    for flag in ('approved_by_supervisor', 'full_equilibrium_solved', 'real_data_validated', 'parameters_identified', 'real_data_estimated', 'old_tests_inherited'):
        if status.get(flag) is not False:
            errors.append(f'Review gate unexpectedly changed: {flag}')
    for forbidden in ('src/structural', 'src/rebuild_theory', 'configs/phase2a.yaml', 'data/processed'):
        if (ROOT / forbidden).exists():
            errors.append(f'Legacy execution path restored: {forbidden}')
    if symbols['industry_parameter_values']:
        errors.append('Unreviewed industry parameter values are not allowed in this candidate.')
    flow_text = (ROOT / 'docs/11_flowcharts.md').read_text(encoding='utf-8')
    embedded_graphs = re.findall(r'```mermaid\s*\n(.*?)```', flow_text, flags=re.S)
    figure_stems = ('01_mechanism', '02_monthly_timing', '03_solution_workflow')
    if len(embedded_graphs) != len(figure_stems):
        errors.append('Flowchart document must contain exactly three Mermaid sources.')
    for index, stem in enumerate(figure_stems):
        source_path = ROOT / 'docs/figures' / (stem + '.mmd')
        svg_path = ROOT / 'docs/figures' / (stem + '.svg')
        if not source_path.exists() or not svg_path.exists():
            errors.append(f'Missing figure source/export: {stem}')
            continue
        if index < len(embedded_graphs) and source_path.read_text(encoding='utf-8').strip() != embedded_graphs[index].strip():
            errors.append(f'Embedded/source Mermaid mismatch: {stem}')
        try:
            if ET.parse(svg_path).getroot().tag != '{http://www.w3.org/2000/svg}svg':
                errors.append(f'Not an SVG document: {stem}')
        except ET.ParseError:
            errors.append(f'Malformed SVG XML: {stem}')
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
        'closure_conditions': len(conditions),
        'flowchart_sources_and_exports': len(figure_stems),
        'mermaid_renderer_executed': False,
        'errors': errors,
        'passed': not errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())

