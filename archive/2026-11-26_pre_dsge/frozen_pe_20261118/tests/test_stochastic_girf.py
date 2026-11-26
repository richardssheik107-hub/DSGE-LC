"""Verify sign conditioning, inherited state timing and stratified integration."""
from pathlib import Path
import unittest

import numpy as np

from model.full_conditions import EXTERNAL_NAMES
from model.stochastic_equilibrium import Problem, load_config
from scripts.run_stochastic_girf import SHOCKS, sign_pairs, summarize_section


class ConditionalGirfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = Path(__file__).resolve().parents[1]/"configs/stochastic_refined.json"
        cls.problem = Problem(load_config(config))

    def test_all_sign_pairs_differ_only_in_target_state(self):
        problem = self.problem
        state = np.broadcast_to(problem.center, (256, problem.state_dimension))
        pre_shock_choice = np.broadcast_to(problem.anchor_policy, (256, problem.policy_dimension))
        for shock in SHOCKS:
            plus, minus = sign_pairs(problem, shock)
            self.assertEqual(len(set(plus) | set(minus)), 512)
            diff = (problem.successors(state, pre_shock_choice, plus) -
                    problem.successors(state, pre_shock_choice, minus))
            expected = np.zeros_like(diff)
            index = EXTERNAL_NAMES.index(shock)
            expected[:, index] = 2*problem.amplitudes[index]
            np.testing.assert_array_equal(diff, expected)

    def test_mc_se_conditions_on_exact_first_period_strata(self):
        plus = np.zeros((2, 256, 2, 1))
        plus[:, :, 0, 0] = 4
        plus[0, :, 1, 0] = 2
        plus[1, :, 1, 0] = 6
        negative = np.zeros_like(plus)
        mean_plus, mean_minus, response, error = summarize_section(plus, negative)
        np.testing.assert_array_equal(response, (mean_plus-mean_minus)/2)
        np.testing.assert_array_equal(response.ravel(), [2, 2])
        np.testing.assert_array_equal(error.ravel(), [0, 1/16])


if __name__ == "__main__":
    unittest.main()
