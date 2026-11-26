"""Local positive-risk projection on an explicitly selected slack-constraint branch.

This is an experimental solver, not a declaration of a stationary equilibrium.
It retains all four owners, all sixteen innovation branches, inherited wealth and
contracts, and the original consumption SDF. Consumption and positive controls
are log-affine; bonds are recovered from each owner's budget, not reset.
Inventory is fixed at zero and all other inequalities are assumed slack during
solving. Their validity must therefore be audited with ``residuals.evaluate``.

At zero risk the three futures conditions coincide to first order. At positive
risk the solver uses one level-pricing condition and two *normalized* SDF pricing
differences. Dividing the latter by the innovation variance changes numerical
units only; no portfolio penalty or identifying restriction is added.
"""
from dataclasses import replace
import numpy as np
from scipy.optimize import least_squares
from .parameters import Parameters
from .state import State, Choice, Branch, next_state, effective_capacity
from .steady_state import solve_anchor
from .shocks import kernel
from .residuals import evaluate


class LocalProjection:
    """A log-affine candidate on the zero-inventory, slack-constraint branch."""

    def __init__(self, parameters=None, radius=1.0):
        self.p = (parameters or Parameters()).validate()
        self.anchor = solve_anchor(self.p)
        self.s0, self.c0 = self.anchor['state'], self.anchor['choice']
        self.l = self.p.construction_lag - 1
        self.r = self.p.ramp_length
        self.nsh = 1 + self.l + self.r
        # z(4), Q_-, C_-, K^M, B, Z, b_WID(3), old h_ID(2), old F.
        self.ns = 13 + self.l + self.r
        self.npositive = 11 + self.nsh
        self.nu = self.npositive + 2
        self.nbasis = self.ns + 1
        self.zslice = slice(0, 4)
        self.bslice = slice(7 + self.l + self.r, 10 + self.l + self.r)
        self.hslice = slice(10 + self.l + self.r, 12 + self.l + self.r)
        self.findex = 12 + self.l + self.r
        self.center = self.pack_state(self.s0)
        physical = np.r_[self.s0.q_prev, self.s0.commitment_prev,
                         self.s0.mature, self.s0.construction, self.s0.ramp]
        risk = max(self.p.shock_scales)
        if risk <= 0:
            raise ValueError('Positive innovation scales are required; zero-risk portfolios are singular')
        self.risk_scale = risk
        self.scale = np.r_[np.maximum(self.p.shock_scales, risk * .1),
                           physical * risk,
                           np.full(3, risk * .2),
                           np.full(2, risk), self.c0.spot * risk] * radius
        self.positive_anchor = np.r_[self.c0.q, self.c0.investment, self.c0.commitment,
                                    self.c0.wage, self.c0.spot, self.c0.forward,
                                    1/self.c0.gross_rate, self.c0.consumption,
                                    self.c0.wm, self.c0.wb, self.c0.wz]
        self.hedge_scale = self.c0.q
        law = kernel(self.p)
        self.prob = np.array([x[0] for x in law])
        self.eps = np.array([x[1] for x in law])
        self.branch_count = len(law)

    def pack_state(self, s):
        if abs(s.inventory_prev) > 1e-14:
            raise ValueError('Projection branch requires inherited inventory = 0')
        return np.r_[s.z, s.q_prev, s.commitment_prev, s.mature,
                     s.construction, s.ramp, s.bonds[:3], s.old_positions[:2], s.old_forward]

    def unpack_state(self, x):
        bonds = np.r_[x[self.bslice], -np.sum(x[self.bslice])]
        positions = np.r_[x[self.hslice], -np.sum(x[self.hslice])]
        return State(np.array(x[:4]), x[4], 0., x[5], x[6],
                     np.array(x[7:7+self.l]), np.array(x[7+self.l:7+self.l+self.r]),
                     bonds, positions, x[self.findex])

    def coefficients(self, flat):
        return np.asarray(flat).reshape(self.nu, self.nbasis)

    def moving_center(self, coef):
        center = self.center.astype(coef.dtype, copy=True)
        # Zero-order risky holdings need not approach the arbitrary h=0 anchor.
        center[self.hslice] = self.hedge_scale * coef[self.npositive:, 0]
        return center

    def states_at(self, flat, nodes):
        coef = self.coefficients(flat)
        return self.moving_center(coef) + np.asarray(nodes) * self.scale

    def controls(self, flat, states):
        coef = self.coefficients(flat)
        states = np.atleast_2d(states)
        normalized = (states - self.moving_center(coef)) / self.scale
        basis = np.column_stack([np.ones(len(states)), normalized])
        v = basis @ coef.T
        positives = self.positive_anchor * np.exp(v[:, :self.npositive])
        h2 = self.hedge_scale * v[:, self.npositive:]
        h = np.column_stack([h2, -np.sum(h2, axis=1)])
        return self.recover(states, positives, h)

    def recover(self, x, a, h):
        p = self.p
        q,j,c,w,spot,forward,bond_price = [a[:,k] for k in range(7)]
        consumption = a[:,7:11]
        shadow = a[:,11:]
        capacity = x[:,6] + x[:,7+self.l:7+self.l+self.r] @ np.array(p.ramp_weights)
        ds = q-x[:,5]
        income_b = spot*ds/p.alpha_s
        nd = p.labor_share*income_b/w
        yb = p.ab*p.fixed_factor**p.phi*nd**p.labor_share*ds**p.alpha_s*x[:,5]**p.alpha_c
        pb = income_b/yb
        p0 = w/p.a0
        omega = 1/(1+np.exp(-(np.log(p.omega_bar/(1-p.omega_bar))+x[:,0])))
        m = p.m_bar*np.exp(x[:,1])
        pj = p.pj_bar*np.exp(x[:,2])
        collateral = p.collateral_bar*np.exp(x[:,3])
        output = yb/(omega*pb**-p.epsilon)
        y0 = (1-omega)*p0**-p.epsilon*output
        n0 = y0/p.a0
        nw = nd+n0+q/p.al
        cq = m*q+p.alpha_q/(p.nu_q+1)*q**(p.nu_q+1)/capacity**p.nu_q+p.adjustment_q/2*(q-x[:,4])**2
        cj = pj*j+p.chi_j*j*j/2+p.congestion*j*np.sum(x[:,7:7+self.l],axis=1)
        ac = p.adjustment_c/2*(c-x[:,5])**2
        b3=x[:,self.bslice]
        bonds=np.column_stack([b3,-np.sum(b3,axis=1)])
        oldh2=x[:,self.hslice]
        oldh=np.column_stack([oldh2,-np.sum(oldh2,axis=1)])
        settlement=oldh*(spot-x[:,self.findex])[:,None]
        income=np.column_stack([w*nw,spot*q-w*q/p.al-cq-cj,
                                income_b-w*nd-spot*(ds+x[:,5])-ac,np.zeros(len(x))])
        income[:,1:]+=settlement
        next_bonds=(bonds+income-consumption)/bond_price[:,None]
        raw_bond_sum=np.sum(next_bonds,axis=1)
        next_bonds[:,3]=-np.sum(next_bonds[:,:3],axis=1)
        return dict(q=q,j=j,c=c,w=w,spot=spot,forward=forward,bond_price=bond_price,
                    consumption=consumption,shadow=shadow,h=h,capacity=capacity,ds=ds,
                    nd=nd,pb=pb,p0=p0,omega=omega,m=m,pj=pj,collateral=collateral,
                    yb=yb,y0=y0,output=output,nw=nw,n0=n0,next_bonds=next_bonds,
                    cq=cq,cj=cj,ac=ac,raw_bond_sum=raw_bond_sum)

    def successors(self, x, a):
        p=self.p; n=len(x); k=self.branch_count
        result=np.repeat(x[:,None,:],k,axis=1)
        result[:,:,:4]=x[:,None,:4]*np.array(p.shock_persistence)+self.eps[None,:,:]*np.array(p.shock_scales)
        result[:,:,4]=a['q'][:,None]; result[:,:,5]=a['c'][:,None]
        completed=x[:,7] if self.l else a['j']
        if self.l:
            if self.l>1:
                result[:,:,7:7+self.l-1]=x[:,None,8:7+self.l]
            result[:,:,7+self.l-1]=a['j'][:,None]
        if self.r:
            result[:,:,6]=(1-p.depreciation)*(x[:,6]+x[:,7+self.l+self.r-1])[:,None]
            result[:,:,7+self.l]=completed[:,None]
            if self.r>1:
                result[:,:,8+self.l:7+self.l+self.r]=(1-p.depreciation)*x[:,None,7+self.l:6+self.l+self.r]
        else:
            result[:,:,6]=((1-p.depreciation)*x[:,6]+completed)[:,None]
        result[:,:,self.bslice]=a['next_bonds'][:,None,:3]
        result[:,:,self.hslice]=a['h'][:,None,:2]
        result[:,:,self.findex]=a['forward'][:,None]
        return result

    def equations(self, flat, nodes, scaled=True):
        x=self.states_at(flat,nodes)
        a=self.controls(flat,x)
        nextx=self.successors(x,a)
        f0=self.controls(flat,nextx.reshape(-1,self.ns))
        n,k=nextx.shape[:2]
        f={key:value.reshape((n,k)+value.shape[1:]) for key,value in f0.items()}
        return self.conditions(x,a,f,scaled)

    def conditions(self,x,a,f,scaled=True,probabilities=None):
        p=self.p
        probabilities=self.prob if probabilities is None else probabilities
        sdf=p.beta*(f['consumption']/a['consumption'][:,None,:])**-np.array(p.gamma)
        em=np.einsum('k,nkj->nj',probabilities,sdf)
        mean=lambda v:np.einsum('k,nk->n',probabilities,v)
        emi=lambda v:mean(sdf[:,:,1]*v)
        emd=lambda v:mean(sdf[:,:,2]*v)
        payoff=f['spot']-a['forward'][:,None]
        pricefoc=mean(sdf[:,:,1]*payoff)
        ndiff=sdf/em[:,None,:]
        diffd=mean((ndiff[:,:,2]-ndiff[:,:,1])*payoff)
        difff=mean((ndiff[:,:,3]-ndiff[:,:,1])*payoff)
        rent=p.alpha_q*p.nu_q/(p.nu_q+1)*(a['q']/a['capacity'])**(p.nu_q+1)
        production=a['spot']-a['w']/p.al-a['m']-p.alpha_q*(a['q']/a['capacity'])**p.nu_q-p.adjustment_q*(a['q']-x[:,4])+emi(p.adjustment_q*(f['q']-a['q'][:,None]))
        ishadow=f['shadow'][:,:,self.l] if self.l else f['shadow'][:,:,1 if self.r else 0]
        # Shadow ordering = mature, construction from remaining 1 to L-1, ramp.
        jgap=a['pj']+p.chi_j*a['j']+p.congestion*np.sum(x[:,7:7+self.l],axis=1)-emi(ishadow)
        cgap=p.adjustment_c*(a['c']-x[:,5])-emd(p.alpha_c*f['pb']*f['yb']/a['c'][:,None]-f['spot']+p.adjustment_c*(f['c']-a['c'][:,None]))
        shadowres=[a['shadow'][:,0]-rent-(1-p.depreciation)*emi(f['shadow'][:,:,0])]
        for h in range(self.l):
            tail=f['shadow'][:,:,1+self.l] if h==0 and self.r else (f['shadow'][:,:,0] if h==0 else f['shadow'][:,:,h])
            shadowres.append(a['shadow'][:,1+h]+p.congestion*a['j']-emi(tail))
        for z in range(self.r):
            tail=f['shadow'][:,:,1+self.l+z+1] if z+1<self.r else f['shadow'][:,:,0]
            shadowres.append(a['shadow'][:,1+self.l+z]-p.ramp_weights[z]*rent-(1-p.depreciation)*emi(tail))
        priceindex=(1-a['omega'])*a['p0']**(1-p.epsilon)+a['omega']*a['pb']**(1-p.epsilon)-1
        labor=a['w']-p.labor_weight*a['nw']**p.labor_elasticity_power*a['consumption'][:,0]**p.gamma[0]
        result=np.column_stack([priceindex,labor,a['raw_bond_sum'],production,jgap,cgap,
                                a['bond_price'][:,None]-em,pricefoc,diffd,difff,*shadowres])
        if scaled:
            scales=np.r_[1,self.c0.wage,self.c0.output,self.c0.spot,p.pj_bar,self.c0.spot,
                         np.full(4,p.beta),self.c0.spot,
                         np.full(2,self.risk_scale**2*self.c0.spot),self.positive_anchor[11:]]
            result=result/scales
        return result.ravel()

    def choice(self, flat, state):
        x=self.pack_state(state)[None,:]
        a={key:value[0] for key,value in self.controls(flat,x).items()}
        sh=a['shadow']
        return Choice(a['q'],a['j'],a['ds'],a['c'],0.,a['consumption'],a['nw'],a['nd'],a['n0'],
                      a['w'],a['spot'],a['forward'],a['p0'],a['pb'],a['y0'],a['yb'],a['output'],
                      1/a['bond_price'],a['next_bonds'],a['h'],sh[0],sh[1:1+self.l],sh[1+self.l:])

    def audit(self, flat, state, tolerance=1e-8):
        c=self.choice(flat,state)
        branches=[]
        for probability,eps in kernel(self.p):
            ns=next_state(state,c,eps,self.p)
            branches.append(Branch(probability,eps,ns,self.choice(flat,ns)))
        return evaluate(state,c,branches,self.p,tolerance)

    def solve(self, initial=None, nodes=None, max_nfev=120, verbose=0):
        nodes=(np.vstack([np.zeros(self.ns),np.eye(self.ns),-np.eye(self.ns)])
               if nodes is None else np.asarray(nodes))
        x0=np.zeros((self.nu,self.nbasis)).ravel() if initial is None else np.asarray(initial).ravel()
        solution=least_squares(lambda v:self.equations(v,nodes),x0,jac='cs',method='trf',
                               x_scale='jac',ftol=1e-11,xtol=1e-11,gtol=1e-11,
                               max_nfev=max_nfev,verbose=verbose)
        return solution,nodes
