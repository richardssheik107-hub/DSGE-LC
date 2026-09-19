"""Numerical theory checks. No calibration, likelihood, posterior or OOS data."""
from dataclasses import replace
from pathlib import Path
import json
import numpy as np
import pytest
from src.rebuild_theory.capacity_storage_v1 import (
    Parameters, reference, reference_residuals, primitives, stage_loss, solve, euler_residuals,
)
ROOT=Path(__file__).resolve().parents[1]


def params():
    data=json.loads((ROOT/'configs/capacity_storage_synthetic_v1.json').read_text())
    assert data['purpose']=='SYNTHETIC_NUMERICAL_CHECK_ONLY_NOT_LITHIUM_CALIBRATION'
    assert not data['lead_is_industry_estimate']
    return Parameters(**data['parameters'])


@pytest.mark.parametrize('lead',[1,2,3,6,12,24])
def test_all_steady_conditions_and_physical_interior(lead):
    p=replace(params(),lead=lead); r=reference(p)
    assert max(abs(v) for v in reference_residuals(p,r).values())<1e-9
    assert 0<r.Q<r.K and min(r.I,r.Y,r.P,r.J)>0


@pytest.mark.parametrize('lead',[1,2,3,6,12,24])
@pytest.mark.parametrize('mode',['joint','capacity_only','storage_only'])
def test_riccati_and_every_euler_coefficient(lead,mode):
    s=solve(replace(params(),lead=lead),mode)
    expected={'joint':lead+4,'capacity_only':lead+3,'storage_only':4}[mode]
    assert s.transition.shape==(expected,expected)
    assert s.shocks.shape==(expected,2)
    assert s.spectral_radius<1 and s.riccati_residual<1e-9
    assert max(euler_residuals(s).values())<1e-9


@pytest.mark.parametrize('lead',[1,2,3,6])
def test_investment_arrives_after_exactly_L_periods(lead):
    p=replace(params(),lead=lead); F,G,_,_=primitives(p,reference(p))
    x=G[:,2].copy()
    for time in range(1,lead):
        assert x[4]==0
        x=F@x
    assert x[4]==1
    assert np.sum(x[5:])==0


@pytest.mark.parametrize('change',[
    {'beta':1.0},{'delta':0.0},{'gamma':0.0},{'kappa':-1.0},
    {'storage_service':0.0},{'loss':-0.1},{'rho_d':1.0},
    {'sigma_c':-1.0},{'a':float('nan')},{'lead':0},{'lead':2.5},{'lead':True},
])
def test_invalid_domain_rejected(change):
    with pytest.raises(ValueError): solve(replace(params(),**change))


def test_pure_storage_cannot_be_disguised_as_positive_stationary_stock():
    p=params();r=reference(p)
    # No service, nonnegative carrying cost and positive price cannot satisfy
    # positive-stock deterministic equality. Its zero-stock regime is different.
    gap=(1-p.beta*(1-p.loss))*r.P+p.storage_cost
    assert gap>0
    with pytest.raises(ValueError,match='storage service'):
        solve(replace(p,storage_service=0.0))


def test_stock_level_really_changes_current_equilibrium_output():
    s=solve(params())
    col=s.state_order.index('i_lag')
    assert abs(s.outputs[0,col])>1e-4
    assert abs(s.transition[s.state_order.index('q_lag'),col])>1e-4


def test_capacity_has_value_even_with_slack_constraint():
    p=params();r=reference(p)
    assert r.Q/r.K<1 and r.W>0
    assert p.gamma/2*(r.Q/r.K)**2>0


def test_zero_deviations_mean_reference_levels_not_zero_economy():
    s=solve(params()); nxt,out=s.step(np.zeros(6),np.zeros(2))
    assert np.allclose(nxt,0)
    assert out['P']==pytest.approx(s.ref.P) and out['Q']==pytest.approx(s.ref.Q)


def test_invalid_physical_path_is_not_clipped():
    s=solve(params());x=np.zeros(6);x[3]=-2*s.ref.I
    with pytest.raises(ValueError,match='interior'): s.step(x,np.zeros(2))
    with pytest.raises(ValueError): s.step(np.zeros(4),np.zeros(2))
    with pytest.raises(ValueError): s.step(np.zeros(6),np.array([np.nan,0.]))


def test_zero_loss_still_has_endogenous_stock_feedback_and_stable_local_solution():
    s=solve(replace(params(),loss=0.0))
    assert s.spectral_radius<1
    assert max(euler_residuals(s).values())<1e-9


def test_hessian_matches_nonlinear_surplus_finite_differences():
    p=params();r=reference(p);_,_,_,H=primitives(p,r)
    n=H.shape[0];zero=np.zeros(n);h=1e-3
    eye=np.eye(n); numeric=np.zeros_like(H)
    for i in range(n):
        for j in range(n):
            numeric[i,j]=(stage_loss(p,r,h*(eye[i]+eye[j]))-stage_loss(p,r,h*(eye[i]-eye[j]))
                          -stage_loss(p,r,h*(-eye[i]+eye[j]))+stage_loss(p,r,-h*(eye[i]+eye[j])))/(4*h*h)
    assert np.max(np.abs(numeric-H))<2e-6


def deterministic_nonlinear_residual(s,x):
    p,r=s.params,s.ref
    xp,o=s.step(x,np.zeros(2));_,op=s.step(xp,np.zeros(2))
    qlag=r.Q+x[2]; cost=p.unit_cost_mean+x[1]
    prod=o['P']-cost-p.gamma*o['Q']/o['K']-p.kappa*(o['Q']-qlag)+p.beta*p.kappa*(op['Q']-o['Q'])
    stock=o['P']+p.storage_cost-p.storage_service/o['I']-p.beta*(1-p.loss)*op['P']
    return max(abs(prod),abs(stock))


def test_local_solution_has_second_order_nonlinear_remainder():
    s=solve(params());direction=np.array([.3,-.2,.4,.5,.6,.1])
    big=deterministic_nonlinear_residual(s,.01*direction)
    small=deterministic_nonlinear_residual(s,.005*direction)
    assert big>0 and .22<small/big<.28


def test_short_synthetic_path_balances_without_future_realised_inputs():
    s=solve(params()); x=np.zeros(6); x[0]=.001
    for _ in range(24):
        nxt,o=s.step(x,np.zeros(2))
        r,p=s.ref,s.params
        balance=(1-p.loss)*(r.I+x[3])+o['Q']+p.net_flow-p.a*o['Y']-o['I']
        assert abs(balance)<1e-10
        assert np.all(np.isfinite(nxt));x=nxt
