"""Structural shock incidence and collateral activation, not a policy solution.

These diagnostics hold endogenous choices fixed. They identify which original
conditions a primitive enters; their derivatives are NOT equilibrium IRFs.
"""

from dataclasses import replace
from itertools import product
import numpy as np

from .economy import real_costs
from .shocks import kernel, mappings


ENTRY_NAMES = (
    "E37.log_relative_final_demand_at_fixed_prices",
    "E09.current_unit_resource_cost",
    "E16.current_unit_construction_cost",
    "E33.I_production_and_construction_resources",
    "E21.F_collateral_requirement",
)


def fixed_choice_entries(state, choice, p):
    """A small set of primitive entries, before endogenous responses."""
    ex = mappings(state, p)
    costs = real_costs(state, choice, p)
    return np.array([
        np.log(ex["omega"] / (1.0 - ex["omega"]))
        - p.epsilon * np.log(choice.price_b / choice.price_0),
        ex["m"],
        ex["pj"],
        costs["production"] + costs["construction"],
        ex["collateral"] * choice.spot * abs(choice.positions[2]),
    ])


def primitive_incidence(state, choice, p, step=1e-5):
    """Analytic incidence checked against the implemented original resources."""
    if step <= 0:
        raise ValueError("A positive difference step is required")
    ex = mappings(state, p)
    analytic = np.zeros((len(ENTRY_NAMES), 4))
    analytic[0, 0] = 1.0
    analytic[1, 1] = ex["m"]
    analytic[2, 2] = ex["pj"]
    analytic[3, 1] = ex["m"] * choice.q
    analytic[3, 2] = ex["pj"] * choice.investment
    analytic[4, 3] = ex["collateral"] * choice.spot * abs(choice.positions[2])
    numerical = np.zeros_like(analytic)
    for k in range(4):
        delta = np.zeros(4)
        delta[k] = step
        plus = fixed_choice_entries(replace(state, z=state.z + delta), choice, p)
        minus = fixed_choice_entries(replace(state, z=state.z - delta), choice, p)
        numerical[:, k] = (plus - minus) / (2 * step)
    return {
        "scope": "partial derivatives with all endogenous choices held fixed; not equilibrium responses",
        "rows": list(ENTRY_NAMES), "columns": list(p.shock_names),
        "analytic": analytic.tolist(), "central_difference": numerical.tolist(),
        "step": step,
        "max_derivative_error": float(np.max(np.abs(analytic - numerical))),
        "primitive_entry_rank_at_candidate": int(np.linalg.matrix_rank(analytic)),
        "structural_identification_rank_claimed": False,
    }


def collateral_activation(state, choice, p):
    """Budget-available margin buffer and a fixed-choice tightening threshold.

    A zero current multiplier only removes the *current* wedge. It does not
    prove that future binding probabilities or current equilibrium choices are
    independent of kappa. The latter needs a policy and all relevant successors.
    """
    ex = mappings(state, p)
    assets = choice.next_bonds[3] / choice.gross_rate
    exposure = choice.spot * abs(choice.positions[2])
    requirement = ex["collateral"] * exposure
    limit = assets / exposure if exposure > 0 else None
    tightening = (float(np.log(assets / requirement))
                  if requirement > 0 and assets > 0 else None)
    return {
        "bond_market_value": float(assets),
        "position_F": float(choice.positions[2]),
        "collateral_parameter": float(ex["collateral"]),
        "collateral_requirement": float(requirement),
        "collateral_slack": float(assets - requirement),
        "multiplier_F": float(choice.collateral_multiplier),
        "requirement_derivative_wrt_log_kappa": float(requirement),
        "fixed_choice_maximum_kappa": None if limit is None else float(limit),
        "fixed_choice_log_tightening_to_binding": tightening,
        "zero_position_requires_no_collateral": bool(exposure == 0),
        "zero_current_wedge_certified_by_zero_multiplier": bool(choice.collateral_multiplier == 0),
        "zero_position_requires_subgradient_interval": bool(exposure == 0),
        "economic_equilibrium_claimed": False,
    }


def shock_scale_table(p):
    """Separate innovation scale, stationary dispersion, support and mapping."""
    rows = []
    for k, (name, rho, sigma) in enumerate(zip(p.shock_names, p.shock_persistence, p.shock_scales)):
        row = {
            "name": name, "rho": rho, "sigma_innovation": sigma,
            "stationary_sd_of_latent_state": float(sigma / np.sqrt(1 - rho**2)),
            "latent_state_support_bound_from_zero": float(sigma / (1 - abs(rho))),
            "absolute_latent_response_half_life_months":
                float(np.log(.5) / np.log(abs(rho))) if 0 < abs(rho) < 1 else 0.0,
        }
        if k == 0:
            odds = np.log(p.omega_bar / (1 - p.omega_bar))
            shifted = 1 / (1 + np.exp(-(odds + sigma)))
            row.update({"mapping": "logistic share", "anchor_share": p.omega_bar,
                        "share_after_plus_one_sd_from_zero": float(shifted),
                        "direct_mapping_change_percentage_points": float(100 * (shifted - p.omega_bar))})
        else:
            row.update({"mapping": "exponential multiplier",
                        "direct_mapping_change_percent_from_zero": float(100 * np.expm1(sigma))})
        rows.append(row)
    return rows


def conditional_exogenous_path(p, shock_index, horizon=12, max_exact_horizon=16):
    """Exact conditional means of ONE primitive, integrating all future shocks.

    Starting from z[-1]=0, condition the innovation at t=0 on +1 or -1.
    Unconditional baseline averages these events. Future signs remain random.
    Other shock dimensions integrate out because E02 is separable. The logistic
    expectation uses 2**h exact histories; exponential moments have a cosh form.
    This is an exogenous-state diagnostic, NEVER an equilibrium price IRF.
    """
    p.validate()
    if shock_index not in range(4) or not isinstance(horizon, int) or horizon < 0:
        raise ValueError("Invalid shock index or horizon")
    if shock_index == 0 and horizon > max_exact_horizon:
        raise ValueError("Exact logistic enumeration horizon exceeded; no silent approximation")
    rho, sigma = p.shock_persistence[shock_index], p.shock_scales[shock_index]
    base = (p.omega_bar, p.m_bar, p.pj_bar, p.collateral_bar)[shock_index]
    rows = []
    for h in range(horizon + 1):
        shift = rho**h * sigma
        if shock_index == 0:
            weights = sigma * rho**np.arange(h)
            paths = np.array(list(product((-1.0, 1.0), repeat=h)), dtype=float).reshape(2**h, h)
            history = paths @ weights
            odds = np.log(base / (1 - base))
            plus = float(np.mean(1 / (1 + np.exp(-(odds + history + shift)))))
            minus = float(np.mean(1 / (1 + np.exp(-(odds + history - shift)))))
        else:
            future_mgf = float(np.prod(np.cosh(sigma * rho**np.arange(h))))
            plus = float(base * np.exp(shift) * future_mgf)
            minus = float(base * np.exp(-shift) * future_mgf)
        unconditional = (plus + minus) / 2
        rows.append({
            "month": h, "latent_conditional_mean_plus": float(shift),
            "primitive_conditional_mean_plus": plus,
            "primitive_conditional_mean_minus": minus,
            "primitive_unconditional_baseline": unconditional,
            "conditional_mean_difference": plus - unconditional,
            "relative_difference_percent": 100 * (plus / unconditional - 1),
            "share_difference_percentage_points": 100 * (plus - unconditional) if shock_index == 0 else None,
        })
    return {"shock": p.shock_names[shock_index], "rows": rows,
            "scope": "exogenous mapping only; endogenous DSGE policy is not used",
            "future_innovations_integrated": True, "equilibrium_irf": False,
            "baseline": "unconditioned current sign, future innovations integrated under the original two-point law"}


def kernel_moments(p):
    rows = kernel(p)
    probabilities = np.array([r[0] for r in rows])
    signs = np.array([r[1] for r in rows])
    innovations = signs * np.array(p.shock_scales)
    mean = probabilities @ innovations
    centered = innovations - mean
    covariance = centered.T @ (centered * probabilities[:, None])
    return {"branches": len(rows), "probability_sum": float(sum(probabilities)),
            "latent_innovation_mean": mean.tolist(),
            "latent_innovation_covariance": covariance.tolist()}
