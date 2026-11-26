"""Source provenance checks and original E25 algebra; no empirical validation."""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('industry_audit', ROOT/'scripts/audit_industry_library.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
from src.theory_audit.modular_equilibrium_checks import Route, Material, conditional_interior_price


def inputs():
    lib=json.loads((ROOT/'data/metadata/industry_literature_library_20260918.json').read_text(encoding='utf-8-sig'))
    bp=json.loads((ROOT/'configs/industry_equation_blueprint_v2.json').read_text(encoding='utf-8-sig'))
    return lib,bp


def put(record, lib, field, value):
    record[lib['columns'].index(field)] = value


def test_actual_ledger_counts_and_no_empirical_claim():
    lib,bp=inputs()
    assert audit.validate(lib,bp)==[]
    rows=audit.unpack(lib)
    assert len(rows)==45 and len(bp['relations'])==28
    assert sum(r['publication_type'] in {'JOURNAL_ARTICLE','WORKING_PAPER','PERSPECTIVE'} for r in rows)==34
    assert lib['full_text_read_count']==0 and not bp['estimated']


@pytest.mark.parametrize('mutation, expected', [
 ('duplicate_id','EMPTY_OR_DUPLICATE_SOURCES'),
 ('duplicate_doi','DUPLICATE_DOI'),
 ('missing_reading','INCOMPLETE_EVIDENCE'),
 ('fake_fulltext','FULL_TEXT_COUNT_MISMATCH'),
 ('wrong_type','INVALID_PUBLICATION_TYPE'),
 ('insecure_url','INVALID_SOURCE_URL'),
 ('row_width','INVALID_LIBRARY'),
 ('missing_policy','POLICY_TIMELINE_COVERAGE'),
 ('hidden_conflict','CONFLICT_HIDDEN'),
 ('bad_date','INVALID_POLICY_DATE'),
 ('wrong_after_sample','WRONG_AFTER_SAMPLE'),
 ('unknown_eq_source','UNKNOWN_RELATION_SOURCE'),
 ('fake_exact_equation','UNVERIFIED_EXACT_ATTRIBUTION'),
 ('fake_estimation','EMPIRICAL_CLAIM_WITHOUT_RUN'),
 ('fake_parameter_count','UNFROZEN_PARAMETER_COUNT'),
 ('premature_closure','UNAPPROVED_CLOSURE_CHOICE'),
 ('duplicate_equation','RELATION_COUNT_OR_DUPLICATE'),
 ('empty_blueprint','RELATION_COUNT_OR_DUPLICATE'),
])
def test_failure_conditions(mutation,expected):
    lib,bp=inputs()
    if mutation=='duplicate_id':put(lib['records'][1],lib,'id',lib['records'][0][0])
    elif mutation=='duplicate_doi':put(lib['records'][1],lib,'doi',lib['records'][0][lib['columns'].index('doi')].upper())
    elif mutation=='missing_reading':put(lib['records'][0],lib,'parts_read','')
    elif mutation=='fake_fulltext':lib['full_text_read_count']=45
    elif mutation=='wrong_type':put(lib['records'][0],lib,'publication_type','FULL_DSGE_PROOF')
    elif mutation=='insecure_url':put(lib['records'][0],lib,'url','file:///private')
    elif mutation=='row_width':lib['records'][0].pop()
    elif mutation=='missing_policy':lib['policy_timelines'].pop()
    elif mutation=='hidden_conflict':next(t for t in lib['policy_timelines'] if t.get('date_conflict'))['issued_date']='2025-01-26'
    elif mutation=='bad_date':lib['policy_timelines'][-1]['effective_date']='2026-99-01'
    elif mutation=='wrong_after_sample':lib['policy_timelines'][-1]['effective_date']='2025-01-01'
    elif mutation=='unknown_eq_source':bp['relations'][0]['sources']=['NOT_READ']
    elif mutation=='fake_exact_equation':bp['relations'][0]['source_role']='COPIED_EXACTLY'
    elif mutation=='fake_estimation':bp['estimated']=True
    elif mutation=='fake_parameter_count':bp['free_parameter_count']=28
    elif mutation=='premature_closure':bp['closure_choice']='ALL_CLOSURES_AT_ONCE'
    elif mutation=='duplicate_equation':bp['relations'][1]['id']=bp['relations'][0]['id']
    elif mutation=='empty_blueprint':bp['relations']=[];bp['relation_group_count']=0
    assert any(e.startswith(expected) for e in audit.validate(lib,bp))


def example():
    # Arbitrary normalized toy units, NOT lithium engineering calibration.
    routes=[Route(2.,2.,1.,1.,20.),Route(3.,3.,.5,1.,20.)]
    materials=[Material(20.,1.,1.,2.,.5,1.,20.),Material(18.,1.,.8,3.,.5,1.,20.)]
    return routes,materials


def test_multiroute_multidemand_clearing_and_fo_conditions():
    routes,materials=example()
    result=conditional_interior_price(routes,materials,net_import=.2,recycled_lc=.1,other_use=.4,net_stock_addition=.3)
    p=result['price']
    assert abs(result['clearing_residual'])<1e-12
    for q,r in zip(result['primary_output'],routes):
        assert abs(p-r.marginal_input_cost-r.convex_cost*q-r.adjustment*(q-r.lag_output))<1e-12
    for y,m in zip(result['material_output'],materials):
        assert abs(m.demand_shift-m.non_lc_cost-m.lc_per_material*p-m.revenue_curvature*y-m.adjustment*(y-m.lag_output))<1e-12


def test_cost_pass_through_is_joint_denominator_not_arbitrary_loading():
    r,m=example();base=conditional_interior_price(r,m);h=1e-5
    altered=[replace(r[0],marginal_input_cost=r[0].marginal_input_cost+h),r[1]]
    actual=(conditional_interior_price(altered,m)['price']-base['price'])/h
    expected=base['inverse_excess_supply_slope']/(r[0].convex_cost+r[0].adjustment)
    assert actual==pytest.approx(expected,abs=1e-9)


def test_stock_purchase_and_import_have_opposite_conditional_effects():
    r,m=example();base=conditional_interior_price(r,m)
    positive=conditional_interior_price(r,m,net_stock_addition=.1)
    negative=conditional_interior_price(r,m,net_import=.1)
    recycled=conditional_interior_price(r,m,recycled_lc=.1)
    assert positive['price']>base['price']>negative['price']
    assert recycled['price']==pytest.approx(negative['price'])


def test_capacity_corner_not_silently_clipped_as_same_interior_model():
    r,m=example();r[0]=replace(r[0],capacity=.001)
    with pytest.raises(ValueError,match='interior'):conditional_interior_price(r,m)


@pytest.mark.parametrize('kind',['empty','nonfinite','negative_curvature','negative_recycling'])
def test_invalid_inputs_fail(kind):
    r,m=example();kwargs={}
    if kind=='empty':r=[]
    if kind=='nonfinite':kwargs['net_import']=float('nan')
    if kind=='negative_curvature':r[0]=replace(r[0],convex_cost=-1.)
    if kind=='negative_recycling':kwargs['recycled_lc']=-1.
    with pytest.raises(ValueError):conditional_interior_price(r,m,**kwargs)
