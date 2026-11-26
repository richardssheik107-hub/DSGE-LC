"""Synthetic all-condition checks; not a nonlinear stochastic solver."""
from dataclasses import asdict, replace
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.full_conditions import (  # noqa: E402
    MODEL_ID, REVISION, JointKernel, ShockBranch, audit_forward_values,
    diagonal_matrix, evaluate_conditions, independent_rademacher_kernel, make_deterministic_anchor,
    primitives, risk_share_positions,
)


def price_risk_candidate(anchor):
    """Unsolved policy with a two-branch, rank-one price-risk test kernel.

The active innovation is standardized; unused zero-loading shocks have been
collapsed. This is a restricted interface test, not the full nine-shock law.
"""
    branches = []
    for sign in (-1, 1):
        innovation = [0.0]*9
        innovation[0] = sign
        branches.append(ShockBranch(0.5, tuple(innovation)))
    kernel = JointKernel(diagonal_matrix(0.8), diagonal_matrix((0.1,)+(0.0,)*8), tuple(branches))
    def policy(state):
        env = primitives(state, anchor.params)
        price = anchor.decision.spot*math.exp(0.25*state.external[0])
        f = anchor.decision.futures
        ds = env["A_s"]*(price/anchor.params.P_star)**(-anchor.params.eta_s)
        c = env["A_c"]*(f/anchor.params.P_star)**(-anchor.params.eta_c)
        hi, hd, hf = risk_share_positions(anchor.decision.inventory, c, anchor.params, env["a_f"])
        return replace(anchor.decision, spot=price, d_s=ds, c=c,
                       h_inventory=hi, h_procurement=hd, h_financial=hf)
    return policy, kernel


def standardized_nine_shock_check(anchor):
    """Exercise all 512 canonical branches, including all four macro states.

Only the supplied policy's price law is analytically specified. Its residuals
remain nonzero: this does not upgrade the candidate to a stochastic solution.
"""
    kernel = independent_rademacher_kernel(
        diagonal_matrix(0.8),
        diagonal_matrix((0.1, 0.01, 0.001, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01)))
    policy, _ = price_risk_candidate(anchor)
    checked = evaluate_conditions(anchor.state, policy, anchor.params, kernel)
    mean = tuple(math.fsum(b.probability*b.innovation[i] for b in kernel.branches)
                 for i in range(9))
    covariance = tuple(tuple(math.fsum(b.probability*(b.innovation[i]-mean[i])
                                                  *(b.innovation[j]-mean[j])
                                                  for b in kernel.branches)
                             for j in range(9)) for i in range(9))
    identity_error = max(abs(covariance[i][j]-(1.0 if i == j else 0.0))
                         for i in range(9) for j in range(9))
    return {"branches": len(kernel.branches), "innovation_mean": mean,
            "innovation_variance": tuple(covariance[i][i] for i in range(9)),
            "identity_covariance_max_error": identity_error,
            "all_nine_shock_loadings_positive": all(kernel.B[i][i] > 0 for i in range(9)),
            "successors_checked": len(checked["successor_checks"]),
            "conditional_moments": checked["conditional_moments"],
            "max_equality_or_kkt_residual": checked["max_equality_or_kkt_residual"],
            "all_local_conditions_passed": checked["all_local_conditions_passed"],
            "global_invariant_domain_verified": False,
            "full_stochastic_equilibrium_solved": False}


def rate_path_candidate():
    """Construction recursion exact, other conditions deliberately unsolved.

U_t=10+5*r_t; r'=0.7*r +/- 0.02; J=.05+.2*r. Thus W_B1 is
-omega_B*J+b*E[U']. Its expansion tests both path discount correlation and
the negative future-J term carried by an existing construction position.
"""
    anchor = make_deterministic_anchor(L=2, R=0)
    params = replace(anchor.params, i_bar=0.05)
    branches = []
    for sign in (-1, 1):
        eps = [0.0]*9
        eps[2] = sign
        branches.append(ShockBranch(0.5, tuple(eps)))
    kernel = JointKernel(diagonal_matrix(0.7),
                        diagonal_matrix((0.0, 0.0, 0.02, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
                        tuple(branches))
    def policy(state):
        r = state.external[2]
        b = primitives(state, params)["b"]
        j = 0.05+0.2*r
        u = 10+5*r
        wb = -params.omega_B*j+b*(10+5*0.7*r)
        return replace(anchor.decision, j=j, w_m=u, w_b=(wb,))
    return params, anchor.state, policy, kernel


def main():
    anchor = make_deterministic_anchor()
    main_check = evaluate_conditions(anchor.state, anchor.policy, anchor.params, anchor.kernel)
    boundaries = []
    for L, R in ((1, 0), (1, 2), (3, 0), (3, 2)):
        case = make_deterministic_anchor(L, R)
        checked = evaluate_conditions(case.state, case.policy, case.params, case.kernel)
        forward = audit_forward_values(case.state, case.policy, case.params, case.kernel, horizon=max(L, 8))
        boundaries.append({"L": L, "R": R, "state_dimension": case.state.dimension,
            "positive_start_J": case.decision.j,
            "max_equality_or_kkt_residual": checked["max_equality_or_kkt_residual"],
            "local_conditions_passed": checked["all_local_conditions_passed"],
            "forward_investment_expansion_error": forward["one_step_minus_expanded_gap"]})
    risky_policy, risky_kernel = price_risk_candidate(anchor)
    risky = evaluate_conditions(anchor.state, risky_policy, anchor.params, risky_kernel)
    nine_shock = standardized_nine_shock_check(anchor)
    rp, rs, rate_policy, rate_kernel = rate_path_candidate()
    rates = audit_forward_values(rs, rate_policy, rp, rate_kernel)
    # Symmetry makes E[U_(t+2)]=10, while the discount product is correlated
    # with U_(t+2). This deliberately incorrect factorization is a comparator.
    rates["incorrect_factorization_Ed_times_EU_for_comparison"] = rates["expected_path_discount_products"][2]*10
    rates["correlation_difference"] = rates["discounted_completed_capacity_value"] - rates["incorrect_factorization_Ed_times_EU_for_comparison"]
    gates = {
        "deterministic_anchor_passed": main_check["all_local_conditions_passed"],
        "four_queue_boundaries_passed": all(x["local_conditions_passed"] and abs(x["forward_investment_expansion_error"]) < 1e-10 for x in boundaries),
        "nonzero_variance_computed_internally": risky["conditional_moments"]["price_variance"] > 0,
        "unsolved_risky_candidate_is_rejected": not risky["all_local_conditions_passed"],
        "stochastic_discount_expansion_passed": abs(rates["one_step_minus_expanded_gap"]) < 1e-10,
        "discount_correlation_is_not_discarded": abs(rates["correlation_difference"]) > 1e-8,
        "standardized_nine_shock_kernel_checked": nine_shock["branches"] == 512
            and nine_shock["successors_checked"] == 512
            and max(abs(x) for x in nine_shock["innovation_mean"]) < 1e-12
            and nine_shock["identity_covariance_max_error"] < 1e-12
            and nine_shock["all_nine_shock_loadings_positive"],
        "unsolved_full_nine_shock_candidate_is_rejected": not nine_shock["all_local_conditions_passed"],
    }
    report = {
        "model_id": MODEL_ID, "revision": REVISION,
        "scope": "all-condition evaluator plus exact deterministic stationary anchor and rejected stochastic candidate",
        "parameters_are_synthetic_reverse_engineered": True,
        "full_stochastic_equilibrium_solved": False, "global_policy_fixed_point_verified": False,
        "global_state_domain_invariance_verified": False, "parameter_calibration_performed": False,
        "macro_external_order": ["g", "e", "r", "zeta", "zA_id", "zm_id", "zJ_id", "zN_id", "zf_id"],
        "tau_convention": "known deterministic path; constant zero in anchor; calendar index is not an extra random state",
        "engineering_convention": "fixed domestic and USD coefficients; FX applies to USD component only",
        "kernel_convention": "canonical benchmark: nine independent +/-1 innovations, variance I9; deterministic anchor collapses B=0 successors; two-branch tests collapse unused zero-loading shocks",
        "producer_value_convention": "Bellman verification of a recovered value, not an eighth independent quantity/price condition",
        "deterministic_anchor": {"parameters": asdict(anchor.params), "state": asdict(anchor.state),
            "decision": asdict(anchor.decision), "kernel": asdict(anchor.kernel), "conditions": main_check,
            "terminal_argument": "On this exact stationary path b<1 and all states, value and shadows are finite constants, so discounted value/state-costate tails vanish. This does not prove the same off-path."},
        "four_queue_boundary_checks": boundaries,
        "nonzero_variance_unsolved_candidate": risky,
        "standardized_nine_shock_candidate": nine_shock,
        "variable_rate_and_future_congestion_check": rates,
        "verification_gates": gates,
        "checks_passed": all(gates.values()),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return int(not all(gates.values()))


if __name__ == "__main__":
    raise SystemExit(main())
