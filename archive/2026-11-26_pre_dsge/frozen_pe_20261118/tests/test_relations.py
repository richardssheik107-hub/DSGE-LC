"""Local identities and timing only. All numbers are synthetic, not calibration."""
import math
import unittest


def derivative(f, x):
    step = 1e-5 * max(1.0, abs(x))
    return (f(x + step) - f(x - step)) / (2 * step)


def advance(B, Z, mature, start, delta):
    """Independent test implementation of E10--E12, including L=1/R=0."""
    completed = B[0] if B else start
    next_B = B[1:] + [start] if B else []
    if Z:
        next_mature = (1 - delta) * (mature + Z[-1])
        next_Z = [completed] + [(1 - delta) * z for z in Z[:-1]]
    else:
        next_mature = (1 - delta) * mature + completed
        next_Z = []
    return next_B, next_Z, next_mature


class RelationChecks(unittest.TestCase):
    def assertClose(self, x, y):
        self.assertAlmostEqual(x, y, delta=2e-7 * max(1.0, abs(y)))

    def test_production_marginal_cost(self):
        for nu in (0.5, 1.0, 2.5):
            m, alpha, k, q, lag, kappa = 2.0, 3.0, 12.0, 7.0, 5.0, 0.2
            f = lambda x: m*x + alpha/(nu+1)*x**(nu+1)/k**nu + kappa/2*(x-lag)**2
            self.assertClose(derivative(f, q), m+alpha*(q/k)**nu+kappa*(q-lag))

    def test_capacity_marginal_service(self):
        for nu in (0.5, 1.0, 3.0):
            alpha, q, k = 2.4, 7.0, 12.0
            f = lambda x: alpha/(nu+1)*q**(nu+1)/x**nu
            self.assertClose(-derivative(f, k), alpha*nu/(nu+1)*(q/k)**(nu+1))

    def test_old_quadratic_is_special_case(self):
        alpha, q, k = 2.3, 5.0, 8.0
        self.assertClose(alpha/(1+1)*q**(1+1)/k**1, alpha*q*q/(2*k))

    def test_future_adjustment_sign(self):
        kappa, q, future = 0.7, 6.0, 9.0
        self.assertClose(derivative(lambda x: kappa/2*(future-x)**2, q), -kappa*(future-q))

    def test_investment_cross_derivatives(self):
        p, chi, omega, j, load = 4.0, 0.3, 0.05, 2.0, 8.0
        f = lambda x, b: p*x+chi*x*x/2+omega*x*b
        self.assertClose(derivative(lambda x: f(x, load), j), p+chi*j+omega*load)
        self.assertClose(derivative(lambda b: f(j, b), load), omega*j)

    def test_constant_elasticity_benefit(self):
        for eta in (0.11, 0.7, 1.0, 2.0):
            ref, A, p, x = 1.0, 3.0, 2.0, 4.0
            exponent = 1-1/eta
            if eta == 1:
                B = lambda u: p*A*math.log(u/ref)
            else:
                B = lambda u: p*A**(1/eta)*(u**exponent-ref**exponent)/exponent
            self.assertClose(derivative(B, x), p*(x/A)**(-1/eta))

    def test_total_demand_elasticity(self):
        A, eta, ref, price, committed = 7.0, 0.4, 2.0, 3.0, 4.0
        ds = A*(price/ref)**(-eta)
        demand = lambda p: A*(p/ref)**(-eta)+committed
        self.assertClose(derivative(demand, price)*price/demand(price), -eta*ds/(ds+committed))

    def test_offset_inventory_service(self):
        h, xi, i0, inv = 0.3, 1.7, 2.0, 4.0
        G = lambda i: h*i-xi*math.log1p(i/i0)
        self.assertClose(derivative(G, inv), h-xi/(inv+i0))
        self.assertEqual(G(0), 0)

    def test_hedge_first_order_conditions(self):
        mu, f, var, alpha, inv, c = 7.0, 6.8, 0.9, 0.98, 4.0, 3.0
        aI, aD, af = 0.3, 0.4, 0.5
        d = mu-f
        hI, hD, hf = -alpha*inv+d/(aI*var), c+d/(aD*var), d/(af*var)
        for residual in (d-aI*var*(alpha*inv+hI), d-aD*var*(hD-c), d-af*var*hf):
            self.assertClose(residual, 0)

    def test_futures_clearing_both_signs(self):
        mu, var, alpha, aI, aD, af = 7.0, 0.9, 0.98, 0.3, 0.4, 0.5
        tau = 1/aI+1/aD+1/af
        for inv, c in ((4.0, 3.0), (2.0, 4.0), (0.0, 0.0)):
            f = mu-var/tau*(alpha*inv-c)
            d = mu-f
            self.assertClose(-alpha*inv+d/(aI*var)+c+d/(aD*var)+d/(af*var), 0)
            self.assertClose(mu-f, var*(alpha*inv-c)/tau)

    def test_inventory_foc_reduction(self):
        beta, alpha, mu, f, var, a, inv = 0.99, 0.98, 7.0, 6.9, 0.9, 0.3, 4.0
        hp = -alpha*inv+(mu-f)/(a*var)
        P, gp = 6.0, 0.2
        raw = -P-gp+beta*(alpha*mu-a*var*alpha*(alpha*inv+hp))
        self.assertClose(raw, -P-gp+beta*alpha*f)

    def test_purchase_foc_reduction(self):
        mu, f, var, a, c, benefit_prime = 7.0, 6.9, 0.9, 0.4, 3.0, 6.9
        hd = c+(mu-f)/(a*var)
        raw = benefit_prime-mu+a*var*(hd-c)
        self.assertClose(raw, benefit_prime-f)

    def test_queue_first_available_date(self):
        for lead in (1, 2, 5):
            B, Z, K = [0.0]*(lead-1), [0.0, 0.0], 0.0
            for t in range(lead+3):
                effective = K+0.4*Z[0]+0.8*Z[1]
                if t < lead:
                    self.assertEqual(effective, 0)
                if t == lead:
                    self.assertClose(effective, 0.4)
                B,Z,K = advance(B,Z,K,float(t==0),0.0)

    def test_ramp_conservation_no_double_count(self):
        B,Z,K = [0.0,0.0], [0.0,0.0,0.0], 2.0
        for t in range(12):
            start = float(t < 4)
            old_total = sum(B)+sum(Z)+K
            B,Z,K = advance(B,Z,K,start,0.0)
            self.assertClose(sum(B)+sum(Z)+K, old_total+start)

    def test_retirement_only_after_first_operation(self):
        B,Z,K = [2.0,3.0], [4.0,5.0], 6.0
        old_total, operational, start, delta = sum(B)+sum(Z)+K, sum(Z)+K, 1.0, 0.1
        B,Z,K = advance(B,Z,K,start,delta)
        self.assertClose(sum(B)+sum(Z)+K, old_total+start-delta*operational)

    def test_no_ramp_and_one_period_construction(self):
        B,Z,K = advance([],[],3.0,2.0,0.1)
        self.assertEqual(B,[])
        self.assertEqual(Z,[])
        self.assertClose(K,4.7)

    def test_state_dimension(self):
        for nz in (2,5):
            for lead in (1,3):
                for ramp in (0,2):
                    pieces = [0]*nz+[0]*3+[0]+[0]*(lead-1)+[0]*ramp
                    self.assertEqual(len(pieces), nz+lead+ramp+3)


if __name__ == '__main__':
    unittest.main()
