"""Economic regressions for timing, original budgets and KKT behavior."""

from dataclasses import replace
import unittest
import numpy as np

from model.dsge import Parameters, Branch, evaluate, solve_anchor
from model.dsge.economy import budgets, diagnostics, real_costs
from model.dsge.shocks import kernel
from model.dsge.state import next_state, effective_capacity, state_vector


class EquationChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.anchor = solve_anchor()

    def test_anchor_all_original_conditions(self):
        audit = self.anchor["audit"]
        self.assertTrue(audit["passed"])
        self.assertLess(audit["max_abs_residual"], 1e-10)
        self.assertGreater(min(self.anchor["choice"].consumption), 0)
        self.assertGreater(audit["diagnostics"]["inventory_gap"], 0)
        self.assertEqual(self.anchor["optimizer"]["reduced_jacobian_rank"], 4)

    def test_all_construction_ramp_boundaries(self):
        for lag, ramp in ((1, ()), (1, (0.45, 0.80)), (3, ()), (3, (0.45, 0.80))):
            with self.subTest(L=lag, R=len(ramp)):
                result = solve_anchor(replace(Parameters(), construction_lag=lag, ramp_weights=ramp))
                self.assertTrue(result["audit"]["passed"])
                self.assertEqual(len(result["choice"].wb), lag - 1)
                self.assertEqual(len(result["choice"].wz), len(ramp))

    def test_first_capacity_arrives_after_L_without_early_depreciation(self):
        for lag, ramp in ((1, ()), (1, (0.4, 0.8)), (3, ()), (3, (0.4, 0.8))):
            p = replace(Parameters(), construction_lag=lag, ramp_weights=ramp)
            state = replace(self.anchor["state"], mature=0.0, construction=np.zeros(lag - 1), ramp=np.zeros(len(ramp)))
            capacities = [effective_capacity(state, p)]
            for t in range(lag + 1):
                choice = replace(self.anchor["choice"], investment=1.0 if t == 0 else 0.0)
                state = next_state(state, choice, np.zeros(4), p)
                capacities.append(effective_capacity(state, p))
            np.testing.assert_array_equal(capacities[:lag], np.zeros(lag))
            self.assertAlmostEqual(capacities[lag], ramp[0] if ramp else 1.0)
            expected_second = (1 - p.depreciation) * (ramp[1] if len(ramp) > 1 else 1.0)
            self.assertAlmostEqual(capacities[lag + 1], expected_second)

    def test_settlement_transfers_wealth_even_when_aggregate_is_zero(self):
        a = self.anchor
        state = replace(a["state"], old_positions=np.array([-0.4, 0.1, 0.3]), old_forward=a["choice"].spot - 0.05)
        delta = budgets(state, a["choice"], a["parameters"]) - budgets(a["state"], a["choice"], a["parameters"])
        np.testing.assert_allclose(delta, [0.0, 0.02, -0.005, -0.015], atol=1e-15)
        self.assertAlmostEqual(sum(delta), 0)
        self.assertGreater(diagnostics(state, a["choice"], a["parameters"])["financial_net_worth"], state.bonds[3])

    def test_aggregate_budget_identity_off_equilibrium(self):
        a = self.anchor
        p, s = a["parameters"], a["state"]
        g = replace(a["choice"], q=a["choice"].q * 1.07, wage=a["choice"].wage * 1.02,
                    output=a["choice"].output * 1.03, next_bonds=np.array([-.05, -.10, -.05, .25]))
        d = diagnostics(s, g, p)
        lc = g.q + p.inventory_survival * s.inventory_prev - g.flexible - s.commitment_prev - g.inventory
        labor = g.labor_w - g.q / p.al - g.labor_d - g.labor_0
        rhs = (-d["final_resource_residual"] - d["assembler_zero_profit_residual"]
               + g.price_0 * (g.output_0 - p.a0 * g.labor_0)
               + (g.price_0 * p.a0 - g.wage) * g.labor_0
               + np.sum(g.next_bonds) / g.gross_rate - np.sum(s.bonds)
               - d["futures_settlement_total"] - g.wage * labor - g.spot * lc)
        self.assertAlmostEqual(sum(budgets(s, g, p)), rhs, places=13)

    def test_original_cost_and_envelope_derivatives(self):
        a = self.anchor
        p, s, g = a["parameters"], a["state"], a["choice"]
        step = 1e-6
        cost = lambda st, ch, key: real_costs(st, ch, p)[key]
        dq = (cost(s, replace(g, q=g.q + step), "production") - cost(s, replace(g, q=g.q - step), "production")) / (2 * step)
        dk = (cost(replace(s, mature=s.mature + step), g, "production") - cost(replace(s, mature=s.mature - step), g, "production")) / (2 * step)
        dj = (cost(s, replace(g, investment=g.investment + step), "construction") - cost(s, replace(g, investment=g.investment - step), "construction")) / (2 * step)
        k = effective_capacity(s, p)
        self.assertAlmostEqual(dq, p.m_bar + p.alpha_q * (g.q / k) ** p.nu_q, places=8)
        self.assertAlmostEqual(dk, -p.alpha_q * p.nu_q / (p.nu_q + 1) * (g.q / k) ** (p.nu_q + 1), places=8)
        self.assertAlmostEqual(dj, p.pj_bar + p.chi_j * g.investment + p.congestion * sum(s.construction), places=8)
        c = replace(g, commitment=1.2 * g.commitment)
        da2 = (cost(replace(s, commitment_prev=s.commitment_prev + step), c, "procurement")
               - cost(replace(s, commitment_prev=s.commitment_prev - step), c, "procurement")) / (2 * step)
        self.assertAlmostEqual(da2, -p.adjustment_c * (c.commitment - s.commitment_prev), places=10)

    def _stochastic_probe(self):
        p = Parameters()
        state, choice = self.anchor["state"], self.anchor["choice"]
        branches = []
        for probability, eps in kernel(p):
            future_state = next_state(state, choice, eps, p)
            cons = choice.consumption.copy()
            cons[3] *= np.exp(0.05 * eps[0])
            future_choice = replace(choice, spot=choice.spot + 0.01 * eps[0], consumption=cons)
            branches.append(Branch(probability, eps, future_state, future_choice))
        return state, choice, branches, p

    def test_declared_kernel_moments(self):
        rows = kernel(Parameters())
        self.assertEqual(len(rows), 16)
        probs = np.array([r[0] for r in rows]); innovations = np.array([r[1] for r in rows])
        np.testing.assert_allclose(probs @ innovations, np.zeros(4), atol=1e-15)
        np.testing.assert_allclose((innovations.T * probs) @ innovations, np.eye(4), atol=1e-15)

    def test_missing_branch_cannot_be_used_as_an_expectation(self):
        state, choice, branches, p = self._stochastic_probe()
        audit = evaluate(state, choice, branches[:-1], p)
        self.assertFalse(audit["passed"])
        self.assertTrue(audit["domain_errors"])

    def test_sdf_price_covariance_is_not_discarded(self):
        state, choice, branches, p = self._stochastic_probe()
        audit = evaluate(state, choice, branches, p)
        covariance = audit["diagnostics"]["covariance_sdf_F_spot"]
        expected = -p.beta * 0.01 * np.sinh(0.1)
        self.assertAlmostEqual(covariance, expected, places=13)
        self.assertGreater(abs(covariance), 1e-4)
        self.assertFalse(audit["passed"])  # It is deliberately not a solved policy.

    def test_zero_position_uses_subgradient_interval(self):
        state, choice, branches, p = self._stochastic_probe()
        bounded = replace(choice, collateral_multiplier=0.2)
        audit = evaluate(state, bounded, branches, p)
        self.assertEqual(audit["residuals"]["E22.futures_F_subgradient"], 0)
        unbounded = evaluate(state, choice, branches, p)
        self.assertGreater(unbounded["residuals"]["E22.futures_F_subgradient"], 0)

    def test_zero_risk_hedges_are_not_uniquely_identified(self):
        a = self.anchor
        positions = np.array([0.1, -0.1, 0.0])
        s = replace(a["state"], old_positions=positions)
        g = replace(a["choice"], positions=positions)
        audit = evaluate(s, g, [Branch(1.0, np.zeros(4), s, g)], a["parameters"])
        self.assertTrue(audit["passed"])

    def test_wrong_consumption_is_rejected_by_budget_and_resources(self):
        a = self.anchor
        cons = a["choice"].consumption.copy(); cons[1] += 0.01
        g = replace(a["choice"], consumption=cons)
        audit = evaluate(a["state"], g, [Branch(1.0, np.zeros(4), a["state"], a["choice"])], a["parameters"])
        self.assertFalse(audit["passed"])
        self.assertAlmostEqual(audit["residuals"]["E33.budget_I"], 0.01)
        self.assertAlmostEqual(audit["residuals"]["E38.final_resources_redundant_audit"], -0.01)

    def test_invalid_consumption_is_not_clipped(self):
        a = self.anchor
        cons = a["choice"].consumption.copy(); cons[3] = -0.01
        g = replace(a["choice"], consumption=cons)
        audit = evaluate(a["state"], g, [Branch(1.0, np.zeros(4), a["state"], a["choice"])], a["parameters"])
        self.assertFalse(audit["passed"])
        self.assertTrue(audit["domain_errors"])
        self.assertEqual(g.consumption[3], -0.01)

    def test_ramping_capacity_does_not_require_positive_mature_stock(self):
        a = self.anchor
        s = replace(a["state"], mature=0.0, ramp=np.array([1.0, 1.0]))
        successor = next_state(s, a["choice"], np.zeros(4), a["parameters"])
        audit = evaluate(s, a["choice"], [Branch(1.0, np.zeros(4), successor, a["choice"])], a["parameters"])
        self.assertEqual(audit["domain_errors"], [])
        self.assertFalse(audit["passed"])

    def test_infeasible_successor_controls_are_rejected(self):
        a = self.anchor
        choices = [replace(a["choice"], investment=-0.1),
                   replace(a["choice"], inventory=-0.1),
                   replace(a["choice"], q=2 * effective_capacity(a["state"], a["parameters"])),
                   replace(a["choice"], next_bonds=np.array([-1.0, 0.1, 0.1, 0.8])),
                   replace(a["choice"], positions=np.array([-100.0, 0.0, 100.0]))]
        for future in choices:
            audit = evaluate(a["state"], a["choice"],
                             [Branch(1.0, np.zeros(4), a["state"], future)], a["parameters"])
            self.assertFalse(audit["passed"])
            self.assertTrue(audit["domain_errors"])

    def test_frozen_anchor_must_also_be_audited_at_reachable_states(self):
        a = self.anchor
        p, g = Parameters(), a["choice"]
        branches = [Branch(prob, eps, next_state(a["state"], g, eps, p), g) for prob, eps in kernel(p)]
        center = evaluate(a["state"], g, branches, p)
        self.assertTrue(center["passed"])  # A single point can misleadingly pass.
        successors = []
        for first in branches:
            future = [Branch(prob, eps, next_state(first.state, g, eps, p), g) for prob, eps in kernel(p)]
            successors.append(evaluate(first.state, g, future, p))
        self.assertTrue(all(not row["passed"] for row in successors))
        self.assertGreater(max(row["max_abs_residual"] for row in successors), 1e-3)

    def test_slack_debt_constraint_rejects_positive_multiplier(self):
        a = self.anchor
        g = replace(a["choice"], debt_multipliers=np.array([0.1, 0.0, 0.0]))
        audit = evaluate(a["state"], g, [Branch(1.0, np.zeros(4), a["state"], a["choice"])], a["parameters"])
        self.assertFalse(audit["passed"])
        self.assertGreater(audit["residuals"]["E35.debt_floor_WID.complementarity[0]"], 0)


if __name__ == "__main__":
    unittest.main()
