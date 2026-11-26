"""Checks for shock scale interpretation and constraint activation."""

from dataclasses import replace
from itertools import product
import unittest
import numpy as np

from model.dsge import solve_anchor
from model.dsge.shock_audit import (
    collateral_activation, conditional_exogenous_path, primitive_incidence,
    shock_scale_table,
)


class ShockAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.anchor = solve_anchor()
        cls.p = cls.anchor["configured_parameters"]
        cls.s, cls.g = cls.anchor["state"], cls.anchor["choice"]

    def test_current_anchor_has_three_primitive_entries_not_four_active_channels(self):
        evidence = primitive_incidence(self.s, self.g, self.p)
        self.assertEqual(evidence["primitive_entry_rank_at_candidate"], 3)
        self.assertLess(evidence["max_derivative_error"], 1e-9)
        self.assertTrue(collateral_activation(self.s, self.g, self.p)["zero_position_requires_no_collateral"])

    def test_nonzero_position_tightening_hits_actual_constraint(self):
        g = replace(self.g, positions=np.array([.1, .1, -.2]))
        evidence = collateral_activation(self.s, g, self.p)
        shift = evidence["fixed_choice_log_tightening_to_binding"]
        self.assertGreater(shift, 0)
        z = self.s.z.copy()
        z[3] += shift
        binding = collateral_activation(replace(self.s, z=z), g, self.p)
        self.assertAlmostEqual(binding["collateral_slack"], 0, places=13)
        self.assertEqual(primitive_incidence(self.s, g, self.p)["primitive_entry_rank_at_candidate"], 4)

    def test_future_randomness_is_integrated_in_level_expectation(self):
        for k in (1, 2, 3):
            row = conditional_exogenous_path(self.p, k, horizon=3)["rows"][3]
            rho, sigma = self.p.shock_persistence[k], self.p.shock_scales[k]
            base = (self.p.omega_bar, self.p.m_bar, self.p.pj_bar, self.p.collateral_bar)[k]
            values = []
            for future in product((-1, 1), repeat=3):
                z = sigma
                for sign in future:
                    z = rho * z + sigma * sign
                values.append(base * np.exp(z))
            self.assertAlmostEqual(row["primitive_conditional_mean_plus"], np.mean(values), places=14)
            self.assertGreater(np.mean(values), base * np.exp(rho**3 * sigma))

    def test_logistic_share_and_conditional_baseline_units_are_distinct(self):
        table = shock_scale_table(self.p)
        self.assertTrue(.22 < table[0]["direct_mapping_change_percentage_points"] < .24)
        self.assertNotAlmostEqual(table[1]["direct_mapping_change_percent_from_zero"], 1., places=4)
        impact = conditional_exogenous_path(self.p, 1, horizon=0)["rows"][0]
        self.assertAlmostEqual(impact["relative_difference_percent"], 100 * np.tanh(.01), places=12)
        with self.assertRaises(ValueError):
            conditional_exogenous_path(self.p, 0, horizon=17)


if __name__ == "__main__":
    unittest.main()
