"""Diagnostics for the frozen policy's large numerical approximation box."""

from collections import Counter
import json
from pathlib import Path

import numpy as np

from model.full_conditions import EXTERNAL_NAMES, DomainError, advance_state, evaluate_conditions
from model.stochastic_validation import draw_validation_states


def state_names(problem):
    p = problem.params
    return (*EXTERNAL_NAMES, "Q_lag", "I_lag", "C_lag", "K_M",
            *(f"B_{h}" for h in range(1, p.L)), *(f"Z_{a}" for a in range(p.R)))


def physical_violations(problem, states, decisions):
    """Separate physical feasibility from the approximation box and first-order conditions."""
    p = problem.params
    q, j, ds, c, inventory, spot, futures = decisions[:, :7].T
    rate_denominator = 1 + p.i_bar + states[:, 2]
    capacity = problem.capacity(states)
    resources = capacity + p.N0 + p.N_scale*states[:, 7] + p.alpha_I*states[:, 10] - states[:, 11]
    qtol = problem.config["scales"]["quantity"] * problem.config["tolerances"]["feasibility"]
    with np.errstate(divide="ignore", invalid="ignore"):
        carry = spot + p.h - p.alpha_I*futures/rate_denominator
    inherited = {
        "nonfinite_state": ~np.isfinite(states).all(axis=1),
        "negative_inherited_quantity": (states[:, 9:] < 0).any(axis=1),
        "nonpositive_discount_denominator": rate_denominator <= 0,
        "nonpositive_capacity": capacity <= 0,
        "unfulfillable_old_commitment": resources <= 0,
    }
    choices = {
        "nonfinite_policy": ~np.isfinite(decisions).all(axis=1),
        "nonpositive_price_or_demand": (ds <= 0) | (c <= 0) | (spot <= 0) | (futures <= 0),
        "negative_current_quantity": (q < 0) | (j < 0) | (inventory < 0),
        "output_above_capacity": q > capacity + qtol,
        "unbounded_inventory_objective": (carry < 0) | ((carry == 0) & (p.xi > 0)),
    }
    return inherited, choices


def _combine(masks):
    return np.logical_or.reduce(tuple(masks.values()))


def _counts(masks):
    return {name: int(values.sum()) for name, values in masks.items()}


def _reasons(masks, index):
    return [name for name, values in masks.items() if values[index]]


def _coefficient_bounds(policy):
    """Conservative termwise intervals on the whole coordinate box [-1,1]^d."""
    coefficients = policy.coefficients[1:]
    even_only = np.all(policy.powers[1:] % 2 == 0, axis=1)
    lower = np.where(even_only[:, None], np.minimum(coefficients, 0), -np.abs(coefficients))
    upper = np.where(even_only[:, None], np.maximum(coefficients, 0), np.abs(coefficients))
    return policy.coefficients[0] + lower.sum(axis=0), policy.coefficients[0] + upper.sum(axis=0)


def predecessor_screens(problem, policy, state):
    """Necessary conditions for a prior state inside the same approximation box.

    These interval tests can exclude an in-box predecessor, but their passage
    cannot exhibit one. An arbitrary initial state need not have a predecessor.
    """
    p = problem.params
    lo, hi = problem.center-problem.radius, problem.center+problem.radius
    lower, upper = _coefficient_bounds(policy)
    qtol = problem.config["scales"]["quantity"]*problem.config["tolerances"]["feasibility"]
    tests = {}

    def necessary(name, actual, low, high, tolerance=qtol):
        actual, low, high = float(actual), float(low), float(high)
        tests[name] = {"observed": actual, "necessary_interval": [low, high],
                       "passes": bool(low-tolerance <= actual <= high+tolerance)}

    for i, name in enumerate(EXTERNAL_NAMES):
        support = problem.persistence[i]*np.array([lo[i], hi[i]])
        support.sort()
        amplitude = problem.amplitudes[i]
        good = any(support[0]-qtol <= state[i]-shock <= support[1]+qtol for shock in (-amplitude, amplitude))
        tests[f"external_predecessor_{name}"] = {
            "observed": float(state[i]), "per_sign_intervals": [[float(x-amplitude) for x in support],
                                                               [float(x+amplitude) for x in support]],
            "passes": bool(good),
        }
    necessary("I_lag_as_previous_I", state[10], lower[4], upper[4])
    necessary("C_lag_as_previous_C", state[11], lower[3], upper[3])
    if p.L > 1:
        for h in range(p.L-2):
            necessary(f"B_{h+1}_as_shifted_previous_B_{h+2}", state[13+h], lo[14+h], hi[14+h])
        necessary("last_B_as_previous_J", state[problem.ramp_start-1], lower[1], upper[1])

    survival = 1-p.delta
    if p.R:
        first_bound = (lo[13], hi[13]) if p.L > 1 else (lower[1], upper[1])
        necessary("Z_0_as_previous_completion", state[problem.ramp_start], *first_bound)
        for a in range(p.R-1):
            necessary(f"Z_{a+1}_as_surviving_previous_Z_{a}",
                      state[problem.ramp_start+a+1], survival*lo[problem.ramp_start+a],
                      survival*hi[problem.ramp_start+a])
        # M' = survival*(M+Z_{R-1}); and Z'_{a+1} fixes previous Z_a.
        zlast_low = max(lo[-1], state[12]/survival-hi[12])
        zlast_high = min(hi[-1], state[12]/survival-lo[12])
        necessary("joint_mature_and_last_ramp_predecessor", zlast_low, lo[-1], zlast_high)
        previous_fixed = state[12]/survival + np.dot(p.g[:-1], state[problem.ramp_start+1:])/survival
        limits = previous_fixed + (p.g[-1]-1)*np.array([zlast_low, zlast_high])
    else:
        completion_low, completion_high = (lo[13], hi[13]) if p.L > 1 else (lower[1], upper[1])
        limits = np.array([max(lo[12], (state[12]-completion_high)/survival),
                           min(hi[12], (state[12]-completion_low)/survival)])
        necessary("joint_mature_and_completion_predecessor", limits[0], lo[12], limits[1])
    necessary("Q_lag_as_previous_capacity_plus_Q_offset_given_queues",
              state[9], min(limits)+lower[0], max(limits)+upper[0])
    return tests


def _raw_dual_gaps(problem, policy, states, choices, block_size=256):
    """Branchwise exact Walsh screening; independent explicit audit cross-checks its extrema."""
    p = problem.params
    result = np.full((len(states), 4), np.nan)
    for first in range(0, len(states), block_size):
        block = slice(first, first+block_size)
        s, d = states[block], choices[block]
        env = problem.environment(s)
        continuation = policy.moments(s, d)
        mean_p, variance = continuation["mean_price"], continuation["price_variance"]
        b, alpha_i = env["b"], p.alpha_I
        carry = d[:, 5]+p.h-p.xi/(d[:, 4]+p.I0)
        output_gradient = (d[:, 5]-env["m"]-p.alpha*(d[:, 0]/env["K_e"])**p.nu
                           -p.kappa*(d[:, 0]-s[:, 9])
                           + b*p.kappa*(continuation["mean_Q"]-d[:, 0]))
        expected_opening = (continuation["mean_W_B"][:, -1] if p.L > 1 else
                            continuation["mean_W_Z"][:, 0] if p.R else continuation["mean_W_M"])
        investment_gap = env["p_j"]+p.chi*d[:, 1]+p.omega_B*s[:, 13:problem.ramp_start].sum(axis=1)-b*expected_opening
        exposure = alpha_i*d[:, 4]-d[:, 3]
        total_tolerance = 1/p.a_I+1/p.a_D+1/env["a_f"]
        original_inventory_gap = carry-b*alpha_i*(mean_p-variance*exposure/total_tolerance)
        reduced_inventory_gap = carry-b*alpha_i*d[:, 6]
        result[block] = np.column_stack((investment_gap, original_inventory_gap, reduced_inventory_gap,
                                         output_gradient))
    return result


def _evaluate_raw(problem, policy, state, decision=None, next_states=None):
    p = problem.params
    row = problem.state_to_array(state)
    current = problem.decision(row, policy.predict(row)) if decision is None else decision
    if next_states is None:
        next_states = tuple(advance_state(state, current, p, problem.kernel, branch)
                            for branch in problem.kernel.branches)
    next_rows = np.asarray([problem.state_to_array(after) for after in next_states])
    next_decisions = policy.predict(next_rows)
    cache = {state: current}
    cache.update((after, problem.decision(row, decision))
                 for after, row, decision in zip(next_states, next_rows, next_decisions))
    tolerance = problem.config["scales"]["quantity"] * problem.config["tolerances"]["feasibility"]
    report = evaluate_conditions(state, cache.__getitem__, p, problem.kernel, tolerance=tolerance)
    env = report["mapped_primitives"]
    inventory = report["original_complementarity"]["E19_inventory_original"]
    investment = report["original_complementarity"]["E16_investment"]
    reduced = report["derived_inventory_complementarity"]
    return {
        "original_equalities_excluding_unrecovered_Bellman": {
            name: val for name, val in report["original_equalities"].items() if name != "producer_Bellman"},
        "derived_equalities": report["derived_checks_not_extra_independent_conditions"],
        "original_complementarity": report["original_complementarity"],
        "reduced_inventory_complementarity": reduced,
        "price_moments": report["conditional_moments"],
        "net_hedging_exposure": p.alpha_I*current.inventory-current.c,
        "risk_premium_mu_minus_F": report["conditional_moments"]["mean_price"]-current.futures,
        "interest_rate_denominator": 1/env["b"],
        "inventory_carry_gap": report["diagnostics"]["inventory_linear_carry_gap"],
        "maximum_physical_margin": report["diagnostics"]["maximum_physical_margin"],
        "duality_raw_gaps": [investment["dual_gap"], inventory["dual_gap"], reduced["dual_gap"]],
    }


def audit_box(problem, policy, training_states, output, *, count=64, seed=177303, provenance=None):
    """Repeat the historical large-box challenge and retain every successor."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    states, sample = draw_validation_states(problem, count, seed, 1.0, training_states)
    state_labels = state_names(problem)
    tol, scales = problem.config["tolerances"], problem.config["scales"]
    choices = policy.predict(states)
    inherited, start_policy = physical_violations(problem, states, choices)
    bad_initial, bad_current_policy = _combine(inherited), _combine(start_policy)
    target_nodes = len(problem.kernel.branches)
    successors = []
    for row, choice in zip(states, choices):
        state, decision = problem.array_to_state(row), problem.decision(row, choice)
        successors.append([
            problem.state_to_array(advance_state(state, decision, problem.params, problem.kernel, shock))
            for shock in problem.kernel.branches
        ])
    successors = np.asarray(successors)
    flat_states = successors.reshape(-1, problem.state_dimension)
    next_choices = np.vstack([policy.predict(part) for part in np.array_split(flat_states, count)])
    next_inherited, next_policy = physical_violations(problem, flat_states, next_choices)
    bad_next_state, bad_next_policy = _combine(next_inherited), _combine(next_policy)
    overrun = np.maximum(np.abs((flat_states-problem.center)/problem.radius)-1, 0)
    out_axes = overrun > tol["feasibility"]
    outside = out_axes.any(axis=1)
    valid_next = ~(bad_next_state | bad_next_policy)
    dual_labels = ("E16_investment", "E19_inventory_original", "E24_inventory_reduced")
    dual_scales = np.array([scales["value"], scales["price"], scales["price"]])
    dual_gaps = np.full((len(flat_states), 4), np.nan)
    dual_gaps[valid_next] = _raw_dual_gaps(problem, policy, flat_states[valid_next], next_choices[valid_next])
    norm_dual = np.maximum(-dual_gaps[:, :3], 0)/dual_scales
    bad_dual = (norm_dual > tol["feasibility"]).any(axis=1)
    start_reports = []
    predecessor_excluded = []
    for index, state_row in enumerate(states):
        bounds = predecessor_screens(problem, policy, state_row)
        failed = [name for name, result in bounds.items() if not result["passes"]]
        predecessor_excluded.append(bool(failed))
        state = problem.array_to_state(state_row)
        raw = None
        raw_error = None
        try:
            raw = _evaluate_raw(problem, policy, state, problem.decision(state_row, choices[index]))
        except DomainError as exc:
            raw_error = str(exc)
        block = slice(index*target_nodes, (index+1)*target_nodes)
        start_dual = np.maximum(-np.array(raw["duality_raw_gaps"]), 0)/dual_scales if raw else None
        start_reports.append({
            "index": index, "state": state_row.tolist(), "inherited_state_violations": _reasons(inherited, index),
            "frozen_policy_primal_violations": _reasons(start_policy, index),
            "one_step_predecessor_in_original_box": "excluded_by_necessary_conditions" if failed else "unresolved",
            "failed_predecessor_checks": failed, "predecessor_checks": bounds,
            "outgoing_outside_count": int(outside[block].sum()),
            "outgoing_economically_infeasible_count": int((~valid_next[block]).sum()),
            "outgoing_dual_violation_count": int(bad_dual[block].sum()),
            "start_normalized_dual_violations": start_dual.tolist() if start_dual is not None else None,
            "original_raw_checks": raw, "raw_check_error": raw_error,
        })
    with (output/"branch_failure_details.jsonl").open("w", encoding="utf-8") as stream:
        for flat_index in np.flatnonzero(outside | ~valid_next | bad_dual):
            index, branch_index = divmod(int(flat_index), target_nodes)
            branch = problem.kernel.branches[branch_index]
            axes = np.flatnonzero(out_axes[flat_index])
            data = {
                "start_index": index, "branch_index": branch_index, "shock": list(branch.innovation),
                "successor": flat_states[flat_index].tolist(),
                "out_of_box": [{
                    "dimension": state_labels[axis],
                    "side": "upper" if flat_states[flat_index, axis] > problem.center[axis] else "lower",
                    "normalized_overrun": float(overrun[flat_index, axis]),
                    "raw_overrun": float(overrun[flat_index, axis]*problem.radius[axis]),
                } for axis in axes],
                "inherited_violations": _reasons(next_inherited, flat_index),
                "primal_violations": _reasons(next_policy, flat_index),
                "normalized_dual_violations": dict(zip(dual_labels, norm_dual[flat_index].tolist()))
                if valid_next[flat_index] else None,
                "raw_dual_gaps": dict(zip(dual_labels, dual_gaps[flat_index, :3].tolist()))
                if valid_next[flat_index] else None,
            }
            stream.write(json.dumps(data, allow_nan=False, separators=(",", ":"))+"\n")
    np.savez_compressed(output/"all_branches.npz", starts=states, successors=successors,
                        innovations=problem.innovations, decisions=next_choices.reshape(count, target_nodes, -1),
                        overrun=overrun.reshape(count, target_nodes, -1), state_names=state_labels,
                        raw_dual_gaps=dual_gaps.reshape(count, target_nodes, -1), dual_labels=(*dual_labels, "E09_output_gradient"))
    dimensions = {}
    for axis, label in enumerate(state_labels):
        if out_axes[:, axis].any():
            pos = int(np.argmax(overrun[:, axis]))
            index, branch = divmod(pos, target_nodes)
            dimensions[label] = {
                "branches": int(out_axes[:, axis].sum()), "starts": int(out_axes[:, axis].reshape(count, -1).any(axis=1).sum()),
                "greatest_overrun_normalized": float(overrun[pos, axis]),
                "greatest_overrun_raw": float(overrun[pos, axis]*problem.radius[axis]),
                "worst_start_index": index, "worst_branch_index": branch,
                "worst_start": states[index].tolist(), "worst_shock": list(problem.kernel.branches[branch].innovation),
                "worst_successor": flat_states[pos].tolist(),
            }
    exact_checks = []
    # Predetermined cross-check design: extrema by breached coordinate and by each dual equation.
    selected = {row["worst_start_index"]*target_nodes+row["worst_branch_index"] for row in dimensions.values()}
    for axis in range(len(dual_labels)):
        if valid_next.any():
            selected.add(int(np.nanargmax(norm_dual[:, axis])))
    for index in sorted(selected):
        after = problem.array_to_state(flat_states[index], time=1)
        record = {"start_index": index//target_nodes, "branch_index": index % target_nodes}
        try:
            raw = _evaluate_raw(problem, policy, after)
            record["explicit_512_original_checks"] = raw
            record["largest_disagreement_with_walsh_dual_screen"] = float(
                np.max(abs(np.array(raw["duality_raw_gaps"])-dual_gaps[index, :3])))
        except DomainError as exc:
            record["explicit_512_error"] = str(exc)
        exact_checks.append(record)
    by_start = outside.reshape(count, -1)
    predecessor_excluded = np.asarray(predecessor_excluded)
    report = {
        "scope": "full approximation box challenge of a frozen polynomial, not a simulated path or global invariant-domain test",
        "provenance": provenance, "initial_seed": seed, "sample": sample, "normalization": scales, "tolerances": tol,
        "physical_initial_states": {"violating": int(bad_initial.sum()), "checks": _counts(inherited),
                                    "frozen_policy_primal_violating": int(bad_current_policy.sum()),
                                    "frozen_policy_checks": _counts(start_policy)},
        "reachability": {
            "physically_feasible_but_actual_predecessor_reachability_not_established": int((~bad_initial).sum()),
            "physically_feasible_without_any_in_box_predecessor_by_necessary_conditions": int((~bad_initial & predecessor_excluded).sum()),
            "physically_feasible_with_unresolved_in_box_predecessor": int((~bad_initial & ~predecessor_excluded).sum()),
            "failures_by_necessary_condition": dict(Counter(name for start in start_reports for name in start["failed_predecessor_checks"])),
            "outgoing_overruns_from_excluded_in_box_predecessor_starts": int(by_start[predecessor_excluded].sum()),
            "outgoing_overruns_from_unresolved_in_box_predecessor_starts": int(by_start[~predecessor_excluded].sum()),
            "starts_generated_by_feasible_simulation": 0,
            "scope_note": "Output of a necessary one-step test restricted to in-box predecessors; arbitrary feasible initial states remain in the audit.",
        },
        "successors": {
            "checked": len(flat_states), "approximation_box_violating": int(outside.sum()),
            "starts_with_approximation_box_violation": int(by_start.any(axis=1).sum()),
            "starts_where_outside_count_depends_on_shock": int(((by_start.sum(axis=1) > 0) &
                                                               (by_start.sum(axis=1) < target_nodes)).sum()),
            "economic_state_infeasible": int(bad_next_state.sum()), "economic_state_checks": _counts(next_inherited),
            "economic_policy_primal_infeasible": int(bad_next_policy.sum()), "economic_policy_checks": _counts(next_policy),
            "any_economic_infeasible": int((~valid_next).sum()),
            "any_normalized_dual_violation": int(bad_dual.sum()),
            "in_box_dual_violation": int((~outside & bad_dual).sum()),
            "out_of_box_dual_violation": int((outside & bad_dual).sum()),
            "outside_and_economically_infeasible": int((outside & ~valid_next).sum()),
            "dual_violations_by_equation": dict(zip(dual_labels, (norm_dual > tol["feasibility"]).sum(axis=0).tolist())),
            "maximum_normalized_dual_violation": dict(zip(dual_labels, np.nanmax(norm_dual, axis=0).tolist())),
        },
        "axis_overruns": dimensions,
        "start_details": start_reports,
        "exact_successor_cross_checks": exact_checks,
        "attachments": ["branch_failure_details.jsonl", "all_branches.npz"],
    }
    (output/"box_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+"\n",
                                         encoding="utf-8")
    return report
