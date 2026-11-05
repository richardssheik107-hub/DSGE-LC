"""Checks of economic boundaries and raw objectives, using synthetic values."""
from dataclasses import replace
import math
import unittest

from model.conditional_market import (
    ConditionalInputs, InfeasibleStateError, inventory_objective_status,
    no_futures_marginal_gaps, original_condition_residuals,
    risk_positions, solve_conditional_market,
)


def example():
    return ConditionalInputs(
        q=1.7, net_imports=0.2, inventory_lag=0.3, commitment_lag=0.2,
        A_s=1.0, A_c=0.4, eta_s=0.6, eta_c=0.5, P_ref=1.0,
        mu=2.0, variance=0.25, beta=0.99, alpha_I=0.98,
        h=0.05, xi=0.05, I0=0.5, a_I=0.3, a_D=0.4, a_f=0.5)


class ConditionalClosureChecks(unittest.TestCase):
    def test_positive_inventory_satisfies_original_conditions(self):
        x = example()
        result = solve_conditional_market(x)
        residuals = original_condition_residuals(x, result)
        self.assertGreater(result.inventory, 0)
        self.assertGreater(result.spot, 0)
        self.assertGreater(result.futures, 0)
        self.assertLess(residuals["max_equality_or_kkt_residual"], 1e-9)
        self.assertAlmostEqual(residuals["E19_inventory_raw_gradient"], 0, places=9)

    def test_zero_inventory_uses_inequality_not_equality(self):
        x = replace(example(), q=0.6, net_imports=0.0, inventory_lag=0.0)
        result = solve_conditional_market(x)
        residuals = original_condition_residuals(x, result)
        self.assertEqual(result.inventory, 0)
        self.assertLess(residuals["E19_inventory_raw_gradient"], 0)
        self.assertGreater(residuals["E24_inventory_gap"], 0)
        self.assertLess(residuals["max_equality_or_kkt_residual"], 1e-9)

    def test_risk_premium_can_have_either_sign(self):
        selling = example()
        buying = replace(selling, q=0.6, net_imports=0.0, inventory_lag=0.0)
        sell_result = solve_conditional_market(selling)
        buy_result = solve_conditional_market(buying)
        self.assertGreater(sell_result.net_exposure, 0)
        self.assertLess(sell_result.futures, selling.mu)
        self.assertLess(buy_result.net_exposure, 0)
        self.assertGreater(buy_result.futures, buying.mu)

    def test_infeasible_material_balance_is_rejected(self):
        for imports in (-0.1, 0.0):
            x = replace(example(), q=0, net_imports=imports,
                        inventory_lag=0, commitment_lag=0)
            with self.assertRaises(InfeasibleStateError):
                solve_conditional_market(x)

    def test_inventory_objective_at_zero_linear_carry_gap(self):
        x = replace(example(), beta=0.5, alpha_I=1, h=0, xi=1)
        self.assertEqual(inventory_objective_status(x, 1, 2)["status"], "unbounded")
        # At k=0, the reduced objective keeps increasing logarithmically.
        values = [x.xi*math.log1p(i/x.I0) for i in (1, 10, 100)]
        self.assertTrue(values[0] < values[1] < values[2])
        flat = replace(x, xi=0)
        self.assertEqual(inventory_objective_status(flat, 1, 2)["status"], "flat_nonunique")
        self.assertEqual(inventory_objective_status(x, 1.1, 2)["status"], "finite_unique")

    def test_zero_variance_price_is_fixed_but_positions_are_not_unique(self):
        x = replace(example(), variance=0)
        result = solve_conditional_market(x)
        self.assertEqual(result.futures, x.mu)
        self.assertEqual(result.position_status, "continuous_limit_selection_not_unique")
        alternative = replace(result, h_inventory=result.h_inventory+2,
                              h_financial=result.h_financial-2)
        for allocation in (result, alternative):
            residuals = original_condition_residuals(x, allocation)
            self.assertLess(residuals["max_equality_or_kkt_residual"], 1e-9)
        self.assertNotEqual(result.h_inventory, alternative.h_inventory)

    def test_risk_allocation_never_divides_by_small_variance(self):
        x = example()
        expected = risk_positions(x, inventory=2, commitment=3)
        for variance in (0, 1e-300, 0.25):
            allocation = risk_positions(replace(x, variance=variance), 2, 3)
            self.assertEqual(allocation, expected)
            self.assertTrue(all(math.isfinite(v) for v in allocation))
        tiny = replace(x, variance=1e-300)
        result = solve_conditional_market(tiny)
        self.assertLess(original_condition_residuals(tiny, result)[
            "max_equality_or_kkt_residual"], 1e-9)

    def test_hedged_inventory_choice_beats_feasible_quantity_deviations(self):
        x = example()
        result = solve_conditional_market(x)
        delta = x.mu-result.futures

        def original_objective(inventory):
            # Reoptimize the hedge for each deviation at the SAME quoted
            # prices and conditional distribution, as a price taker does.
            position = -x.alpha_I*inventory+delta/(x.a_I*x.variance)
            carry = x.h*inventory-x.xi*math.log1p(inventory/x.I0)
            return -result.spot*inventory-carry+x.beta*(
                x.alpha_I*inventory*x.mu+position*delta
                -0.5*x.a_I*x.variance*(x.alpha_I*inventory+position)**2)

        optimum = original_objective(result.inventory)
        for deviation in (0, result.inventory/2, result.inventory+0.5):
            self.assertGreater(optimum, original_objective(deviation))

    def test_no_futures_conditions_follow_raw_unhedged_objectives(self):
        x = example()
        inventory, commitment, spot = 0.7, 0.6, 1.8
        gaps = no_futures_marginal_gaps(x, inventory, commitment, spot)
        step = 1e-5

        def inventory_payoff(i):
            return -spot*i-x.h*i+x.xi*math.log1p(i/x.I0)+x.beta*(
                x.alpha_I*i*x.mu-0.5*x.a_I*x.variance*(x.alpha_I*i)**2)

        def procurement_payoff(c):
            power = 1-1/x.eta_c
            benefit = x.P_ref*x.A_c**(1/x.eta_c)*(c**power-1)/power
            return x.beta*(benefit-c*x.mu-0.5*x.a_D*x.variance*c*c)

        di = (inventory_payoff(inventory+step)-inventory_payoff(inventory-step))/(2*step)
        dc = (procurement_payoff(commitment+step)-procurement_payoff(commitment-step))/(2*step)
        self.assertAlmostEqual(-di, gaps["inventory_gap"], places=8)
        self.assertAlmostEqual(dc/x.beta, gaps["procurement_gradient_before_discount"], places=8)
        self.assertNotIn("futures", gaps)


if __name__ == "__main__":
    unittest.main()
