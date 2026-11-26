"""Audit original equations at one state and all supplied conditional branches.

The caller supplies future choices. This evaluator verifies their timing and
computes expectations under the declared kernel; it does not solve a policy or
establish global feasibility/transversality. All named residuals are audit
conditions, including deliberately redundant accounting checks.
"""

from dataclasses import fields
import numpy as np
from .economy import budgets, diagnostics, downstream_output
from .shocks import kernel, mappings
from .state import effective_capacity, next_state, state_vector


def _domain(state, choice, p):
    errors = []
    shapes = ((state.z, 4), (state.construction, p.construction_lag - 1),
              (state.ramp, p.ramp_length), (state.bonds, 4), (state.old_positions, 3),
              (choice.consumption, 4), (choice.next_bonds, 4), (choice.positions, 3),
              (choice.wb, p.construction_lag - 1), (choice.wz, p.ramp_length),
              (choice.debt_multipliers, 3))
    if any(np.shape(v) != (n,) for v, n in shapes):
        errors.append("State/control vector dimension mismatch")
        return errors
    for obj in (state, choice):
        for field in fields(obj):
            if not np.all(np.isfinite(getattr(obj, field.name))):
                errors.append("Nonfinite " + field.name)
    if errors:
        return errors
    positive = (state.commitment_prev, choice.flexible, choice.commitment,
                choice.labor_w, choice.labor_d, choice.labor_0, choice.wage, choice.spot,
                choice.forward, choice.price_0, choice.price_b, choice.output_0,
                choice.output_b, choice.output, choice.gross_rate)
    if min(positive) <= 0 or min(choice.consumption) <= 0 or effective_capacity(state, p) <= 0:
        errors.append("Positive-consumption/interior-production domain violated")
    if state.q_prev < 0 or state.inventory_prev < 0 or state.mature < 0 or choice.q < 0:
        errors.append("Negative inherited/current physical quantity")
    if np.any(state.construction < 0) or np.any(state.ramp < 0):
        errors.append("Negative capacity queue")
    return errors


def _successor_feasibility(state, choice, p, tolerance):
    """Feasible successor controls are necessary, even before their FOCs are solved."""
    errors = []
    if choice.investment < -tolerance or choice.inventory < -tolerance:
        errors.append("Negative successor investment or inventory")
    if choice.q > effective_capacity(state, p) + tolerance:
        errors.append("Successor output exceeds effective capacity")
    if np.any(choice.next_bonds[:3] < np.array(p.debt_floors) - tolerance):
        errors.append("Successor debt limit violated")
    ex = mappings(state, p)
    slack = choice.next_bonds[3] / choice.gross_rate - ex["collateral"] * choice.spot * abs(choice.positions[2])
    if slack < -tolerance:
        errors.append("Successor collateral constraint violated")
    return errors


def evaluate(state, choice, branches, p, tolerance=1e-8):
    """Return all residuals and reject domain/kernel errors without clipping."""
    p.validate()
    errors = _domain(state, choice, p)
    if not branches:
        errors.append("The conditional distribution is empty")
    actual = {}
    for index, branch in enumerate(branches):
        branch_errors = _domain(branch.state, branch.choice, p)
        if not branch_errors:
            branch_errors += _successor_feasibility(branch.state, branch.choice, p, tolerance)
        errors.extend(f"branch {index}: {error}" for error in branch_errors)
        if np.shape(branch.innovation) != (4,) or not np.all(np.isfinite(branch.innovation)):
            errors.append("Invalid innovation shape")
            continue
        key = tuple(float(v) for v in branch.innovation)
        if key in actual:
            errors.append("Repeated kernel branch")
        actual[key] = branch.probability
    expected = {tuple(float(v) for v in eps): prob for prob, eps in kernel(p)}
    if actual.keys() != expected.keys() or any(not np.isfinite(actual[k])
            or abs(actual[k] - expected[k]) > 1e-14 for k in actual if k in expected):
        errors.append("Branches do not enumerate the declared finite-support kernel")
    if errors:
        return {"passed": False, "domain_errors": errors, "max_abs_residual": None,
                "residuals": {}, "full_dsge_equilibrium_solved": False}

    r = {}

    def put(name, value):
        arr = np.asarray(value).reshape(-1)
        if arr.size == 1:
            r[name] = float(arr[0])
        else:
            for i, item in enumerate(arr):
                r[f"{name}[{i}]"] = float(item)

    def kkt(name, primal, dual):
        put(name + ".primal_violation", np.minimum(primal, 0))
        put(name + ".dual_violation", np.minimum(dual, 0))
        put(name + ".complementarity", np.asarray(primal) * dual)

    probabilities = np.array([b.probability for b in branches])
    future = [b.choice for b in branches]
    future_cons = np.array([g.consumption for g in future])
    sdf = p.beta * (future_cons / choice.consumption) ** -np.array(p.gamma)
    em = probabilities @ sdf
    prices = np.array([g.spot for g in future])
    payoff = prices - choice.forward
    expectation = lambda array: float(probabilities @ np.asarray(array))
    emi = lambda array: float(probabilities @ (sdf[:, 1] * np.asarray(array)))
    emd = lambda array: float(probabilities @ (sdf[:, 2] * np.asarray(array)))
    ex = mappings(state, p)
    capacity = effective_capacity(state, p)
    q, j, inv, c = choice.q, choice.investment, choice.inventory, choice.commitment
    income_b = choice.price_b * choice.output_b
    mc = (choice.wage / p.al + ex["m"] + p.alpha_q * (q / capacity) ** p.nu_q
          + p.adjustment_q * (q - state.q_prev)
          - emi([p.adjustment_q * (g.q - q) for g in future]))
    rent = p.alpha_q * p.nu_q / (p.nu_q + 1) * (q / capacity) ** (p.nu_q + 1)
    rent += choice.capacity_multiplier

    put("E03.downstream_technology", choice.output_b - downstream_output(state, choice, p))
    put("E04.flexible_foc", choice.spot - p.alpha_s * income_b / choice.flexible)
    put("E09.production_foc", choice.spot - mc - choice.capacity_multiplier + choice.lower_q_multiplier)
    kkt("E09.capacity", capacity - q, choice.capacity_multiplier)
    kkt("E09.lower_output", q, choice.lower_q_multiplier)
    for index, branch in enumerate(branches):
        implied = next_state(state, choice, branch.innovation, p)
        put(f"E10_E12_E29_E30.transition_branch_{index}", state_vector(branch.state) - state_vector(implied))
    put("E14.mature_envelope", choice.wm - rent - (1 - p.depreciation) * emi([g.wm for g in future]))
    for a in range(p.ramp_length):
        next_value = [g.wz[a + 1] if a + 1 < p.ramp_length else g.wm for g in future]
        put(f"E14.ramp_envelope_{a}", choice.wz[a] - p.ramp_weights[a] * rent
            - (1 - p.depreciation) * emi(next_value))
    for h in range(p.construction_lag - 1):
        next_value = [(g.wz[0] if p.ramp_length else g.wm) if h == 0 else g.wb[h - 1] for g in future]
        put(f"E15.construction_envelope_{h}", choice.wb[h] + p.congestion * j - emi(next_value))
    investment_value = emi([g.wb[-1] if p.construction_lag > 1 else
                           (g.wz[0] if p.ramp_length else g.wm) for g in future])
    investment_gap = ex["pj"] + p.chi_j * j + p.congestion * np.sum(state.construction) - investment_value
    kkt("E16.investment", j, investment_gap)

    f_foce = probabilities @ (sdf * payoff[:, None])
    put("E22.futures_I", f_foce[1])
    put("E22.futures_D", f_foce[2])
    f_wedge = choice.collateral_multiplier * ex["collateral"] * choice.spot
    # At h_F=0 the subgradient is an interval, not the single number zero.
    f_residual = (max(0.0, abs(f_foce[3]) - f_wedge) if choice.positions[2] == 0
                  else f_foce[3] - f_wedge * np.sign(choice.positions[2]))
    put("E22.futures_F_subgradient", f_residual)
    collateral_slack = choice.next_bonds[3] / choice.gross_rate - ex["collateral"] * choice.spot * abs(choice.positions[2])
    kkt("E21.collateral", collateral_slack, choice.collateral_multiplier)
    procurement_future = [g.price_b * p.alpha_c * g.output_b / c - g.spot
                          + p.adjustment_c * (g.commitment - c) for g in future]
    put("E23.procurement_foc", p.adjustment_c * (c - state.commitment_prev) - emd(procurement_future))
    inventory_gap = choice.spot + p.storage_linear + p.storage_quadratic * inv - p.inventory_survival * emi(prices)
    kkt("E24.inventory", inv, inventory_gap)
    put("E25.LC_market", q + p.inventory_survival * state.inventory_prev - choice.flexible - state.commitment_prev - inv)
    put("E26.futures_market", np.sum(choice.positions))
    put("E26.inherited_futures_market", np.sum(state.old_positions))

    for owner, value in zip(("W", "I", "D", "F"), budgets(state, choice, p)):
        put("E33.budget_" + owner, value)
    put("E34.labor_supply", choice.wage - p.labor_weight * choice.labor_w ** p.labor_elasticity_power
        * choice.consumption[0] ** p.gamma[0])
    put("E34.downstream_labor", choice.wage - p.labor_share * income_b / choice.labor_d)
    put("E35.bond_euler_WID", 1 / choice.gross_rate - em[:3] - choice.debt_multipliers)
    kkt("E35.debt_floor_WID", choice.next_bonds[:3] - np.array(p.debt_floors), choice.debt_multipliers)
    put("E35.bond_euler_F", 1 / choice.gross_rate - em[3] - choice.collateral_multiplier / choice.gross_rate)
    put("E35.bond_market", np.sum(choice.next_bonds))
    put("E35.inherited_bond_market", np.sum(state.bonds))
    put("E39.inherited_debt_floor", np.minimum(state.bonds[:3] - p.debt_floors, 0))
    put("E36.non_LC_technology", choice.output_0 - p.a0 * choice.labor_0)
    put("E36.non_LC_labor", choice.wage - choice.price_0 * p.a0)
    put("E37.CES_demand_0", choice.output_0 - (1 - ex["omega"]) * choice.price_0 ** -p.epsilon * choice.output)
    put("E37.CES_demand_B", choice.output_b - ex["omega"] * choice.price_b ** -p.epsilon * choice.output)
    price_index_power = (1 - ex["omega"]) * choice.price_0 ** (1 - p.epsilon) + ex["omega"] * choice.price_b ** (1 - p.epsilon)
    put("E37.CES_price_index", price_index_power ** (1 / (1 - p.epsilon)) - 1)
    put("E38.labor_market", choice.labor_w - q / p.al - choice.labor_d - choice.labor_0)
    diag = diagnostics(state, choice, p)
    put("E38.final_resources_redundant_audit", diag["final_resource_residual"])
    put("E37.zero_profit_redundant_audit", diag["assembler_zero_profit_residual"])

    future_wealth = [choice.next_bonds[3] + choice.positions[2] * price for price in payoff]
    if diag["financial_net_worth"] <= 0 or min(future_wealth) <= 0:
        errors.append("F current or a reachable next-period net worth is nonpositive")
    for index, branch in enumerate(branches):
        put(f"E39.successor_debt_floor_{index}", np.minimum(branch.state.bonds[:3] - p.debt_floors, 0))
    mean_price = expectation(prices)
    variance_price = expectation((prices - mean_price) ** 2)
    covariance_f = expectation((sdf[:, 3] - em[3]) * (prices - mean_price))
    diag.update({
        "mean_future_spot": mean_price, "variance_future_spot": variance_price,
        "risk_premium": mean_price - choice.forward, "basis_forward_minus_spot": choice.forward - choice.spot,
        "inventory_gap": float(inventory_gap), "investment_gap": float(investment_gap),
        "collateral_slack": float(collateral_slack), "sdf_means": em.tolist(),
        "covariance_sdf_F_spot": covariance_f,
        "futures_F_pricing_left": float(f_foce[3]),
        "collateral_pricing_wedge_size": float(f_wedge),
        "capital_marginal_value": float(rent), "min_successor_F_net_worth": float(min(future_wealth)),
    })
    # E27 is an implication of E22, not an additional independent restriction.
    if choice.positions[2] != 0 or choice.collateral_multiplier == 0:
        wedge = f_wedge * np.sign(choice.positions[2])
        diag["premium_from_covariance_and_collateral"] = float((wedge - covariance_f) / em[3])
        put("E27.premium_decomposition_redundant_audit", mean_price - choice.forward - (wedge - covariance_f) / em[3])
    if not np.all(np.isfinite(list(r.values()))):
        errors.append("Nonfinite original-equation residual")
    max_residual = max(abs(v) for v in r.values())
    return {"passed": max_residual <= tolerance and not errors, "tolerance": tolerance,
            "max_abs_residual": max_residual, "residuals": r, "domain_errors": errors,
            "diagnostics": diag, "branch_count": len(branches),
            "residual_count_including_redundancy": len(r),
            "independent_equation_count_verified": False,
            "scope": "one current state, original local conditions and declared successor branches",
            "global_feasibility_verified": False, "global_transversality_verified": False,
            "full_dsge_equilibrium_solved": False}
