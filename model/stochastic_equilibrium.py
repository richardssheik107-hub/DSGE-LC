"""Nonlinear projection of the E04/E09/E14–16/E23–25/E27 policy system."""

from functools import cached_property, lru_cache
from itertools import combinations_with_replacement, product
import json
from math import comb

import numpy as np
from scipy.linalg import ordqz, schur
from scipy.optimize import brentq

from model.full_conditions import (
    Decision, DomainError, Parameters, State, diagonal_matrix,
    independent_rademacher_kernel, make_deterministic_anchor, risk_share_positions,
)


def load_config(path):
    with open(path, encoding="utf-8") as source:
        return json.load(source)


class Problem:
    def __init__(self, config):
        self.config = config
        self.params = Parameters(**{**config["parameters"], "g": tuple(config["parameters"]["g"])})
        p = self.params
        p.validate()
        self.anchor = make_deterministic_anchor(p.L, p.R)
        self.state_dimension = 12 + p.L + p.R
        self.policy_dimension = 7 + p.L + p.R
        self.center = self.state_to_array(self.anchor.state)
        self.radius = np.asarray(config["domain_radius"], dtype=float)
        if self.radius.shape != self.center.shape or not np.all(self.radius > 0):
            raise ValueError("domain_radius must have one positive entry per state")
        if config["technology_path"] != {"type": "constant", "value": p.tau_constant}:
            raise ValueError("This stationary projector requires a declared constant technology path")
        if config["shock_distribution"] != "independent_rademacher_9":
            raise ValueError("The polynomial moment integrator requires independent Rademacher shocks")
        self.persistence = np.asarray(config["transition_diagonal"], dtype=float)
        self.amplitudes = np.asarray(config["shock_amplitudes"], dtype=float)
        self.kernel = independent_rademacher_kernel(
            diagonal_matrix(self.persistence.tolist()), diagonal_matrix(self.amplitudes.tolist()))
        self.innovations = np.asarray([b.innovation for b in self.kernel.branches])
        s = config["scales"]
        self.policy_scale = np.array([s["quantity"]] * 5 + [s["price"]] * 2
                                     + [s["value"]] * (p.L + p.R))
        self.anchor_policy = self.pack(self.anchor.decision)

    @property
    def ramp_start(self):
        return 12 + self.params.L

    @property
    def ramp_values_start(self):
        return 7 + self.params.L

    @staticmethod
    def state_to_array(state):
        return np.asarray((*state.external, state.q_lag, state.inventory_lag,
                           state.commitment_lag, state.mature_capacity,
                           *state.construction, *state.ramp), dtype=float)

    def array_to_state(self, row, time=0):
        return State(tuple(row[:9]), *row[9:13], tuple(row[13:self.ramp_start]),
                     tuple(row[self.ramp_start:]), time)

    @staticmethod
    def pack(d):
        return np.array([d.q, d.j, d.d_s, d.c, d.inventory, d.spot, d.futures,
                         d.w_m, *d.w_b, *d.w_z])

    def decision(self, row, packed_policy_row, producer_value=0.0):
        u = packed_policy_row
        z = self.ramp_values_start
        a_f = self.params.af0 * np.exp(self.params.gamma_zeta * row[3] + row[8])
        return Decision(*u[:7], producer_value, u[7], tuple(u[z:]), tuple(u[8:z]),
                        *risk_share_positions(u[4], u[3], self.params, a_f))

    def capacity(self, states):
        return states[..., 12] + states[..., self.ramp_start:] @ self.params.g

    def environment(self, states):
        p = self.params
        g, e, r, zeta, za, zm, zj, zn, zf = np.moveaxis(states[..., :9], -1, 0)
        fx = p.FX_bar * np.exp(e)
        a = p.D0 * np.exp(p.lambda_g*g + p.lambda_tau*p.tau_constant + za)
        net_imports = p.N0 + p.N_scale*zn
        capacity = self.capacity(states)
        denominator = 1 + p.i_bar + r
        if np.any(denominator <= 0) or np.any(capacity <= 0):
            raise DomainError("Nonpositive discount denominator or capacity")
        return dict(A=a, A_s=(1-p.omega)*a, A_c=p.omega*a, FX=fx,
                    m=np.exp(zm)*(p.m_domestic+fx*p.m_usd), p_j=p.pJ0*np.exp(zj),
                    N=net_imports, a_f=p.af0*np.exp(p.gamma_zeta*zeta+zf),
                    b=1/denominator, K_e=capacity,
                    margin=capacity+net_imports+p.alpha_I*states[..., 10]-states[..., 11])

    def successor_center(self, states, decisions):
        p = self.params
        nxt = np.empty_like(states)
        nxt[:, :9] = states[:, :9]*self.persistence
        nxt[:, 9:12] = decisions[:, [0, 4, 3]]
        completion = decisions[:, 1]
        if p.L > 1:
            completion = states[:, 13]
            nxt[:, 13:self.ramp_start-1] = states[:, 14:self.ramp_start]
            nxt[:, self.ramp_start-1] = decisions[:, 1]
        survival = 1-p.delta
        if p.R:
            nxt[:, 12] = survival*(states[:, 12]+states[:, -1])
            nxt[:, self.ramp_start] = completion
            nxt[:, self.ramp_start+1:] = survival*states[:, self.ramp_start:-1]
        else:
            nxt[:, 12] = survival*states[:, 12]+completion
        return nxt

    def successors(self, states, decisions, innovation_indices=None):
        nxt = self.successor_center(states, decisions)
        if innovation_indices is not None:
            nxt[:, :9] += self.innovations[innovation_indices]*self.amplitudes
            return nxt
        nodes = np.broadcast_to(nxt[:, None, :], (len(nxt), 512, self.state_dimension)).copy()
        nodes[:, :, :9] += self.innovations*self.amplitudes
        return nodes

    def residual(self, states, decisions, moments):
        """Natural maps in physical units, scaled by fixed benchmark units."""
        p = self.params
        env = self.environment(states)
        q, j, ds, c, inventory, spot, futures, wm = decisions[:, :8].T
        if (not np.isfinite(decisions).all() or np.any(spot <= 0) or np.any(futures <= 0)
                or np.any(q < 0) or np.any(inventory <= -p.I0)):
            raise DomainError("Policy trial outside the formula domain")
        wb, wz = decisions[:, 8:self.ramp_values_start], decisions[:, self.ramp_values_start:]
        mean_q, mean_p, var_p, mean_wm = (moments[k] for k in
            ("mean_Q", "mean_price", "price_variance", "mean_W_M"))
        mean_wb, mean_wz = moments["mean_W_B"], moments["mean_W_Z"]
        b, ke = env["b"], env["K_e"]
        xb = states[:, 13:self.ramp_start].sum(axis=1)
        production_gradient = (spot-env["m"]-p.alpha*(q/ke)**p.nu
                               -p.kappa*(q-states[:, 9])+b*p.kappa*(mean_q-q))
        service = p.alpha*p.nu/(p.nu+1)*(q/ke)**(p.nu+1)+np.maximum(production_gradient, 0)
        completion = mean_wz[:, 0] if p.R else mean_wm
        opening = mean_wb[:, -1] if p.L > 1 else completion
        investment_gap = env["p_j"]+p.chi*j+p.omega_B*xb-b*opening
        inventory_gap = spot+p.h-p.xi/(inventory+p.I0)-b*p.alpha_I*futures
        natural_step = self.config["scales"]["quantity"]/self.config["scales"]["price"]
        tolerance = 1/p.a_I+1/p.a_D+1/env["a_f"]
        residuals = [
            q-np.minimum(np.maximum(q+natural_step*production_gradient, 0), ke),
            np.minimum(j, natural_step*investment_gap),
            ds-env["A_s"]*(spot/p.P_star)**(-p.eta_s),
            c-env["A_c"]*(futures/p.P_star)**(-p.eta_c),
            np.minimum(inventory, natural_step*inventory_gap),
            q+env["N"]+p.alpha_I*states[:, 10]-ds-states[:, 11]-inventory,
            futures-mean_p+var_p/tolerance*(p.alpha_I*inventory-c),
            wm-service-b*(1-p.delta)*mean_wm,
        ]
        for h in range(p.L-1):
            after = completion if h == 0 else mean_wb[:, h-1]
            residuals.append(wb[:, h]+p.omega_B*j-b*after)
        for a in range(p.R):
            after = mean_wz[:, a+1] if a+1 < p.R else mean_wm
            residuals.append(wz[:, a]-p.g[a]*service-b*(1-p.delta)*after)
        scale = self.policy_scale.copy()
        scale[5] = self.config["scales"]["quantity"]
        return np.column_stack(residuals)/scale

    def current_update(self, states, moments):
        """Exact nested active-set current solve with frozen continuation moments."""
        p = self.params
        env = self.environment(states)
        results = []
        tiny = np.finfo(float).eps
        for i, s in enumerate(states):
            b, ke, m, a_s, a_c, a_f, net_imports, pj, margin = (
                env[k][i] for k in ("b", "K_e", "m", "A_s", "A_c", "a_f", "N", "p_j", "margin"))
            if margin <= 0:
                raise DomainError("Current resources cannot cover inherited commitments")
            mu, var, eq, em = (moments[k][i] for k in ("mean_price", "price_variance", "mean_Q", "mean_W_M"))
            eb, ez = moments["mean_W_B"][i], moments["mean_W_Z"][i]
            coefficient = var/(1/p.a_I+1/p.a_D+1/a_f)

            def commitment(futures):
                return a_c*(futures/p.P_star)**(-p.eta_c)

            def futures_at(inventory):
                if var == 0:
                    return mu
                return brentq(lambda f: f-mu+coefficient*(p.alpha_I*inventory-commitment(f)),
                              tiny, max(p.P_star, mu+coefficient*a_c), xtol=2e-14)

            def cost(q):
                return m+p.alpha*(q/ke)**p.nu+p.kappa*(q-s[9])-b*p.kappa*(eq-q)

            def market(spot):
                q = 0.0 if spot <= cost(0) else ke if spot >= cost(ke) else brentq(
                    lambda q: spot-cost(q), 0, ke, xtol=2e-14)
                ds = a_s*(spot/p.P_star)**(-p.eta_s)
                goods = q+net_imports+p.alpha_I*s[10]-s[11]-ds
                # On the goods clearing manifold, inventory equals these net goods.
                inventory = max(goods, 0.0)
                futures = futures_at(inventory)
                gap = spot+p.h-p.xi/(inventory+p.I0)-b*p.alpha_I*futures
                # If goods<0, no feasible I can clear. Otherwise the stock KKT
                # selects I=0 when its gap is positive, or solves its interior zero.
                balance = goods if goods <= 0 else min(goods, gap)
                return balance, q, ds, inventory, futures

            def clear_without_inventory(spot):
                _, q, ds, _, _ = market(spot)
                return q+net_imports+p.alpha_I*s[10]-s[11]-ds

            upper = max(1.0, mu)
            while market(upper)[0] <= 0:
                upper *= 2
                if not np.isfinite(upper):
                    raise DomainError("Could not bracket the current market root")
            no_stock_price = brentq(clear_without_inventory, tiny, upper, xtol=2e-14)
            f0 = futures_at(0.0)
            if no_stock_price+p.h-p.xi/p.I0-b*p.alpha_I*f0 >= 0:
                spot = no_stock_price
                _, q, ds, _, _ = market(spot)
                inventory, futures = 0.0, f0
            else:
                def inventory_gap(spot):
                    _, _, _, stock, future = market(spot)
                    return spot+p.h-p.xi/(stock+p.I0)-b*p.alpha_I*future
                spot = brentq(inventory_gap, no_stock_price, upper, xtol=2e-14)
                _, q, ds, inventory, futures = market(spot)
            if spot+p.h-b*p.alpha_I*futures <= 0 and p.xi > 0:
                raise DomainError("Inventory objective is unbounded")
            xb = s[13:self.ramp_start].sum()
            completion = ez[0] if p.R else em
            opening = eb[-1] if p.L > 1 else completion
            j = max((b*opening-pj-p.omega_B*xb)/p.chi, 0.0)
            service = p.alpha*p.nu/(p.nu+1)*(q/ke)**(p.nu+1)+max(spot-cost(q), 0.0)
            wb = [-p.omega_B*j+b*(eb[h-1] if h else completion) for h in range(p.L-1)]
            wz = [p.g[a]*service+b*(1-p.delta)*(ez[a+1] if a+1 < p.R else em) for a in range(p.R)]
            results.append([q, j, ds, commitment(futures), inventory, spot, futures,
                            service+b*(1-p.delta)*em, *wb, *wz])
        return np.asarray(results)


def basis_powers(dimension, degree):
    if degree not in (1, 2, 3, 4):
        raise ValueError("implemented projection orders are affine through quartic")
    rows = [np.zeros(dimension, dtype=int), *np.eye(dimension, dtype=int)]
    for order in range(2, degree+1):
        for factors in combinations_with_replacement(range(dimension), order):
            if order == 4 and sum(i >= 9 for i in factors) < 3:
                continue
            rows.append(np.bincount(factors, minlength=dimension))
    return np.asarray(rows)


@lru_cache(maxsize=16)
def basis_structure(dimension, degree):
    powers = basis_powers(dimension, degree)
    # Index dimension adds an always-one column for lower-order monomials.
    factors = np.full((len(powers), degree), dimension, dtype=int)
    lookup = {tuple(a): i for i, a in enumerate(powers)}
    shifts = []
    for i, a in enumerate(powers):
        values = np.repeat(np.arange(dimension), a)
        factors[i, :len(values)] = values
        eligible = np.flatnonzero(a[:9])
        for counts in product(*(range(a[j]+1) for j in eligible)):
            if not any(counts):
                continue
            exponent = a.copy()
            exponent[eligible] -= counts
            factor = np.prod([comb(a[j], k) for j, k in zip(eligible, counts)], dtype=float)
            mask = sum((1 << j) for j, k in zip(eligible, counts) if k % 2)
            shifts.append((lookup[tuple(exponent)], i, mask, factor,
                           tuple(j for j, k in zip(eligible, counts) for _ in range(k))))
    return powers, factors, shifts


class PolynomialPolicy:
    """Policy in physical units. Q is represented as effective capacity plus a signed offset."""
    def __init__(self, problem, powers, coefficients):
        self.problem = problem
        self.powers = np.asarray(powers)
        self.coefficients = np.asarray(coefficients)
        n = problem.state_dimension
        degree = int(self.powers.sum(axis=1).max())
        canonical, self.factors, self.shifts = basis_structure(n, degree)
        if not np.array_equal(self.powers, canonical):
            raise ValueError("invalid polynomial basis ordering")

    def basis(self, normalized):
        x = np.asarray(normalized)
        x = np.concatenate([x, np.ones((*x.shape[:-1], 1))], axis=-1)
        terms = x[..., self.factors[:, 0]]
        for column in self.factors.T[1:]:
            terms *= x[..., column]
        return terms

    def design(self, states):
        return self.basis((np.asarray(states)-self.problem.center)/self.problem.radius)

    def predict(self, states):
        s = np.asarray(states)
        decisions = self.design(s) @ self.coefficients
        decisions[..., 0] += self.problem.capacity(s)
        return decisions

    @cached_property
    def shift_arrays(self):
        pr = self.problem
        shock = pr.amplitudes/pr.radius[:9]
        lower, upper, masks, factors, indices = zip(*self.shifts)
        masks, remapped = np.unique(masks, return_inverse=True)
        weights = np.asarray([factor*np.prod(shock[list(j)]) for factor, j in zip(factors, indices)])
        return (np.asarray(lower), np.asarray(upper), masks, remapped, weights,
                np.asarray([len(j) for j in indices]))

    def _average_basis(self, basis, amplitude_scale):
        lower, upper, masks, remapped, weight, order = self.shift_arrays
        constant = masks[remapped] == 0
        mean = basis.copy()
        if constant.any():
            np.add.at(mean.T, upper[constant],
                      (basis[:, lower[constant]]*(weight[constant]*amplitude_scale**order[constant])).T)
        return mean

    def expected_design(self, states, decisions):
        return self._average_basis(self.design(self.problem.successor_center(states, decisions)), 1.0)

    def moments(self, states, decisions, amplitude_scale=1.0):
        """Exact integration via orthogonal monomials of the nine signs."""
        pr = self.problem
        nxt = pr.successor_center(states, decisions)
        basis = self.design(nxt)
        mean = self._average_basis(basis, amplitude_scale) @ self.coefficients
        mean[:, 0] += pr.capacity(nxt)
        lower, upper, masks, remapped, weight, order = self.shift_arrays
        random = masks[remapped] != 0
        by_mask = np.zeros((len(self.powers), len(masks)))
        term = self.coefficients[upper, 5]*weight*amplitude_scale**order
        np.add.at(by_mask, (lower[random], remapped[random]), term[random])
        variance = np.square(basis @ by_mask).sum(axis=1)
        return unpack_moments(pr, mean, variance)


def unpack_moments(problem, mean, variance):
    z = problem.ramp_values_start
    return dict(mean_Q=mean[:, 0], mean_price=mean[:, 5], price_variance=variance,
                mean_W_M=mean[:, 7], mean_W_B=mean[:, 8:z], mean_W_Z=mean[:, z:])


def derivative(function, point, step=1e-5):
    identity = np.eye(len(point))
    return np.column_stack([(function(point+step*d)-function(point-step*d))/(2*step)
                            for d in identity])


def linear_start(problem):
    """Solve the stable subspace of the deterministic first-order RE system."""
    p = problem
    n, m = p.state_dimension, p.policy_dimension
    s0, u0 = p.center, p.anchor_policy
    fs = derivative(lambda s: p.residual(s[None], u0[None],
                    unpack_moments(p, u0[None], np.zeros(1)))[0], s0)
    fu = derivative(lambda u: p.residual(s0[None], u[None],
                    unpack_moments(p, u0[None], np.zeros(1)))[0], u0)
    fm = derivative(lambda u: p.residual(s0[None], u0[None],
                    unpack_moments(p, u[None], np.zeros(1)))[0], u0)
    a = derivative(lambda s: p.successor_center(s[None], u0[None])[0], s0)
    b = derivative(lambda u: p.successor_center(s0[None], u[None])[0], u0)
    left = np.block([[np.eye(n), np.zeros((n, m))], [np.zeros((m, n)), fm]])
    right = np.block([[a, b], [-fs, -fu]])
    _, _, alpha, beta, _, z = ordqz(right, left, sort="iuc", output="complex")
    stable = np.sum(np.abs(alpha) < np.abs(beta))
    if stable != n:
        raise ValueError(f"Linear initialization requires {n} stable directions, obtained {stable}")
    slope = np.linalg.solve(z[:n, :n].T, z[n:, :n].T).T.real
    return slope, a+b@slope, fu+fm@slope@b, fm


class Projector:
    def __init__(self, problem, states, degree, linearization):
        self.problem, self.states = problem, states
        slope, closed_loop, current_jac, future_jac = linearization
        n, m = problem.state_dimension, problem.policy_dimension
        self.powers = basis_powers(n, degree)
        coef = np.zeros((len(self.powers), m))
        coef[0] = problem.anchor_policy
        coef[0, 0] -= problem.capacity(problem.center)
        coef[1:n+1] = slope.T*problem.radius[:, None]
        capacity_gradient = np.zeros(n)
        capacity_gradient[12] = 1
        capacity_gradient[problem.ramp_start:] = problem.params.g
        coef[1:n+1, 0] -= capacity_gradient*problem.radius
        self.start = coef
        policy = PolynomialPolicy(problem, self.powers, coef)
        design = policy.design(states)
        self.project = np.linalg.pinv(design)
        following = problem.center + (states-problem.center) @ closed_loop.T
        operator = self.project @ policy.design(following)
        t, z = schur(operator, output="complex")
        self.z, self.t = z, t
        self.inverse_current = np.linalg.inv(current_jac.T)
        self.interaction = future_jac.T @ self.inverse_current
        self.inverse_rows = np.linalg.inv(np.eye(m)[None]+np.diag(t)[:, None, None]*self.interaction)

    def residual(self, coefficient, amplitude):
        policy = PolynomialPolicy(self.problem, self.powers, coefficient)
        u = policy.predict(self.states)
        moments = policy.moments(self.states, u, amplitude)
        return self.problem.residual(self.states, u, moments)

    def correction(self, residual):
        target = self.z.conj().T @ self.project @ residual @ self.inverse_current
        rows = np.zeros_like(target)
        for i in range(len(rows)-1, -1, -1):
            continuation = (self.t[i, i+1:] @ rows[i+1:]) @ self.interaction
            rows[i] = (target[i]-continuation) @ self.inverse_rows[i]
        return (self.z @ rows).real
