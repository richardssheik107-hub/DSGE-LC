"""Local capacity-storage equilibrium. THEORY/SYNTHETIC ONLY; no data estimator.

Price-taking sectors share a constant discount factor and expectations. A
separable surplus potential yields their equilibrium FOCs. The Riccati solution
is a first-order interior solution, not a global occasionally-binding solver.
Unmodelled net flows are fixed at the reference; no future realised inputs enter.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal
import numpy as np
from numpy.typing import NDArray
from scipy.linalg import solve_discrete_are
from scipy.optimize import brentq

Array = NDArray[np.float64]
Mode = Literal['joint', 'capacity_only', 'storage_only']


@dataclass(frozen=True)
class Parameters:
    beta: float
    delta: float
    gamma: float
    kappa: float
    a: float
    b: float
    invest_price: float
    invest_curvature: float
    storage_cost: float
    storage_service: float
    loss: float
    demand_mean: float
    non_lc_cost: float
    unit_cost_mean: float
    net_flow: float
    rho_d: float
    rho_c: float
    sigma_d: float
    sigma_c: float
    lead: int

    def validate(self) -> None:
        if isinstance(self.lead, bool) or not isinstance(self.lead, int) or self.lead < 1:
            raise ValueError('lead must be a positive integer, not an estimated month count')
        if not all(np.isfinite(v) for v in asdict(self).values()):
            raise ValueError('nonfinite parameter')
        if not 0 < self.beta < 1 or not 0 < self.delta < 1 or not 0 <= self.loss < 1:
            raise ValueError('invalid discount, depreciation or physical loss')
        positive = (self.gamma, self.a, self.b, self.invest_price,
                    self.invest_curvature, self.storage_service, self.unit_cost_mean)
        if min(positive) <= 0:
            raise ValueError('positive interior requires positive technology, investment and storage service')
        if min(self.kappa, self.storage_cost, self.sigma_d, self.sigma_c) < 0:
            raise ValueError('negative curvature, cash storage cost or shock scale')
        if max(abs(self.rho_d), abs(self.rho_c)) >= 1:
            raise ValueError('exogenous processes must be stationary in this candidate')


@dataclass(frozen=True)
class Reference:
    Q: float
    K: float
    I: float
    Y: float
    P: float
    J: float
    W: float


def reference(p: Parameters) -> Reference:
    """Unique slack-capacity, positive-stock deterministic reference, when it exists.

Solve for utilisation r=Q/K. No arbitrary state levels are inserted. This does
not calibrate any parameter to the lithium industry.
"""
    p.validate()
    theta_k = 1 - p.beta * (1-p.delta)
    theta_i = 1 - p.beta * (1-p.loss)
    def from_ratio(r: float) -> Reference:
        price = p.unit_cost_mean + p.gamma*r
        value = 0.5*p.gamma*r*r/theta_k
        cap = (p.beta**p.lead*value-p.invest_price)/(p.invest_curvature*p.delta)
        stock = p.storage_service/(p.storage_cost+theta_i*price)
        material = (p.demand_mean-p.non_lc_cost-p.a*price)/p.b
        return Reference(r*cap, cap, stock, material, price, p.delta*cap, value)
    lower = np.sqrt(2*theta_k*p.invest_price/(p.beta**p.lead*p.gamma))
    upper = min(1.0, (p.demand_mean-p.non_lc_cost-p.a*p.unit_cost_mean)/(p.a*p.gamma))
    if not 0 < lower < upper:
        raise ValueError('no positive-investment, slack-capacity interior reference')
    def balance(r: float) -> float:
        s = from_ratio(r)
        return s.Q+p.net_flow-p.a*s.Y-p.loss*s.I
    if not balance(lower) < 0 < balance(upper):
        raise ValueError('reference lies at a boundary or outside the admissible interior')
    ans = from_ratio(brentq(balance, lower, upper, xtol=1e-13, rtol=1e-13))
    if min(ans.Q, ans.K-ans.Q, ans.I, ans.Y, ans.P, ans.J) <= 0:
        raise ValueError('invalid physical reference')
    return ans


def reference_residuals(p: Parameters, r: Reference) -> dict[str, float]:
    return {
        'production': r.P-p.unit_cost_mean-p.gamma*r.Q/r.K,
        'demand': p.demand_mean-p.non_lc_cost-p.b*r.Y-p.a*r.P,
        'balance': r.Q+p.net_flow-p.a*r.Y-p.loss*r.I,
        'capacity': r.J-p.delta*r.K,
        'capacity_value': (1-p.beta*(1-p.delta))*r.W-0.5*p.gamma*(r.Q/r.K)**2,
        'investment': p.invest_price+p.invest_curvature*r.J-p.beta**p.lead*r.W,
        'storage': (1-p.beta*(1-p.loss))*r.P+p.storage_cost-p.storage_service/r.I,
    }


def primitives(p: Parameters, r: Reference) -> tuple[Array, Array, Array, Array]:
    """Physical dynamics F,G,S and negative-surplus Hessian in [state,control]."""
    n = p.lead+4
    F, G, S = np.zeros((n,n)), np.zeros((n,3)), np.zeros((n,2))
    F[0,0], F[1,1] = p.rho_d, p.rho_c
    S[0,0], S[1,1] = p.sigma_d, p.sigma_c
    G[2,0], G[3,1], F[4,4] = 1, 1, 1-p.delta
    if p.lead == 1:
        G[4,2] = 1
    else:
        F[4,5] = 1
        for j in range(p.lead-2):
            F[5+j,6+j] = 1
        G[-1,2] = 1
    eye = np.eye(n+3)
    z, c, lagq, lagi, k = eye[0], eye[1], eye[2], eye[3], eye[4]
    q, inv, j = eye[n], eye[n+1], eye[n+2]
    y = ((1-p.loss)*lagi+q-inv)/p.a
    sym = lambda a,b: np.outer(a,b)+np.outer(b,a)
    H = p.b*np.outer(y,y)-sym(z,y)+sym(c,q)
    H += p.gamma/r.K*np.outer(q,q)-p.gamma*r.Q/r.K**2*sym(q,k)
    H += p.gamma*r.Q**2/r.K**3*np.outer(k,k)
    H += p.kappa*np.outer(q-lagq,q-lagq)
    H += p.storage_service/r.I**2*np.outer(inv,inv)
    H += p.invest_curvature*np.outer(j,j)
    return F,G,S,H


def stage_loss(p: Parameters, r: Reference, deviations: Array) -> float:
    """Nonlinear negative surplus for derivative checks; not a likelihood."""
    n = p.lead+4
    d = np.asarray(deviations, dtype=float)
    if d.shape != (n+3,) or not np.all(np.isfinite(d)):
        raise ValueError('invalid state-control vector')
    z,c,lagq,lagi,k = d[:5]
    q,stock,j = r.Q+d[n], r.I+d[n+1], r.J+d[n+2]
    capacity, lagq, lagi = r.K+k, r.Q+lagq, r.I+lagi
    if capacity <= 0 or stock <= 0:
        raise ValueError('log/perspective cost requires positive stock and capacity')
    y = ((1-p.loss)*lagi+q+p.net_flow-stock)/p.a
    cost = ((p.unit_cost_mean+c)*q + p.gamma*q*q/(2*capacity)
            + p.kappa*(q-lagq)**2/2 + p.invest_price*j+p.invest_curvature*j*j/2
            + p.storage_cost*stock-p.storage_service*np.log(stock/r.I))
    return cost-(p.demand_mean+z-p.non_lc_cost)*y+p.b*y*y/2


@dataclass
class Solution:
    params: Parameters
    ref: Reference
    mode: Mode
    state_order: tuple[str, ...]
    control_order: tuple[str, ...]
    full_indices: tuple[int, ...]
    control_indices: tuple[int, ...]
    transition: Array
    shocks: Array
    policy: Array
    outputs: Array
    value_hessian: Array
    riccati_residual: float
    spectral_radius: float

    def step(self, deviation: Array, next_innovation: Array) -> tuple[Array, dict[str,float]]:
        """s_(t+1)=T s_t+S eps_(t+1); reject invalid local physical paths."""
        x, e = np.asarray(deviation,dtype=float), np.asarray(next_innovation,dtype=float)
        if x.shape != (len(self.state_order),) or e.shape != (2,):
            raise ValueError('wrong state or innovation shape')
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(e)):
            raise ValueError('nonfinite state or innovation')
        p,r = self.params,self.ref
        full = np.zeros(p.lead+4); full[list(self.full_indices)] = x
        controls = np.zeros(3); controls[list(self.control_indices)] = self.policy@x
        q,stock,j = np.array([r.Q,r.I,r.J])+controls
        capacity, price, material = r.K+full[4], r.P+(self.outputs@x)[0], r.Y+(self.outputs@x)[1]
        physical = [capacity, r.Q+full[2], r.I+full[3], q, capacity-q, stock, j, price, material]
        if p.lead > 1: physical.extend(r.J+full[5:])
        if min(physical) <= 0:
            raise ValueError('outside strict interior: do not clip; use a constrained solver')
        return self.transition@x+self.shocks@e, dict(Q=q,I=stock,J=j,K=capacity,P=price,Y=material)


def solve(p: Parameters, mode: Mode = 'joint') -> Solution:
    """First-order RE solution plus matched-reference mechanism restrictions.

capacity_only fixes stock at reference (E24); storage_only fixes installed
capacity. They are conditional comparisons, not three separately fitted models.
"""
    if mode not in ('joint','capacity_only','storage_only'):
        raise ValueError('unknown comparison mode')
    r = reference(p)
    F,G,S,H = primitives(p,r)
    n = p.lead+4
    state_names = ('z_demand','c_unit_cost','q_lag','i_lag','capacity')+tuple(f'pipeline_{j}' for j in range(1,p.lead))
    if mode == 'joint': si,ci = tuple(range(n)),(0,1,2)
    elif mode == 'capacity_only': si,ci = tuple(j for j in range(n) if j != 3),(0,2)
    else: si,ci = (0,1,2,3),(0,1)
    block = list(si)+[n+j for j in ci]
    H = H[np.ix_(block,block)]
    F,G,S = F[np.ix_(si,si)],G[np.ix_(si,ci)],S[list(si)]
    ns = len(si); Q,N,R = H[:ns,:ns],H[:ns,ns:],H[ns:,ns:]
    V = solve_discrete_are(np.sqrt(p.beta)*F,np.sqrt(p.beta)*G,Q,R,s=N)
    D = R+p.beta*G.T@V@G
    if np.min(np.linalg.eigvalsh(D)) <= 0:
        raise ValueError('Bellman control curvature is not positive definite')
    U = -np.linalg.solve(D,N.T+p.beta*G.T@V@F)
    T = F+G@U
    residual = V-(Q+N@U+U.T@N.T+U.T@R@U+p.beta*T.T@V@T)
    error = float(np.max(np.abs(residual)))
    radius = float(max(abs(np.linalg.eigvals(T))))
    if error > 1e-8 or radius >= 1:
        raise ValueError('no verified stable interior local solution')
    all_policy = np.zeros((3,ns)); all_policy[list(ci)] = U
    states = np.eye(n)[list(si)].T
    yrow = ((1-p.loss)*states[3]+all_policy[0]-all_policy[1])/p.a
    prow = (states[0]-p.b*yrow)/p.a
    outputs = np.vstack([prow,yrow,all_policy])
    return Solution(p,r,mode,tuple(state_names[i] for i in si),
                    tuple(('production','inventory','investment')[i] for i in ci),
                    si,ci,T,S,U,outputs,V,error,radius)


def euler_residuals(s: Solution) -> dict[str,float]:
    """Check EVERY coefficient of independent linearised FOCs, not just a path."""
    p,r,T = s.params,s.ref,s.transition
    n = p.lead+4
    ex = np.eye(n)[list(s.full_indices)].T
    price,y,q,stock,j = s.outputs
    eq = {}
    eq['production'] = (price-ex[1]-p.gamma/r.K*q+p.gamma*r.Q/r.K**2*ex[4]
                        -p.kappa*(q-ex[2])+p.beta*p.kappa*(q@T-q))
    eq['demand'] = ex[0]-p.b*y-p.a*price
    eq['balance'] = (1-p.loss)*ex[3]+q-p.a*y-stock
    if s.mode != 'capacity_only':
        eq['storage'] = price+p.storage_service/r.I**2*stock-p.beta*(1-p.loss)*price@T
    if s.mode != 'storage_only':
        w = -s.value_hessian[s.full_indices.index(4)]
        eq['capacity_value'] = w-p.gamma*r.Q/r.K**2*q+p.gamma*r.Q**2/r.K**3*ex[4]-p.beta*(1-p.delta)*w@T
        eq['investment'] = p.invest_curvature*j-p.beta**p.lead*w@np.linalg.matrix_power(T,p.lead)
    return {name:float(np.max(np.abs(val))) for name,val in eq.items()}
