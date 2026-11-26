"""Design guards and toy algebra only; no calibration, fitting or identification proof."""
from dataclasses import replace
import json
from math import log
from pathlib import Path

import pytest

from src.theory_audit.modular_equilibrium_checks import (
    Material, Route, conditional_interior_price,
)

ROOT = Path(__file__).resolve().parents[1]


def configuration():
    return json.loads((ROOT / 'configs/model_selection_20260919.json').read_text(encoding='utf-8'))


def example():
    # Arbitrary toy units; R is specifically recycled LC in this test fixture.
    # Other primary LC is NOT relabelled recycling in data or the proposed model.
    route = Route(2.0, 2.0, 1.0, 1.0, 100.0)
    material = Material(20.0, 1.0, 1.2, 3.0, 0.0, 1.0, 100.0)
    flows = dict(net_import=0.3, recycled_lc=0.2, other_use=0.4, net_stock_addition=0.5)
    return route, material, flows


def direct_price(route, material, flows):
    """C08 evaluated independently of the existing multigroup helper."""
    g = route.convex_cost + route.adjustment
    a, b = material.lc_per_material, material.revenue_curvature
    den = a * a / b + 1.0 / g
    numerator = (
        a * (material.demand_shift - material.non_lc_cost) / b
        + flows['other_use'] + flows['net_stock_addition']
        - flows['net_import'] - flows['recycled_lc']
        + (route.marginal_input_cost - route.adjustment * route.lag_output) / g
    )
    return numerator / den, den


def test_all_28_candidate_relations_have_exactly_one_selection_role():
    groups = configuration()['equation_roles']
    ids = [item for group in groups.values() for item in group]
    assert len(ids) == len(set(ids)) == 28
    assert set(ids) == {f'E{i:02}' for i in range(1, 29)}


def test_recommendation_is_not_estimation_or_approval():
    c = configuration()
    assert c['status'] == 'RECOMMENDED_NOT_FROZEN'
    assert c['state_count'] is None and c['free_parameter_count'] is None
    assert not c['new_empirical_estimation'] and not c['identification_verified']
    assert not c['synthetic_parameter_recovery_run']
    assert c['supervisor_approval_evidence'] is None
    assert not c['thesis_submission_ready']


def test_exclusive_closure_and_no_extra_price_equation():
    c = configuration()
    assert c['selected_closure'] == 'E24' and c['excluded_closure'] == 'E23'
    assert c['fixed_design_restrictions'] == {
        'downstream_adjustment_zeta': 0, 'independent_price_ar': False,
    }
    assert len(c['current_endogenous']) == len(c['independent_current_conditions']) == 3
    assert c['inventory_role'] == 'ACCOUNTING_WITH_EXTERNALLY_GIVEN_NET_STOCK_ADDITION'


def test_old_assets_are_not_relabelled_as_new_model_evidence():
    c = configuration()
    assert not c['old_draws_reused_as_new_posterior'] and not c['old_results_relabelled']
    assert not c['old_pressure_is_physical_inventory']
    assert not c['old_battery_installation_is_direct_material_output']
    assert c['recycling_in_R_counted_once']
    assert set(c['legacy_comparisons'].values()) == {'PROTOCOL_DRAFT_NOT_RUN'}


def test_one_producer_one_material_matches_existing_E25_and_focs():
    r, m, flows = example()
    price, _ = direct_price(r, m, flows)
    out = conditional_interior_price([r], [m], **flows)
    q, y = out['primary_output'][0], out['material_output'][0]
    assert out['price'] == pytest.approx(price)
    assert price - r.marginal_input_cost - r.convex_cost*q - r.adjustment*(q-r.lag_output) == pytest.approx(0, abs=1e-12)
    assert m.demand_shift - m.non_lc_cost - m.lc_per_material*price - m.revenue_curvature*y == pytest.approx(0, abs=1e-12)
    assert out['clearing_residual'] == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize('change', ['cost', 'demand', 'stock', 'imports', 'other_output', 'lag_output'])
def test_conditional_derivatives_share_clearing_denominator(change):
    r, m, flows = example()
    p0, den = direct_price(r, m, flows)
    h, g = 1e-5, r.convex_cost + r.adjustment
    if change == 'cost':
        r = replace(r, marginal_input_cost=r.marginal_input_cost+h)
        expected = 1/(g*den)
    elif change == 'demand':
        m = replace(m, demand_shift=m.demand_shift+h)
        expected = m.lc_per_material/(m.revenue_curvature*den)
    elif change == 'lag_output':
        expected = -r.adjustment/(g*den)
        r = replace(r, lag_output=r.lag_output+h)
    else:
        key = {'stock':'net_stock_addition', 'imports':'net_import', 'other_output':'recycled_lc'}[change]
        flows[key] += h
        expected = (1 if change == 'stock' else -1)/den
    p1 = conditional_interior_price([r], [m], **flows)['price']
    assert (p1-p0)/h == pytest.approx(expected, abs=1e-8)


def test_inventory_stock_flow_identity_is_separate_from_pressure_index():
    r, m, flows = example()
    out = conditional_interior_price([r], [m], **flows)
    previous_inventory, physical_loss = 2.0, 0.01
    end_inventory = ((1-physical_loss)*previous_inventory + out['primary_output'][0]
                     + flows['recycled_lc'] + flows['net_import']
                     - m.lc_per_material*out['material_output'][0] - flows['other_use'])
    assert end_inventory == pytest.approx((1-physical_loss)*previous_inventory + flows['net_stock_addition'])
    assert end_inventory >= 0


def test_using_total_output_requires_removing_separate_other_output_term():
    r, m, flows = example()
    out = conditional_interior_price([r], [m], **flows)
    total = out['primary_output'][0] + flows['recycled_lc']
    use = m.lc_per_material*out['material_output'][0] + flows['other_use']
    residual = total + flows['net_import'] - use - flows['net_stock_addition']
    assert residual == pytest.approx(0, abs=1e-12)
    assert residual + flows['recycled_lc'] != pytest.approx(0)


def test_yoy_is_twelve_month_log_changes_not_one_month():
    levels = [100.0 + i*i + i for i in range(14)]
    monthly = [log(levels[i])-log(levels[i-1]) for i in range(1, len(levels))]
    yoy = log(levels[12])-log(levels[0])
    assert yoy == pytest.approx(sum(monthly[:12]))
    assert yoy != pytest.approx(monthly[11])


def test_capacity_corner_is_not_silently_relabelled_interior():
    r, m, flows = example()
    r = replace(r, capacity=0.001)
    with pytest.raises(ValueError, match='interior'):
        conditional_interior_price([r], [m], **flows)


def test_unobserved_material_scale_is_not_identified_by_lc_clearing_alone():
    r, m, flows = example()
    base = conditional_interior_price([r], [m], **flows)
    scale = 2.0
    # Without observing Y or fixing engineering units, these scaled material
    # objects generate identical LC price, production and physical LC use.
    other = replace(m, demand_shift=m.demand_shift/scale,
                    non_lc_cost=m.non_lc_cost/scale,
                    lc_per_material=m.lc_per_material/scale,
                    revenue_curvature=m.revenue_curvature/scale**2,
                    lag_output=m.lag_output*scale, capacity=m.capacity*scale)
    scaled = conditional_interior_price([r], [other], **flows)
    assert scaled['price'] == pytest.approx(base['price'])
    assert scaled['primary_output'] == pytest.approx(base['primary_output'])
    assert scaled['material_output'][0] == pytest.approx(scale*base['material_output'][0])
    assert other.lc_per_material*scaled['material_output'][0] == pytest.approx(m.lc_per_material*base['material_output'][0])
