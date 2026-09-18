"""Small algebraic examples for docs/theory/lithium_partial_equilibrium_v1.md.

No empirical inputs, calibration, filtering, fitting, or file writes.
Units must be matched by the caller: Q/U/I are the SAME commodity, P/m its price.
These examples do not validate identification or the lithium industry itself.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, log
from typing import Sequence


def _finite(*values: float) -> None:
    if not all(isfinite(x) for x in values):
        raise ValueError('All illustrative quantities must be finite')


@dataclass(frozen=True)
class ProductionProblem:
    curvature: float
    adjustment: float
    capacity: float

    def __post_init__(self) -> None:
        _finite(self.curvature, self.adjustment, self.capacity)
        if self.curvature <= 0 or self.adjustment < 0 or self.capacity < 0:
            raise ValueError('Require g>0, kappa>=0 and K>=0')

    @property
    def rho(self) -> float:
        return self.adjustment/(self.curvature+self.adjustment)

    @property
    def alpha(self) -> float:
        return 1/(self.curvature+self.adjustment)

    def choose(self, expected_price: float, unit_input_cost: float,
               previous_output: float) -> float:
        _finite(expected_price, unit_input_cost, previous_output)
        if previous_output < 0:
            raise ValueError('previous output must be nonnegative')
        interior = self.rho*previous_output + self.alpha*(expected_price-unit_input_cost)
        return min(self.capacity, max(0.0, interior))

    def objective(self, output: float, price: float, cost: float, previous: float) -> float:
        _finite(output, price, cost, previous)
        if not 0 <= output <= self.capacity or previous < 0:
            raise ValueError('infeasible output')
        return ((price-cost)*output-self.curvature*output**2/2
                -self.adjustment*(output-previous)**2/2)


def route_input_cost(ore_cny_per_tonne: float, tonnes_ore_per_tonne_carbonate: float,
                     other_cny_per_tonne_carbonate: float) -> float:
    """Unit conversion example, NOT an empirical lithium conversion coefficient."""
    _finite(ore_cny_per_tonne, tonnes_ore_per_tonne_carbonate,
            other_cny_per_tonne_carbonate)
    if min(ore_cny_per_tonne, tonnes_ore_per_tonne_carbonate,
           other_cny_per_tonne_carbonate) < 0:
        raise ValueError('nonnegative inputs required')
    return (ore_cny_per_tonne*tonnes_ore_per_tonne_carbonate
            +other_cny_per_tonne_carbonate)


def interior_market(demand_shift: float, demand_slope: float, net_imports: float,
                    desired_inventory_change: float, previous_output: float,
                    rho: float, alpha: float, input_cost: float) -> tuple[float,float,float]:
    """T5 price, output and use. Reject non-interior results; no hidden clipping."""
    _finite(demand_shift, demand_slope, net_imports, desired_inventory_change,
            previous_output, rho, alpha, input_cost)
    if demand_slope < 0 or alpha <= 0 or not 0 <= rho < 1 or previous_output < 0:
        raise ValueError('invalid local supply/demand assumptions')
    price=(demand_shift+desired_inventory_change-net_imports-rho*previous_output
           +alpha*input_cost)/(alpha+demand_slope)
    output=rho*previous_output+alpha*(price-input_cost)
    use=demand_shift-demand_slope*price
    if min(price,output,use) <= 0:
        raise ValueError('not an admissible interior equilibrium; solve constrained model')
    return price,output,use


def end_inventory(previous: float, production: float, imports: float, exports: float,
                  cathode_use: float, conversion_and_other_use: float,
                  losses: float = 0.0) -> float:
    """Single carbonate boundary, no already-included ore/recycling double count."""
    _finite(previous, production, imports, exports, cathode_use, conversion_and_other_use, losses)
    if min(previous, production, imports, exports, cathode_use, conversion_and_other_use, losses) < 0:
        raise ValueError('component amounts must be nonnegative')
    result=previous+production+imports-exports-cathode_use-conversion_and_other_use-losses
    if result < 0:
        raise ValueError('physical ledger infeasible; do not clip or invent supply')
    return result


def log_changes(levels: Sequence[float], lag: int) -> list[float]:
    if not isinstance(lag,int) or isinstance(lag,bool) or lag < 1 or len(levels) <= lag:
        raise ValueError('positive integer lag shorter than history required')
    _finite(*levels)
    if any(x <= 0 for x in levels):
        raise ValueError('strictly positive levels required')
    return [log(levels[t])-log(levels[t-lag]) for t in range(lag,len(levels))]
