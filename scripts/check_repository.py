"""Check equation metadata, numerical-evidence hashes and frozen archive bytes."""
from pathlib import Path
import csv
import hashlib
import json
import re
import sys
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def check_hashes(fingerprints, errors, label):
    for source, expected in fingerprints.items():
        path = (ROOT / source).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            errors.append(f'{label}: missing or out-of-scope source {source}')
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(f'{label}: source changed after evidence {source}')


def check_local_stochastic(status, spec, anchor, errors):
    """Verify stored arrays and their implications; never call an economic solver."""
    start = len(errors)
    metrics = {}

    def need(value, message):
        if not value:
            errors.append('Local stochastic evidence: ' + message)

    def close(actual, expected, tolerance, message):
        actual, expected = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
        need(actual.shape == expected.shape and np.all(np.isfinite(actual))
             and np.all(np.isfinite(expected))
             and np.max(np.abs(actual - expected), initial=0) <= tolerance * (1 + np.max(np.abs(expected), initial=0)), message)

    try:
        record = read_json(status['local_stochastic_validation_document'])
        snapshot = read_json(status['local_policy_snapshot'])
        need(record['model_id'] == snapshot['model_id'] == status['model_id'], 'model identifiers disagree')
        kind = 'LOCAL_FIRST_ORDER_RE_WITH_LEADING_RISKY_PORTFOLIO'
        need(record['result_kind'] == snapshot['result_kind'] == kind, 'result is not identified as local first order')
        for key in ('full_positive_risk_nonlinear_policy_solved', 'stationary_wealth_distribution_verified',
                    'full_dynamic_rank_all_regimes_verified', 'data_calibrated_or_estimated'):
            need(record[key] is False, 'unsupported completion ' + key)
        need(snapshot['full_nonlinear_policy_solved'] is False, 'snapshot claims nonlinear completion')
        need(record['all_values_synthetic'] is True, 'synthetic scope missing')
        need(record['first_order_local_equations_passed'] is True
             and np.isfinite(record['linear_equation_max_residual'])
             and 0 <= record['linear_equation_max_residual'] < 1e-10, 'linear equations fail numerical tolerance')
        need(record['evidence_io_guard_added']['economic_equations_or_algorithm_changed'] is False,
             'evidence overwrite protection scope missing')
        need(record['working_sigma'] == .001 and record['configured_sigma'] == .01, 'documented innovation scales changed')
        check_hashes(record['economic_source_sha256'], errors, 'Local stochastic')
        check_hashes(snapshot['source_sha256'], errors, 'Policy snapshot')
        need(record['economic_source_sha256'] == snapshot['source_sha256'], 'policy/evidence source fingerprints differ')
        need(set(spec['implementation_files']) <= set(record['economic_source_sha256']), 'implementation not covered by local source fingerprints')
        need('scripts/solve_stochastic.py' in record['economic_source_sha256'], 'local solver script fingerprint missing')

        p = snapshot['parameters']
        lag, ramp = p['construction_lag'], len(p['ramp_weights'])
        build = lag - 1
        ns, ny = 13 + build + ramp, 12 + build + ramp
        g = np.asarray(snapshot['first_order_transition'], dtype=float)
        k = np.asarray(snapshot['first_order_policy'], dtype=float)
        coef = np.asarray(snapshot['policy_coefficients'], dtype=float)
        scale = np.asarray(snapshot['state_scale'], dtype=float)
        center = np.asarray(snapshot['state_center'], dtype=float)
        positive = np.asarray(snapshot['positive_control_anchor'], dtype=float)
        h = np.asarray(snapshot['leading_holdings_IDF'], dtype=float)
        if g.shape != (ns, ns) or k.shape != (ny, ns) or coef.shape != (ny + 2, ns + 1):
            raise ValueError('policy/transition dimensions do not match selected regime')
        need(all(np.all(np.isfinite(a)) for a in (g, k, coef, scale, center, positive, h)), 'nonfinite policy coefficient')
        need(scale.shape == center.shape == (ns,) and positive.shape == (ny,) and h.shape == (3,), 'snapshot vector dimensions disagree')
        need(np.min(scale) > 0 and np.min(positive) > 0, 'nonpositive normalization or anchor control')
        need(record['state_count'] == ns == spec['local_state_count']
             and record['canonical_state_count'] == ns + 1
             and record['first_order_control_count'] == ny == spec['local_first_order_control_count'], 'selected/full dimension scopes disagree')
        close(p['shock_scales'], [.001] * 4, 1e-14, 'snapshot shock scales differ')
        close(coef[:ny, 1:], k, 1e-12, 'coefficient snapshot and linear decision rule differ')
        close(coef[:ny, 0], np.zeros(ny), 1e-14, 'linear snapshot has unsupported higher-order intercepts')
        close(coef[ny:, 1:], np.zeros((2, ns)), 1e-14, 'unidentified first-order holding slopes were added')
        close(coef[ny:, 0] * positive[0], h[:2], 1e-12, 'holding level normalization differs')
        close(center[10 + build + ramp:12 + build + ramp], h[:2], 1e-12, 'inherited contract center differs')
        need(abs(h.sum()) < 1e-12, 'leading futures holdings do not clear')
        close(h, record['leading_portfolio']['holdings_IDF'], 1e-12, 'reported and saved portfolios disagree')
        a = anchor['choice']
        anchor_controls = [a['q'], a['investment'], a['commitment'], a['wage'], a['spot'],
                           a['forward'], 1 / a['gross_rate'], *a['consumption'], a['wm'], *a['wb'], *a['wz']]
        close(positive, anchor_controls, 1e-12, 'policy normalization differs from checked deterministic anchor')

        # Stored policy must satisfy pricing/Euler restrictions, not merely label them passed.
        pricing = positive[5] * k[5] - positive[4] * k[4] @ g
        euler = np.array([positive[6] * k[6] + p['beta'] * gamma * (k[7 + j] @ g - k[7 + j])
                          for j, gamma in enumerate(p['gamma'])])
        need(np.max(abs(pricing)) < 1e-10 and np.max(abs(euler)) < 1e-10,
             'saved policy fails linear original bond/futures restrictions')
        close(g[:4], np.column_stack([np.diag(p['shock_persistence']), np.zeros((4, ns - 4))]), 1e-10,
              'exogenous law is inconsistent with policy transition')
        close(g[4], positive[0] / scale[4] * k[0], 1e-10, 'production memory transition differs')
        close(g[5], positive[2] / scale[5] * k[2], 1e-10, 'procurement memory transition differs')
        for j in range(build):
            target = np.zeros(ns)
            if j + 1 < build:
                target[8 + j] = scale[8 + j] / scale[7 + j]
            else:
                target = positive[1] / scale[7 + j] * k[1]
            close(g[7 + j], target, 1e-10, 'construction queue transition differs')
        for j in range(ramp):
            target = np.zeros(ns)
            index = 7 + build + j
            if j:
                target[index - 1] = (1 - p['depreciation']) * scale[index - 1] / scale[index]
            elif build:
                target[7] = scale[7] / scale[index]
            else:
                target = positive[1] / scale[index] * k[1]
            close(g[index], target, 1e-10, 'ramp queue transition differs')
        target = np.zeros(ns)
        target[6] = 1 - p['depreciation']
        if ramp:
            target[6 + build + ramp] = (1 - p['depreciation']) * scale[6 + build + ramp] / scale[6]
        elif build:
            target[7] = scale[7] / scale[6]
        else:
            target += positive[1] / scale[6] * k[1]
        close(g[6], target, 1e-10, 'mature capacity transition differs')
        close(g[-1], positive[5] / scale[-1] * k[5], 1e-10, 'inherited forward quote transition differs')
        close(g[10 + build + ramp:12 + build + ramp], np.zeros((2, ns)), 1e-12,
              'chosen constant leading portfolio transition differs')
        # Check inherited wealth against linearized original household budgets.
        unit = np.eye(ns)
        capacity_row = scale[6] * unit[6]
        for j, weight in enumerate(p['ramp_weights']):
            capacity_row += weight * scale[7 + build + j] * unit[7 + build + j]
        capacity = anchor['state']['mature'] + np.dot(p['ramp_weights'], anchor['state']['ramp'])
        q0, j0, c0, w0, spot0, _, bond0 = positive[:7]
        current_build = sum(anchor['state']['construction'])
        build_row = sum((scale[7 + j] * unit[7 + j] for j in range(build)), np.zeros(ns))
        production_cost = (p['m_bar'] * q0 * (scale[1] * unit[1] + k[0])
                           + p['alpha_q'] / (p['nu_q'] + 1) * q0 ** (p['nu_q'] + 1) / capacity ** p['nu_q']
                           * ((p['nu_q'] + 1) * k[0] - p['nu_q'] * capacity_row / capacity))
        construction_cost = (p['pj_bar'] * j0 * (scale[2] * unit[2] + k[1])
                             + p['chi_j'] * j0 ** 2 * k[1]
                             + p['congestion'] * j0 * (current_build * k[1] + build_row))
        profit_i = spot0 * q0 * (k[4] + k[0]) - w0 * q0 / p['al'] * (k[3] + k[0]) - production_cost - construction_cost
        income_b = spot0 / p['alpha_s'] * ((q0 - c0) * k[4] + q0 * k[0] - scale[5] * unit[5])
        profit_d = (p['phi'] + p['alpha_c']) * income_b - spot0 * (c0 * k[4] + scale[5] * unit[5])
        wage_income = w0 * anchor['choice']['labor_w'] * (k[3] + (k[3] - p['gamma'][0] * k[7]) / p['labor_elasticity_power'])
        profits = (wage_income, profit_i, profit_d)
        settlement = spot0 * k[4] - scale[-1] * unit[-1]
        for owner in range(3):
            index = 7 + build + ramp + owner
            payment = h[owner - 1] * settlement if owner else np.zeros(ns)
            target = (scale[index] * unit[index] + profits[owner] + payment
                      - positive[7 + owner] * k[7 + owner]
                      - bond0 * anchor['state']['bonds'][owner] * k[6]) / (bond0 * scale[index])
            close(g[index], target, 1e-10, 'saved wealth transition violates an original household budget')

        eigen = np.linalg.eigvals(g)
        neutral = int(np.count_nonzero(abs(eigen - 1) < 1e-7))
        need(np.max(abs(eigen)) <= 1 + 1e-7 and neutral == 3,
             'saved transition lacks the documented stable/three-neutral-root structure')
        need(record['neutral_wealth_root_count'] == status['neutral_wealth_root_count'] == spec['neutral_wealth_root_count'] == neutral,
             'neutral wealth root count differs')
        need(record['stable_neutral_root_count'] == ns and record['generalized_indeterminate_pairs'] == 0,
             'Schur subspace count or regularity evidence disagrees')
        need(np.isfinite(record['graph_condition_number']) and record['graph_condition_number'] < 1e8,
             'stable subspace graph is numerically singular')
        tangent = np.asarray(record['futures_zero_risk_first_order_tangent']['matrix'], dtype=float)
        need(tangent.shape == (3, 8) and np.linalg.matrix_rank(tangent, tol=1e-10) == 1,
             'original three-row futures tangent is not rank one')
        close(tangent[:, -2:], np.zeros((3, 2)), 1e-14, 'zero-risk holdings derivative is nonzero')
        portfolio = record['leading_portfolio']
        cov = np.asarray(portfolio['unscaled_covariance_differences'], dtype=float)
        scaled = np.max(abs(cov)) / (.001 ** 2 * positive[4])
        need(np.isfinite(scaled) and scaled < 1e-7, 'leading covariance conditions do not pass')
        close(scaled, portfolio['scaled_covariance_residual'], 1e-12, 'covariance residual scaling differs')
        need(portfolio['conditional_spot_variance'] > 0 and portfolio['zero_risk_anchor_collateral_slack'] > 0,
             'leading solution has no price risk or violates the slack collateral regime')

        total_rows = 0
        mapped_controls = {'Q': 0, 'J': 1, 'C': 2, 'w': 3, 'P': 4, 'F': 5,
                           'q_bond': 6, 'cW': 7, 'cI': 8, 'cD': 9, 'cF': 10}
        for entry in status['local_irf_files']:
            rows = list(csv.DictReader((ROOT / entry['path']).open(encoding='utf-8')))
            total_rows += len(rows)
            need(len(rows) == 148, 'IRF file must contain 4 shocks by 37 months')
            observed = {(row['shock'], int(row['month'])) for row in rows}
            expected = {(shock, month) for shock in spec['shock_states'] for month in range(37)}
            need(observed == expected and len(observed) == len(rows), 'IRF coverage or unique shock/month keys differ')
            for row in rows:
                numeric = {key: float(value) for key, value in row.items() if key != 'shock'}
                need(all(np.isfinite(list(numeric.values()))), 'IRF contains nonfinite observations')
                need(numeric['sigma'] == entry['sigma'] and numeric['innovation'] == 1, 'IRF impulse scale differs')
                impulse = np.zeros(ns)
                shock_index = spec['shock_states'].index(row['shock'])
                impulse[shock_index] = entry['sigma'] / scale[shock_index]
                state = np.linalg.matrix_power(g, int(row['month'])) @ impulse
                response = k @ state
                for name, control in mapped_controls.items():
                    close(numeric[name + '_change'], positive[control] * response[control], 1e-9,
                          'IRF does not reproduce saved policy: ' + name)
                    close(numeric[name + '_percent'], 100 * response[control], 1e-8,
                          'IRF percent normalization differs: ' + name)
                capacity_change = scale[6] * state[6] + np.dot(p['ramp_weights'], scale[7 + build:7 + build + ramp] * state[7 + build:7 + build + ramp])
                close(numeric['K_effective_change'], capacity_change, 1e-9, 'IRF capacity response differs from saved states')
                need(abs(numeric['first_order_premium_change']) < 1e-10, 'first-order IRF falsely includes a risk-premium response')
                if row['shock'] == 'z_kappa':
                    need(max(abs(v) for key, v in numeric.items() if key.endswith(('_change', '_percent'))) < 1e-12,
                         'slack-branch collateral shock is not locally zero')
                if int(row['month']) < lag:
                    need(abs(numeric['K_effective_change']) < 1e-12, 'new capacity appears before the construction lag')
        need(record['irf']['horizon_months'] == 36 and record['irf']['future_innovations_integrated_not_assumed_known'] is True,
             'conditional-mean IRF scope missing')
        ratios = record['sigma_doubling_error_ratios']
        need(len(ratios) == 2 and all(3.5 < r < 4.5 for r in ratios), 'nonlinear truncation error no longer scales quadratically')
        working = record['nonlinear_original_condition_audit_of_linear_candidate']
        need(working['max_original_residual'] > 1e-8 and working['failed_count'] > 0 and working['domain_error_count'] == 0,
             'linear approximation was misrepresented as a passing nonlinear policy')

        attempt = record['nonlinear_projection_attempt']
        need(attempt['optimizer_success'] is False and attempt['evaluations'] == attempt['max_nfev'] == 350,
             'documented rejected projection optimization evidence differs')
        need(attempt['sampled_candidate_gate_passed'] is False and attempt['global_stochastic_equilibrium_solved'] is False,
             'rejected nonlinear projection was promoted to a solution')
        rejected_eigen = np.array([complex(e['real'], e['imag']) for e in attempt['conditional_mean_transition_eigenvalues']])
        close(max(abs(rejected_eigen)), attempt['conditional_mean_transition_spectral_radius'], 1e-12,
              'rejected projection spectral radius differs')
        need(max(abs(rejected_eigen)) > 1 + 2e-5, 'rejected transition instability evidence missing')
        for key, minimum in (('fit_audit', 35), ('heldout_audit', 64), ('reachable_path_audit', 4)):
            audit = attempt[key]
            rows = audit['records']
            finite = [r['max_abs_residual'] for r in rows if r['max_abs_residual'] is not None]
            need(audit['count'] == len(rows) >= minimum and audit['tolerance'] == 1e-8, 'projection audit coverage/tolerance differs')
            close(max(finite), audit['max_original_residual'], 1e-12, 'projection audit maximum is inconsistent')
            need(audit['failed_count'] == sum(not row['passed'] for row in rows) > 0,
                 'projection failed-state count differs')
            need(audit['domain_error_count'] == sum(bool(row['domain_errors']) for row in rows), 'projection domain failures differ')
            for row in rows:
                passed = not row['domain_errors'] and row['max_abs_residual'] is not None and row['max_abs_residual'] <= 1e-8
                need(row['passed'] == passed, 'individual projection state contradicts original residual gate')
        need(attempt['reachable_path_audit']['domain_error_count'] > 0
             and any('collateral' in message for row in attempt['reachable_path_audit']['records'] for message in row['domain_errors']),
             'reachable successor collateral failure was lost')
        metrics = {'local_linear_equation_residual': record['linear_equation_max_residual'],
                   'saved_policy_bond_euler_residual': float(np.max(abs(euler))),
                   'saved_policy_futures_residual': float(np.max(abs(pricing))),
                   'neutral_wealth_roots': neutral, 'local_irf_rows_verified': total_rows,
                   'rejected_nonlinear_projection_retained': True}
    except (OSError, KeyError, TypeError, ValueError, IndexError, np.linalg.LinAlgError) as error:
        errors.append('Local stochastic evidence could not be verified: ' + str(error))
    metrics['local_first_order_evidence_verified'] = len(errors) == start
    return metrics


def check_shock_evidence(status, spec, errors):
    start = len(errors)
    try:
        record = read_json(status['shock_validation_document'])
        def need(value, message):
            if not value:
                errors.append('Shock evidence: ' + message)
        need(record['model_id'] == status['model_id'] and record['passed'] is True, 'model or passed field differs')
        need(record['tests']['passed'] is True and record['tests']['run'] >= 4, 'shock regression evidence missing')
        need(record['equilibrium_irfs_computed'] is False and record['positive_risk_equilibrium_solved_by_this_script'] is False,
             'primitive incidence falsely declared an equilibrium response')
        check_hashes(record['source_sha256'], errors, 'Shock audit')
        need(set(spec['implementation_files']) <= set(record['source_sha256']), 'implementation absent from shock fingerprints')
        need('scripts/validate_shocks.py' in record['source_sha256'], 'shock audit script fingerprint missing')
        law = record['kernel']
        need(law['branches'] == 16 and abs(law['probability_sum'] - 1) < 1e-14, 'finite kernel probability mass differs')
        need(np.max(abs(np.array(law['latent_innovation_mean']))) < 1e-14, 'innovation mean differs')
        sigmas = np.array([r['sigma_innovation'] for r in record['scales']])
        need([r['name'] for r in record['scales']] == spec['shock_states'] and np.all(sigmas > 0), 'shock names/scales differ')
        need(np.max(abs(np.array(law['latent_innovation_covariance']) - np.diag(sigmas ** 2))) < 1e-14,
             'innovation covariance differs from independent declared scales')
        for probe, rank in ((record['anchor_primitive_incidence'], 3), (record['nonzero_position_probe']['incidence'], 4)):
            analytic, numerical = np.array(probe['analytic']), np.array(probe['central_difference'])
            derivative_error = float(np.max(abs(analytic - numerical)))
            need(analytic.shape == (5, 4) and np.linalg.matrix_rank(analytic) == rank == probe['primitive_entry_rank_at_candidate'],
                 'fixed-choice incidence rank differs')
            need(derivative_error < 1e-9 and abs(derivative_error - probe['max_derivative_error']) < 1e-14,
                 'primitive derivative numerical check fails')
            need(probe['structural_identification_rank_claimed'] is False, 'primitive rank was called statistical identification')
        anchor = record['anchor_collateral_activation']
        nonzero = record['nonzero_position_probe']['collateral']
        need(anchor['position_F'] == 0 and anchor['collateral_requirement'] == 0 and anchor['collateral_slack'] > 0,
             'zero-position collateral activation diagnostic differs')
        need(record['nonzero_position_probe']['is_equilibrium'] is False and nonzero['collateral_requirement'] > 0,
             'nonzero fixed-position probe was claimed as an equilibrium')
        need(len(record['exogenous_paths']) == 4, 'missing exogenous conditional path')
        for path in record['exogenous_paths']:
            need(path['future_innovations_integrated'] is True and path['equilibrium_irf'] is False,
                 'primitive paths mislabel future risk or equilibrium scope')
            need(len(path['rows']) == 13, 'exogenous path horizon differs')
            for row in path['rows']:
                baseline = (row['primitive_conditional_mean_plus'] + row['primitive_conditional_mean_minus']) / 2
                need(abs(baseline - row['primitive_unconditional_baseline']) < 1e-12
                     and abs(row['primitive_conditional_mean_plus'] - baseline - row['conditional_mean_difference']) < 1e-12,
                     'conditional primitive baseline does not integrate the original signs')
    except (OSError, KeyError, TypeError, ValueError, IndexError, np.linalg.LinAlgError) as error:
        errors.append('Shock evidence could not be verified: ' + str(error))
    return len(errors) == start


def check_report_artifacts(status, errors):
    start = len(errors)
    try:
        plot = read_json(status['weekly_report']['figure_manifest'])
        if plot['model_id'] != status['model_id'] or plot['result_kind'] != 'LOCAL_FIRST_ORDER_RE_WITH_LEADING_RISKY_PORTFOLIO':
            errors.append('Figure manifest identifies a different model/result.')
        if not (plot['synthetic_parameters'] is True and plot['nonlinear_girf'] is False
                and plot['estimated_uncertainty_bands'] is False and plot['sigma_each'] == .001
                and plot['horizon_displayed_months'] == 24 and plot['horizon_in_source_months'] == 36):
            errors.append('Figure manifest scope/amplitude changed.')
        check_hashes({plot['source']: plot['source_sha256'],
                      'scripts/plot_stochastic_results.py': plot['plot_script_sha256'],
                      **plot['sources']}, errors, 'Report figures')
        if len(plot['sources']) != 4:
            errors.append('Expected two figures, each with PNG and SVG.')
        for artifact in status['current_artifacts']:
            path = ROOT / artifact
            if not path.is_file():
                errors.append('Missing current deliverable: ' + artifact)
            elif path.suffix == '.docx':
                with zipfile.ZipFile(path) as document:
                    if 'word/document.xml' not in document.namelist():
                        errors.append('Current Word deliverable lacks main document XML: ' + artifact)
    except (OSError, KeyError, TypeError, ValueError, zipfile.BadZipFile) as error:
        errors.append('Report artifacts could not be verified: ' + str(error))
    return len(errors) == start


def main():
    errors = []
    status = read_json('project.json')
    spec = read_json(status['model_specification'])
    refs = read_json(status['reference_registry'])
    manifest = read_json(status['archive_manifest'])
    validation = read_json(status['validation_document'])

    historical = read_json(status['archive_validation_document'])
    if status['model_id'] != spec['model_id'] or validation['model_id'] != spec['model_id']:
        errors.append('Active model identifiers disagree.')
    if status['canonical_equations'] != spec['canonical_document']:
        errors.append('Active canonical equation paths disagree.')
    if status['stage'] != 'LOCAL_STOCHASTIC_SOLUTION_AND_VALIDATION':
        errors.append('Model stage changed without revising this gate and evidence.')
    if spec['status'] != 'LOCAL_FIRST_ORDER_STOCHASTIC_RE_VERIFIED_NONLINEAR_PROJECTION_REJECTED':
        errors.append('Specification implementation scope disagrees.')
    for key in ('approved_by_supervisor', 'full_dsge_solver_implemented',
                'full_dsge_equilibrium_solved', 'real_data_validated',
                'parameters_identified', 'real_data_estimated', 'old_tests_inherited',
                'archive_is_default_reference', 'archive_in_default_test_discovery',
                'nonlinear_policy_solved', 'second_order_policy_solved', 'nonlinear_projection_candidate_accepted',
                'global_successor_feasibility_verified', 'global_transversality_verified',
                'stationary_wealth_distribution_verified', 'full_dynamic_rank_all_regimes_verified',
                'nonlinear_girfs_computed', 'time_varying_risk_premium_identified'):
        if status.get(key) is not False:
            errors.append(f'Unsupported completed/inherited gate: {key}')
    for key in ('equation_chain_reconstructed', 'original_condition_evaluator_implemented',
                'deterministic_stationary_kkt_anchor_solved', 'dsge_steady_state_solved',
                'local_first_order_policy_solved', 'leading_risky_portfolio_selected',
                'local_conditional_mean_irfs_computed', 'selected_regime_schur_solution_verified'):
        if status.get(key) is not True:
            errors.append(f'Implemented equation/anchor gate missing: {key}')
    for key in ('closed_form_pe_E27_inherited', 'legacy_tests_inherited',
                'nonlinear_policy_solved', 'calibrated', 'estimated',
                'independent_condition_count_verified', 'complete_dynamic_rank_verified',
                'full_dsge_solver_implemented', 'full_dsge_equilibrium_solved',
                'second_order_policy_solved', 'global_successor_feasibility_verified',
                'global_transversality_verified', 'stationary_wealth_distribution_verified',
                'nonlinear_projection_candidate_accepted', 'nonlinear_girfs_computed'):
        if spec.get(key) is not False:
            errors.append(f'Unsupported specification completion: {key}')
    for key in ('stochastic_policy_solver_implemented', 'local_first_order_policy_solved',
                'leading_risky_portfolio_selected', 'local_conditional_mean_irfs_computed',
                'selected_regime_schur_solution_verified'):
        if spec.get(key) is not True:
            errors.append(f'Implemented local scope missing: {key}')
    if spec['independent_condition_count'] is not None:
        errors.append('An unverified independent equation count was declared.')
    if spec['structural_kkt_unknown_count'] != '36 + L + R' or spec['structural_kkt_condition_count'] != '36 + L + R':
        errors.append('Documented necessary KKT count differs.')
    if spec['shock_states'] != ['z_omega', 'z_m', 'z_pj', 'z_kappa']:
        errors.append('Active shock definitions differ.')
    if status['checks'] != ['python scripts/check_repository.py', 'python scripts/validate_equation_chain.py',
                           'python scripts/validate_shocks.py', 'python scripts/solve_stochastic.py',
                           'python -m unittest discover -s tests -v']:
        errors.append('Default checks differ from current-only gates.')
    anchor_check_start = len(errors)
    for key in ('dsge_results_inherited', 'full_dsge_equilibrium_solved', 'full_dsge_solver_implemented', 'real_data_estimated'):
        if validation.get(key) is not False:
            errors.append(f'Unsupported validation result: {key}')
    if not validation.get('passed') or not validation['original_equation_audit']['passed']:
        errors.append('Current numerical validation did not pass.')
    if validation['original_equation_audit']['max_abs_residual'] > 1e-8:
        errors.append('Stationary KKT residual exceeds tolerance.')
    if not validation['tests']['passed'] or validation['tests']['run'] < 17:
        errors.append('Current economic regression evidence incomplete.')
    if validation['anchor_selection']['global_optimum_proved'] is not False:
        errors.append('Global optimality was not established.')
    if not validation['frozen_anchor_positive_risk_probe']['candidate_rejected']:
        errors.append('Failing positive-risk candidate was not rejected.')
    for source, expected in validation['source_sha256'].items():
        path = ROOT / source
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(f'Economic source changed after numerical evidence: {source}')
    for source in spec['implementation_files']:
        if source not in validation['source_sha256']:
            errors.append(f'Implemented file absent from validation fingerprints: {source}')

    anchor_verified = len(errors) == anchor_check_start
    local_metrics = check_local_stochastic(status, spec, validation, errors)
    shock_verified = check_shock_evidence(status, spec, errors)
    report_artifacts_verified = check_report_artifacts(status, errors)

    canonical = (ROOT / spec['canonical_document']).read_text(encoding='utf-8')
    headings = re.findall(r'^### (E\d{2})｜(.+)$', canonical, re.M)
    groups = spec['equation_groups']
    if headings != [(g['id'], g['title']) for g in groups]:
        errors.append('Canonical equation headings do not match the machine index.')
    if [g['id'] for g in groups] != [f'E{i:02}' for i in range(1, 41)]:
        errors.append('Expected E01--E40 groups exactly once, not a scalar equation count.')
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
        if not group.get('implementation_status'):
            errors.append(f'Missing implementation scope for {group["id"]}')

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
                  'data/README.md', 'model/README.md', 'model/dsge/README.md', 'references/README.md')]
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
    for run in historical['frozen_pe_checks']['commands']:
        if run['exit_code'] != 0 or run['passed'] is not True:
            errors.append(f'Frozen baseline check was not successful: {run["command"]}')

    report = {
        'scope': 'active equation consistency, existing numerical-evidence fingerprints and archive integrity; no economic solver invoked by this script',
        'model_id': status['model_id'], 'equation_groups': len(groups),
        'independent_equation_count_verified': False,
        'reference_records': len(ids), 'primary_reference': status['primary_reference_id'],
        'active_markdown_files': len(active_md), 'local_links_checked': links,
        'archive_files_verified': len(archived_paths), 'archive_bytes_verified': archived_bytes,
        'excluded_metadata_records': len(manifest['excluded']),
        'historical_tests_executed_by_this_check': False,
        'local_stochastic_result_scope': 'selected-regime first-order RE, leading portfolio and conditional-mean IRF; not global/nonlinear equilibrium',
        **local_metrics, 'shock_evidence_verified': shock_verified,
        'report_artifacts_verified': report_artifacts_verified,
        'full_nonlinear_stochastic_equilibrium_solved': False,
        'stationary_kkt_evidence_verified': anchor_verified,
        'errors': errors, 'passed': not errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())
