"""Check audit identities without depending on ignored run artifacts."""
from pathlib import Path
import unittest

import numpy as np

from model.full_conditions import advance_state, evaluate_conditions
from model.stochastic_domain_audit import predecessor_screens
from model.stochastic_equilibrium import Problem, PolynomialPolicy, basis_powers, load_config
from model.stochastic_path_audit import FrozenMoments, period_audit


class FrozenPolicyAuditTests(unittest.TestCase):
    def setUp(self):
        config = Path(__file__).resolve().parents[1]/"configs/stochastic_refined.json"
        self.problem = Problem(load_config(config))
        basis = basis_powers(self.problem.state_dimension, 4)
        coefficients = np.zeros((len(basis), self.problem.policy_dimension))
        coefficients[0] = self.problem.anchor_policy
        coefficients[0, 0] = 0.0  # exact binding capacity
        coefficients[1, 5] = 0.01  # nonzero conditional price variance
        coefficients[10, 6] = -0.001  # intentionally miss the futures equation
        coefficients[19, 7] = -1e-4
        self.policy = PolynomialPolicy(self.problem, basis, coefficients)

    def test_all_period_residuals_match_explicit_originals(self):
        p, frozen = self.problem, self.policy
        row = p.center.copy()
        row[0] += 0.1*p.radius[0]
        row[9] += 0.02*p.radius[9]
        current = frozen.predict(row[None])
        fast = period_audit(p, frozen, FrozenMoments(frozen), row[None], current)

        def decision(state):
            s = p.state_to_array(state)
            return p.decision(s, frozen.predict(s))

        scalar = evaluate_conditions(p.array_to_state(row), decision, p.params, p.kernel)
        self.assertGreater(scalar["conditional_moments"]["price_variance"], 0)
        for name, residual in scalar["original_equalities"].items():
            if name != "producer_Bellman":
                self.assertAlmostEqual(fast.raw[name][0], residual, places=12)
        for name, residual in scalar["original_complementarity"].items():
            for field in ("primal_violation", "dual_violation", "product"):
                self.assertAlmostEqual(fast.raw[f"{name}_{field}"][0], residual[field], places=12)

    def test_necessary_predecessor_screen_keeps_known_successors(self):
        p = self.problem
        start = p.array_to_state(p.center)
        decision = p.decision(p.center, self.policy.predict(p.center))
        for branch in p.kernel.branches[::19]:
            successor = advance_state(start, decision, p.params, p.kernel, branch)
            row = p.state_to_array(successor)
            checks = predecessor_screens(p, self.policy, row)
            self.assertTrue(all(x["passes"] for x in checks.values()))
        row[9] += 0.1
        checks = predecessor_screens(p, self.policy, row)
        self.assertFalse(checks["Q_lag_as_previous_capacity_plus_Q_offset_given_queues"]["passes"])


if __name__ == "__main__":
    unittest.main()
