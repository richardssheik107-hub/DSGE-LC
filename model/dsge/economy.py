"""Physical technology, accounts and original derivatives in real final-good units."""

import numpy as np
from .state import effective_capacity
from .shocks import mappings


def real_costs(state, choice, p):
    k = effective_capacity(state, p)
    ex = mappings(state, p)
    q, j, i, c = choice.q, choice.investment, choice.inventory, choice.commitment
    cq = ex["m"] * q + p.alpha_q / (p.nu_q + 1) * q ** (p.nu_q + 1) / k ** p.nu_q
    cq += p.adjustment_q / 2 * (q - state.q_prev) ** 2
    cj = ex["pj"] * j + p.chi_j / 2 * j ** 2 + p.congestion * j * np.sum(state.construction)
    storage = p.storage_linear * i + p.storage_quadratic / 2 * i ** 2
    procurement = p.adjustment_c / 2 * (c - state.commitment_prev) ** 2
    return {"production": float(cq), "construction": float(cj),
            "storage": float(storage), "procurement": float(procurement)}


def downstream_output(state, choice, p):
    return (p.ab * p.fixed_factor ** p.phi * choice.labor_d ** p.labor_share
            * choice.flexible ** p.alpha_s * state.commitment_prev ** p.alpha_c)


def budgets(state, choice, p):
    """Four uses-minus-sources residuals, including inherited futures settlement."""
    costs = real_costs(state, choice, p)
    xi = state.old_positions * (choice.spot - state.old_forward)
    out = choice.consumption + choice.next_bonds / choice.gross_rate - state.bonds
    out = out.copy()
    out[0] -= choice.wage * choice.labor_w
    out[1] += choice.wage * choice.q / p.al + costs["production"] + costs["construction"] + costs["storage"]
    out[1] -= choice.spot * (choice.q + p.inventory_survival * state.inventory_prev - choice.inventory) + xi[0]
    out[2] += choice.wage * choice.labor_d + choice.spot * (choice.flexible + state.commitment_prev) + costs["procurement"]
    out[2] -= choice.price_b * choice.output_b + xi[1]
    out[3] -= xi[2]
    return out


def diagnostics(state, choice, p):
    costs = real_costs(state, choice, p)
    value_output = choice.price_0 * choice.output_0 + choice.price_b * choice.output_b
    return {
        "effective_capacity": effective_capacity(state, p),
        "capacity_utilization": choice.q / effective_capacity(state, p),
        "real_costs": costs,
        "final_resource_residual": float(choice.output - np.sum(choice.consumption) - sum(costs.values())),
        "assembler_zero_profit_residual": float(value_output - choice.output),
        "futures_settlement_total": float(np.sum(state.old_positions) * (choice.spot - state.old_forward)),
        "financial_net_worth": float(state.bonds[3] + state.old_positions[2] * (choice.spot - state.old_forward)),
        "aggregate_net_bonds": float(np.sum(state.bonds)),
    }
