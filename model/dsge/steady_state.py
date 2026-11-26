"""Solve a synthetic stationary KKT anchor; not a positive-risk equilibrium."""

from dataclasses import replace
import numpy as np
from scipy.optimize import least_squares
from .parameters import Parameters
from .state import Branch, Choice, State
from .residuals import evaluate


def stationary_queues(investment, p):
    construction = np.full(p.construction_lag - 1, investment)
    ramp = investment * (1 - p.depreciation) ** np.arange(p.ramp_length)
    mature = investment * (1 - p.depreciation) ** p.ramp_length / p.depreciation
    return mature, construction, ramp


def stationary_shadows(rent, investment, p):
    wm = rent / (1 - p.beta * (1 - p.depreciation))
    wz = np.empty(p.ramp_length)
    tail = wm
    for a in reversed(range(p.ramp_length)):
        tail = p.ramp_weights[a] * rent + p.beta * (1 - p.depreciation) * tail
        wz[a] = tail
    tail = wz[0] if p.ramp_length else wm
    wb = np.empty(p.construction_lag - 1)
    for h in range(p.construction_lag - 1):
        tail = -p.congestion * investment + p.beta * tail
        wb[h] = tail
    return wm, wb, wz, p.beta * tail


def _candidate(log_unknowns, p):
    wage, spot, q, investment = np.exp(log_unknowns)
    mature, construction, ramp = stationary_queues(investment, p)
    capacity = mature + np.dot(p.ramp_weights, ramp)
    income_b = spot * q / (p.alpha_s + p.alpha_c)
    flexible = p.alpha_s * income_b / spot
    commitment = p.alpha_c * income_b / spot
    labor_d = p.labor_share * income_b / wage
    output_b = (p.ab * p.fixed_factor ** p.phi * labor_d ** p.labor_share
                * flexible ** p.alpha_s * commitment ** p.alpha_c)
    price_b = income_b / output_b
    price_0 = wage / p.a0
    output = output_b / (p.omega_bar * price_b ** -p.epsilon)
    output_0 = (1 - p.omega_bar) * price_0 ** -p.epsilon * output
    labor_0 = output_0 / p.a0
    labor_w = labor_0 + labor_d + q / p.al
    cq = p.m_bar * q + p.alpha_q / (p.nu_q + 1) * q ** (p.nu_q + 1) / capacity ** p.nu_q
    cj = p.pj_bar * investment + p.chi_j / 2 * investment ** 2 + p.congestion * investment * np.sum(construction)
    consumption = np.array([wage * labor_w, spot * q - wage * q / p.al - cq - cj,
                            p.phi * income_b, 0.0]) + (1 - p.beta) * np.array(p.anchor_bonds)
    rent = p.alpha_q * p.nu_q / (p.nu_q + 1) * (q / capacity) ** (p.nu_q + 1)
    wm, wb, wz, investment_value = stationary_shadows(rent, investment, p)
    state = State(np.zeros(4), q, 0.0, commitment, mature, construction, ramp,
                  np.array(p.anchor_bonds), np.zeros(3), spot)
    choice = Choice(q, investment, flexible, commitment, 0.0, consumption,
                    labor_w, labor_d, labor_0, wage, spot, spot, price_0, price_b,
                    output_0, output_b, output, 1 / p.beta, np.array(p.anchor_bonds),
                    np.zeros(3), wm, wb, wz)
    reduced = np.array([
        spot - wage / p.al - p.m_bar - p.alpha_q * (q / capacity) ** p.nu_q,
        (1 - p.omega_bar) * price_0 ** (1 - p.epsilon) + p.omega_bar * price_b ** (1 - p.epsilon) - 1,
        p.pj_bar + p.chi_j * investment + p.congestion * np.sum(construction) - investment_value,
        wage - p.labor_weight * labor_w ** p.labor_elasticity_power * consumption[0] ** p.gamma[0],
    ])
    return state, choice, reduced


def solve_anchor(parameters=None):
    """Return a checked anchor on a fixed-wealth, h=0, zero-inventory branch.

    All shock scales are explicitly zero in this deterministic calculation. The
    configured positive shock scales are not a claim about a stochastic mean.
    The solver does not select a unique wealth distribution or zero-risk hedge.
    """
    configured = (parameters or Parameters()).validate()
    p = replace(configured, shock_scales=(0.0, 0.0, 0.0, 0.0))
    initial = np.log([1.35, 0.55, 0.22, 0.021])
    objective = lambda x: _candidate(x, p)[2]
    solution = least_squares(objective, initial, xtol=1e-13, ftol=1e-13, gtol=1e-13,
                             max_nfev=1000, bounds=(-12.0, 8.0))
    state, choice, reduced = _candidate(solution.x, p)
    branch = Branch(1.0, np.zeros(4), state, choice)
    audit = evaluate(state, choice, [branch], p)
    if not solution.success or not audit["passed"]:
        raise RuntimeError("Stationary KKT anchor failed original-equation audit: " + repr(audit))
    step = 1e-5
    jacobian = np.column_stack([(objective(solution.x + np.eye(4)[i] * step)
                                - objective(solution.x - np.eye(4)[i] * step)) / (2 * step) for i in range(4)])
    singular_values = np.linalg.svd(jacobian, compute_uv=False)
    return {
        "parameters": p, "configured_parameters": configured,
        "state": state, "choice": choice, "audit": audit,
        "optimizer": {"success": bool(solution.success), "evaluations": int(solution.nfev),
                      "reduced_max_residual": float(np.max(np.abs(reduced))),
                      "reduced_unknowns": ["log_wage", "log_spot", "log_output_LC", "log_investment"],
                      "reduced_jacobian_rank": int(np.linalg.matrix_rank(jacobian)),
                      "reduced_jacobian_singular_values": singular_values.tolist(),
                      "reduced_jacobian_condition_number": float(singular_values[0] / singular_values[-1]),
                      "rank_scope": "four-variable reduced real stationary system only; not full DSGE/BK"},
    }
