"""Multiperiod checks of a frozen polynomial, with independent scalar checkpoints."""

from collections import Counter
from dataclasses import dataclass
import numpy as np

from model.stochastic_validation import audit_states, draw_validation_states, profit_flow


DEFAULT_TIERS = ((48, 120), (96, 480), (256, 1440))
DEFAULT_SEED = 761337


def state_names(problem):
    return (
        "g", "e", "r", "zeta", "z_A", "z_m", "z_J", "z_N", "z_f",
        "Q_lag", "I_lag", "C_lag", "K_M",
        *(f"B_{h+1}" for h in range(problem.params.L-1)),
        *(f"Z_{a}" for a in range(problem.params.R)),
    )


class FrozenMoments:
    """Cache exact shift coefficients; these do not alter the frozen rule."""

    def __init__(self, policy, value_coefficients=None):
        self.policy = policy
        self.problem = policy.problem
        original = policy.coefficients
        self.value_coefficients = value_coefficients
        if value_coefficients is not None:
            original = np.column_stack((original, value_coefficients))
        self.mean_coefficients = original.copy()
        lower, upper, masks, indices, weights, _ = policy.shift_arrays
        constant = masks[indices] == 0
        np.add.at(self.mean_coefficients, lower[constant],
                  original[upper[constant]] * weights[constant, None])
        random = ~constant
        by_mask = np.zeros((len(original), len(masks)))
        np.add.at(by_mask, (lower[random], indices[random]), original[upper[random], 5] * weights[random])
        # A sparse row set avoids multiplying basis terms that cancel identically.
        self.random_rows = np.flatnonzero(np.any(by_mask != 0, axis=1))
        self.by_mask = by_mask[self.random_rows]

    def evaluate(self, states, decisions):
        center = self.problem.successor_center(states, decisions)
        basis = self.policy.design(center)
        mean = basis @ self.mean_coefficients
        mean[:, 0] += self.problem.capacity(center)
        variance = np.square(basis[:, self.random_rows] @ self.by_mask).sum(axis=1)
        return mean, variance


@dataclass(frozen=True)
class Residuals:
    raw: dict[str, np.ndarray]
    scaled: dict[str, np.ndarray]
    categories: dict[str, str]
    domain_fraction: np.ndarray
    lawful: np.ndarray
    variables: np.ndarray


def period_audit(problem, policy, moments, states, decisions):
    """Vectorized original residuals; separate domain, hard economics and duals."""
    prices = problem.config["scales"]["price"]
    units = problem.config["scales"]["quantity"]
    vals = problem.config["scales"]["value"]
    tol = problem.config["tolerances"]["feasibility"]
    p = problem.params
    ke = problem.capacity(states)
    g, e, r, zeta, za, zm, zj, zn, zf = states[:, :9].T
    quantity, investment, flexible, committed, stock, spot, futures, mature_value = decisions[:, :8].T
    denominator = 1+p.i_bar+r
    imports = p.N0+p.N_scale*zn
    margin = ke+imports+p.alpha_I*states[:, 10]-states[:, 11]
    discount = np.full(len(states), np.nan)
    np.divide(1, denominator, out=discount, where=denominator > 0)
    carry = spot+p.h-discount*p.alpha_I*futures
    lawful = (
        np.isfinite(states).all(axis=1) & np.isfinite(decisions).all(axis=1)
        & (np.min(states[:, 9:], axis=1) >= 0) & (ke > 0) & (margin > 0) & (denominator > 0)
        & (quantity >= 0) & ((quantity-ke) <= tol*units) & (investment >= 0) & (stock >= 0)
        & (flexible > 0) & (committed > 0) & (spot > 0) & (futures > 0)
        & ((carry >= 0) if p.xi == 0 else (carry > 0))
    )
    raw, scales, categories = {}, {}, {}

    def record(name, residual, scale, category="original_equalities"):
        raw[name], scales[name], categories[name] = np.asarray(residual), scale, category

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        continuation, variance = moments.evaluate(states, decisions)
        expected_spot = continuation[:, 5]
        spread = expected_spot-futures
        demand_scale = p.D0*np.exp(p.lambda_g*g+p.lambda_tau*p.tau_constant+za)
        variable_cost = np.exp(zm)*(p.m_domestic+p.FX_bar*np.exp(e)*p.m_usd)
        new_start_cost = p.pJ0*np.exp(zj)
        risk_financial = p.af0*np.exp(p.gamma_zeta*zeta+zf)
        risk_capacity = 1/p.a_I+1/p.a_D+1/risk_financial
        net_exposure = p.alpha_I*stock-committed
        implied_spread = variance/risk_capacity*net_exposure
        # Recover the original three positions before evaluating their FOCs.
        hedge_i = -p.alpha_I*stock+net_exposure/(risk_capacity*p.a_I)
        hedge_d = committed+net_exposure/(risk_capacity*p.a_D)
        hedge_f = net_exposure/(risk_capacity*risk_financial)
        e_q, e_wm = continuation[:, 0], continuation[:, 7]
        b_end = problem.ramp_values_start
        e_b, e_z = continuation[:, 8:b_end], continuation[:, b_end:problem.policy_dimension]
        output_gradient = (spot-variable_cost-p.alpha*(quantity/ke)**p.nu
                           -p.kappa*(quantity-states[:, 9])+discount*p.kappa*(e_q-quantity))
        output_upper_dual, output_lower_dual = np.maximum(output_gradient, 0), np.maximum(-output_gradient, 0)
        service = p.alpha*p.nu/(p.nu+1)*(quantity/ke)**(p.nu+1)+output_upper_dual
        finish_value = e_z[:, 0] if p.R else e_wm
        j_value = e_b[:, -1] if p.L > 1 else finish_value
        j_gap = (new_start_cost+p.chi*investment
                 +p.omega_B*states[:, 13:problem.ramp_start].sum(axis=1)-discount*j_value)
        g_stock = p.h-p.xi/(stock+p.I0)
        inv_exposure, purchase_exposure = p.alpha_I*stock+hedge_i, hedge_d-committed
        flexible_marginal = p.P_star*(flexible/((1-p.omega)*demand_scale))**(-1/p.eta_s)
        purchase_marginal = p.P_star*(committed/(p.omega*demand_scale))**(-1/p.eta_c)
        inventory_gap = spot+g_stock-discount*p.alpha_I*(expected_spot-p.a_I*variance*inv_exposure)
        reduced_inventory_gap = spot+g_stock-discount*p.alpha_I*futures
        record("E09_Q_stationarity_reconstructed", output_gradient-output_upper_dual+output_lower_dual, prices)
        record("E04_flexible_demand_gradient", flexible_marginal-spot, prices)
        record("E19_inventory_hedge_gradient", discount*(spread-p.a_I*variance*inv_exposure), prices)
        record("E20_procurement_gradient", discount*(purchase_marginal-expected_spot
                                                     +p.a_D*variance*purchase_exposure), prices)
        record("E20_procurement_hedge_gradient", discount*(spread-p.a_D*variance*purchase_exposure), prices)
        record("E21_financial_hedge_gradient", discount*(spread-risk_financial*variance*hedge_f), prices)
        record("E25_goods_clearing", quantity+imports+p.alpha_I*states[:, 10]
               -flexible-states[:, 11]-stock, units)
        record("E26_futures_clearing", hedge_i+hedge_d+hedge_f, units)
        record("E14_mature_value", mature_value-service-discount*(1-p.delta)*e_wm, vals)
        for a in range(p.R):
            after = e_z[:, a+1] if a+1 < p.R else e_wm
            record(f"E14_ramp_value_{a}", decisions[:, b_end+a]-p.g[a]*service-discount*(1-p.delta)*after, vals)
        for h in range(p.L-1):
            after = e_b[:, h-1] if h else finish_value
            record(f"E15_construction_value_{h+1}", decisions[:, 8+h]+p.omega_B*investment-discount*after, vals)
        record("E23_procurement_reduced", purchase_marginal-futures, prices, "derived_equalities")
        record("E27_futures_reduced", implied_spread-spread, prices, "derived_equalities")
        record("E28_positive_inventory_only", np.where(stock > 0, spot+g_stock-discount*p.alpha_I*
               (expected_spot-implied_spread), 0), prices, "derived_equalities")
        for name, primal, gap, unit in (
                ("E09_output_lower", quantity, output_lower_dual, prices),
                ("E09_capacity_upper", ke-quantity, output_upper_dual, prices),
                ("E16_investment", investment, j_gap, vals),
                ("E19_inventory_original", stock, inventory_gap, prices),
                ("E24_inventory_reduced", stock, reduced_inventory_gap, prices)):
            record(name+"_primal_violation", np.maximum(-primal, 0), units, "primal")
            record(name+"_dual_violation", np.maximum(-gap, 0), unit, "dual")
            record(name+"_product", primal*gap, units*unit, "complementarity")
            record(name+"_natural", np.minimum(primal/units, gap/unit), 1, "natural_complementarity")
        if moments.value_coefficients is not None and lawful.all():
            level = policy.design(states) @ moments.value_coefficients
            record("producer_Bellman", level-profit_flow(problem, states, decisions)-discount*continuation[:, -1],
                   problem.config["scales"]["profit"], "bellman")
    scaled = {name: np.abs(value)/scales[name] for name, value in raw.items()}
    fraction = np.max(np.abs((states-problem.center)/problem.radius), axis=1)
    variables = np.column_stack((decisions[:, :7], ke, expected_spot, variance, net_exposure, spread, implied_spread))
    return Residuals(raw, scaled, categories, fraction, lawful, variables)


VARIABLE_NAMES = ("Q", "J", "D_s", "C", "I", "P", "F", "K_e", "expected_spot", "price_variance",
                  "net_hedge_exposure", "risk_premium", "risk_premium_E27")


def _null_nonfinite(array):
    return [float(x) if np.isfinite(x) else None for x in array]


def simulate_tier(problem, policy, training_states, seed_sequence, n_paths, horizon, value_coefficients=None):
    """Fixed cohorts and checkpoint positions; simulated failures are retained."""
    rng_initial, rng_burn, rng_path = map(np.random.default_rng, seed_sequence.spawn(3))
    root_seed = int(rng_initial.integers(1, 2**31))
    n_coordinates = problem.state_dimension
    n_branches = len(problem.kernel.branches)
    burnin = 48
    start_types = np.asarray(["anchor", "local_feasible_draw", "anchor_burnin"])[np.arange(n_paths) % 3]
    local_indices = np.flatnonzero(start_types == "local_feasible_draw")
    burn_indices = np.flatnonzero(start_types == "anchor_burnin")
    roots = np.broadcast_to(problem.center, (n_paths, n_coordinates)).copy()
    roots[local_indices], draws = draw_validation_states(
        problem, len(local_indices), root_seed, problem.config["validation"]["radius_fraction"], training_states)
    current = roots.copy()
    starts = current.copy()
    selected_times = (0, horizon//3, (2*horizon)//3, horizon)
    selected_indices = np.unique([0, 1, 2, n_paths//2, n_paths-1])
    checkpoints, labels = [], []
    burn_shocks = rng_burn.integers(n_branches, size=(burnin, len(burn_indices)), dtype=np.uint16)
    shocks = rng_path.integers(n_branches, size=(horizon, n_paths), dtype=np.uint16)
    frozen_moments = FrozenMoments(policy, value_coefficients)
    first = {key: {} for key in ("approximation_box", "economic", "primal", "dual", "residual")}
    counts = {phase: Counter() for phase in ("burnin", "simulation")}
    maxima = {}
    values = np.empty((horizon+1, n_paths, len(VARIABLE_NAMES)))
    tol = problem.config["tolerances"]
    axis_labels = state_names(problem)
    failure_rows = {}
    maximum_domain = 0.0

    for t in range(-burnin, horizon+1):
        if t < 0:
            indices = burn_indices
            phase = "burnin"
        else:
            indices = np.arange(n_paths)
            phase = "simulation"
            if t == 0:
                starts = current.copy()
        segment = current[indices]
        decisions = policy.predict(segment)
        res = period_audit(problem, policy, frozen_moments, segment, decisions)
        maximum_domain = max(maximum_domain, float(np.nanmax(res.domain_fraction)))
        flags = {
            "approximation_box": res.domain_fraction > 1+tol["feasibility"],
            "economic": ~res.lawful,
            "primal": np.zeros(len(indices), dtype=bool), "dual": np.zeros(len(indices), dtype=bool),
            "residual": np.zeros(len(indices), dtype=bool),
        }
        for name, scaled in res.scaled.items():
            category = res.categories[name]
            if category in ("primal", "dual"):
                flag, threshold = category, tol["feasibility"]
            else:
                flag = "residual"
                threshold = tol["complementarity" if category == "complementarity" else "equilibrium"]
            flags[flag] |= (~np.isfinite(scaled) | (scaled > threshold))
            finite_score = np.where(np.isfinite(scaled), scaled, -1)
            row = int(np.argmax(finite_score))
            if name not in maxima or finite_score[row] > maxima[name]["max_normalized"]:
                maxima[name] = {
                    "category": category, "max_normalized": float(finite_score[row]),
                    "signed_raw_at_max": _null_nonfinite([res.raw[name][row]])[0],
                    "path": int(indices[row]), "period": t,
                }
        counts[phase]["each_period_states_checked"] += len(indices)
        for key, flag in flags.items():
            counts[phase][key] += int(flag.sum())
            for offset in np.flatnonzero(flag):
                index = int(indices[offset])
                if index in first[key]:
                    continue
                normalized = (segment[offset]-problem.center)/problem.radius
                outside = np.flatnonzero(np.abs(normalized) > 1+tol["feasibility"])
                burn_count = t+burnin if t < 0 else burnin
                burn_selection = (
                    burn_shocks[:burn_count, np.searchsorted(burn_indices, index)].tolist()
                    if start_types[index] == "anchor_burnin" else []
                )
                record = {
                    "period": t, "path": index, "start_type": start_types[index],
                    "root": roots[index].tolist(), "state": _null_nonfinite(segment[offset]),
                    "decisions": _null_nonfinite(decisions[offset]),
                    "burnin_shocks_to_failure": burn_selection,
                    "simulation_shocks_to_failure": shocks[:max(t, 0), index].tolist(),
                    "outside_dimensions": {
                        axis_labels[k]: {
                            "value": float(segment[offset, k]), "signed_radius": float(normalized[k]),
                            "excess_in_original_units": float(abs(segment[offset, k]-problem.center[k])-problem.radius[k]),
                        } for k in outside
                    },
                    "maximum_radius_fraction": float(res.domain_fraction[offset]),
                    "signed_raw_residuals": {name: _null_nonfinite([row[offset]])[0] for name,row in res.raw.items()},
                    "absolute_normalized_residuals": {name: _null_nonfinite([row[offset]])[0] for name,row in res.scaled.items()},
                }
                first[key][index] = record
                failure_rows.setdefault(key, (record, segment[offset].copy()))
        if t in selected_times:
            labels.extend({"period": t, "path": int(i), "start_type": start_types[i]} for i in selected_indices)
            checkpoints.extend(segment[selected_indices])
        if t >= 0:
            values[t] = res.variables
        if t < horizon:
            branch_indices = burn_shocks[t+burnin] if t < 0 else shocks[t]
            current[indices] = problem.successors(segment, decisions, branch_indices)

    # A separately named diagnostic supplements the predeclared checkpoints.
    # The selected sample above remains independent of all outcomes.
    checkpoint_states = np.asarray(checkpoints)
    explicit = audit_states(problem, policy, value_coefficients, checkpoint_states, tol)
    failure_explicit = {}
    for group, (label, row) in failure_rows.items():
        failure_explicit[group] = {"path": label["path"], "period": label["period"],
                                   "audit": audit_states(problem, policy, value_coefficients, row[None, :], tol)}
    quantiles = np.nanquantile(values, [0, 0.05, 0.5, 0.95, 1], axis=(0, 1))
    variable_summary = {
        name: dict(zip(("min", "p05", "median", "p95", "max"), _null_nonfinite(q)))
        for name, q in zip(VARIABLE_NAMES, quantiles.T)
    }
    report = {
        "seed_spawn_key": seed_sequence.spawn_key, "root_draw_seed": root_seed,
        "horizon_months": horizon, "unique_paths": n_paths, "burnin_months": burnin,
        "cohort_sizes": dict(Counter(start_types)), "local_initial_draws": draws,
        "counts_at_all_periods": {k: dict(v) for k, v in counts.items()},
        "maximum_absolute_radius_fraction_visited": maximum_domain,
        "number_of_paths_with_either_burnin_or_simulation_failure": {k: len(v) for k,v in first.items()},
        "maximum_residual_by_equation": maxima,
        "first_failure_records_by_path_and_category": first,
        "first_observed_failure_explicit_check": failure_explicit,
        "checkpoint_selection": {"time_rule": "0, floor(H/3), floor(2H/3), H",
                                 "path_rule": "sorted unique indices 0,1,2,floor(N/2),N-1",
                                 "predeclared_checkpoints": labels, "states": checkpoint_states.tolist(),
                                 "branches_per_checkpoint": n_branches},
        "checkpoint_explicit_512_original_audit": explicit,
        "key_variable_statistics_over_untruncated_paths": variable_summary,
    }
    arrays = {
        "roots": roots, "starts": starts, "burnin_path_indices": burn_indices,
        "burnin_shock_indices": burn_shocks, "simulated_shock_indices": shocks,
        "checkpoint_states": checkpoint_states,
    }
    return report, arrays
