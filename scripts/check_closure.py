"""Synthetic conditional-market audit; never a full equilibrium declaration."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.conditional_market import (  # noqa: E402
    ConditionalInputs, inventory_objective_status,
    original_condition_residuals, solve_conditional_market,
)


def synthetic_inputs():
    """Normalized illustrative values, not Chinese lithium-market calibration."""
    return ConditionalInputs(
        q=1.7, net_imports=0.2, inventory_lag=0.3, commitment_lag=0.2,
        A_s=1.0, A_c=0.4, eta_s=0.6, eta_c=0.5, P_ref=1.0,
        mu=2.0, variance=0.25, beta=0.99, alpha_I=0.98,
        h=0.05, xi=0.05, I0=0.5, a_I=0.3, a_D=0.4, a_f=0.5)


def main():
    base = synthetic_inputs()
    cases = {
        "positive_inventory_net_selling_pressure": base,
        "zero_inventory_net_buying_pressure": replace(
            base, q=0.6, net_imports=0.0, inventory_lag=0.0),
        "zero_variance_continuous_limit_selection": replace(base, variance=0.0),
    }
    results = []
    for name, inputs in cases.items():
        result = solve_conditional_market(inputs)
        residuals = original_condition_residuals(inputs, result)
        results.append({
            "case": name,
            "synthetic_inputs": asdict(inputs),
            "conditional_moments": {
                "provenance": "fixed_for_conditional_check",
                "mean": inputs.mu,
                "variance": inputs.variance,
                "generated_by_same_dynamic_policy": False,
            },
            "solution": asdict(result),
            "inventory_objective": inventory_objective_status(
                inputs, result.spot, result.futures),
            "original_and_reduced_residuals": residuals,
        })
    max_residual = max(r["original_and_reduced_residuals"][
        "max_equality_or_kkt_residual"] for r in results)
    passed = max_residual < 1e-9
    report = {
        "scope": "conditional fixed-production two-market block and raw FOC/KKT checks",
        "parameters_are_industry_calibration": False,
        "units": "normalized synthetic units for mathematical checks only",
        "full_equilibrium_solved": False,
        "rational_expectations_fixed_point_verified": False,
        "production_and_investment_optimality_verified": False,
        "state_domain_invariance_verified": False,
        "zero_variance_positions_unique": False,
        "cases": results,
        "max_equality_or_kkt_residual": max_residual,
        "conditional_check_passed": passed,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
