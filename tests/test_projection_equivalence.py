"""Independent checks of projection elimination against the original equations.

No policy fit is performed. Non-equilibrium candidates deliberately retain
economic residuals, so these tests verify algebra and timing, not convergence.
"""

from dataclasses import replace
import unittest

import numpy as np

from model.dsge.local_projection import LocalProjection
from model.dsge.parameters import Parameters
from model.dsge.shocks import kernel
from model.dsge.state import next_state


class ProjectionEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(20261126)
        cls.cases = []
        for lag, ramp in ((1, ()), (1, (.45, .80)), (3, ()), (3, (.45, .80))):
            parameters = replace(Parameters(), construction_lag=lag, ramp_weights=ramp)
            projection = LocalProjection(parameters)
            coefficients = rng.normal(0., 3e-5, (projection.nu, projection.nbasis)).ravel()
            nodes = rng.normal(0., .05, (3, projection.ns))
            states = projection.states_at(coefficients, nodes)
            controls = projection.controls(coefficients, states)
            cases = []
            for row in states:
                state = projection.unpack_state(row)
                choice = projection.choice(coefficients, state)
                audit = projection.audit(coefficients, state)
                cases.append((state, choice, audit))
            cls.cases.append((projection, coefficients, nodes, states, controls, cases))

    def test_reduced_conditions_equal_original_conditions_off_equilibrium(self):
        """Every retained equality has the original evaluator as its oracle."""
        for projection, coefficients, nodes, _, _, cases in self.cases:
            p = projection.p
            reduced = projection.equations(coefficients, nodes, scaled=False).reshape(
                len(nodes), projection.nu)
            for row, (_, choice, audit) in enumerate(cases):
                with self.subTest(L=p.construction_lag, R=p.ramp_length, point=row):
                    self.assertFalse(audit["domain_errors"])
                    self.assertGreater(audit["max_abs_residual"], 1e-7)
                    residual = audit["residuals"]
                    diagnostic = audit["diagnostics"]
                    em = np.asarray(diagnostic["sdf_means"])
                    # The projection uses the price-index power, and clears net
                    # bonds instead of keeping the F budget as a fourth equality.
                    # Its two normalized pricing differences are exactly
                    # R_j/E[M_j] - R_I/E[M_I] on the slack collateral branch.
                    originals = [
                        (1 + residual["E37.CES_price_index"]) ** (1 - p.epsilon) - 1,
                        residual["E34.labor_supply"],
                        -residual["E33.budget_F"] * choice.gross_rate,
                        residual["E09.production_foc"],
                        diagnostic["investment_gap"],
                        residual["E23.procurement_foc"],
                        *[residual[f"E35.bond_euler_WID[{j}]"] for j in range(3)],
                        residual["E35.bond_euler_F"],
                        residual["E22.futures_I"],
                        residual["E22.futures_D"] / em[2]
                        - residual["E22.futures_I"] / em[1],
                        residual["E22.futures_F_subgradient"] / em[3]
                        - residual["E22.futures_I"] / em[1],
                        residual["E14.mature_envelope"],
                        *[residual[f"E15.construction_envelope_{j}"]
                          for j in range(p.construction_lag - 1)],
                        *[residual[f"E14.ramp_envelope_{j}"]
                          for j in range(p.ramp_length)],
                    ]
                    np.testing.assert_allclose(reduced[row], originals, atol=1e-12, rtol=1e-12)

    def test_all_branch_transitions_match_original_timing(self):
        """Construction and ramp boundaries use the original state transition."""
        for projection, _, _, states, controls, cases in self.cases:
            generated = projection.successors(states, controls)
            for row, (state, choice, _) in enumerate(cases):
                for branch, (_, innovation) in enumerate(kernel(projection.p)):
                    with self.subTest(L=projection.p.construction_lag,
                                      R=projection.p.ramp_length, point=row, branch=branch):
                        original = next_state(state, choice, innovation, projection.p)
                        np.testing.assert_allclose(
                            generated[row, branch], projection.pack_state(original),
                            atol=1e-13, rtol=1e-13)

    def test_eliminated_accounts_and_market_conditions_hold_off_equilibrium(self):
        """Recovery closes only the advertised identities, even at a bad policy."""
        names = (
            "E03.downstream_technology", "E04.flexible_foc", "E25.LC_market",
            "E26.futures_market", "E33.budget_W", "E33.budget_I", "E33.budget_D",
            "E34.downstream_labor", "E35.bond_market", "E36.non_LC_technology",
            "E36.non_LC_labor", "E37.CES_demand_0", "E37.CES_demand_B",
            "E38.labor_market",
        )
        for projection, _, _, _, _, cases in self.cases:
            for row, (_, _, audit) in enumerate(cases):
                with self.subTest(L=projection.p.construction_lag,
                                  R=projection.p.ramp_length, point=row):
                    self.assertFalse(audit["domain_errors"])
                    values = [audit["residuals"][name] for name in names]
                    np.testing.assert_allclose(values, 0., atol=1e-12, rtol=0.)
                    # F budget, Euler equations and final-resource balance still
                    # require the retained equilibrium conditions to be solved.
                    self.assertFalse(audit["passed"])


if __name__ == "__main__":
    unittest.main()
