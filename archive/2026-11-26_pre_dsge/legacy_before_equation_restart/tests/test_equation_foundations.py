"""Pure synthetic algebra tests; not empirical estimation or prior calibration."""
import json
import math
import random
from pathlib import Path
import pytest
from src.theory_audit.equation_checks import (
    ProductionProblem, route_input_cost, interior_market, end_inventory, log_changes,
)


def test_interior_supply_matches_foc_and_grid_optimum():
    m=ProductionProblem(2.0,3.0,20.0)
    q=m.choose(12,2,4)
    assert q == pytest.approx(4.4)
    assert 12-2-2*q-3*(q-4) == pytest.approx(0)
    assert m.objective(q,12,2,4) >= max(m.objective(i/100,12,2,4) for i in range(2001))-1e-10


def test_supply_price_cost_and_inertia_are_linked():
    m=ProductionProblem(2,3,100)
    assert m.rho == pytest.approx(.6)
    assert m.alpha == pytest.approx(.2)
    assert m.choose(12,2,4)-m.choose(11,2,4) == pytest.approx(m.alpha)
    assert m.choose(12,3,4)-m.choose(12,2,4) == pytest.approx(-m.alpha)


def test_supply_capacity_and_shutdown_are_kkt_corners():
    m=ProductionProblem(1,1,10)
    assert m.choose(100,1,5)==10
    assert m.choose(1,100,5)==0
    assert m.objective(10,100,1,5)>m.objective(9.9,100,1,5)


@pytest.mark.parametrize('g,k,cap',[(0,1,10),(-1,1,10),(1,-1,10),(1,1,-1),(float('nan'),1,1)])
def test_supply_bad_curvature_constraints_rejected(g,k,cap):
    with pytest.raises(ValueError):ProductionProblem(g,k,cap)


def test_route_conversion_is_not_ore_price_subtraction():
    # Arbitrary illustrative units, NOT a calibrated recovery/input coefficient.
    converted=route_input_cost(10,4,7)
    assert converted==47
    assert 100-converted != 100-10


def market(j=5.0):
    return interior_market(100,2,5,j,20,.5,3,10)


def test_price_formula_clears_same_unit_market():
    p,q,u=market()
    assert q+5 == pytest.approx(u+5)
    assert p == pytest.approx(24)


def test_cost_passthrough_is_conditional_on_slopes():
    p,*_=market()
    p2,*_=interior_market(100,2,5,5,20,.5,3,11)
    assert p2-p==pytest.approx(3/5)


def test_inventory_initial_stock_and_target_have_opposite_effects():
    target,initial=15,10
    p,*_=market(target-initial)
    higher_target,*_=market(target+1-initial)
    higher_initial,*_=market(target-initial-1)
    assert higher_target>p>higher_initial


def test_bad_equilibrium_not_silently_clipped():
    with pytest.raises(ValueError):interior_market(1,2,100,0,20,.5,3,10)


def test_physical_inventory_ledger_closes():
    assert end_inventory(30,100,10,5,90,10,1)==34


def test_negative_inventory_is_visible_not_filled():
    with pytest.raises(ValueError):end_inventory(1,1,0,0,4,0)


def test_yoy_is_sum_of_twelve_monthly_log_changes():
    rng=random.Random(20260918)
    values=[100.]
    for _ in range(35):values.append(values[-1]*math.exp(rng.uniform(-.1,.15)))
    monthly=log_changes(values,1)
    yoy=log_changes(values,12)
    for j,v in enumerate(yoy):
        assert v==pytest.approx(sum(monthly[j:j+12]),abs=1e-12)


def test_same_growth_cannot_identify_physical_stock_balance():
    # Multiplying all output levels by ten leaves growth unchanged, not material balances.
    levels=[100*1.02**i for i in range(24)]
    scaled=[10*x for x in levels]
    assert log_changes(levels,12)==pytest.approx(log_changes(scaled,12))
    assert end_inventory(100,100,0,0,120,0)==80
    assert end_inventory(100,1000,0,0,120,0)==980


def test_whole_equation_yoy_filter_not_single_month_price():
    # Exact log-linear decision, then apply the same 12-period operator to every term.
    x_p=[.001*t*t for t in range(40)]
    x_c=[.004*t+.03*math.sin(t) for t in range(40)]
    x_q=[0.]
    rho,bp,bc=.4,.7,.2
    for t in range(1,40):x_q.append(rho*x_q[-1]+bp*x_p[t-1]-bc*x_c[t-1])
    for t in range(13,40):
        lhs=x_q[t]-x_q[t-12]
        rhs=(rho*(x_q[t-1]-x_q[t-13])+bp*(x_p[t-1]-x_p[t-13])
             -bc*(x_c[t-1]-x_c[t-13]))
        assert lhs==pytest.approx(rhs,abs=1e-12)
    wrong=rho*(x_q[-2]-x_q[-14])+bp*(x_p[-2]-x_p[-3])-bc*(x_c[-2]-x_c[-3])
    assert abs((x_q[-1]-x_q[-13])-wrong)>1e-3


def test_literature_is_evidence_not_fabricated_empirical_validation():
    root=Path(__file__).resolve().parents[1]
    raw=json.loads((root/'data/metadata/equation_evidence_20260918.json').read_text(encoding='utf-8'))
    sources=raw['sources']
    assert len(sources)==18
    assert len({x['id'] for x in sources})==18
    for x in sources:
        assert x['url'].startswith('https://')
        assert x['actually_read'] and x['does_not_establish'] and x['reading_level']
        assert x['empirical_evidence_for_legacy_equation'] is False


def test_documents_preserve_proposed_not_estimated_boundary():
    root=Path(__file__).resolve().parents[1]
    text=(root/'docs/theory/lithium_partial_equilibrium_v1.md').read_text(encoding='utf-8')
    assert 'NEW_ILLUSTRATIVE_DERIVATION_NOT_ESTIMATED' in text
    assert '不是现有M0微观基础已经完成的证明' in text
    assert 'D01保持IN_PROGRESS' in (root/'docs/research/equation_foundations_20260918.md').read_text(encoding='utf-8')
