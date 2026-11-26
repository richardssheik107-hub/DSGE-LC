"""Reproduce the synthetic stationary anchor and current-equation regression gate."""

import argparse
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import scipy
from model.dsge import Parameters, Branch, evaluate, solve_anchor
from model.dsge.economy import budgets, diagnostics, real_costs
from model.dsge.state import effective_capacity, next_state
from model.dsge.shocks import kernel


def derivative_evidence(anchor):
    p, s, g = anchor["parameters"], anchor["state"], anchor["choice"]
    step = 1e-6
    cost = lambda st, ch, key: real_costs(st, ch, p)[key]
    k = effective_capacity(s, p)
    pairs = {}
    pairs["production_dQ"] = (
        (cost(s, replace(g, q=g.q + step), "production") - cost(s, replace(g, q=g.q - step), "production")) / (2 * step),
        p.m_bar + p.alpha_q * (g.q / k) ** p.nu_q)
    pairs["production_dK"] = (
        (cost(replace(s, mature=s.mature + step), g, "production") - cost(replace(s, mature=s.mature - step), g, "production")) / (2 * step),
        -p.alpha_q * p.nu_q / (p.nu_q + 1) * (g.q / k) ** (p.nu_q + 1))
    pairs["construction_dJ"] = (
        (cost(s, replace(g, investment=g.investment + step), "construction") - cost(s, replace(g, investment=g.investment - step), "construction")) / (2 * step),
        p.pj_bar + p.chi_j * g.investment + p.congestion * sum(s.construction))
    # Probe a nonstationary procurement plan: its lag derivative must have the
    # opposite sign and enter the continuation value, not disappear at C=C_-.
    gg = replace(g, commitment=1.2 * g.commitment)
    pairs["procurement_dC_previous"] = (
        (cost(replace(s, commitment_prev=s.commitment_prev + step), gg, "procurement")
         - cost(replace(s, commitment_prev=s.commitment_prev - step), gg, "procurement")) / (2 * step),
        -p.adjustment_c * (gg.commitment - s.commitment_prev))
    return {"central_difference_step": step,
            "checks": {key: {"numerical": float(a), "analytic": float(b), "absolute_error": float(abs(a - b))}
                       for key, (a, b) in pairs.items()},
            "max_absolute_error": float(max(abs(a - b) for a, b in pairs.values()))}


def account_evidence(anchor):
    p, s = anchor["parameters"], anchor["state"]
    g = replace(anchor["choice"], q=anchor["choice"].q * 1.07,
                wage=anchor["choice"].wage * 1.02,
                output=anchor["choice"].output * 1.03,
                next_bonds=np.array([-.05, -.10, -.05, .25]))
    d = diagnostics(s, g, p)
    lc = g.q + p.inventory_survival * s.inventory_prev - g.flexible - s.commitment_prev - g.inventory
    labor = g.labor_w - g.q / p.al - g.labor_d - g.labor_0
    rhs = (-d["final_resource_residual"] - d["assembler_zero_profit_residual"]
           + g.price_0 * (g.output_0 - p.a0 * g.labor_0)
           + (g.price_0 * p.a0 - g.wage) * g.labor_0
           + np.sum(g.next_bonds) / g.gross_rate - np.sum(s.bonds)
           - d["futures_settlement_total"] - g.wage * labor - g.spot * lc)
    lhs = float(sum(budgets(s, g, p)))
    return {"scope": "arbitrary off-equilibrium quantity, wage, final output and net-asset perturbation",
            "budget_residual_sum": lhs, "market_resource_identity_rhs": float(rhs),
            "identity_absolute_error": float(abs(lhs - rhs))}


def frozen_positive_risk_probe(anchor):
    """A failing candidate checked beyond the center, not a stochastic solver."""
    p, g = anchor["configured_parameters"], anchor["choice"]
    branches = [Branch(prob, eps, next_state(anchor["state"], g, eps, p), g) for prob, eps in kernel(p)]
    center = evaluate(anchor["state"], g, branches, p)
    rows = []
    for first in branches:
        future = [Branch(prob, eps, next_state(first.state, g, eps, p), g) for prob, eps in kernel(p)]
        audit = evaluate(first.state, g, future, p)
        worst = max(audit["residuals"], key=lambda key: abs(audit["residuals"][key]))
        rows.append({"state_z": first.state.z.tolist(), "passed": audit["passed"],
                     "max_abs_residual": audit["max_abs_residual"], "worst_condition": worst,
                     "conditional_branches": len(future)})
    return {"candidate": "constant deterministic-anchor choices under configured positive innovations",
            "scope": "center plus all 16 first-period successors, each with a full 16-branch expectation",
            "center_passed": center["passed"], "center_max_abs_residual": center["max_abs_residual"],
            "successor_states_audited": len(rows),
            "successor_states_rejected": sum(not row["passed"] for row in rows),
            "max_abs_successor_residual": max(row["max_abs_residual"] for row in rows),
            "rows": rows, "candidate_rejected": any(not row["passed"] for row in rows),
            "global_policy_validation_claimed": False,
            "lesson": "current-state FOCs can pass while the same candidate fails at reachable states"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    anchor = solve_anchor()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_equation_chain.py")
    captured = io.StringIO()
    result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
    boundaries = []
    for lag, ramp in ((1, ()), (1, (0.45, 0.80)), (3, ()), (3, (0.45, 0.80))):
        case = solve_anchor(replace(Parameters(), construction_lag=lag, ramp_weights=ramp))
        boundaries.append({"L": lag, "R": len(ramp), "max_abs_original_residual": case["audit"]["max_abs_residual"],
                           "min_consumption": float(min(case["choice"].consumption)),
                           "capacity_utilization": case["audit"]["diagnostics"]["capacity_utilization"],
                           "passed": case["audit"]["passed"]})
    cons = anchor["choice"].consumption.copy()
    cons[1] += 0.01
    wrong = replace(anchor["choice"], consumption=cons)
    rejected = evaluate(anchor["state"], wrong,
                        [Branch(1.0, np.zeros(4), anchor["state"], anchor["choice"])], anchor["parameters"])
    source_paths = sorted((ROOT / "model" / "dsge").glob("*.py"))
    source_paths += [ROOT / "scripts" / "validate_equation_chain.py", ROOT / "tests" / "test_equation_chain.py"]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
    report = {
        "model_id": "LC_DSGE_EQCHAIN_20261126",
        "validated_on": "2026-11-26",
        "scope": "new original-equation evaluator and synthetic deterministic stationary KKT anchor",
        "stage": "EQUATION_CHAIN_AND_DETERMINISTIC_ANCHOR",
        "synthetic_parameters": True, "china_calibration_claimed": False,
        "real_data_estimated": False, "full_dsge_equilibrium_solved": False,
        "full_dsge_solver_implemented": False, "dsge_results_inherited": False,
        "configured_positive_risk_kernel_branches": 16,
        "configured_parameters": anchor["configured_parameters"].to_dict(),
        "anchor_parameters": anchor["parameters"].to_dict(),
        "anchor_selection": {
            "shock_scales": "all four set to zero for this deterministic calculation",
            "log_center": "z=0 is the deterministic reference, not the stochastic unconditional mean of levels",
            "inventory": "I=0; strictly positive storage dual supports the corner",
            "positions": "h_I=h_D=h_F=0 selected; zero-risk positions are not unique",
            "bonds_order": ["W", "I", "D", "F"],
            "bonds": list(anchor["parameters"].anchor_bonds),
            "wealth_distribution": "fixed initial allocation with exact counterparties; not endogenously selected as unique",
            "stationary_tail_limits": "bounded stationary real/asset states and constant M=beta<1 imply discounted tails vanish on this selected deterministic path",
            "global_optimum_proved": False,
            "qualification": "KKT candidate verified; nonconcave internal congestion means FOCs alone do not prove global optimality",
        },
        "state": anchor["state"].as_dict(), "choice": anchor["choice"].as_dict(),
        "optimizer": anchor["optimizer"], "original_equation_audit": anchor["audit"],
        "boundary_cases": boundaries, "derivative_checks": derivative_evidence(anchor),
        "off_equilibrium_accounting_identity": account_evidence(anchor),
        "frozen_anchor_positive_risk_probe": frozen_positive_risk_probe(anchor),
        "deliberately_wrong_candidate": {
            "change": "increase I-owner current consumption by 0.01 without a source of funds",
            "rejected": not rejected["passed"], "max_abs_residual": rejected["max_abs_residual"],
            "I_budget_residual": rejected["residuals"]["E33.budget_I"],
            "resource_residual": rejected["residuals"]["E38.final_resources_redundant_audit"],
        },
        "tests": {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                  "passed": result.wasSuccessful(), "details": captured.getvalue().splitlines()},
        "runtime": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                    "platform": platform.platform(), "lockfile_reproduction_claimed": False},
        "commands": ["python -m unittest discover -s tests -v", "python scripts/validate_equation_chain.py --write-report"],
        "source_sha256": hashes,
        "remaining_gates": ["finite-positive-risk policy solution", "global successor feasibility and solvency",
                            "full dynamic Jacobian/rank and appropriate determinacy analysis", "global optimality or verified solution selection",
                            "positive-risk TVC/tail verification", "GIRF and mechanism counterfactuals",
                            "China trade/payment extension", "parameter identification and real estimation"],
    }
    report["passed"] = (result.wasSuccessful() and anchor["audit"]["passed"]
                        and all(row["passed"] for row in boundaries) and not rejected["passed"]
                        and report["derivative_checks"]["max_absolute_error"] < 1e-7
                        and report["off_equilibrium_accounting_identity"]["identity_absolute_error"] < 1e-12
                        and report["frozen_anchor_positive_risk_probe"]["candidate_rejected"])
    if args.write_report:
        target = ROOT / "docs" / "validation" / "equation_chain_20261126.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"model_id": report["model_id"], "passed": report["passed"],
               "original_max_residual": anchor["audit"]["max_abs_residual"],
               "tests_run": result.testsRun, "tests_passed": result.wasSuccessful(),
               "boundary_cases": boundaries, "max_derivative_error": report["derivative_checks"]["max_absolute_error"],
               "off_equilibrium_accounting_error": report["off_equilibrium_accounting_identity"]["identity_absolute_error"],
               "frozen_positive_risk_candidate_rejected": report["frozen_anchor_positive_risk_probe"]["candidate_rejected"],
               "frozen_positive_risk_max_successor_residual": report["frozen_anchor_positive_risk_probe"]["max_abs_successor_residual"],
               "full_dsge_equilibrium_solved": False, "report_written": args.write_report}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
