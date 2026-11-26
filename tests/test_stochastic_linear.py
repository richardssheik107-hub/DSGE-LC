"""Economic checks for the locally stochastic RE and portfolio calculation."""
import unittest
from dataclasses import replace
import numpy as np
from model.dsge import Parameters
from model.dsge.local_projection import LocalProjection
from model.dsge.linear_re import (solve_linear,select_portfolio,portfolio_conditions,
                                  futures_tangent_audit,linear_irfs)


class StochasticLinearTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=LocalProjection(replace(Parameters(),shock_scales=(.001,)*4))
        cls.selected=select_portfolio(cls.model)

    def test_stable_subspace_preserves_three_neutral_wealth_modes(self):
        sol=self.selected['solution']
        self.assertEqual(sol['stable_count'],self.model.ns)
        self.assertEqual(sol['generalized_indeterminate_pairs'],0)
        self.assertLess(sol['linear_equation_max_residual'],1e-10)
        eig=sol['closed_eigenvalues']
        self.assertEqual(np.count_nonzero(abs(eig-1)<1e-7),3)
        self.assertLessEqual(max(abs(eig)),1+1e-7)

    def test_original_three_futures_conditions_have_rank_one_at_zero_risk(self):
        audit=futures_tangent_audit(self.model)
        self.assertEqual(np.shape(audit['matrix']),(3,8))
        self.assertEqual(audit['rank'],1)
        self.assertEqual(audit['holdings_derivative_max'],0)
        np.testing.assert_allclose(audit['matrix'][0],audit['matrix'][1],atol=1e-14)
        np.testing.assert_allclose(audit['matrix'][0],audit['matrix'][2],atol=1e-14)

    def test_leading_portfolio_is_selected_by_risk_not_arbitrary_zero_holdings(self):
        arbitrary=portfolio_conditions(self.model,solve_linear(self.model,(0.,0.)))
        selected=self.selected
        self.assertGreater(max(abs(arbitrary['differences'])),1e-10)
        self.assertLess(selected['portfolio_scaled_residual'],1e-7)
        self.assertGreater(selected['pricing']['conditional_spot_variance'],0)
        self.assertAlmostEqual(sum(selected['solution']['holdings']),0,places=14)
        self.assertGreater(max(abs(selected['solution']['holdings'])),.01)

    def test_linear_conditional_price_expectation_and_slack_margin_irf(self):
        rows=linear_irfs(self.model,self.selected['solution'],12)['rows']
        self.assertLess(max(abs(row['first_order_premium_change']) for row in rows),1e-11)
        for row in rows:
            if row['shock']=='z_kappa':
                self.assertTrue(all(abs(v)<1e-12 for k,v in row.items() if k.endswith('_change')))
        self.assertTrue(any(abs(row['P_change'])>1e-8 for row in rows if row['shock']=='z_m'))
        # A new start at t=0 reaches the first ramp stage at t=L, never sooner.
        for shock in self.model.p.shock_names[:3]:
            selected=[row for row in rows if row['shock']==shock]
            for row in selected[:self.model.p.construction_lag]:
                self.assertAlmostEqual(row['K_effective_change'],0,places=12)
            self.assertGreater(abs(selected[self.model.p.construction_lag]['K_effective_change']),1e-8)

    def test_original_nonlinear_residual_scales_quadratically_not_as_exact_solution(self):
        errors=[]
        for sigma in (.0005,.001):
            m=LocalProjection(replace(Parameters(),shock_scales=(sigma,)*4))
            sel=select_portfolio(m);coef=sel['coefficients'].ravel()
            center=m.moving_center(sel['coefficients'])
            # A +1 cost innovation, holding inherited predetermined quantities fixed.
            state=center.copy();state[1]=sigma
            audit=m.audit(coef,m.unpack_state(state))
            self.assertFalse(audit['passed'])
            self.assertFalse(audit['domain_errors'])
            errors.append(audit['max_abs_residual'])
        self.assertGreater(errors[1]/errors[0],3.5)
        self.assertLess(errors[1]/errors[0],4.5)

    def test_queue_boundaries_have_consistent_local_re_solutions(self):
        for lag,ramp in ((1,()),(1,(.45,.8)),(3,()),(3,(.45,.8))):
            with self.subTest(lag=lag,ramp=ramp):
                m=LocalProjection(replace(Parameters(),construction_lag=lag,
                                          ramp_weights=ramp,shock_scales=(.001,)*4))
                selected=select_portfolio(m)
                self.assertLess(selected['solution']['linear_equation_max_residual'],1e-10)
                self.assertLess(selected['portfolio_scaled_residual'],1e-7)
                self.assertEqual(selected['solution']['stable_count'],m.ns)


if __name__=='__main__':unittest.main()
