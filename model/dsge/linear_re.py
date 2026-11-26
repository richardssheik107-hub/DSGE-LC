"""Local rational-expectations diagnostics and leading risky-portfolio selection.

This module linearizes the original selected-regime equations, selects a stable
(or neutral wealth) generalized-Schur subspace, and uses *second-order* pricing
covariances to determine zero-order risky holdings. It never identifies those
holdings using the rank-one first-order futures-pricing block.

The solution is local. Three permanent-owner wealth roots may be neutral; no
ergodic wealth distribution or global transversality proof follows from this.
"""
import numpy as np
from scipy.linalg import ordqz
from scipy.optimize import root
from .local_projection import LocalProjection


def complex_jacobian(fun, x, step=1e-25):
    x=np.asarray(x,dtype=float)
    return np.column_stack([np.imag(fun(x.astype(complex)+1j*step*np.eye(len(x))[j]))/step
                            for j in range(len(x))])


def solve_linear(projection, holdings=(0.,0.), unit_root_tolerance=2e-7):
    """Return linear control coefficients after stable-subspace selection.

    ``holdings`` are the level I,D futures positions (F clears). They remain
    arbitrary at first order; use ``select_portfolio`` for their leading risky
    choice under the slack collateral regime.
    """
    m=projection; ns=m.ns; ny=m.npositive
    h2=np.asarray(holdings,dtype=float)
    hedge=np.r_[h2,-h2.sum()]
    center=m.center.copy();center[m.hslice]=h2
    keep=np.r_[np.arange(11),np.arange(13,m.nu)]
    def recover(dx,dy):
        x=center+np.asarray(dx)*m.scale
        y=m.positive_anchor*np.exp(dy)
        return x,m.recover(x[None,:],y[None,:],hedge[None,:])
    def equilibrium(v):
        x,a=recover(v[:ns],v[ns:ns+ny])
        xf,af=recover(v[ns+ny:2*ns+ny],v[2*ns+ny:])
        f={key:value[:,None,...] for key,value in af.items()}
        return m.conditions(x[None,:],a,f,scaled=True,probabilities=np.ones(1))[keep]
    der=complex_jacobian(equilibrium,np.zeros(2*(ns+ny)))
    fx,fy,fxp,fyp=np.split(der,[ns,ns+ny,2*ns+ny],axis=1)
    def transition(v):
        x,a=recover(v[:ns],v[ns:])
        nxt=m.prob @ m.successors(x[None,:],a)[0]
        return (nxt-center)/m.scale
    dt=complex_jacobian(transition,np.zeros(ns+ny))
    tx,ty=dt[:,:ns],dt[:,ns:]
    # A E[z'] = B z, ordered generalized eigenvalues of (B,A).
    a=np.block([[np.eye(ns),np.zeros((ns,ny))],[-fxp,-fyp]])
    b=np.block([[tx,ty],[fx,fy]])
    select=lambda alpha,beta:np.abs(alpha) <= (1+unit_root_tolerance)*np.abs(beta)
    bs,as_,alpha,beta,q,z=ordqz(b,a,sort=select,output='complex')
    pair_norm=np.abs(alpha)+np.abs(beta)
    indeterminate=int(np.sum(pair_norm < 1e-12))
    if indeterminate:
        raise RuntimeError('Generalized pencil contains indeterminate zero/zero pairs')
    eig=np.divide(alpha,beta,out=np.full_like(alpha,np.inf),where=abs(beta)>1e-14)
    stable=np.flatnonzero(select(alpha,beta))
    if len(stable)!=ns:
        raise RuntimeError(f'Expected {ns} stable/neutral roots; found {len(stable)}: {eig}')
    upper=z[:ns,:ns];lower=z[ns:,:ns]
    if np.linalg.matrix_rank(upper)!=ns:
        raise RuntimeError('Stable eigenspace is not a graph over the predetermined states')
    policy=lower@np.linalg.inv(upper)
    if np.max(abs(policy.imag))>1e-6:
        raise RuntimeError('Complex linear decision rule exceeds numerical tolerance')
    policy=policy.real
    closed=tx+ty@policy
    residual=fx+fy@policy+(fxp+fyp@policy)@closed
    return dict(policy=policy,transition=closed,eigenvalues=eig,
                closed_eigenvalues=np.linalg.eigvals(closed),
                stable_count=len(stable),state_count=ns,control_count=ny,
                graph_condition_number=float(np.linalg.cond(upper)),
                linear_equation_max_residual=float(np.max(abs(residual))),
                holdings=hedge,derivatives=dict(fx=fx,fy=fy,fxp=fxp,fyp=fyp,tx=tx,ty=ty),
                generalized_indeterminate_pairs=indeterminate,
                generalized_min_pair_norm=float(np.min(pair_norm)))


def portfolio_conditions(projection, solution):
    """Leading covariance equalities across I,D,F; one independent priced payoff."""
    m=projection;p=m.p
    # Conditional next-state risk arises through the four z innovations only.
    load=solution['policy'][:,:4]*np.array(p.shock_scales)[None,:]/m.scale[:4]
    spotload=m.c0.spot*load[4]
    # Normalized SDF innovation = -gamma_j * dlog(c_j).
    sdfload=-np.array(p.gamma)[:,None]*load[7:11]
    cov=sdfload@spotload
    difference=np.array([cov[2]-cov[1],cov[3]-cov[1]])
    return dict(differences=difference,covariances=cov,spot_innovation_load=spotload,
                consumption_log_innovation_load=load[7:11],
                conditional_spot_variance=float(spotload@spotload))


def select_portfolio(projection, initial=(-.10,.05)):
    m=projection
    def objective(h):
        solution=solve_linear(m,h)
        return portfolio_conditions(m,solution)['differences']/(m.risk_scale**2*m.c0.spot)
    result=root(objective,np.array(initial,dtype=float),tol=1e-9)
    solution=solve_linear(m,result.x)
    pricing=portfolio_conditions(m,solution)
    checked_residual=objective(result.x)
    if not np.all(np.isfinite(checked_residual)) or max(abs(checked_residual))>1e-7:
        raise RuntimeError('Leading risky portfolio selection failed residual gate: '+str(result.message))
    collateral_slack=(m.p.beta*m.c0.next_bonds[3]
                      -m.p.collateral_bar*m.c0.spot*abs(solution['holdings'][2]))
    if collateral_slack <= 0:
        raise ValueError('Leading portfolio violates the selected slack-collateral regime')
    coef=np.zeros((m.nu,m.nbasis))
    coef[:m.npositive,1:]=solution['policy']
    coef[m.npositive:,0]=result.x/m.hedge_scale
    return dict(solution=solution,pricing=pricing,coefficients=coef,
                portfolio_solver_success=bool(result.success),
                portfolio_scaled_residual=float(max(abs(objective(result.x)))),
                portfolio_evaluations=int(result.nfev),
                zero_risk_anchor_collateral_slack=float(collateral_slack))


def futures_tangent_audit(projection):
    """The three original E22 FOCs, not a single retained pricing row."""
    m=projection;p=m.p
    def foc(v):
        current_f=m.c0.forward*np.exp(v[0])
        future_p=m.c0.spot*np.exp(v[1])
        sdf=p.beta*np.exp(-np.array(p.gamma)*v[2:6])
        # v[6:8] are the two independent holdings; zero payoff eliminates them.
        return sdf[1:]*(future_p-current_f)
    matrix=complex_jacobian(foc,np.zeros(8))
    singular=np.linalg.svd(matrix,compute_uv=False)
    return {'rank':int(np.linalg.matrix_rank(matrix,tol=1e-10)),
            'matrix':matrix.tolist(),'singular_values':singular.tolist(),
            'columns':['log_current_F','log_future_P','log_future_cW','log_future_cI',
                       'log_future_cD','log_future_cF','current_hI','current_hD'],
            'rows':['original_E22_I','original_E22_D','original_E22_F_slack'],
            'holdings_derivative_max':float(np.max(abs(matrix[:,-2:]))),
            'scope':'original futures first-order tangent block only, at zero-risk payoff'}


def linear_irfs(projection,solution,horizon=36):
    """Conditional-mean responses to a +1 innovation, retaining future risk.

    These are first-order local responses, not nonlinear GIRFs. A zero baseline
    innovation is the unconditional innovation *mean*, not a third support atom.
    """
    m=projection;p=m.p;ns=m.ns;ny=m.npositive
    center=m.center.copy();center[m.hslice]=solution['holdings'][:2]
    hedge=solution['holdings']
    names=['Q','J','C','P','F','w','q_bond','cW','cI','cD','cF','K_effective',
           'Y','YB','Y0','N','ND','N0','Ds','bW_next','bI_next','bD_next','bF_next','F_net_worth']
    def observables(v):
        x=center+m.scale*v[:ns]
        a=m.recover(x[None,:],(m.positive_anchor*np.exp(v[ns:]))[None,:],hedge[None,:])
        a={key:value[0] for key,value in a.items()}
        wealth=-sum(x[m.bslice])+hedge[2]*(a['spot']-x[m.findex])
        return np.r_[a['q'],a['j'],a['c'],a['spot'],a['forward'],a['w'],a['bond_price'],
                     a['consumption'],a['capacity'],a['output'],a['yb'],a['y0'],a['nw'],
                     a['nd'],a['n0'],a['ds'],a['next_bonds'],wealth]
    zero=np.zeros(ns+ny);baseline=observables(zero)
    derivative=complex_jacobian(observables,zero)
    policy=solution['policy'];g=solution['transition']
    mapping=derivative[:,:ns]+derivative[:,ns:]@policy
    rows=[];states=[]
    for shock,name in enumerate(p.shock_names):
        state=np.zeros(ns);state[shock]=p.shock_scales[shock]/m.scale[shock]
        for period in range(horizon+1):
            delta=mapping@state
            choice_delta=policy@state
            next_expected_spot=m.c0.spot*(policy@g@state)[4]
            row={'shock':name,'month':period,'innovation':1.0,'sigma':p.shock_scales[shock]}
            for key,change,base in zip(names,delta,baseline):
                row[key+'_change']=float(change)
                if key not in ['bW_next','bI_next','bD_next','bF_next']:
                    row[key+'_percent']=float(100*change/base)
            row['basis_change']=float(delta[4]-delta[3])
            row['first_order_premium_change']=float(next_expected_spot-delta[4])
            rows.append(row);states.append((name,period,state.copy()))
            state=g@state
    return {'rows':rows,'normalized_states':states,'baseline':dict(zip(names,baseline)),
            'observable_derivative':mapping,'horizon':horizon}
