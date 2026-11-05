"""Meaningful boundary, derivative and expectation checks for full conditions."""
from dataclasses import replace
import math
import unittest

from model.full_conditions import (
    DomainError, JointKernel, ShockBranch, advance_state, audit_forward_values,
    diagonal_matrix, evaluate_conditions, make_deterministic_anchor, primitives,
)
from scripts.check_full_conditions import price_risk_candidate, rate_path_candidate, standardized_nine_shock_check


class FullConditionsTests(unittest.TestCase):
    def test_complete_synthetic_anchor_and_four_queue_boundaries(self):
        for L, R in ((1, 0), (1, 2), (3, 0), (3, 2)):
            with self.subTest(L=L, R=R):
                a = make_deterministic_anchor(L, R)
                result = evaluate_conditions(a.state, a.policy, a.params, a.kernel)
                self.assertLess(result["max_equality_or_kkt_residual"], 1e-10)
                self.assertTrue(result["all_local_conditions_passed"])
                self.assertGreater(a.decision.j, 0)
                self.assertGreater(a.params.omega_B, 0)
                self.assertGreater(a.params.kappa, 0)
                self.assertEqual(a.state.dimension, L+R+12)
                nxt = advance_state(a.state, a.decision, a.params, a.kernel, a.kernel.branches[0])
                for name in ("q_lag", "inventory_lag", "commitment_lag", "mature_capacity"):
                    self.assertAlmostEqual(getattr(nxt, name), getattr(a.state, name), places=12)
                self.assertEqual(nxt.construction, a.state.construction)
                for x, y in zip(nxt.ramp, a.state.ramp):
                    self.assertAlmostEqual(x, y, places=12)
                forward = audit_forward_values(a.state, a.policy, a.params, a.kernel)
                self.assertAlmostEqual(forward["expanded_investment_gap"], 0, places=10)
                self.assertFalse(result["full_equilibrium_solved"])

    def test_new_completion_is_not_depreciated_for_R_zero(self):
        for L in (1, 3):
            a = make_deterministic_anchor(L, 0)
            d = replace(a.decision, j=0.3)
            s = replace(a.state, construction=(0.2, 0.1) if L == 3 else ())
            nxt = advance_state(s, d, a.params, a.kernel, a.kernel.branches[0])
            completion = 0.2 if L == 3 else 0.3
            expected = (1-a.params.delta)*s.mature_capacity+completion
            self.assertAlmostEqual(nxt.mature_capacity, expected)
            wrong = (1-a.params.delta)*(s.mature_capacity+completion)
            self.assertNotAlmostEqual(nxt.mature_capacity, wrong)

    def test_first_ramp_stage_and_construction_timing(self):
        a = make_deterministic_anchor(3, 2)
        d = replace(a.decision, j=0.3)
        s = replace(a.state, construction=(0.2, 0.1), ramp=(0.04, 0.06))
        nxt = advance_state(s, d, a.params, a.kernel, a.kernel.branches[0])
        self.assertEqual(nxt.construction, (0.1, 0.3))
        self.assertEqual(nxt.ramp[0], 0.2)
        self.assertAlmostEqual(nxt.ramp[1], (1-a.params.delta)*0.04)
        self.assertAlmostEqual(nxt.mature_capacity, (1-a.params.delta)*(s.mature_capacity+0.06))

    def test_joint_policy_generates_price_moments_and_rejects_unsolved_candidate(self):
        a = make_deterministic_anchor()
        policy, kernel = price_risk_candidate(a)
        result = evaluate_conditions(a.state, policy, a.params, kernel)
        moments = result["conditional_moments"]
        self.assertAlmostEqual(moments["mean_price"], 2*math.cosh(0.025), places=13)
        self.assertAlmostEqual(moments["price_variance"], (2*math.sinh(0.025))**2, places=13)
        self.assertFalse(moments["externally_supplied_price_moments"])
        self.assertFalse(result["all_local_conditions_passed"])
        self.assertGreater(result["max_equality_or_kkt_residual"], 1e-5)
        with self.assertRaises(TypeError):
            evaluate_conditions(a.state, policy, a.params, kernel, mu=99)

    def test_variable_rate_products_and_all_future_congestion_terms(self):
        p, s, policy, kernel = rate_path_candidate()
        report = audit_forward_values(s, policy, p, kernel)
        b0 = 1/(1+p.i_bar)
        exact_value = sum(0.5*b0/(1+p.i_bar+r)*(10+5*0.7*r) for r in (-0.02, 0.02))
        exact_congestion = p.omega_B*sum(0.5*b0*(0.05+0.2*r) for r in (-0.02, 0.02))
        self.assertAlmostEqual(report["discounted_completed_capacity_value"], exact_value, places=13)
        self.assertAlmostEqual(report["discounted_future_congestion_cost"], exact_congestion, places=13)
        self.assertGreater(exact_congestion, 0)
        self.assertAlmostEqual(report["one_step_minus_expanded_gap"], 0, places=12)
        self.assertGreater(abs(exact_value-report["expected_path_discount_products"][2]*10), 1e-8)
        self.assertGreater(abs(report["expected_path_discount_products"][2]-b0*b0), 1e-8)
        self.assertFalse(report["infinite_horizon_tvc_proved_by_this_finite_check"])

    def test_production_gradient_matches_original_two_period_objective(self):
        a = make_deterministic_anchor()
        p = replace(a.params, kappa=0.7, nu=1.4)
        s = replace(a.state, q_lag=0.9)
        current = replace(a.decision, q=0.6)
        continuation = replace(a.decision, q=0.7)
        def policy(state):
            return current if state.time == 0 else continuation
        result = evaluate_conditions(s, policy, p, a.kernel)
        env = primitives(s, p)
        k = s.mature_capacity+sum(g*z for g, z in zip(p.g, s.ramp))
        def objective(q):
            return current.spot*q-env["m"]*q-p.alpha/(p.nu+1)*q**(p.nu+1)/k**p.nu \
                   -p.kappa/2*(q-s.q_lag)**2-env["b"]*p.kappa/2*(continuation.q-q)**2
        eps = 1e-6
        fd = (objective(current.q+eps)-objective(current.q-eps))/(2*eps)
        self.assertAlmostEqual(fd, result["diagnostics"]["output_unconstrained_gradient"], places=8)
        self.assertAlmostEqual(result["recovered"]["Q_lag_envelope"], p.kappa*(0.6-0.9))
        self.assertAlmostEqual(result["recovered"]["expected_next_Q_lag_envelope"], p.kappa*(0.7-0.6))

    def test_zero_variance_does_not_falsely_identify_positions(self):
        a = make_deterministic_anchor()
        d = replace(a.decision, h_inventory=a.decision.h_inventory+100,
                    h_procurement=a.decision.h_procurement-100)
        result = evaluate_conditions(a.state, lambda s: d, a.params, a.kernel)
        self.assertTrue(result["all_local_conditions_passed"])
        self.assertFalse(result["diagnostics"]["zero_variance_positions_unique"])
        self.assertEqual(result["diagnostics"]["zero_variance_position_status"], "other_zero_sum_selection_nonunique")

    def test_future_commitment_failure_is_rejected_without_clipping(self):
        a = make_deterministic_anchor()
        bad = replace(a.decision, c=100.0)
        with self.assertRaisesRegex(DomainError, "successor branch 0"):
            evaluate_conditions(a.state, lambda s: bad, a.params, a.kernel)
        self.assertEqual(bad.c, 100.0)

    def test_infeasible_continuation_output_cannot_pass_as_a_valid_policy(self):
        a = make_deterministic_anchor()
        def policy(state):
            return a.decision if state.time == 0 else replace(a.decision, q=2.0)
        with self.assertRaisesRegex(DomainError, "successor branch 0.*output exceeds"):
            evaluate_conditions(a.state, policy, a.params, a.kernel)
        with self.assertRaisesRegex(DomainError, "forward continuation output exceeds"):
            audit_forward_values(a.state, policy, a.params, a.kernel)

    def test_all_nine_standardized_shocks_generate_512_successors(self):
        a = make_deterministic_anchor()
        report = standardized_nine_shock_check(a)
        self.assertEqual(report["branches"], 512)
        self.assertEqual(report["successors_checked"], 512)
        self.assertTrue(report["all_nine_shock_loadings_positive"])
        self.assertEqual(report["innovation_mean"], (0.0,)*9)
        self.assertEqual(report["innovation_variance"], (1.0,)*9)
        self.assertEqual(report["identity_covariance_max_error"], 0.0)
        self.assertAlmostEqual(report["conditional_moments"]["mean_price"], 2*math.cosh(0.025), places=13)
        self.assertAlmostEqual(report["conditional_moments"]["price_variance"], (2*math.sinh(0.025))**2, places=13)
        self.assertFalse(report["all_local_conditions_passed"])
        self.assertFalse(report["full_stochastic_equilibrium_solved"])

    def test_engineering_fx_split_and_known_tau_calendar(self):
        a = make_deterministic_anchor()
        x = list(a.state.external)
        x[1], x[5] = math.log(2), math.log(3)
        s = replace(a.state, external=tuple(x), time=7)
        env = primitives(s, a.params, tau_path=lambda t: 0.1*t)
        self.assertAlmostEqual(env["m"], 3*(a.params.m_domestic+2*a.params.FX_bar*a.params.m_usd))
        self.assertAlmostEqual(env["A"], a.params.D0*math.exp(a.params.lambda_tau*0.7))
        self.assertEqual(s.dimension, a.params.L+a.params.R+12)
        self.assertAlmostEqual(env["tau"], 0.7)
        with self.assertRaisesRegex(DomainError, "cannot both be zero"):
            evaluate_conditions(a.state, a.policy,
                                replace(a.params, m_domestic=0.0, m_usd=0.0), a.kernel)

    def test_invalid_rate_domain_and_joint_probability_are_rejected(self):
        a = make_deterministic_anchor()
        ext = list(a.state.external)
        ext[2] = -1-a.params.i_bar
        with self.assertRaises(DomainError):
            primitives(replace(a.state, external=tuple(ext)), a.params)
        bad = JointKernel(a.kernel.A, a.kernel.B, (ShockBranch(0.9, (0.0,)*9),))
        with self.assertRaisesRegex(DomainError, "sum to one"):
            evaluate_conditions(a.state, a.policy, a.params, bad)
        with self.assertRaises(DomainError):
            evaluate_conditions(replace(a.state, external=(0.0,)*5), a.policy, a.params, a.kernel)

    def test_nonpositive_carry_is_not_rescued_by_local_goods_balance(self):
        a = make_deterministic_anchor()
        d = replace(a.decision, futures=100)
        result = evaluate_conditions(a.state, lambda s: d, a.params, a.kernel)
        self.assertEqual(result["diagnostics"]["inventory_objective_status"], "unbounded")
        self.assertFalse(result["all_local_conditions_passed"])

    def test_value_equations_are_checked_not_assumed(self):
        a = make_deterministic_anchor()
        d = replace(a.decision, producer_value=a.decision.producer_value+10,
                    w_b=(a.decision.w_b[0]+1, *a.decision.w_b[1:]))
        result = evaluate_conditions(a.state, lambda s: d, a.params, a.kernel)
        self.assertGreater(abs(result["original_equalities"]["producer_Bellman"]), 0.1)
        self.assertGreater(abs(result["original_equalities"]["E15_construction_value_1"]), 0.5)
        self.assertFalse(result["all_local_conditions_passed"])


if __name__ == "__main__":
    unittest.main()
