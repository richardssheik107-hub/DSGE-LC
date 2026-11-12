"""All-condition evaluator for the macro LC candidate, using only stdlib.

This module evaluates a supplied policy; it does not solve the stochastic
policy fixed point, prove invariant-domain existence, or estimate parameters.
All continuation moments are generated internally with the SAME policy,
transition and finite joint shock kernel. No mu/variance input is accepted.
The deterministic anchor is synthetic and verifies a stationary point only.

External state order: (g, e, r, zeta, zA_id, zm_id, zJ_id, zN_id, zf_id).
State.time indexes an optional known deterministic tau path. It is a calendar
index, not a tenth stochastic state; such a policy is generally time dependent.
"""
from dataclasses import dataclass, replace
from itertools import product
import math

MODEL_ID = "LC_V2_MACRO_REVIEW_20261030"
REVISION = "ALL_CONDITIONS_CLOSURE_20261105"
EXTERNAL_NAMES = ("g", "e", "r", "zeta", "zA_id", "zm_id", "zJ_id", "zN_id", "zf_id")


class DomainError(ValueError):
    """An input or a successor lies outside the declared economic domain."""


def _finite(values, name):
    if not all(math.isfinite(x) for x in values):
        raise DomainError(name + " must contain only finite numbers")


@dataclass(frozen=True)
class Parameters:
    L: int = 3
    R: int = 2
    delta: float = 0.05
    g: tuple = (1/3, 2/3)
    alpha: float = 0.2
    nu: float = 1.0
    kappa: float = 0.15
    chi: float = 1.0
    omega_B: float = 0.05
    D0: float = 1.0
    omega: float = 0.25
    eta_s: float = 0.5
    eta_c: float = 0.5
    P_star: float = 1.0
    lambda_g: float = 0.3
    lambda_tau: float = 0.1
    tau_constant: float = 0.0
    FX_bar: float = 1.0
    m_domestic: float = 0.6
    m_usd: float = 0.2
    pJ0: float = 1.0
    N0: float = 0.1
    N_scale: float = 0.1
    af0: float = 0.5
    gamma_zeta: float = 0.5
    i_bar: float = 0.02
    alpha_I: float = 0.98
    h: float = 0.04
    xi: float = 0.1
    I0: float = 0.5
    a_I: float = 0.8
    a_D: float = 1.2

    def validate(self):
        if type(self.L) is not int or self.L < 1 or type(self.R) is not int or self.R < 0:
            raise DomainError("L must be an integer >=1 and R an integer >=0")
        if len(self.g) != self.R:
            raise DomainError("g must have R entries, empty when R=0")
        scalar = [v for k, v in vars(self).items() if k not in ("g", "L", "R")]
        _finite(scalar, "parameters")
        _finite(self.g, "ramp efficiencies")
        if not 0 <= self.delta < 1 or not 0 < self.alpha_I <= 1 or not 0 < self.omega < 1:
            raise DomainError("invalid depreciation, inventory survival, or demand share")
        if any(not 0 < x <= 1 for x in self.g) or tuple(sorted(self.g)) != tuple(self.g):
            raise DomainError("g must be nondecreasing and in (0,1]")
        for name in ("alpha", "nu", "chi", "D0", "eta_s", "eta_c", "P_star", "FX_bar", "pJ0", "af0", "I0", "a_I", "a_D"):
            if getattr(self, name) <= 0:
                raise DomainError(name + " must be strictly positive")
        for name in ("kappa", "omega_B", "m_domestic", "m_usd", "h", "xi"):
            if getattr(self, name) < 0:
                raise DomainError(name + " must be nonnegative")
        if self.m_domestic + self.m_usd <= 0:
            raise DomainError("domestic and USD variable-cost coefficients cannot both be zero")


@dataclass(frozen=True)
class State:
    external: tuple
    q_lag: float
    inventory_lag: float
    commitment_lag: float
    mature_capacity: float
    construction: tuple
    ramp: tuple
    time: int = 0

    @property
    def dimension(self):
        return len(self.external) + 4 + len(self.construction) + len(self.ramp)


@dataclass(frozen=True)
class Decision:
    """Minimal choices/shadows plus recovered positions and a value-level check.

producer_value is used to verify the producer's Bellman value along a supplied
policy. It is a recovered diagnostic, not an additional free variable in the
minimal 7+L+R equilibrium system. Positions are likewise recovery quantities.
"""
    q: float
    j: float
    d_s: float
    c: float
    inventory: float
    spot: float
    futures: float
    producer_value: float
    w_m: float
    w_z: tuple
    w_b: tuple
    h_inventory: float
    h_procurement: float
    h_financial: float


@dataclass(frozen=True)
class ShockBranch:
    probability: float
    innovation: tuple


@dataclass(frozen=True)
class JointKernel:
    """Finite JOINT law. A/B and branch correlations are explicit inputs.

A/B are 9x9 in this implementation. Their block-diagonal restriction, if used,
is a modelling choice. Nine states do not require nine independent shocks.
No identity covariance or independence is silently imposed on branch values.
The canonical E01 benchmark is produced by independent_rademacher_kernel;
an arbitrary JointKernel may be only a restricted interface test. Accepting
its finite probabilities does not certify stationarity, the canonical shock
normalization, or an invariant economic domain.
"""
    A: tuple
    B: tuple
    branches: tuple

    def validate(self):
        for name, matrix in (("A", self.A), ("B", self.B)):
            if len(matrix) != 9 or any(len(row) != 9 for row in matrix):
                raise DomainError(name + " must be 9 by 9")
            _finite([x for row in matrix for x in row], name)
        if not self.branches:
            raise DomainError("at least one shock branch is required")
        for branch in self.branches:
            if len(branch.innovation) != 9 or not math.isfinite(branch.probability) or branch.probability <= 0:
                raise DomainError("branches need positive probabilities and nine innovations")
            _finite(branch.innovation, "innovation")
        if abs(math.fsum(x.probability for x in self.branches) - 1) > 1e-12:
            raise DomainError("joint branch probabilities must sum to one; no normalization is applied")


def diagonal_matrix(value):
    """A nine-state diagonal matrix, with a common or nine separate entries."""
    values = tuple(value) if isinstance(value, (tuple, list)) else (value,)*9
    if len(values) != 9:
        raise DomainError("a diagonal requires nine entries")
    _finite(values, "diagonal entries")
    return tuple(tuple(values[i] if i == j else 0.0 for j in range(9)) for i in range(9))


def independent_rademacher_kernel(A, B):
    """Canonical standardized innovation law: 512 independent +/-1 branches.

All nine innovations have zero mean and identity covariance. Their physical
amplitudes belong in B, not in the innovation values. A and B still need the
chosen model's block restrictions and stability/domain checks; this factory
only specifies the innovation law.
"""
    branches = tuple(ShockBranch(1/512, innovation)
                     for innovation in product((-1.0, 1.0), repeat=9))
    kernel = JointKernel(A, B, branches)
    kernel.validate()
    return kernel


def deterministic_kernel():
    """Zero shock loading, with 512 equivalent successors collapsed to one.

The displayed zero innovation is a representative of the B=0 limit. Its
zero covariance is not asserted to be the canonical unit-covariance law.
"""
    return JointKernel(diagonal_matrix(0.8), diagonal_matrix(0.0),
                       (ShockBranch(1.0, (0.0,)*9),))


def primitives(state, params, tau_path=None):
    """Declared 10.30 macro mapping with a fixed engineering cost split.

USD inputs and domestic processing coefficients are constants in this
minimal implementation; giving them stochastic laws requires extra explicit
states or functions of the existing state. FX applies only to the USD part.
"""
    if len(state.external) != 9:
        raise DomainError("external state must have exactly four macro and five idiosyncratic entries")
    _finite(state.external, "external state")
    g, e, r, zeta, zA, zm, zJ, zN, zf = state.external
    tau = params.tau_constant if tau_path is None else tau_path(state.time)
    _finite((tau,), "deterministic tau")
    denominator = 1 + params.i_bar + r
    if denominator <= 0:
        raise DomainError("1+i_bar+r must be positive; the rate is never clipped")
    try:
        A = params.D0*math.exp(params.lambda_g*g + params.lambda_tau*tau + zA)
        fx = params.FX_bar*math.exp(e)
        out = {
            "A": A, "A_s": (1-params.omega)*A, "A_c": params.omega*A,
            "FX": fx, "m": math.exp(zm)*(params.m_domestic + fx*params.m_usd),
            "p_j": params.pJ0*math.exp(zJ), "N": params.N0 + params.N_scale*zN,
            "a_f": params.af0*math.exp(params.gamma_zeta*zeta + zf),
            "b": 1/denominator, "tau": tau,
        }
    except OverflowError as exc:
        raise DomainError("macro mapping is outside finite numerical range") from exc
    _finite(out.values(), "mapped primitives")
    for name in ("A", "A_s", "A_c", "FX", "m", "p_j", "a_f", "b"):
        if out[name] <= 0:
            raise DomainError("mapped " + name + " must remain positive")
    return out


def effective_capacity(state, params):
    return state.mature_capacity + math.fsum(g*z for g, z in zip(params.g, state.ramp))


def validate_state(state, params, tau_path=None):
    if len(state.external) != 9 or len(state.construction) != params.L-1 or len(state.ramp) != params.R:
        raise DomainError("state dimensions disagree with nine external states and L/R queues")
    if type(state.time) is not int:
        raise DomainError("time is an integer calendar index")
    quantities = (state.q_lag, state.inventory_lag, state.commitment_lag,
                  state.mature_capacity, *state.construction, *state.ramp)
    _finite(quantities, "state quantities")
    if any(x < 0 for x in quantities):
        raise DomainError("inherited physical quantities cannot be negative")
    env = primitives(state, params, tau_path)
    k = effective_capacity(state, params)
    if k <= 0:
        raise DomainError("K_e must be positive; the zero-capacity perspective extension is not imposed")
    margin = k + env["N"] + params.alpha_I*state.inventory_lag - state.commitment_lag
    if margin <= 0:
        raise DomainError("maximum physical resources cannot meet inherited commitment plus positive flexible demand")
    return env, k, margin


def validate_decision(decision, params):
    if len(decision.w_z) != params.R or len(decision.w_b) != params.L-1:
        raise DomainError("shadow-value queue lengths disagree with L/R")
    values = [v for k, v in vars(decision).items() if k not in ("w_z", "w_b")]
    _finite((*values, *decision.w_z, *decision.w_b), "policy decision")
    for name in ("spot", "futures", "d_s", "c"):
        if getattr(decision, name) <= 0:
            raise DomainError(name + " must be positive")
    for name in ("q", "j", "inventory"):
        if getattr(decision, name) < 0:
            raise DomainError(name + " cannot be negative; no clipping is applied")


def advance_state(state, decision, params, kernel, branch):
    """Advance queues exactly; a newly completed project is not depreciated.

For R=0: K_M'=(1-delta)K_M+completion. For R>0 the completion
enters Z_0 undepreciated; depreciation starts after its first operating period.
For L=1 completion=J and construction is empty.
"""
    external = tuple(math.fsum(a*x for a, x in zip(row_a, state.external))
                     + math.fsum(b*eps for b, eps in zip(row_b, branch.innovation))
                     for row_a, row_b in zip(kernel.A, kernel.B))
    completion = state.construction[0] if params.L > 1 else decision.j
    construction = state.construction[1:] + (decision.j,) if params.L > 1 else ()
    survival = 1-params.delta
    if params.R:
        ramp = (completion,) + tuple(survival*z for z in state.ramp[:-1])
        mature = survival*(state.mature_capacity + state.ramp[-1])
    else:
        ramp = ()
        mature = survival*state.mature_capacity + completion
    return State(external, decision.q, decision.inventory, decision.c,
                 mature, construction, ramp, state.time+1)


def _complementarity(primal, dual):
    return {"primal": primal, "dual_gap": dual,
            "primal_violation": max(-primal, 0.0),
            "dual_violation": max(-dual, 0.0),
            "product": primal*dual}


def _benefit_marginal(quantity, scale, eta, params):
    return params.P_star*(quantity/scale)**(-1/eta)


def risk_share_positions(inventory, commitment, params, a_f):
    """Stable clearing selection; at v=0 other zero-sum positions also work."""
    tolerances = (1/params.a_I, 1/params.a_D, 1/a_f)
    T = math.fsum(tolerances)
    H = params.alpha_I*inventory-commitment
    w = tuple(t/T for t in tolerances)
    return (-params.alpha_I*inventory+w[0]*H,
            commitment+w[1]*H, w[2]*H)


def evaluate_conditions(state, policy, params, kernel, tau_path=None, tolerance=1e-9):
    """Return all local residuals; every continuation value is internal.

Passing all residuals at one state is not a global fixed-point certificate.
The derivatives use the price-taking convention: an individual deviation
holds the aggregate price law fixed. Multipliers are recovered from the
bounded production VI, then its bound complementarities are checked.
"""
    params.validate()
    kernel.validate()
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise DomainError("residual tolerance must be finite and positive")
    env, k, margin = validate_state(state, params, tau_path)
    d = policy(state)
    validate_decision(d, params)
    future = []
    checks = []
    for index, branch in enumerate(kernel.branches):
        sp = advance_state(state, d, params, kernel, branch)
        try:
            ep, kp, mp = validate_state(sp, params, tau_path)
            dp = policy(sp)
            validate_decision(dp, params)
            if dp.q > kp + tolerance:
                raise DomainError("continuation output exceeds its own effective capacity")
        except DomainError as exc:
            raise DomainError(f"successor branch {index}: {exc}") from exc
        future.append((branch.probability, sp, dp))
        checks.append({"branch": index, "probability": branch.probability,
                       "state_dimension": sp.dimension, "K_e": kp,
                       "maximum_physical_margin": mp, "b": ep["b"],
                       "output_capacity_violation": max(dp.q-kp, 0.0)})
    def expectation(get):
        return math.fsum(prob*get(sp, dp) for prob, sp, dp in future)
    mu = expectation(lambda sp, dp: dp.spot)
    variance = expectation(lambda sp, dp: (dp.spot-mu)**2)
    eq = expectation(lambda sp, dp: dp.q)
    ev = expectation(lambda sp, dp: dp.producer_value)
    ewm = expectation(lambda sp, dp: dp.w_m)
    ewz = tuple(expectation(lambda sp, dp, a=a: dp.w_z[a]) for a in range(params.R))
    ewb = tuple(expectation(lambda sp, dp, h=h: dp.w_b[h]) for h in range(params.L-1))
    b, survival = env["b"], 1-params.delta
    delta = mu-d.futures
    output_gradient = d.spot-env["m"]-params.alpha*(d.q/k)**params.nu \
                      - params.kappa*(d.q-state.q_lag) + b*params.kappa*(eq-d.q)
    cap_multiplier = max(output_gradient, 0.0)
    lower_multiplier = max(-output_gradient, 0.0)
    service = params.alpha*params.nu/(params.nu+1)*(d.q/k)**(params.nu+1)+cap_multiplier
    completion_value = ewz[0] if params.R else ewm
    next_investment_value = ewb[-1] if params.L > 1 else completion_value
    XB = math.fsum(state.construction)
    investment_gap = env["p_j"]+params.chi*d.j+params.omega_B*XB-b*next_investment_value
    gprime = params.h-params.xi/(d.inventory+params.I0)
    stock_exposure = params.alpha_I*d.inventory+d.h_inventory
    procurement_exposure = d.h_procurement-d.c
    marginal_s = _benefit_marginal(d.d_s, env["A_s"], params.eta_s, params)
    marginal_c = _benefit_marginal(d.c, env["A_c"], params.eta_c, params)
    inventory_gradient = -d.spot-gprime+b*params.alpha_I*(mu-params.a_I*variance*stock_exposure)
    procurement_gradient = b*(marginal_c-mu+params.a_D*variance*procurement_exposure)
    cost_q = env["m"]*d.q+params.alpha/(params.nu+1)*d.q**(params.nu+1)/k**params.nu \
             + params.kappa/2*(d.q-state.q_lag)**2
    cost_j = env["p_j"]*d.j+params.chi/2*d.j*d.j+params.omega_B*d.j*XB
    profit = d.spot*d.q-cost_q-cost_j
    equality = {
        "producer_Bellman": d.producer_value-profit-b*ev,
        "E09_Q_stationarity_reconstructed": output_gradient-cap_multiplier+lower_multiplier,
        "E04_flexible_demand_gradient": marginal_s-d.spot,
        "E19_inventory_hedge_gradient": b*(delta-params.a_I*variance*stock_exposure),
        "E20_procurement_gradient": procurement_gradient,
        "E20_procurement_hedge_gradient": b*(delta-params.a_D*variance*procurement_exposure),
        "E21_financial_hedge_gradient": b*(delta-env["a_f"]*variance*d.h_financial),
        "E25_goods_clearing": d.q+env["N"]+params.alpha_I*state.inventory_lag-d.d_s-state.commitment_lag-d.inventory,
        "E26_futures_clearing": d.h_inventory+d.h_procurement+d.h_financial,
        "E14_mature_value": d.w_m-service-b*survival*ewm,
    }
    for a in range(params.R):
        after = ewz[a+1] if a+1 < params.R else ewm
        equality[f"E14_ramp_value_{a}"] = d.w_z[a]-params.g[a]*service-b*survival*after
    for h in range(params.L-1):
        after = ewb[h-1] if h else completion_value
        equality[f"E15_construction_value_{h+1}"] = d.w_b[h]+params.omega_B*d.j-b*after
    comp = {
        "E09_output_lower": _complementarity(d.q, lower_multiplier),
        "E09_capacity_upper": _complementarity(k-d.q, cap_multiplier),
        "E16_investment": _complementarity(d.j, investment_gap),
        "E19_inventory_original": _complementarity(d.inventory, -inventory_gradient),
    }
    T = 1/params.a_I+1/params.a_D+1/env["a_f"]
    H = params.alpha_I*d.inventory-d.c
    derived = {
        "E23_procurement_reduced": marginal_c-d.futures,
        "E27_futures_reduced": d.futures-mu+variance/T*H,
    }
    inventory_reduced = _complementarity(d.inventory, d.spot+gprime-b*params.alpha_I*d.futures)
    residuals = [abs(x) for x in equality.values()] + [abs(x) for x in derived.values()]
    for item in (*comp.values(), inventory_reduced):
        residuals += [item["primal_violation"], item["dual_violation"], abs(item["product"])]
    _finite(residuals, "residuals")
    max_residual = max(residuals, default=0.0)
    carry = d.spot+params.h-b*params.alpha_I*d.futures
    inventory_status = "unbounded" if carry < 0 or (carry == 0 and params.xi > 0) else (
        "flat_nonunique" if carry == 0 else "finite_unique")
    selected = risk_share_positions(d.inventory, d.c, params, env["a_f"])
    choice_difference = max(abs(x-y) for x, y in zip(selected, (d.h_inventory, d.h_procurement, d.h_financial)))
    return {
        "model_id": MODEL_ID, "revision": REVISION,
        "scope": "all local structural conditions for one supplied policy, not a stochastic equilibrium solver",
        "minimal_policy_unknowns": 7+params.L+params.R,
        "producer_value_is_recovered_Bellman_check_not_extra_independent_condition": True,
        "state_dimension": state.dimension, "calendar_index": state.time,
        "mapped_primitives": env,
        "conditional_moments": {"provenance": "same_policy_same_transition_same_branch_weights",
            "externally_supplied_price_moments": False, "mean_price": mu, "price_variance": variance,
            "mean_Q": eq, "mean_producer_value": ev, "mean_W_M": ewm,
            "mean_W_Z": ewz, "mean_W_B": ewb},
        "original_equalities": equality, "original_complementarity": comp,
        "derived_checks_not_extra_independent_conditions": derived,
        "derived_inventory_complementarity": inventory_reduced,
        "recovered": {"lambda_capacity": cap_multiplier, "mu_output": lower_multiplier,
            "current_capacity_service": service, "Q_lag_envelope": params.kappa*(d.q-state.q_lag),
            "expected_next_Q_lag_envelope": params.kappa*(eq-d.q)},
        "diagnostics": {"output_unconstrained_gradient": output_gradient,
            "inventory_original_gradient": inventory_gradient, "investment_gap": investment_gap,
            "current_producer_profit": profit, "maximum_physical_margin": margin,
            "inventory_linear_carry_gap": carry, "inventory_objective_status": inventory_status,
            "zero_variance_positions_unique": False if variance == 0 else None,
            "zero_variance_position_status": ("continuous_limit_selection_nonunique" if choice_difference <= tolerance
                else "other_zero_sum_selection_nonunique") if variance == 0 else "not_zero_variance",
            "risk_share_selection_deviation_not_a_constraint_at_v0": choice_difference},
        "successor_checks": checks, "max_equality_or_kkt_residual": max_residual,
        "all_local_conditions_passed": max_residual <= tolerance and inventory_status != "unbounded",
        "full_equilibrium_solved": False, "global_domain_invariance_verified": False,
        "infinite_horizon_tvc_verified": False, "parameter_calibration_performed": False,
    }


def audit_forward_values(state, policy, params, kernel, tau_path=None, horizon=None, max_nodes=100000):
    """Enumerate finite paths, retaining d_{t,t+k} INSIDE expectations.

Reports investment's positive future-congestion cost and completed-capacity
value, plus finite-horizon tail diagnostics. A small finite tail does not
establish the infinite-horizon transversality condition.
"""
    params.validate()
    kernel.validate()
    horizon = max(params.L, 1) if horizon is None else horizon
    if type(horizon) is not int or horizon < params.L:
        raise DomainError("forward horizon must be an integer at least L")
    env, _, _ = validate_state(state, params, tau_path)
    d0 = policy(state)
    validate_decision(d0, params)
    frontier = [(1.0, 1.0, state, d0)]
    discount_products = [1.0]
    congestion_terms = []
    completed_value = None
    for step in range(1, horizon+1):
        if len(frontier)*len(kernel.branches) > max_nodes:
            raise DomainError("finite path enumeration exceeds max_nodes; no branches silently dropped")
        new = []
        for probability, discount, s, d in frontier:
            current_b = primitives(s, params, tau_path)["b"]
            for branch in kernel.branches:
                sp = advance_state(s, d, params, kernel, branch)
                _, kp, _ = validate_state(sp, params, tau_path)
                dp = policy(sp)
                validate_decision(dp, params)
                if dp.q > kp + 1e-9:
                    raise DomainError("forward continuation output exceeds its own effective capacity")
                new.append((probability*branch.probability, discount*current_b, sp, dp))
        frontier = new
        discount_products.append(math.fsum(p*disc for p, disc, s, d in frontier))
        if step < params.L:
            congestion_terms.append(math.fsum(p*disc*d.j for p, disc, s, d in frontier))
        if step == params.L:
            completed_value = math.fsum(p*disc*(d.w_z[0] if params.R else d.w_m)
                                        for p, disc, s, d in frontier)
    future_congestion = params.omega_B*math.fsum(congestion_terms)
    current_cost = env["p_j"]+params.chi*d0.j+params.omega_B*math.fsum(state.construction)
    expanded_gap = current_cost+future_congestion-completed_value
    one_step = evaluate_conditions(state, policy, params, kernel, tau_path)["diagnostics"]["investment_gap"]
    return {
        "horizon": horizon, "terminal_paths": len(frontier),
        "expected_path_discount_products": discount_products,
        "expected_discounted_future_J_by_building_period": congestion_terms,
        "discounted_future_congestion_cost": future_congestion,
        "discounted_completed_capacity_value": completed_value,
        "expanded_investment_gap": expanded_gap, "one_step_investment_gap": one_step,
        "one_step_minus_expanded_gap": one_step-expanded_gap,
        "discounted_mature_value_tail": math.fsum(p*disc*(1-params.delta)**horizon*d.w_m
                                                   for p, disc, s, d in frontier),
        "discounted_producer_value_tail": math.fsum(p*disc*d.producer_value for p, disc, s, d in frontier),
        "discounted_absolute_state_costate_tail": math.fsum(p*disc*(
            abs(params.kappa*(d.q-s.q_lag)*s.q_lag) + abs(d.w_m*s.mature_capacity)
            + math.fsum(abs(w*x) for w, x in zip(d.w_b, s.construction))
            + math.fsum(abs(w*x) for w, x in zip(d.w_z, s.ramp)))
            for p, disc, s, d in frontier),
        "infinite_horizon_tvc_proved_by_this_finite_check": False,
    }


@dataclass(frozen=True)
class DeterministicAnchor:
    params: Parameters
    state: State
    decision: Decision
    kernel: JointKernel

    def policy(self, state):
        """Constant continuation defines an exact stationary path only."""
        return self.decision


def make_deterministic_anchor(L=3, R=2):
    """Synthetic binding-capacity steady state with positive investment.

D0, xi and pJ0 are reverse-engineered from chosen quantities/prices. This is
an algebraic anchor, not data estimation or a globally valid constant policy.
"""
    params = Parameters(L=L, R=R, g=tuple((a+1)/(R+1) for a in range(R)))
    params.validate()
    b = 1/(1+params.i_bar)
    survival = 1-params.delta
    k, q, price, inventory = 1.0, 1.0, 2.0, 0.5
    capacity_per_start = survival**R/params.delta+math.fsum(params.g[a]*survival**a for a in range(R))
    j = k/capacity_per_start
    ramp = tuple(survival**a*j for a in range(R))
    mature = survival**R*j/params.delta
    construction = (j,)*(L-1)
    total_use = q+params.N0-(1-params.alpha_I)*inventory
    unit_demand = (1-params.omega)*(price/params.P_star)**(-params.eta_s) \
                  + params.omega*(price/params.P_star)**(-params.eta_c)
    D0 = total_use/unit_demand
    xi = (price+params.h-b*params.alpha_I*price)*(inventory+params.I0)
    params = replace(params, D0=D0, xi=xi)
    ds = (1-params.omega)*D0*(price/params.P_star)**(-params.eta_s)
    c = params.omega*D0*(price/params.P_star)**(-params.eta_c)
    m = params.m_domestic+params.FX_bar*params.m_usd
    lam = price-m-params.alpha*(q/k)**params.nu
    if lam <= 0:
        raise DomainError("anchor requires positive binding-capacity rent")
    service = params.alpha*params.nu/(params.nu+1)*(q/k)**(params.nu+1)+lam
    wm = service/(1-b*survival)
    wz = [0.0]*R
    after = wm
    for a in reversed(range(R)):
        wz[a] = params.g[a]*service+b*survival*after
        after = wz[a]
    wb = []
    after = wz[0] if R else wm
    for h in range(1, L):
        after = -params.omega_B*j+b*after
        wb.append(after)
    investment_continuation = wb[-1] if L > 1 else (wz[0] if R else wm)
    pJ0 = b*investment_continuation-params.chi*j-params.omega_B*math.fsum(construction)
    if pJ0 <= 0:
        raise DomainError("synthetic anchor generates nonpositive construction price")
    params = replace(params, pJ0=pJ0)
    state = State((0.0,)*9, q, inventory, c, mature, construction, ramp)
    cost_q = m*q+params.alpha/(params.nu+1)*q**(params.nu+1)/k**params.nu
    cost_j = pJ0*j+params.chi/2*j*j+params.omega_B*j*math.fsum(construction)
    value = (price*q-cost_q-cost_j)/(1-b)
    hi, hd, hf = risk_share_positions(inventory, c, params, params.af0)
    decision = Decision(q, j, ds, c, inventory, price, price, value, wm,
                        tuple(wz), tuple(wb), hi, hd, hf)
    return DeterministicAnchor(params, state, decision, deterministic_kernel())
