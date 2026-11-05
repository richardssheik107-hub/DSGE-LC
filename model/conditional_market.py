"""Conditional two-market block for LC_V2_REVIEW_20261029.

This is NOT a dynamic rational-expectations solver. Current production q and
the next-price mean and variance are supplied, not solved. Production,
investment, capacity shadow values, state-domain invariance and the policy
fixed point must be verified elsewhere before calling a result an equilibrium.

Quantities and prices in the accompanying checks are synthetic and normalized.
No industry parameter defaults or data estimates are provided here.
"""
from dataclasses import dataclass
import math


class InfeasibleStateError(ValueError):
    """The supplied state cannot support positive flexible consumption."""


class NumericalFailure(RuntimeError):
    """A finite, adequately accurate conditional root was not obtained."""


@dataclass(frozen=True)
class ConditionalInputs:
    q: float
    net_imports: float
    inventory_lag: float
    commitment_lag: float
    A_s: float
    A_c: float
    eta_s: float
    eta_c: float
    P_ref: float
    mu: float
    variance: float
    beta: float
    alpha_I: float
    h: float
    xi: float
    I0: float
    a_I: float
    a_D: float
    a_f: float


@dataclass(frozen=True)
class ConditionalResult:
    inventory: float
    spot: float
    futures: float
    commitment: float
    flexible_demand: float
    h_inventory: float
    h_procurement: float
    h_financial: float
    risk_capacity: float
    net_exposure: float
    inventory_gap: float
    inventory_regime: str
    position_status: str


def _validate(x):
    for name, value in vars(x).items():
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    positive = ("A_s", "A_c", "eta_s", "eta_c", "P_ref", "mu", "I0",
                "a_I", "a_D", "a_f")
    for name in positive:
        if getattr(x, name) <= 0:
            raise ValueError(f"{name} must be strictly positive")
    for name in ("q", "inventory_lag", "commitment_lag", "variance", "h", "xi"):
        if getattr(x, name) < 0:
            raise ValueError(f"{name} must be nonnegative")
    if not 0 < x.beta < 1:
        raise ValueError("beta must lie strictly between zero and one")
    if not 0 < x.alpha_I <= 1:
        raise ValueError("alpha_I must lie in (0, 1]")
    available = x.q + x.net_imports + x.alpha_I*x.inventory_lag - x.commitment_lag
    if not math.isfinite(available) or available <= 0:
        raise InfeasibleStateError(
            "q + net_imports + alpha_I*inventory_lag - commitment_lag "
            "must be strictly positive; no clipping or rationing is applied")
    return available


def risk_capacity_and_weights(x):
    """Aggregate risk tolerance and shares; independent of price variance."""
    tolerances = (1/x.a_I, 1/x.a_D, 1/x.a_f)
    total = sum(tolerances)
    if not math.isfinite(total) or total <= 0:
        raise ValueError("risk capacity is not numerically finite and positive")
    return total, tuple(t/total for t in tolerances)


def risk_positions(x, inventory, commitment):
    """Reconstruct clearing positions without dividing by conditional variance.

For variance > 0 these are the E22/E26 solution. At variance == 0 they are
only its continuous-limit selection; the original objectives leave all
zero-sum positions indifferent when F == mu.
    """
    total, weights = risk_capacity_and_weights(x)
    exposure = x.alpha_I*inventory - commitment
    return (
        -x.alpha_I*inventory + weights[0]*exposure,
        commitment + weights[1]*exposure,
        weights[2]*exposure,
        total,
        exposure,
    )


def inventory_objective_status(x, spot, futures):
    """Check finiteness after optimizing the inventory holder's hedge.

The inventory-dependent objective is -k*I + xi*log(1+I/I0), where
k = spot+h-beta*alpha_I*futures. With xi>0, even k==0 is unbounded.
    """
    k = spot + x.h - x.beta*x.alpha_I*futures
    if k < 0 or (k == 0 and x.xi > 0):
        status = "unbounded"
    elif k == 0:
        status = "flat_nonunique"
    else:
        status = "finite_unique"
    return {"linear_carry_gap": k, "status": status}


def _commitment(x, futures):
    if futures <= 0:
        raise NumericalFailure("the procurement optimum requires positive F")
    try:
        value = x.A_c*(futures/x.P_ref)**(-x.eta_c)
    except OverflowError as exc:
        raise NumericalFailure("commitment exceeds floating-point range") from exc
    if not math.isfinite(value) or value <= 0:
        raise NumericalFailure("commitment is not numerically finite and positive")
    return value


def _futures_given_inventory(x, inventory, total, tolerance, max_iterations):
    if x.variance == 0:
        return x.mu, _commitment(x, x.mu)
    coefficient = x.variance/total
    # H(F)=F-mu+(v/T)*(alpha_I*I-C(F)) is strictly increasing.
    # Its limit at F=0 is negative infinity. The following upper bound has
    # F>=P_ref and C(F)<=A_c, hence H(F)>=0 in exact arithmetic.
    low = 0.0
    high = max(x.P_ref, x.mu + coefficient*x.A_c)
    if not math.isfinite(high):
        raise NumericalFailure("cannot form a finite futures-price bracket")
    for _ in range(max_iterations):
        futures = (low + high)/2
        if futures == low or futures == high:
            raise NumericalFailure("futures root exceeds floating-point resolution")
        commitment = _commitment(x, futures)
        residual = futures-x.mu+coefficient*(x.alpha_I*inventory-commitment)
        scale = max(1.0, futures, x.mu,
                    abs(coefficient*x.alpha_I*inventory), abs(coefficient*commitment))
        if abs(residual) <= tolerance*scale:
            return futures, commitment
        if residual > 0:
            high = futures
        else:
            low = futures
    raise NumericalFailure("futures-price bisection did not converge")


def solve_conditional_market(x, tolerance=1e-12, max_iterations=200):
    """Solve only E23--E27 conditional on q, mu and variance.

Available material B is fixed. For 0<=I<B, spot clearing gives
P(I)=P_ref*[A_s/(B-I)]**(1/eta_s). P increases, F decreases, and the
inventory marginal gap increases strictly with I. Check I=0 first; otherwise
bisect its unique interior zero. The open upper endpoint B is never used as
a candidate state. Infeasible inputs are rejected, not truncated.
    """
    available = _validate(x)
    if not math.isfinite(tolerance) or tolerance <= 0 or max_iterations < 1:
        raise ValueError("positive tolerance and iteration limit are required")
    total, _ = risk_capacity_and_weights(x)

    def at_inventory(inventory):
        if not 0 <= inventory < available:
            raise InfeasibleStateError("inventory must leave positive flexible consumption")
        try:
            spot = x.P_ref*(x.A_s/(available-inventory))**(1/x.eta_s)
        except OverflowError as exc:
            raise NumericalFailure("spot price exceeds floating-point range") from exc
        if not math.isfinite(spot) or spot <= 0:
            raise NumericalFailure("spot price is not numerically finite and positive")
        futures, commitment = _futures_given_inventory(
            x, inventory, total, tolerance/10, max_iterations)
        gap = spot+x.h-x.xi/(inventory+x.I0)-x.beta*x.alpha_I*futures
        return spot, futures, commitment, gap

    inventory = 0.0
    spot, futures, commitment, gap = at_inventory(inventory)
    regime = "zero_inventory"
    if gap < 0:
        low, high = 0.0, available
        regime = "positive_inventory"
        for _ in range(max_iterations):
            inventory = (low+high)/2
            if inventory == low or inventory == high:
                raise NumericalFailure("inventory root exceeds floating-point resolution")
            spot, futures, commitment, gap = at_inventory(inventory)
            scale = max(1.0, spot, x.h, x.xi/(inventory+x.I0),
                        x.beta*x.alpha_I*futures)
            if abs(gap) <= tolerance*scale:
                break
            if gap > 0:
                high = inventory
            else:
                low = inventory
        else:
            raise NumericalFailure("inventory bisection did not converge")
    h_i, h_d, h_f, total, exposure = risk_positions(x, inventory, commitment)
    flexible = x.A_s*(spot/x.P_ref)**(-x.eta_s)
    status = ("continuous_limit_selection_not_unique" if x.variance == 0
              else "unique_given_exposure_prices_and_positive_variance")
    return ConditionalResult(
        inventory, spot, futures, commitment, flexible, h_i, h_d, h_f,
        total, exposure, gap, regime, status)


def original_condition_residuals(x, result):
    """Evaluate original objectives as well as reduced relations.

At zero inventory, the raw inventory derivative may be strictly negative.
It is a diagnostic, not an equality residual. KKT violation/complementarity
are used in max_equality_or_kkt_residual instead.
    """
    i, c, p, f = result.inventory, result.commitment, result.spot, result.futures
    h_i, h_d, h_f = result.h_inventory, result.h_procurement, result.h_financial
    delta = x.mu-f
    gp = x.h-x.xi/(i+x.I0)
    benefit_prime = x.P_ref*(c/x.A_c)**(-1/x.eta_c)
    inventory_gradient = -p-gp+x.beta*(
        x.alpha_I*x.mu-x.a_I*x.variance*x.alpha_I*(x.alpha_I*i+h_i))
    procurement_gradient = x.beta*(benefit_prime-x.mu+x.a_D*x.variance*(h_d-c))
    gap = p+gp-x.beta*x.alpha_I*f
    residuals = {
        "E19_inventory_raw_gradient": inventory_gradient,
        "E19_inventory_dual_violation": max(inventory_gradient, 0.0),
        "E19_inventory_complementarity": i*inventory_gradient,
        "E20_procurement_gradient": procurement_gradient,
        "E22_inventory_position": delta-x.a_I*x.variance*(x.alpha_I*i+h_i),
        "E22_procurement_position": delta-x.a_D*x.variance*(h_d-c),
        "E22_financial_position": delta-x.a_f*x.variance*h_f,
        "E23_procurement_marginal_gap": benefit_prime-f,
        "E24_inventory_gap": gap,
        "E24_inventory_dual_violation": max(-gap, 0.0),
        "E24_inventory_complementarity": i*gap,
        "E25_spot_clearing": x.q+x.net_imports+x.alpha_I*x.inventory_lag
        -result.flexible_demand-x.commitment_lag-i,
        "E26_futures_clearing": h_i+h_d+h_f,
        "E27_futures_pricing": f-x.mu+x.variance*result.net_exposure/result.risk_capacity,
    }
    non_equality_diagnostics = {"E19_inventory_raw_gradient", "E24_inventory_gap"}
    residuals["max_equality_or_kkt_residual"] = max(
        abs(value) for key, value in residuals.items() if key not in non_equality_diagnostics)
    return residuals


def no_futures_marginal_gaps(x, inventory, commitment, spot):
    """Raw h=0 counterfactual quantity conditions, NOT a solved equilibrium.

There is no F in this counterfactual. In particular, it is not constructed by
substituting F=P in the traded-futures model.
    """
    if inventory < 0 or commitment <= 0:
        raise ValueError("inventory must be nonnegative and commitment positive")
    gp = x.h-x.xi/(inventory+x.I0)
    benefit_prime = x.P_ref*(commitment/x.A_c)**(-1/x.eta_c)
    return {
        "inventory_gap": spot+gp-x.beta*x.alpha_I*(
            x.mu-x.a_I*x.variance*x.alpha_I*inventory),
        "procurement_gradient_before_discount": benefit_prime-x.mu
        -x.a_D*x.variance*commitment,
    }
