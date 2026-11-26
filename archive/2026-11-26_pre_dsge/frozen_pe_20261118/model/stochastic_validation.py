"""Independent economic audit of a saved stochastic policy approximation."""
from dataclasses import asdict, replace
import math

import numpy as np

from model.full_conditions import (
    DomainError, advance_state, evaluate_conditions, make_deterministic_anchor,
    primitives, risk_share_positions, validate_state,
)


def profit_flow(problem, states, decisions):
    """Producer profit at the supplied prices, without a price derivative."""
    p = problem.params
    e = problem.environment(states)
    q, j, spot = decisions[:, 0], decisions[:, 1], decisions[:, 5]
    q_cost = e["m"] * q + p.alpha / (p.nu + 1) * q * (q / e["K_e"]) ** p.nu
    q_cost += p.kappa / 2 * (q - states[:, 9]) ** 2
    j_cost = (e["p_j"] + p.omega_B * states[:, 13:12 + p.L].sum(axis=1)) * j
    j_cost += p.chi / 2 * j ** 2
    return spot * q - q_cost - j_cost


def recover_producer_value(problem, policy, training_states):
    """Project V-bE[V'] onto producer profit. V never updates the policy."""
    design = policy.design(training_states)
    weights = np.array([branch.probability for branch in problem.kernel.branches])
    current = policy.predict(training_states)
    target = profit_flow(problem, training_states, current)
    discount = problem.environment(training_states)["b"]
    bellman = design.copy()
    if hasattr(policy, "expected_design"):
        bellman -= discount[:, None] * policy.expected_design(training_states, current)
        projection_quadrature = "exact Rademacher basis moments"
    else:
        block_size = max(1, min(24, 2_000_000 // (len(weights) * design.shape[1])))
        for first in range(0, len(current), block_size):
            block = slice(first, first + block_size)
            next_states = problem.successors(training_states[block], current[block])
            next_design = policy.design(next_states.reshape(-1, training_states.shape[1]))
            weighted = np.einsum("k,bkf->bf", weights, next_design.reshape(len(next_states), len(weights), -1))
            bellman[block] -= discount[block, None] * weighted
        projection_quadrature = "explicit weighted basis evaluation at every target branch"
    coefficients, _, rank, _ = np.linalg.lstsq(bellman, target, rcond=1e-12)
    if not np.all(np.isfinite(coefficients)):
        raise DomainError("projected producer value is nonfinite")
    return coefficients, {
        "method": "linear discounted Bellman projection", "quadrature": projection_quadrature,
        "rank": int(rank), "columns": design.shape[1],
        "training_states": len(training_states),
        "raw_training_max": float(np.max(np.abs(bellman @ coefficients - target))),
        "coefficients": coefficients.tolist(),
    }


def _outside_domain(problem, states, tolerance):
    scaled = np.abs((states - problem.center) / problem.radius)
    return np.max(scaled, axis=-1) > 1 + tolerance


def draw_validation_states(problem, target, seed, radius_fraction, training_states):
    """Seeded feasible points in a declared local box, including its faces."""
    if not 0 < radius_fraction <= 1 or target < 1:
        raise ValueError("validation radius fraction must be in (0,1], count must be positive")
    rng = np.random.default_rng(seed)
    excluded = {tuple(row) for row in training_states}
    rows = []
    rejected = 0
    edge_count = 0
    while len(rows) < target and rejected < 30 * target:
        u = rng.uniform(-1, 1, size=problem.state_dimension)
        on_edge = len(rows) % 5 == 0
        if on_edge:
            axis = edge_count % problem.state_dimension
            u[axis] = -1 if (edge_count // problem.state_dimension) % 2 else 1
        row = problem.center + radius_fraction * problem.radius * u
        try:
            validate_state(problem.array_to_state(row), problem.params)
        except DomainError:
            rejected += 1
            continue
        key = tuple(row)
        if key in excluded:
            rejected += 1
            continue
        rows.append(row)
        excluded.add(key)
        edge_count += int(on_edge)
    if len(rows) != target:
        raise DomainError(f"constructed only {len(rows)} of {target} distinct feasible validation starts")
    return np.asarray(rows), {
        "requested": target, "accepted": len(rows), "rejected_before_policy_evaluation": rejected,
        "sample_box_faces": edge_count, "radius_fraction_of_policy_domain": radius_fraction,
        "boundaries_are_faces_of": "independent validation box",
    }


def _mc_summary(values):
    return {
        "mean": float(np.mean(values)),
        "sampling_standard_error": float(np.std(values, ddof=1) / np.sqrt(values.size))
        if values.size > 1 else None,
        "max_abs": float(np.max(np.abs(values))),
    }


def _finite_or_none(value):
    return float(value) if math.isfinite(value) else None


def discount_support_bound(problem):
    """Invariant enclosing box for the external states, when rho(abs(A))<1."""
    a = np.abs(np.array(problem.kernel.A))
    radius = float(np.max(np.abs(np.linalg.eigvals(a))))
    if radius >= 1:
        return {"found": False, "rho_abs_transition": radius}
    shocks = np.array([branch.innovation for branch in problem.kernel.branches])
    shock_bound = np.max(np.abs(shocks @ np.array(problem.kernel.B).T), axis=0)
    start = np.abs(problem.center[:9]) + problem.radius[:9]
    excess = np.maximum(a @ start + shock_bound - start, 0)
    box = start + np.linalg.solve(np.eye(9) - a, excess)
    # Use a tiny positive uniform slack to make the computed box enclosing
    # even when equalities are reached up to floating-point roundoff.
    box += np.linalg.solve(np.eye(9) - a, np.full(9, 1e-14))
    denominator = 1 + problem.params.i_bar - box[2]
    b_max = float(1 / denominator) if denominator > 0 else None
    return {
        "found": True, "rho_abs_transition": radius, "external_abs_upper": box.tolist(),
        "enclosure_independently_checked": bool(np.all(a @ box + shock_bound <= box)),
        "rate_denominator_lower": float(denominator), "b_max": b_max,
        "guarantees_uniform_discount_decay":
            bool(np.all(a @ box + shock_bound <= box)) and b_max is not None and b_max < 1,
        "scope": "external box; conditional on bounded profits and costates for objective and tail bounds",
    }


def policy_box_bounds(problem, policy, value_coefficients, discount_bound):
    """Simple coefficient envelope, conditional on staying in the policy box."""
    p = problem.params
    lower = problem.center - problem.radius
    upper = problem.center + problem.radius
    ramp_weights = np.asarray(p.g)
    capacity_min = float(lower[12] + lower[12 + p.L:] @ ramp_weights)
    capacity_max = float(upper[12] + upper[12 + p.L:] @ ramp_weights)
    b_max = discount_bound.get("b_max")
    if capacity_min <= 0 or not discount_bound.get("guarantees_uniform_discount_decay"):
        return None
    ext = np.asarray(discount_bound["external_abs_upper"])
    max_m = math.exp(ext[5]) * (p.m_domestic + p.FX_bar * math.exp(ext[1]) * p.m_usd)
    max_pj = p.pJ0 * math.exp(ext[6])
    q_lag_max = float(upper[9])
    xb_max = float(sum(upper[13:12 + p.L]))
    caps = np.sum(np.abs(policy.coefficients), axis=0)
    j_max, spot_max, wm_max = map(float, caps[[1, 5, 7]])
    adj_max = max(capacity_max, q_lag_max)
    max_cost_q = (max_m * capacity_max
                  + p.alpha/(p.nu+1)*capacity_max*(capacity_max/capacity_min)**p.nu
                  + p.kappa/2*adj_max**2)
    max_cost_j = (max_pj + p.omega_B*xb_max)*j_max + p.chi/2*j_max**2
    profit_bound = spot_max*capacity_max + max_cost_q + max_cost_j
    state_costate_bound = (p.kappa*adj_max*q_lag_max + wm_max*float(upper[12])
                           + float(np.dot(caps[8:], upper[13:])))
    return {
        "condition": "feasible counterparty decisions and all states stay in the declared policy box",
        "state_invariance_proved": False, "b_max": b_max,
        "undiscounted_absolute_profit_upper": profit_bound, "mature_shadow_upper": wm_max,
        "producer_value_polynomial_upper": float(np.sum(np.abs(value_coefficients))),
        "state_costate_absolute_sum_upper": state_costate_bound,
    }


def audit_paths(problem, policy, value_coefficients, options, tolerances):
    """Independent paths retain each realized b on its own continuation."""
    p = problem.params
    seed = int(options["path_seed"])
    paths = int(options["paths"])
    if paths < 2:
        raise ValueError("path diagnostics require at least two independent paths")
    horizons = sorted({int(h) for h in options["horizons"]} | {p.L})
    if horizons[0] <= 0:
        raise ValueError("tail horizons must be positive")
    rng = np.random.default_rng(seed)
    branch_prob = np.array([b.probability for b in problem.kernel.branches])
    states = np.broadcast_to(problem.center, (paths, problem.state_dimension)).copy()
    discount = np.ones(paths)
    accumulated_profit = np.zeros(paths)
    future_congestion = np.zeros(paths)
    maximum_excursion = 0.0
    outside_count = 0
    min_capacity = math.inf
    min_rate_denominator = math.inf
    min_physical_margin = math.inf
    min_carry = math.inf
    initial_j = None
    path_starts = []
    tail_results = []
    expanded = None
    failure = None
    value0 = float((policy.design(states[:1]) @ value_coefficients)[0])
    path_check_count = int(options.get("path_check_count", 32))
    if not 0 <= path_check_count <= paths:
        raise ValueError("path_check_count must be between zero and paths")
    picked = rng.choice(paths, size=path_check_count, replace=False)
    for period in range(horizons[-1] + 1):
        try:
            d = policy.predict(states)
            env = problem.environment(states)
        except (DomainError, FloatingPointError, OverflowError) as exc:
            failure = {"period": period, "message": str(exc), "paths_in_aborted_batch": paths}
            break
        q, j, ds, c, inventory, spot, futures = d[:, :7].T
        capacity, margin, b = env["K_e"], env["margin"], env["b"]
        carry = spot + p.h - b * p.alpha_I * futures
        rate_denominator = 1 + p.i_bar + states[:, 2]
        unexplored = _outside_domain(problem, states, tolerances["feasibility"])
        outside_count += int(np.count_nonzero(unexplored))
        maximum_excursion = max(maximum_excursion, float(np.max(np.abs((states - problem.center) / problem.radius))))
        min_capacity = min(min_capacity, float(np.min(capacity)))
        min_rate_denominator = min(min_rate_denominator, float(np.min(rate_denominator)))
        min_physical_margin = min(min_physical_margin, float(np.min(margin)))
        min_carry = min(min_carry, float(np.min(carry)))
        valid = (
            np.all(np.isfinite(states), axis=1) & np.all(np.isfinite(d), axis=1)
            & (np.min(states[:, 9:], axis=1) >= 0) & (capacity > 0) & (margin > 0)
            & (rate_denominator > 0) & (carry >= 0) & ((p.xi == 0) | (carry > 0))
            & (q >= 0) & ((q - capacity) <= tolerances["feasibility"] * problem.config["scales"]["quantity"])
            & (j >= 0) & (inventory >= 0) & (ds > 0) & (c > 0) & (spot > 0) & (futures > 0)
        )
        if not np.all(valid):
            bad = int(np.flatnonzero(~valid)[0])
            failure = {
                "period": period, "invalid_paths": int(np.count_nonzero(~valid)), "example_path": bad,
                "state": [_finite_or_none(x) for x in states[bad]],
                "policy": [_finite_or_none(x) for x in d[bad]],
                "physical_margin": _finite_or_none(margin[bad]), "carry": _finite_or_none(carry[bad]),
                "rate_denominator": _finite_or_none(rate_denominator[bad]),
            }
            break
        if period == 0:
            initial_j = float(j[0])
        if period == horizons[min(1, len(horizons) - 1)] and len(picked):
            path_starts.extend(states[picked].copy())
        if 0 < period < p.L:
            future_congestion += p.omega_B * discount * j
        if period == p.L:
            completed = d[:, 7 + p.L] if p.R else d[:, 7]
            current_pj = problem.environment(problem.center[None, :])["p_j"][0]
            initial_cost = current_pj + p.chi * initial_j + p.omega_B * problem.center[13:12 + p.L].sum()
            expanded = _mc_summary(initial_cost + future_congestion - discount * completed)
            expanded["discounted_future_congestion"] = _mc_summary(future_congestion)
            expanded["discounted_completed_capacity"] = _mc_summary(discount * completed)
        if period in horizons:
            level = policy.design(states) @ value_coefficients
            state_costates = (
                np.abs(p.kappa * (q - states[:, 9]) * states[:, 9])
                + np.abs(d[:, 7] * states[:, 12])
                + np.sum(np.abs(d[:, 8:] * states[:, 13:]), axis=1)
            )
            tail_results.append({
                "horizon": period, "path_discount": _mc_summary(discount),
                "discounted_absolute_mature_tail": _mc_summary(discount * (1 - p.delta) ** period * np.abs(d[:, 7])),
                "discounted_absolute_state_costate_tail": _mc_summary(discount * state_costates),
                "discounted_absolute_producer_value_tail": _mc_summary(discount * np.abs(level)),
                "bellman_roll_forward_minus_projected_V": _mc_summary(accumulated_profit + discount * level - value0),
            })
        if period < horizons[-1]:
            accumulated_profit += discount * profit_flow(problem, states, d)
            discount *= b
            states = problem.successors(states, d, rng.choice(len(branch_prob), paths, p=branch_prob))
    bound = discount_support_bound(problem)
    box_bounds = policy_box_bounds(problem, policy, value_coefficients, bound)
    if bound.get("guarantees_uniform_discount_decay"):
        for row in tail_results:
            horizon = row["horizon"]
            row["uniform_discount_upper_bound"] = bound["b_max"] ** horizon
            if box_bounds is not None:
                disc = row["uniform_discount_upper_bound"]
                profit_upper = box_bounds["undiscounted_absolute_profit_upper"]
                row["conditional_on_policy_box_upper_bounds"] = {
                    "discounted_absolute_future_profit_sum": disc * profit_upper / (1-bound["b_max"]),
                    "discounted_absolute_mature_tail": disc * (1-p.delta)**horizon * box_bounds["mature_shadow_upper"],
                    "discounted_absolute_state_costate_tail": disc * box_bounds["state_costate_absolute_sum_upper"],
                    "discounted_absolute_producer_value_tail": disc * box_bounds["producer_value_polynomial_upper"],
                }
    decay_names = ["path_discount", "discounted_absolute_mature_tail",
                   "discounted_absolute_state_costate_tail", "discounted_absolute_producer_value_tail"]
    decay = (
        failure is None and len(tail_results) > 1
        and all(last[key]["mean"] <= first[key]["mean"]
                for first, last in zip(tail_results, tail_results[1:]) for key in decay_names)
    )
    return np.asarray(path_starts).reshape(-1, problem.state_dimension), {
        "seed": seed, "paths": paths, "horizons": tail_results, "outside_domain_path_periods": outside_count,
        "maximum_domain_fraction": _finite_or_none(maximum_excursion), "failure": failure,
        "min_capacity": _finite_or_none(min_capacity), "min_rate_denominator": _finite_or_none(min_rate_denominator),
        "min_physical_margin": _finite_or_none(min_physical_margin), "min_inventory_carry": _finite_or_none(min_carry),
        "external_discount_bound": bound, "conditional_policy_box_envelopes": box_bounds,
        "tails_decayed_over_reported_horizons": decay,
        "sampled_tail_diagnostic_passed": decay and outside_count == 0,
        "global_invariant_domain_verified": False, "infinite_horizon_TVC_proved": False,
        "expanded_investment_gap": expanded,
    }


def _record(rows, category, name, value, scale, index):
    rows.setdefault(category, {}).setdefault(name, []).append((float(value), float(scale), index))


def _statistics(rows, states):
    def summarize(records):
        values = np.array([value for value, _, _ in records])
        scales = np.array([scale for _, scale, _ in records])
        abs_raw = np.abs(values)
        normalized = abs_raw / scales
        worst = int(np.argmax(normalized))
        idx = records[worst][2]
        quantiles = [0.5, 0.95, 0.99, 1.0]
        names = ["median", "p95", "p99", "max"]
        return {
            "count": len(records), "fixed_scale": float(scales[worst]),
            "absolute_raw": dict(zip(names, np.quantile(abs_raw, quantiles).tolist())),
            "absolute_normalized": dict(zip(names, np.quantile(normalized, quantiles).tolist())),
            "worst_signed_raw": float(values[worst]), "worst_state_index": idx,
            "worst_state": states[idx].tolist(),
        }
    return {category: {name: summarize(records) for name, records in series.items()} for category, series in rows.items()}


def audit_states(problem, policy, value_coefficients, states, tolerances):
    p = problem.params
    scales = problem.config["scales"]
    quantity, price, value = (scales[key] for key in ("quantity", "price", "value"))
    qtol = tolerances["feasibility"] * quantity
    domain_tol = tolerances["feasibility"]
    branches = problem.kernel.branches
    all_rows, errors = {}, []
    moments = []
    successor_count = 0
    outside_start_count = 0
    outside_successor_count = 0
    next_carry_bad = 0
    boundary_counts = dict(output_zero=0, output_at_capacity=0, investment_zero=0, inventory_zero=0)
    minima = dict(capacity=math.inf, commitment_margin=math.inf, carry=math.inf,
                  rate_denominator=math.inf, price=math.inf, demand=math.inf)
    for index, row in enumerate(states):
        try:
            state = problem.array_to_state(row)
            packed = policy.predict(row[None, :])[0]
            current_value = float((policy.design(row[None, :]) @ value_coefficients)[0]) if value_coefficients is not None else 0
            current = problem.decision(row, packed, current_value)
            # Advance each branch with the original scalar transition and use
            # batch policy evaluation only as a cache for the original auditor.
            future_states = tuple(advance_state(state, current, p, problem.kernel, branch) for branch in branches)
            next_rows = np.array([problem.state_to_array(sp) for sp in future_states])
            successor_count += len(next_rows)
            outside_start_count += int(_outside_domain(problem, row, domain_tol))
            outside_successor_count += int(np.count_nonzero(_outside_domain(problem, next_rows, domain_tol)))
            batch_next = problem.successors(row[None, :], packed[None, :])[0]
            timing_error = float(np.max(np.abs(batch_next - next_rows)))
            _record(all_rows, "state_transition", "E01_E10_E11_E12_E30_max", timing_error, quantity, index)
            next_packed = policy.predict(next_rows)
            next_values = policy.design(next_rows) @ value_coefficients if value_coefficients is not None else np.zeros(len(next_rows))
            policy_cache = {state: current}
            policy_cache.update({
                sp: problem.decision(arr, d, float(v))
                for sp, arr, d, v in zip(future_states, next_rows, next_packed, next_values)
            })
            checked = evaluate_conditions(state, policy_cache.__getitem__, p, problem.kernel, tolerance=qtol)
        except (DomainError, FloatingPointError, OverflowError) as exc:
            errors.append({"index": index, "state": row.tolist(), "message": str(exc)})
            continue
        for name, residual in checked["original_equalities"].items():
            if name == "producer_Bellman":
                if value_coefficients is not None:
                    _record(all_rows, "bellman", name, residual, scales["profit"], index)
            else:
                scale = value if name.startswith(("E14", "E15")) else (
                    quantity if name.startswith(("E25", "E26")) else price
                )
                _record(all_rows, "original_equalities", name, residual, scale, index)
        for name, residual in checked["derived_checks_not_extra_independent_conditions"].items():
            _record(all_rows, "derived_equalities", name, residual, price, index)
        for name, items in {
            **checked["original_complementarity"], "E24_inventory_reduced": checked["derived_inventory_complementarity"],
        }.items():
            dual_scale = value if name.startswith("E16") else price
            _record(all_rows, "primal", name, items["primal_violation"], quantity, index)
            _record(all_rows, "dual", name, items["dual_violation"], dual_scale, index)
            _record(all_rows, "complementarity", name, items["product"], quantity * dual_scale, index)
            _record(all_rows, "natural_complementarity", name,
                    min(items["primal"] / quantity, items["dual_gap"] / dual_scale), 1.0, index)
        env, diagnostics = checked["mapped_primitives"], checked["diagnostics"]
        cm = checked["conditional_moments"]
        successors = checked["successor_checks"]
        _record(all_rows, "primal", "successor_output_capacity",
                max(x["output_capacity_violation"] for x in successors), quantity, index)
        next_env = problem.environment(next_rows)
        carry_next = next_packed[:, 5] + p.h - next_env["b"] * p.alpha_I * next_packed[:, 6]
        next_carry_bad += int(np.count_nonzero((carry_next < 0) | ((p.xi > 0) & (carry_next == 0))))
        minima["carry"] = min(minima["carry"], diagnostics["inventory_linear_carry_gap"], float(np.min(carry_next)))
        k = float(problem.environment(row[None, :])["K_e"][0])
        minima["capacity"] = min(minima["capacity"], k, min(item["K_e"] for item in successors))
        minima["commitment_margin"] = min(minima["commitment_margin"], diagnostics["maximum_physical_margin"],
                                           min(item["maximum_physical_margin"] for item in successors))
        minima["rate_denominator"] = min(minima["rate_denominator"], 1/env["b"], min(1/item["b"] for item in successors))
        minima["price"] = min(minima["price"], current.spot, current.futures, float(next_packed[:, 5:7].min()))
        minima["demand"] = min(minima["demand"], current.d_s, current.c, float(next_packed[:, 2:4].min()))
        boundary_counts["output_zero"] += int(current.q <= qtol)
        boundary_counts["output_at_capacity"] += int(k - current.q <= qtol)
        boundary_counts["investment_zero"] += int(current.j <= qtol)
        boundary_counts["inventory_zero"] += int(current.inventory <= qtol)
        variance = cm["price_variance"]
        mu = cm["mean_price"]
        risk_capacity = 1 / p.a_I + 1 / p.a_D + 1 / env["a_f"]
        formula_premium = variance / risk_capacity * (p.alpha_I * current.inventory - current.c)
        moments.append((mu, variance, mu - current.futures, formula_premium))
        if current.inventory > 0:
            implied_f = mu - formula_premium
            e28 = (current.spot + p.h - p.xi / (current.inventory + p.I0)
                   - env["b"] * p.alpha_I * implied_f)
            _record(all_rows, "derived_equalities", "E28_positive_inventory_only", e28, price, index)
    stats = _statistics(all_rows, states)
    maxima = {
        key: max((x["absolute_normalized"]["max"] for x in variables.values()), default=0.0)
        for key, variables in stats.items()
    }
    economic = {f"{category}/{name}": item
                for category in ("original_equalities", "derived_equalities", "complementarity", "natural_complementarity")
                for name, item in stats.get(category, {}).items()}
    worst = max(economic, key=lambda name: economic[name]["absolute_normalized"]["max"]) if economic else None
    finite_stock = (minima["carry"] >= 0 if p.xi == 0 else minima["carry"] > 0)
    premium_diagnostic = {}
    if moments:
        _, _, premium, formula = np.array(moments).T
        difference = np.max(np.abs(premium - formula))
        formula_max = np.max(np.abs(formula))
        premium_diagnostic = {
            "raw_max_abs_error": float(difference),
            "max_error_relative_to_max_abs_formula_premium": float(difference / formula_max) if formula_max > 0 else None,
            "sign_disagreements": int(np.sum(premium * formula < 0)),
        }
    return {
        "distinct_requested_states": len(states), "successfully_evaluated_states": len(moments), "errors": errors,
        "successors_tested": successor_count, "outside_policy_domain_starts": outside_start_count,
        "outside_policy_domain_successors": outside_successor_count, "successors_with_unbounded_inventory": next_carry_bad,
        "global_domain_invariance_verified": False,
        "prior_commitment_and_positive_domain_minima": {k: v if math.isfinite(v) else None for k, v in minima.items()},
        "active_constraints_on_validation_states": boundary_counts, "per_condition": stats,
        "maxima_normalized": maxima, "worst_economic_condition": worst,
        "worst_economic_condition_statistics": economic.get(worst),
        "price_moments": {
            name: {k: float(v) for k, v in zip(("min", "median", "max"), np.quantile(series, (0, 0.5, 1)))}
            for name, series in zip(("conditional_mean_spot", "conditional_price_variance", "risk_premium",
                                     "risk_premium_implied_by_E27"), np.array(moments).T)
        } if moments else {},
        "risk_premium_consistency_diagnostic": premium_diagnostic,
        "checks": {
            "all_points_evaluated": not errors and bool(moments),
            "original_and_derived_equations": all(maxima.get(k, math.inf) <= tolerances["equilibrium"]
                                                  for k in ("original_equalities", "derived_equalities")),
            "primal_and_dual_feasibility": all(maxima.get(k, math.inf) <= tolerances["feasibility"] for k in ("primal", "dual")),
            "original_and_reduced_complementarity": maxima.get("complementarity", math.inf) <= tolerances["complementarity"],
            "natural_complementarity": maxima.get("natural_complementarity", math.inf) <= tolerances["equilibrium"],
            "bounded_inventory_choice": finite_stock and next_carry_bad == 0 and bool(moments),
            "approximation_box_coverage": outside_start_count == outside_successor_count == 0 and not errors and bool(moments),
            "observed_nonzero_price_risk": any(m[1] > 0 for m in moments),
            "independent_transition_match": maxima.get("state_transition", math.inf) <= tolerances["feasibility"],
            **({"recovered_producer_Bellman": maxima.get("bellman", math.inf) <= tolerances["equilibrium"]}
               if value_coefficients is not None else {}),
        },
    }


def audit_boundary_fixtures():
    """Synthetic edge cases, separate from fitted stochastic-policy coverage."""
    fixtures = []
    for L, R in ((1, 0), (1, 2), (3, 0), (3, 2)):
        anchor = make_deterministic_anchor(L, R)
        nxt = advance_state(anchor.state, anchor.decision, anchor.params, anchor.kernel, anchor.kernel.branches[0])
        old = asdict(anchor.state)
        new = asdict(nxt)
        keys = ("q_lag", "inventory_lag", "commitment_lag", "mature_capacity", "construction", "ramp")
        errors = [np.max(np.abs(np.asarray(old[k]) - np.asarray(new[k])), initial=0.0) for k in keys]
        r = evaluate_conditions(anchor.state, anchor.policy, anchor.params, anchor.kernel)
        fixtures.append({"case": f"queue_L{L}_R{R}", "max_raw_residual": r["max_equality_or_kkt_residual"],
                         "max_stationary_transition_error": float(max(errors)),
                         "passed": bool(r["all_local_conditions_passed"] and max(errors) <= 1e-10)})
    anchor = make_deterministic_anchor(1, 0)
    state, p, d = anchor.state, anchor.params, anchor.decision
    ds = (1 - p.omega) * (d.q + p.N0)
    c = p.omega * (d.q + p.N0)
    p = replace(p, D0=(d.q + p.N0) * (d.spot / p.P_star) ** p.eta_s,
                xi=0.5 * (d.spot + p.h - primitives(state, p)["b"] * p.alpha_I * d.futures) * p.I0)
    state = replace(state, inventory_lag=0.0, commitment_lag=c)
    hi, hd, hf = risk_share_positions(0.0, c, p, p.af0)
    d = replace(d, d_s=ds, c=c, inventory=0.0, h_inventory=hi, h_procurement=hd, h_financial=hf)
    r = evaluate_conditions(state, lambda _: d, p, anchor.kernel)
    dual = r["original_complementarity"]["E19_inventory_original"]["dual_gap"]
    fixtures.append({"case": "zero_inventory", "max_raw_residual": r["max_equality_or_kkt_residual"],
                     "strictly_positive_dual_gap": dual, "passed": r["all_local_conditions_passed"] and dual > 0})
    edge_p = replace(p, xi=2 * p.xi)
    edge = evaluate_conditions(state, lambda _: d, edge_p, anchor.kernel)
    dual_edge = edge["original_complementarity"]["E19_inventory_original"]["dual_gap"]
    fixtures.append({"case": "inventory_switching_point", "max_raw_residual": edge["max_equality_or_kkt_residual"],
                     "dual_gap": dual_edge, "passed": edge["all_local_conditions_passed"] and abs(dual_edge) < 1e-10})
    p = replace(p, delta=0.0)
    env = primitives(state, p)
    wm = r["recovered"]["current_capacity_service"] / (1 - env["b"])
    p = replace(p, pJ0=env["b"] * wm + 1.0)
    profit = d.spot*d.q - env["m"]*d.q - p.alpha/(p.nu+1)*d.q
    d = replace(d, j=0.0, w_m=wm, producer_value=profit/(1 - env["b"]))
    r = evaluate_conditions(state, lambda _: d, p, anchor.kernel)
    dual = r["original_complementarity"]["E16_investment"]["dual_gap"]
    cap_dual = r["recovered"]["lambda_capacity"]
    fixtures.append({"case": "zero_investment_and_binding_capacity", "max_raw_residual": r["max_equality_or_kkt_residual"],
                     "strictly_positive_investment_dual_gap": dual, "capacity_multiplier": cap_dual,
                     "passed": r["all_local_conditions_passed"] and dual > 0 and cap_dual > 0})
    edge = evaluate_conditions(state, lambda _: d, replace(p, pJ0=env["b"] * wm), anchor.kernel)
    dual_edge = edge["original_complementarity"]["E16_investment"]["dual_gap"]
    fixtures.append({"case": "investment_switching_point", "max_raw_residual": edge["max_equality_or_kkt_residual"],
                     "dual_gap": dual_edge, "passed": edge["all_local_conditions_passed"] and abs(dual_edge) < 1e-10})
    # Separate stationary interior-output witness: zero investment holds
    # capacity fixed, while a lower demand scale clears at marginal cost.
    q = 0.8
    spot = env["m"] + p.alpha * (q / state.mature_capacity) ** p.nu
    use = q + p.N0
    p = replace(p, D0=use * (spot / p.P_star) ** p.eta_s,
                xi=0.5 * (spot + p.h - env["b"] * p.alpha_I * spot) * p.I0)
    ds = (1-p.omega) * use
    c = p.omega * use
    state = replace(state, q_lag=q, commitment_lag=c)
    wm = p.alpha * p.nu / (p.nu+1) * (q/state.mature_capacity) ** (p.nu+1) / (1-env["b"])
    profit = spot*q - env["m"]*q - p.alpha/(p.nu+1)*q*(q/state.mature_capacity)**p.nu
    hi, hd, hf = risk_share_positions(0.0, c, p, p.af0)
    d = replace(d, q=q, d_s=ds, c=c, spot=spot, futures=spot, w_m=wm, producer_value=profit/(1-env["b"]),
                h_inventory=hi, h_procurement=hd, h_financial=hf)
    r = evaluate_conditions(state, lambda _: d, p, anchor.kernel)
    no_rents = max(r["recovered"]["lambda_capacity"], r["recovered"]["mu_output"]) <= 1e-10
    fixtures.append({"case": "interior_production", "max_raw_residual": r["max_equality_or_kkt_residual"],
                     "capacity_slack": state.mature_capacity-q,
                     "passed": r["all_local_conditions_passed"] and no_rents and 0 < q < state.mature_capacity})
    return {"checks": fixtures, "passed": all(case["passed"] for case in fixtures)}


def compare_policies(problem, reference, alternatives, states):
    """Compare candidates on identical states with exact Rademacher moments."""
    p = problem.params
    names = ["Q", "J", "D_s", "C", "I", "P", "F", "W_M"]
    names += [f"W_B_{h}" for h in range(1, p.L)]
    names += [f"W_Z_{a}" for a in range(p.R)]

    def measures(policy):
        values = policy.predict(states)
        moments = policy.moments(states, values)
        mu, var = moments["mean_price"], moments["price_variance"]
        return values, moments, np.column_stack((mu, var, mu-values[:, 6]))

    def differences(current, base, labels):
        absolute = np.abs(current-base)
        return {label: {"max_abs": float(np.max(column)), "p95_abs": float(np.quantile(column, 0.95))}
                for label, column in zip(labels, absolute.T)}

    base_values, base_moments, base_price_measures = measures(reference)
    comparisons = []
    test_keys = {tuple(row) for row in states}
    for name, candidate, training_states in alternatives:
        try:
            values, moments, price_measures = measures(candidate)
            reduced_max = float(np.max(np.abs(problem.residual(states, values, moments))))
        except (DomainError, FloatingPointError, OverflowError) as exc:
            comparisons.append({"candidate": name, "evaluation_error": str(exc)})
            continue
        same_basis = np.array_equal(candidate.powers, reference.powers)
        comparisons.append({
            "candidate": name, "basis_degree": int(candidate.powers.sum(axis=1).max()),
            "basis_terms": len(candidate.powers), "same_basis": bool(same_basis),
            "overlap_with_candidate_training_states": sum(tuple(row) in test_keys for row in training_states),
            "coefficient_max_abs_difference": (
                float(np.max(np.abs(candidate.coefficients-reference.coefficients))) if same_basis else None),
            "policy_differences": differences(values, base_values, names),
            "moment_differences": differences(price_measures, base_price_measures,
                                               ["conditional_mean_spot", "conditional_variance", "risk_premium"]),
            "candidate_reduced_residual_max_absolute_normalized": reduced_max,
        })
    return {
        "shared_test_states": len(states), "reference_basis_degree": int(reference.powers.sum(axis=1).max()),
        "reference_reduced_residual_max_absolute_normalized": float(
            np.max(np.abs(problem.residual(states, base_values, base_moments)))),
        "integration": "exact Rademacher moments at the same states; primary audit uses explicit 512 successors",
        "comparisons": comparisons,
    }


def validate_policy(problem, policy, training_states, config, residual_only=False, alternatives=()):
    validation = config["validation"]
    tolerances = config["tolerances"]
    states, sample = draw_validation_states(problem, validation["count"], validation["seed"],
                                            validation.get("radius_fraction", 0.15), training_states)
    if residual_only:
        conditions = audit_states(problem, policy, None, states, tolerances)
        return {
            "residual_only": True, "numerical_acceptance_passed": False,
            "acceptance_gates": conditions["checks"],
            "state_dimension": problem.state_dimension, "minimal_policy_dimension": problem.policy_dimension,
            "full_target_nodes_per_state": len(problem.kernel.branches),
            "fixed_scales": config["scales"], "tolerances": tolerances, "sample": sample,
            "independent_state_seed": validation["seed"], "conditions": conditions,
            **({"sensitivity": compare_policies(problem, policy, alternatives, states)} if alternatives else {}),
        }
    value_coefficients, value_info = recover_producer_value(problem, policy, training_states)
    path_points, tails = audit_paths(problem, policy, value_coefficients, validation, tolerances)
    sample_keys = {tuple(row) for row in np.concatenate((states, training_states))}
    genuinely_independent = []
    for row in path_points:
        key = tuple(row)
        if key not in sample_keys:
            genuinely_independent.append(row)
            sample_keys.add(key)
    sample["path_points_available"] = len(path_points)
    sample["path_points_distinct_and_out_of_training"] = len(genuinely_independent)
    combined = np.vstack((states, genuinely_independent)) if genuinely_independent else states
    conditions = audit_states(problem, policy, value_coefficients, combined, tolerances)
    paths = audit_states(problem, policy, value_coefficients, np.asarray(genuinely_independent), tolerances) if genuinely_independent else None
    # Exact one-step gap for comparison with the sampled multi-period expansion.
    center = audit_center_investment(problem, policy)
    expanded = tails["expanded_investment_gap"]
    if expanded and expanded["sampling_standard_error"] is not None:
        expanded["exact_one_step_gap"] = center
        expanded["expansion_minus_one_step"] = expanded["mean"] - center
        expanded["consistent_with_one_step_at_four_standard_errors"] = (
            abs(expanded["expansion_minus_one_step"]) <= 4*expanded["sampling_standard_error"]
            + tolerances["equilibrium"]*config["scales"]["value"]
        )
    boundary = audit_boundary_fixtures()
    gates = {
        **conditions["checks"], "at_least_200_independent_starts": len(states) >= 200,
        "independent_path_states": paths is not None and len(genuinely_independent) == validation.get("path_check_count", 32),
        "path_tail_diagnostic": tails["sampled_tail_diagnostic_passed"],
        "discount_support_bound": tails["external_discount_bound"].get("guarantees_uniform_discount_decay", False),
        "investment_expansion_MC_check": bool(expanded and expanded.get("consistent_with_one_step_at_four_standard_errors")),
        "separate_boundary_fixtures": boundary["passed"],
    }
    return {
        "acceptance_gates": gates, "numerical_acceptance_passed": all(gates.values()),
        "state_dimension": problem.state_dimension, "minimal_policy_dimension": problem.policy_dimension,
        "full_target_nodes_per_state": len(problem.kernel.branches),
        "fixed_scales": config["scales"], "tolerances": tolerances,
        "independent_state_seed": validation["seed"], "sample": sample,
        "training_states": len(training_states), "conditions": conditions, "path_conditions": paths,
        "boundary_fixtures": boundary, "producer_value_projection": value_info, "tails": tails,
        **({"sensitivity": compare_policies(problem, policy, alternatives, combined)} if alternatives else {}),
        "parameter_calibration_performed": False, "global_invariance_or_uniqueness_proved": False,
    }


def audit_center_investment(problem, policy):
    p = problem.params
    state = problem.center[None, :]
    packed = policy.predict(state)
    after = problem.successors(state, packed)[0]
    continuation = policy.predict(after)
    column = 7 + p.L - 1 if p.L > 1 else (8 if p.R else 7)
    expected = math.fsum(branch.probability * x for branch, x in zip(problem.kernel.branches, continuation[:, column]))
    env = problem.environment(state)
    return float(env["p_j"][0] + p.chi * packed[0, 1] + p.omega_B * state[0, 13:12 + p.L].sum()
                 - env["b"][0] * expected)
