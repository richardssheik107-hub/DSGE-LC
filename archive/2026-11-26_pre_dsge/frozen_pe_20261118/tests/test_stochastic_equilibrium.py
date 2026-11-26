"""Targeted structural checks for the stochastic solver's numerical blocks."""
from dataclasses import asdict, replace
from pathlib import Path
import math
import unittest

import numpy as np

from model.full_conditions import (
    advance_state,
    effective_capacity,
    evaluate_conditions,
    make_deterministic_anchor,
    primitives,
    risk_share_positions,
)
from model.stochastic_equilibrium import PolynomialPolicy, Problem, basis_powers, load_config


CONFIG = Path(__file__).resolve().parents[1] / "configs" / "stochastic_baseline.json"


def pack_decision(decision):
    return np.array(
        [
            decision.q, decision.j, decision.d_s, decision.c, decision.inventory,
            decision.spot, decision.futures, decision.w_m, *decision.w_b, *decision.w_z,
        ],
        dtype=float,
    )


def continuation_moments(state, current, continuation, problem):
    """Independent scalar transition and probability oracle for a conditional node."""
    successors = [
        continuation(advance_state(state, current, problem.params, problem.kernel, branch))
        for branch in problem.kernel.branches
    ]
    weights = [branch.probability for branch in problem.kernel.branches]

    def expected(get):
        return math.fsum(probability * get(decision)
                         for probability, decision in zip(weights, successors))

    mean_price = expected(lambda d: d.spot)
    return {
        "mean_price": np.array([mean_price]),
        "price_variance": np.array([expected(lambda d: (d.spot - mean_price) ** 2)]),
        "mean_Q": np.array([expected(lambda d: d.q)]),
        "mean_W_M": np.array([expected(lambda d: d.w_m)]),
        "mean_W_B": np.array([[expected(lambda d: d.w_b[i]) for i in range(problem.params.L-1)]]),
        "mean_W_Z": np.array([[expected(lambda d: d.w_z[i]) for i in range(problem.params.R)]]),
    }


def recover_node_value(decision, state, params, next_value):
    """Recover the Bellman level for the original-condition oracle."""
    env = primitives(state, params)
    capital = effective_capacity(state, params)
    produce = (
        env["m"] * decision.q
        + params.alpha * decision.q ** (params.nu + 1) / ((params.nu + 1) * capital ** params.nu)
        + params.kappa / 2 * (decision.q - state.q_lag) ** 2
    )
    invest = (
        env["p_j"] * decision.j + params.chi / 2 * decision.j ** 2
        + params.omega_B * decision.j * math.fsum(state.construction)
    )
    value = decision.spot * decision.q - produce - invest + env["b"] * next_value
    return replace(decision, producer_value=value)


class StochasticEquilibriumTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(CONFIG)

    def make_problem(self, L, R, **parameters):
        anchor = make_deterministic_anchor(L, R)
        params = replace(anchor.params, **parameters)
        return Problem({
            **self.config,
            "parameters": asdict(params),
            "domain_radius": [
                *self.config["domain_radius"][:13],
                *([0.02] * (L - 1 + R)),
            ],
        })

    def test_vectorized_successors_match_scalar_equations_at_every_queue_boundary(self):
        for L, R in ((1, 0), (1, 2), (3, 0), (3, 2)):
            with self.subTest(L=L, R=R):
                problem = self.make_problem(L, R)
                anchor = problem.anchor
                state = replace(
                    anchor.state,
                    external=tuple((i - 4) * 0.0001 for i in range(9)),
                    construction=tuple(0.02 * (i + 1) for i in range(L - 1)),
                    ramp=tuple(0.03 * (i + 1) for i in range(R)),
                )
                decision = replace(anchor.decision, j=0.081, q=0.88, inventory=0.42, c=0.26)
                second = replace(state, inventory_lag=0.18, mature_capacity=1.14)
                second_decision = replace(decision, j=0.045, q=0.91, inventory=0.33)
                states = np.stack([problem.state_to_array(state), problem.state_to_array(second)])
                decisions = np.stack([pack_decision(decision), pack_decision(second_decision)])
                successor_rows = problem.successors(states, decisions)
                branches = problem.kernel.branches
                self.assertEqual(len(branches), 512)
                self.assertEqual(successor_rows.shape, (2, len(branches), L + R + 12))
                self.assertEqual(decisions.shape[1], 7 + L + R)
                for i, (si, di) in enumerate(((state, decision), (second, second_decision))):
                    expected = np.stack([
                        problem.state_to_array(advance_state(si, di, problem.params, problem.kernel, branch))
                        for branch in branches
                    ])
                    np.testing.assert_allclose(successor_rows[i], expected, rtol=1e-14, atol=1e-15)
                    first = problem.array_to_state(successor_rows[i, 0])
                    completion = si.construction[0] if L > 1 else di.j
                    if L > 1:
                        self.assertEqual(first.construction, si.construction[1:] + (di.j,))
                    else:
                        self.assertEqual(first.construction, ())
                    if R:
                        self.assertEqual(first.ramp[0], completion)
                        self.assertAlmostEqual(
                            first.mature_capacity,
                            (1 - problem.params.delta) * (si.mature_capacity + si.ramp[-1]),
                        )
                    else:
                        self.assertEqual(first.ramp, ())
                        self.assertAlmostEqual(
                            first.mature_capacity,
                            (1 - problem.params.delta) * si.mature_capacity + completion,
                        )
                selected = np.array([17, len(branches) - 1])
                np.testing.assert_allclose(
                    problem.successors(states, decisions, innovation_indices=selected),
                    successor_rows[np.arange(2), selected],
                    rtol=1e-14, atol=1e-15,
                )

    def test_binding_capacity_and_exact_zero_inventory_and_investment_at_risky_node(self):
        # Construct an isolated conditional-node stress test without changing the benchmark.
        # The hypothetical continuation has positive price variance and negative construction
        # value. It is not claimed to be a stochastic equilibrium.
        high_cost = 2 * make_deterministic_anchor(3, 2).params.pJ0
        problem = self.make_problem(3, 2, h=0.5, pJ0=high_cost)
        anchor = problem.anchor
        state = replace(anchor.state, inventory_lag=0.0)
        row = problem.state_to_array(state)

        def continuation(successor):
            future_spot = 2.0 + math.copysign(0.025, successor.external[0])
            return replace(
                anchor.decision,
                q=0.8 * effective_capacity(successor, problem.params),
                spot=future_spot,
                w_b=(-0.1, -0.2),
            )

        moments = continuation_moments(state, anchor.decision, continuation, problem)
        self.assertGreater(moments["price_variance"][0], 0)
        packed = problem.current_update(row[None, :], moments)[0]
        decision = problem.decision(row, packed)
        decision = recover_node_value(decision, state, problem.params, anchor.decision.producer_value)
        self.assertEqual(decision.inventory, 0.0)
        self.assertEqual(decision.j, 0.0)
        self.assertAlmostEqual(decision.q, effective_capacity(state, problem.params), places=13)
        self.assertLess(decision.w_b[-1], 0)

        def policy(point):
            return decision if point.time == state.time else continuation(point)

        result = evaluate_conditions(state, policy, problem.params, problem.kernel)
        self.assertLess(result["max_equality_or_kkt_residual"], 1e-9)
        for key in ("E09_capacity_upper", "E16_investment", "E19_inventory_original"):
            conditions = result["original_complementarity"][key]
            self.assertAlmostEqual(conditions["product"], 0.0, places=11, msg=key)
            self.assertGreater(conditions["dual_gap"], 1e-3, msg=key)
        self.assertAlmostEqual(
            result["conditional_moments"]["price_variance"], moments["price_variance"][0],
            places=14,
        )
        self.assertNotEqual(decision.futures, moments["mean_price"][0])

    def test_both_sides_of_the_quantity_constraint_switches(self):
        problem = self.make_problem(3, 2)
        anchor = problem.anchor
        params = anchor.params
        state = replace(anchor.state, inventory_lag=0.0)
        row = problem.state_to_array(state)
        env = primitives(state, params)
        capacity = effective_capacity(state, params)
        net_goods = capacity + env["N"] - state.commitment_lag
        spot_at_zero_stock = params.P_star * (env["A_s"] / net_goods) ** (1 / params.eta_s)
        moments = continuation_moments(state, anchor.decision, anchor.policy, problem)

        holding_cost_switch = env["b"] * params.alpha_I * anchor.decision.spot \
            - spot_at_zero_stock + params.xi / params.I0
        project_cost_switch = env["b"] * anchor.decision.w_b[-1] \
            - params.omega_B * sum(state.construction)
        domestic_cost_switch = spot_at_zero_stock - env["FX"] * params.m_usd \
            - params.alpha - params.kappa * (capacity - state.q_lag) \
            + env["b"] * params.kappa * (anchor.decision.q - capacity)

        def current(**parameters):
            test_problem = self.make_problem(3, 2, **parameters)
            result = test_problem.current_update(row[None, :], moments)
            self.assertLess(
                np.max(np.abs(test_problem.residual(row[None, :], result, moments))),
                1e-9,
            )
            return test_problem.decision(row, result[0])

        step = 1e-5
        self.assertEqual(current(h=holding_cost_switch + step).inventory, 0.0)
        self.assertGreater(current(h=holding_cost_switch - step).inventory, 0.0)
        self.assertEqual(current(h=0.5, pJ0=project_cost_switch + step).j, 0.0)
        self.assertGreater(current(h=0.5, pJ0=project_cost_switch - step).j, 0.0)
        self.assertAlmostEqual(current(h=0.5, m_domestic=domestic_cost_switch - step).q, capacity)
        self.assertLess(current(h=0.5, m_domestic=domestic_cost_switch + step).q, capacity)

    def test_zero_price_variance_has_exact_futures_mean_and_nonunique_clearing_positions(self):
        problem = self.make_problem(3, 2)
        anchor = problem.anchor
        row = problem.state_to_array(anchor.state)
        moments = continuation_moments(anchor.state, anchor.decision, anchor.policy, problem)
        self.assertEqual(moments["price_variance"][0], 0.0)
        packed = problem.current_update(row[None, :], moments)[0]
        decision = problem.decision(row, packed, producer_value=anchor.decision.producer_value)
        self.assertEqual(decision.futures, moments["mean_price"][0])
        expected_positions = risk_share_positions(
            decision.inventory, decision.c, problem.params,
            primitives(anchor.state, problem.params)["a_f"],
        )
        np.testing.assert_allclose(
            (decision.h_inventory, decision.h_procurement, decision.h_financial),
            expected_positions, rtol=1e-13, atol=1e-13,
        )
        alternative = replace(
            decision, h_inventory=decision.h_inventory + 0.37,
            h_procurement=decision.h_procurement - 0.37,
        )
        evaluation = evaluate_conditions(
            anchor.state, lambda s: alternative if s.time == 0 else anchor.decision,
            problem.params, anchor.kernel,
        )
        self.assertLess(evaluation["max_equality_or_kkt_residual"], 1e-9)
        self.assertFalse(evaluation["diagnostics"]["zero_variance_positions_unique"])

    def test_polynomial_moments_equal_explicit_512_branch_averages(self):
        problem = self.make_problem(3, 2)
        rng = np.random.default_rng(27619)
        states = np.stack([
            problem.center + problem.radius * rng.uniform(-0.4, 0.4, problem.state_dimension)
            for _ in range(3)
        ])
        for degree in (1, 2, 3, 4):
            with self.subTest(degree=degree):
                powers = basis_powers(problem.state_dimension, degree)
                coef = rng.normal(0, 0.001, (len(powers), problem.policy_dimension))
                coef[0] = problem.anchor_policy
                coef[0, 0] = -0.025
                policy = PolynomialPolicy(problem, powers, coef)
                current = policy.predict(states)
                actual = policy.moments(states, current)
                next_policy = policy.predict(problem.successors(states, current))
                means = next_policy.mean(axis=1)
                variances = ((next_policy[:, :, 5] - means[:, None, 5]) ** 2).mean(axis=1)
                self.assertTrue(np.all(variances > 0))
                expected = {
                    "mean_Q": means[:, 0],
                    "mean_price": means[:, 5],
                    "price_variance": variances,
                    "mean_W_M": means[:, 7],
                    "mean_W_B": means[:, 8:10],
                    "mean_W_Z": means[:, 10:],
                }
                for key, target in expected.items():
                    np.testing.assert_allclose(
                        actual[key], target, rtol=1e-11,
                        atol=1e-16 if key == "price_variance" else 1e-12,
                        err_msg=key,
                    )


if __name__ == "__main__":
    unittest.main()
