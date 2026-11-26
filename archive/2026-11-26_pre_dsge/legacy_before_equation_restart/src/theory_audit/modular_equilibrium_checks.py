"""Own E25 interior algebra, not a calibrated or dynamic economic solver.

Flow magnitudes use one period and the same LC boundary; no observations read.
Inactive capacity/zero-production assumptions are checked rather than silently clipped.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class Route:
    marginal_input_cost:float
    convex_cost:float
    adjustment:float
    lag_output:float
    capacity:float

@dataclass(frozen=True)
class Material:
    demand_shift:float
    non_lc_cost:float
    lc_per_material:float
    revenue_curvature:float
    adjustment:float
    lag_output:float
    capacity:float


def conditional_interior_price(routes,materials,net_import=0.,recycled_lc=0.,other_use=0.,net_stock_addition=0.):
    """Return C0 conditional equilibrium only when all assumed interiors hold."""
    if not routes or not materials:raise ValueError('nonempty routes and material groups required')
    numbers=[net_import,recycled_lc,other_use,net_stock_addition]
    for obj in [*routes,*materials]:numbers.extend(vars(obj).values())
    if not all(isfinite(v) for v in numbers):raise ValueError('finite scalars required')
    if recycled_lc<0 or other_use<0:raise ValueError('physical flow must be nonnegative')
    for r in routes:
        if r.convex_cost<=0 or r.adjustment<0 or r.lag_output<0 or r.capacity<=0:raise ValueError('invalid supply parameters')
    for m in materials:
        if m.revenue_curvature<=0 or m.adjustment<0 or m.lc_per_material<=0 or m.lag_output<0 or m.capacity<=0:raise ValueError('invalid demand parameters')
    s_slope=sum(1/(r.convex_cost+r.adjustment) for r in routes)
    s_intercept=sum((r.adjustment*r.lag_output-r.marginal_input_cost)/(r.convex_cost+r.adjustment) for r in routes)
    d_slope=sum(m.lc_per_material**2/(m.revenue_curvature+m.adjustment) for m in materials)
    d_intercept=sum(m.lc_per_material*(m.demand_shift-m.non_lc_cost+m.adjustment*m.lag_output)/(m.revenue_curvature+m.adjustment) for m in materials)
    price=(d_intercept+other_use+net_stock_addition-net_import-recycled_lc-s_intercept)/(d_slope+s_slope)
    q=[(price-r.marginal_input_cost+r.adjustment*r.lag_output)/(r.convex_cost+r.adjustment) for r in routes]
    y=[(m.demand_shift-m.non_lc_cost-m.lc_per_material*price+m.adjustment*m.lag_output)/(m.revenue_curvature+m.adjustment) for m in materials]
    if price<=0 or any(not 0<val<r.capacity for val,r in zip(q,routes)) or any(not 0<val<m.capacity for val,m in zip(y,materials)):raise ValueError('interior formula inapplicable; constrained equilibrium required')
    supply=sum(q)+recycled_lc+net_import
    use=sum(m.lc_per_material*val for m,val in zip(materials,y))+other_use
    return {'price':price,'primary_output':q,'material_output':y,'clearing_residual':supply-use-net_stock_addition,'inverse_excess_supply_slope':1/(d_slope+s_slope)}
