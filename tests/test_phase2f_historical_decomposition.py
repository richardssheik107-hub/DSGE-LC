"""Phase 2F shock reconstruction, decomposition, episode and subset tests."""
from __future__ import annotations

import numpy as np
import pytest

from src.structural.historical_decomposition import *


def fixture_system():
    A=np.diag([.5,.6,.7,.8,.4]);B=np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,0],[.2,.3,-.4,1.]])
    shocks=np.array([[1.,2.,3.,4.],[-1.,.5,0.,2.],[.2,-.3,.8,-1.]])
    initial=np.array([.2,-.1,.3,.4,.5]);ic,c=historical_contributions(A,B,initial,shocks);states=ic+c.sum(1)
    return A,B,shocks,initial,states,ic,c


def test_15_b_full_column_rank():
    assert np.linalg.matrix_rank(fixture_system()[1])==4


def test_16_known_epsilon_recovered_exactly():
    A,B,shocks,_,states,_,_=fixture_system();got,_,error,rank=reconstruct_smoothed_shocks(states,A,B)
    assert rank==4 and error<1e-12 and np.allclose(got,shocks)


def test_17_no_pseudoinverse_used():
    import inspect
    assert "pinv" not in inspect.getsource(reconstruct_smoothed_shocks)
    assert 'lapack_driver="gelsy"' in inspect.getsource(reconstruct_smoothed_shocks)


def test_18_b_epsilon_reconstructs_transition_residual():
    A,B,_,_,states,_,_=fixture_system();shocks,residual,_,_=reconstruct_smoothed_shocks(states,A,B)
    assert np.allclose(shocks@B.T,residual)


def test_19_shock_order_preserved():
    A,B,shocks,_,states,_,_=fixture_system();got,_,_,_=reconstruct_smoothed_shocks(states,A,B)
    assert np.allclose(got[:,[0,1,2,3]],shocks)


def test_20_initial_condition_recursion():
    A,_,_,initial,_,ic,_=fixture_system();assert np.allclose(ic[0],initial) and np.allclose(ic[2],A@A@initial)


def test_21_shock_contribution_recursion():
    A,B,shocks,_,_,_,c=fixture_system();assert np.allclose(c[1],shocks[0,:,None]*B.T) and np.allclose(c[2],c[1]@A.T+shocks[1,:,None]*B.T)


def test_22_sum_contributions_equals_state_path():
    _,_,_,_,states,ic,c=fixture_system();assert decomposition_identity_error(states,ic,c)<1e-12


def test_23_t0_has_no_fabricated_shock():
    assert np.all(fixture_system()[-1][0]==0)


def test_24_first_shock_is_second_sample_month():
    _,_,shocks,_,_,_,c=fixture_system();assert np.allclose(c[1,:,4],shocks[0]*fixture_system()[1][4])


def test_25_price_state_index_exact():
    assert fixture_system()[-1].shape[-1]==5 and np.any(fixture_system()[-1][...,4])


def test_26_spot_measurement_identity_consistent():
    states=fixture_system()[4];H=np.array([[0,0,0,0,1.]])
    assert np.allclose(states@H.T,states[:,4,None])


def test_27_window_boundaries_exact():
    months=np.array(["2021-01","2021-02","2021-03","2021-04"]);idx=np.where((months>="2021-02")&(months<="2021-03"))[0]
    assert idx.tolist()==[1,2]


def test_28_net_contribution_sum_correct():
    values=np.arange(24.).reshape(2,3,4);assert np.allclose(episode_contributions(values,[1,2]),values[:,1:3].sum(1))


def test_29_absolute_activity_nonnegative():
    activity,_=activity_shares(np.array([[[1,-2],[3,-4]]]),[0,1]);assert np.all(activity>=0)


def test_30_activity_shares_sum_to_one():
    _,shares=activity_shares(np.array([[[1,-2],[3,-4]]]),[0,1]);assert np.allclose(shares.sum(-1),1)


def test_zero_activity_share_is_undefined_not_four_zeros():
    _, shares = activity_shares(np.zeros((2, 3, 4)), [0, 1, 2])
    assert np.isnan(shares).all()


def test_31_signed_net_shares_not_used():
    import inspect
    assert "abs(values" in inspect.getsource(activity_shares)


def test_32_dominant_shock_classification():
    activity,shares=activity_shares(np.array([[[1,2,1,1],[1,3,1,1]]]),[0,1]);assert np.argmax(shares[0])==1


def test_33_equal_draws_per_chain():
    x=np.arange(4*20*2).reshape(4,20,2);subset,indices=select_equal_per_chain(x,5,7);assert subset.shape==(4,5,2) and indices.shape==(4,5)


def test_34_fixed_seed():
    x=np.arange(4*20).reshape(4,20,1);assert np.array_equal(select_equal_per_chain(x,5,7)[1],select_equal_per_chain(x,5,7)[1])


def test_35_selection_is_not_thinning():
    x=np.arange(4*100).reshape(4,100,1);idx=select_equal_per_chain(x,20,7)[1];assert not np.all(np.diff(idx[0])==np.diff(idx[0])[0])


def test_36_subset_median_metric():
    rng=np.random.default_rng(1);x=rng.normal(size=(4,1000,3));subset,_=select_equal_per_chain(x,500,2);assert np.max(np.abs(subset_representativeness(x,subset)))<.1


def test_rank_failure_is_hard_error():
    A,B,_,_,states,_,_=fixture_system();B[:,3]=B[:,2]
    with pytest.raises(ValueError,match="full column rank"):reconstruct_smoothed_shocks(states,A,B)
