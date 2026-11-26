import numpy as np
import pytest

from src.theory_audit.c0_state_space import (
    C0StateParams, CONTROL_ORDER, OUTPUT_ORDER, SHOCK_ORDER, STATE_ORDER,
    one_step, output_matrices, reduced_coefficients, transition_matrices,
)


def params():
    return C0StateParams(g=2.0, kappa=1.0, b=3.0, a=1.2,
                         rho_d=.7, rho_c=.6, sigma_d=.1, sigma_c=.2,
                         inventory_loss=.01)


def primitive_solution(p, x_lag, shocks, u):
    z = p.rho_d*x_lag[0] + p.sigma_d*shocks[0]
    c = p.rho_c*x_lag[1] + p.sigma_c*shocks[1]
    v, other, j, net_import, other_output = u
    G = p.g+p.kappa
    D = p.a*p.a/p.b + 1/G
    price = (p.a*(z-v)/p.b + other+j-net_import-other_output
             + (c-p.kappa*x_lag[2])/G)/D
    q = (price-c+p.kappa*x_lag[2])/G
    y = (z-v-p.a*price)/p.b
    inv = (1-p.inventory_loss)*x_lag[3] + j
    return np.array([z,c,q,inv]), np.array([price,y])


def test_orders_are_explicit_and_small():
    assert STATE_ORDER == ("z_demand", "c_unit_cost", "q_reference", "i_physical")
    assert SHOCK_ORDER == ("eps_demand", "eps_cost")
    assert len(CONTROL_ORDER) == 5 and OUTPUT_ORDER == ("p_lc", "y_material")


def test_affine_matrices_match_primitive_equilibrium():
    p=params(); x0=np.array([.2,-.1,.5,2.0]); e=np.array([.3,-.2]); u=np.array([.1,.2,.05,.07,.03])
    expected_x, expected_out = primitive_solution(p,x0,e,u)
    x,out=one_step(p,x0,e,u)
    assert x == pytest.approx(expected_x, abs=1e-12)
    assert out == pytest.approx(expected_out, abs=1e-12)


def test_price_is_output_not_independent_ar_state():
    A,B,C=transition_matrices(params()); H,De,F=output_matrices(params())
    assert A.shape==(4,4) and B.shape==(4,2) and C.shape==(4,5)
    assert H.shape==(2,4) and De.shape==(2,2) and F.shape==(2,5)
    assert "p_lc" not in STATE_ORDER


def test_inventory_is_accounting_state_under_E24_not_feedback_state():
    p=params(); A,B,C=transition_matrices(p)
    assert A[3,3] == pytest.approx(1-p.inventory_loss)
    assert C[3,CONTROL_ORDER.index("j_net_stock")] == 1
    assert np.all(A[:3,3] == 0)


def test_cost_and_demand_signs_follow_joint_equilibrium():
    p=params(); c=reduced_coefficients(p)
    assert c["phi_a"]>0 and c["phi_m"]>0 and c["phi_f"]>0
    assert c["q_z"]>0 and c["q_c"]<0 and c["q_q"]>=0


def test_net_import_and_other_output_reduce_price_while_stock_addition_raises_it():
    p=params(); H,De,F=output_matrices(p)
    assert F[0,CONTROL_ORDER.index("j_net_stock")] > 0
    assert F[0,CONTROL_ORDER.index("n_net_import")] < 0
    assert F[0,CONTROL_ORDER.index("r_other_output")] < 0


def test_non_lc_cost_reduces_material_output_and_lc_price():
    p=params(); H,De,F=output_matrices(p)
    idx=CONTROL_ORDER.index("v_non_lc")
    assert F[1,idx] < 0
    assert F[0,idx] < 0


def test_market_clearing_holds_in_primitive_solution():
    p=params(); x0=np.array([.2,-.1,.5,2.0]); e=np.array([.3,-.2]); u=np.array([.1,.2,.05,.07,.03])
    x,out=primitive_solution(p,x0,e,u)
    q=x[2]; price,y=out; v,other,j,n,r=u
    assert q+r+n-p.a*y-other-j == pytest.approx(0,abs=1e-12)


def test_invalid_parameters_fail_closed():
    with pytest.raises(ValueError):
        transition_matrices(C0StateParams(g=0,kappa=1,b=3,a=1,rho_d=.7,rho_c=.6,sigma_d=.1,sigma_c=.1))
    with pytest.raises(ValueError):
        transition_matrices(C0StateParams(g=2,kappa=1,b=3,a=1,rho_d=1.1,rho_c=.6,sigma_d=.1,sigma_c=.1))


def test_zero_shocks_controls_preserve_origin():
    p=params(); x,out=one_step(p,np.zeros(4),np.zeros(2),np.zeros(5))
    assert np.allclose(x,0) and np.allclose(out,0)
