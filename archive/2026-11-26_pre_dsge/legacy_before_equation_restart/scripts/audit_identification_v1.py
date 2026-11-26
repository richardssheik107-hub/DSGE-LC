"""Evidence-limited identification audit. No empirical fit, posterior or recovery.

Uses the unchanged interior model and an explicitly ideal, synchronous monthly
observation design. Synthetic means/autocovariances are not real data. Exact
symmetries establish non-identification, but numerical full rank at a toy point
would not establish practical/global identification in the eventual dataset.
"""
from pathlib import Path
from dataclasses import replace, asdict
import json, sys
import numpy as np
from scipy.linalg import solve_discrete_lyapunov
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.rebuild_theory.capacity_storage_v1 import Parameters, solve


def fixture():
    cfg=json.loads((ROOT/'configs/capacity_storage_synthetic_v1.json').read_text())
    assert cfg['purpose']=='SYNTHETIC_NUMERICAL_CHECK_ONLY_NOT_LITHIUM_CALIBRATION'
    return Parameters(**cfg['parameters'])


def measurement(sol, names=('P','Q','I','m')):
    p,r=sol.params,sol.ref
    n=len(sol.state_order);eye=np.eye(n)
    rows={'P':sol.outputs[0],'Y':sol.outputs[1],'Q':sol.outputs[2],
          'I':sol.outputs[3],'J':sol.outputs[4],
          'K':eye[sol.state_order.index('capacity')],
          'm':eye[sol.state_order.index('c_unit_cost')]}
    means={'P':r.P,'Y':r.Y,'Q':r.Q,'I':r.I,'J':r.J,'K':r.K,'m':p.unit_cost_mean}
    return np.vstack([rows[x] for x in names]),np.array([means[x] for x in names])


def moments(p, names=('P','Q','I','m'), lags=12):
    s=solve(p)
    H,mean=measurement(s,names)
    V=solve_discrete_lyapunov(s.transition,s.shocks@s.shocks.T)
    covs=[];power=np.eye(len(s.state_order))
    for _ in range(lags+1):
        covs.append(H@power@V@H.T)
        power=power@s.transition
    return np.concatenate([mean]+[c.ravel() for c in covs])


def shifted_intercept(p, d=0.25):
    return replace(p,demand_mean=p.demand_mean+d,non_lc_cost=p.non_lc_cost+d)


def scaled_capacity(p, s=2.):
    # Valid when both trajectories remain slack: not a global upper-bound symmetry.
    return replace(p,gamma=s*p.gamma,invest_price=p.invest_price/s,
                   invest_curvature=p.invest_curvature/s**2)


def scaled_material(p, s=2.):
    return replace(p,a=p.a/s,b=p.b/s**2,demand_mean=p.demand_mean/s,
                   non_lc_cost=p.non_lc_cost/s,sigma_d=p.sigma_d/s)


def norm_error(a,b):
    return float(np.max(np.abs(a-b)/np.maximum(1.,np.abs(a))))


def observability(sol,names):
    H,_=measurement(sol,names);rows=[];power=np.eye(len(sol.state_order))
    for _ in range(len(sol.state_order)):
        rows.append(H@power);power=power@sol.transition
    O=np.vstack(rows)
    # Fix parameter values. This tests state observability, not parameter ID.
    sv=np.linalg.svd(O,compute_uv=False)
    return {'rank':int(np.linalg.matrix_rank(O)),'states':len(sol.state_order),
            'singular_values':sv.tolist()}


def sensitivity(p,names,step):
    keys=[k for k in asdict(p) if k!='lead']
    y0=moments(p,names);J=[]
    for key in keys:
        v=getattr(p,key);h=step*max(abs(v),0.01)
        plus=moments(replace(p,**{key:v+h}),names)
        minus=moments(replace(p,**{key:v-h}),names)
        J.append((plus-minus)/(2*h)*max(abs(v),0.01))
    J=np.column_stack(J)
    # Explicit unit scaling; ranks are reported over thresholds, not just one.
    row_scale=np.maximum(np.abs(y0),0.01)
    J=J/row_scale[:,None]
    col_norm=np.linalg.norm(J,axis=0)
    J=J/np.maximum(col_norm,1e-14)
    sv=np.linalg.svd(J,compute_uv=False)
    return {'parameters':keys,'step':step,'moments':len(y0),
            'sv':sv.tolist(),'ranks':{str(t):int(np.sum(sv>sv[0]*t)) for t in (1e-4,1e-6,1e-8)},
            'warning':'Toy finite-moment local diagnostic; rank depends on tolerance/scales/design. Not empirical identification.'}


def main():
    p=fixture();s=solve(p);names=('P','Q','I','m')
    y=moments(p,names)
    variants={'intercept_shift':shifted_intercept(p),'capacity_scale':scaled_capacity(p),
              'material_scale':scaled_material(p)}
    symmetry={}
    for name,p2 in variants.items():
        s2=solve(p2)
        symmetry[name]={'observable_moment_error':norm_error(y,moments(p2,names)),
                        'base_reference':asdict(s.ref),'alternative_reference':asdict(s2.ref)}
    report={'scope':'SYNTHETIC_ID_PREFLIGHT_NOT_FINAL_IDENTIFICATION',
            'source_commit':'0b5e3cf8138ac7a861c3e0758c23608f601ca6c2',
            'empirical_fit':False,'parameter_recovery':False,'observation_frozen':False,
            'design':{'names':names,'lags':12,'frequency':'ideal synchronous monthly levels',
                      'measurement_noise':0,'lead':p.lead,'lead_is_industry_estimate':False},
            'symmetries':symmetry,
            'state_observability':observability(s,names),
            'symmetry_broken_by_observing_K':norm_error(moments(p,('P','Q','I','m','K')),moments(scaled_capacity(p),('P','Q','I','m','K'))),
            'symmetry_broken_by_observing_Y':norm_error(moments(p,('P','Q','I','m','Y')),moments(scaled_material(p),('P','Q','I','m','Y'))),
            'sensitivities':[sensitivity(p,names,h) for h in (1e-4,1e-5)],
            'all_series_assumed_matched_and_available':True,
            'real_series_availability_not_inferred':True}
    out=ROOT/'docs/rebuild/data_id_v1/synthetic_identification_check.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'symmetry_errors':{k:v['observable_moment_error'] for k,v in symmetry.items()},
                      'state_observability':report['state_observability'],
                      'ranks':[r['ranks'] for r in report['sensitivities']]},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
