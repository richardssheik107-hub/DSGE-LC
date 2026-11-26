#!/usr/bin/env python3
"""Reproduce the local RE solution, leading portfolio and clearly scoped IRFs.

Default execution recomputes diagnostics without overwriting evidence. Use
--write-report to save the checked linear solution and the CSV conditional-mean
responses. --fit-projection additionally attempts a nonlinear positive-risk
local fit; optimization alone never promotes it to an accepted equilibrium.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import platform
import sys
from dataclasses import replace
import numpy as np
import scipy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from model.dsge import Parameters
from model.dsge.local_projection import LocalProjection
from model.dsge.linear_re import select_portfolio,linear_irfs,futures_tangent_audit,complex_jacobian
from model.dsge.state import effective_capacity,next_state


def jsonable(value):
    if isinstance(value,np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value,(np.floating,np.integer,np.bool_)):
        return value.item()
    if isinstance(value,complex):
        return {'real':float(value.real),'imag':float(value.imag)}
    if isinstance(value,dict):
        return {k:jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [jsonable(v) for v in value]
    return value


def audit_states(m,coef,states,tolerance=1e-8):
    records=[];largest={};minima={key:float('inf') for key in [
        'consumption','capacity_slack','inventory_gap','debt_floor_slack',
        'collateral_slack','F_net_worth','successor_F_net_worth']}
    for label,s in states:
        try:
            with np.errstate(over='raise',invalid='raise',divide='raise'):
                a=m.audit(coef,s,tolerance)
                c=m.choice(coef,s)
        except (FloatingPointError,ValueError,OverflowError) as error:
            a={'passed':False,'max_abs_residual':None,'residuals':{},
               'domain_errors':[type(error).__name__+': '+str(error)]}
        if 'diagnostics' in a:
            d=a['diagnostics']
            values={'consumption':min(c.consumption),
                    'capacity_slack':effective_capacity(s,m.p)-c.q,
                    'inventory_gap':d['inventory_gap'],
                    'debt_floor_slack':min(c.next_bonds[:3]-m.p.debt_floors),
                    'collateral_slack':d['collateral_slack'],
                    'F_net_worth':d['financial_net_worth'],
                    'successor_F_net_worth':d['min_successor_F_net_worth']}
            for key,value in values.items():minima[key]=min(minima[key],float(value))
        for key,value in a['residuals'].items():
            if abs(value)>abs(largest.get(key,0)):largest[key]=float(value)
        records.append({'state':label,'passed':a['passed'],
                        'max_abs_residual':a['max_abs_residual'],'domain_errors':a['domain_errors']})
    finite=[r['max_abs_residual'] for r in records if r['max_abs_residual'] is not None]
    return {'count':len(records),'tolerance':tolerance,
            'max_original_residual':max(finite) if finite else None,
            'failed_count':sum(not r['passed'] for r in records),
            'domain_error_count':sum(bool(r['domain_errors']) for r in records),
            'minima':{key:(value if np.isfinite(value) else None) for key,value in minima.items()},'largest_equations':dict(sorted(largest.items(),key=lambda kv:abs(kv[1]),reverse=True)[:15]),
            'records':records}


def one_scale(sigma,horizon=36):
    m=LocalProjection(replace(Parameters(),shock_scales=(sigma,)*4))
    selected=select_portfolio(m)
    solution=selected['solution'];co=selected['coefficients'].ravel()
    irfs=linear_irfs(m,solution,horizon)
    center=m.moving_center(selected['coefficients'])
    states=[(f'{shock}_month_{period}',m.unpack_state(center+m.scale*state))
            for shock,period,state in irfs['normalized_states']]
    audit=audit_states(m,co,states)
    return m,selected,irfs,audit


def source_hashes():
    paths=sorted((ROOT/'model/dsge').glob('*.py'))+[Path(__file__).resolve()]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def nonlinear_attempt(m,selected,max_nfev):
    fit,nodes=m.solve(selected['coefficients'].ravel(),max_nfev=max_nfev)
    co=m.coefficients(fit.x);center=m.moving_center(co)
    def transition(x):
        a=m.controls(fit.x,x[None,:])
        return (m.prob@m.successors(x[None,:],a)[0]-center)/m.scale
    jac=complex_jacobian(lambda x:transition(center+m.scale*x),np.zeros(m.ns))
    eig=np.linalg.eigvals(jac)
    fitted=[(f'fit_{j}',m.unpack_state(x)) for j,x in enumerate(m.states_at(fit.x,nodes))]
    held=np.random.default_rng(20261126).uniform(-.5,.5,(64,m.ns))
    heldout=[(f'holdout_{j}',m.unpack_state(x)) for j,x in enumerate(m.states_at(fit.x,held))]
    # A reachable path uses the actual nonlinear state transition and a fixed seed.
    state=m.unpack_state(center);rng=np.random.default_rng(71126);path=[]
    for month in range(120):
        path.append((f'path_month_{month}',state))
        try:
            with np.errstate(over='raise',invalid='raise',divide='raise'):
                a=m.audit(fit.x,state)
                if a['domain_errors']:break
                c=m.choice(fit.x,state)
                state=next_state(state,c,rng.choice([-1.,1.],size=4),m.p)
        except (FloatingPointError,ValueError,OverflowError):
            break
    af=audit_states(m,fit.x,fitted);ah=audit_states(m,fit.x,heldout);ap=audit_states(m,fit.x,path)
    # This gate is evidence for a sampled local candidate only, never a global proof.
    passed=(fit.success and max(abs(eig))<=1+2e-5 and
            all(a['failed_count']==0 and a['domain_error_count']==0 for a in (af,ah,ap)))
    return {'optimizer_success':bool(fit.success),'optimizer_message':str(fit.message),
            'evaluations':int(fit.nfev),'max_nfev':max_nfev,'cost':float(fit.cost),
            'max_scaled_fit_residual':float(max(abs(fit.fun))),
            'optimality':float(fit.optimality),'coefficients':co,
            'conditional_mean_transition_eigenvalues':eig,
            'conditional_mean_transition_spectral_radius':float(max(abs(eig))),
            'fit_audit':af,'heldout_audit':ah,'reachable_path_audit':ap,
            'sampled_candidate_gate_passed':bool(passed),
            'global_stochastic_equilibrium_solved':False,
            'scope':'finite collocation/heldout/reachable-path check of selected regime; no invariant-domain or TVC proof'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-report',action='store_true')
    parser.add_argument('--fit-projection',action='store_true')
    parser.add_argument('--max-nfev',type=int,default=150)
    args=parser.parse_args()
    evidence_path=ROOT/'docs/validation/local_stochastic_20261126.json'
    if args.write_report and not args.fit_projection and evidence_path.exists():
        try:
            previous=json.loads(evidence_path.read_text())
        except (OSError,json.JSONDecodeError) as error:
            parser.error('Refusing to overwrite unreadable existing evidence: '+str(error))
        if 'nonlinear_projection_attempt' in previous:
            parser.error('Existing evidence includes a nonlinear projection attempt. '
                         'Refusing to remove it with a linear-only write. Reproduce the complete evidence with '
                         '--fit-projection --max-nfev 350 --write-report, or omit --write-report for read-only recomputation.')
    m,selected,irfs,audit=one_scale(.001)
    large,large_selected,large_irfs,large_audit=one_scale(.01)
    small,small_selected,small_irfs,small_audit=one_scale(.0005)
    double,double_selected,double_irfs,double_audit=one_scale(.002)
    solution=selected['solution'];eig=solution['closed_eigenvalues']
    innovation_loading=np.zeros((m.ns,4))
    innovation_loading[:4]=np.diag(np.array(m.p.shock_scales)/m.scale[:4])
    permanent=np.linalg.matrix_power(solution['transition'],1000)@innovation_loading
    permanent2=np.linalg.matrix_power(solution['transition'],2000)@innovation_loading
    source=source_hashes()
    tangent=futures_tangent_audit(m)
    report={'model_id':'LC_DSGE_EQCHAIN_20261126',
            'result_kind':'LOCAL_FIRST_ORDER_RE_WITH_LEADING_RISKY_PORTFOLIO',
            'working_sigma':.001,'configured_sigma':.01,'all_values_synthetic':True,
            'evidence_io_guard_added':{
                'change':'Refuse a linear-only write that would remove an existing nonlinear projection attempt',
                'economic_equations_or_algorithm_changed':False,
                'numerical_results_regenerated_with_this_script':True},
            'kernel':'four independent symmetric +/-1 innovations; all 16 branches',
            'selected_regime':{'inventory':0,'capacity_multiplier':0,'debt_multipliers':[0,0,0],
                               'collateral_multiplier':0,'positive_investment':True},
            'state_count':m.ns,'canonical_state_count':m.p.state_dimension,
            'state_reduction':'inherited inventory fixed at zero on the strict zero-inventory branch',
            'first_order_control_count':m.npositive,
            'first_order_local_equations_passed':bool(solution['linear_equation_max_residual']<1e-10),
            'linear_equation_max_residual':solution['linear_equation_max_residual'],
            'stable_neutral_root_count':solution['stable_count'],
            'neutral_wealth_root_count':int(sum(abs(eig-1)<1e-7)),
            'closed_transition_eigenvalues':eig,
            'neutral_wealth_innovation_diagnostic':{
                'remaining_innovation_loading_rank':int(np.linalg.matrix_rank(permanent,tol=1e-7)),
                'bond_WID_loading_after_1000_steps':m.scale[m.bslice,None]*permanent[m.bslice],
                'fixed_loading_residual':float(np.max(abs(solution['transition']@permanent-permanent))),
                'difference_1000_to_2000_steps':float(np.max(abs(permanent2-permanent))),
                'scope':'linearized model only; shocks excite non-decaying wealth directions, so no stationary unconditional covariance or stationary FEVD is reported'},
            'generalized_eigenvalues':solution['eigenvalues'],
            'generalized_indeterminate_pairs':solution['generalized_indeterminate_pairs'],
            'graph_condition_number':solution['graph_condition_number'],
            'futures_zero_risk_first_order_tangent':tangent,
            'leading_portfolio':{'holdings_IDF':solution['holdings'],
                                 'optimizer_success':selected['portfolio_solver_success'],
                                 'scaled_covariance_residual':selected['portfolio_scaled_residual'],
                                 'unscaled_covariance_differences':selected['pricing']['differences'],
                                 'conditional_spot_variance':selected['pricing']['conditional_spot_variance'],
                                 'zero_risk_anchor_collateral_slack':selected['zero_risk_anchor_collateral_slack'],
                                 'interpretation':'zero-order portfolio selected by second-order covariance equality; not a full second-order policy'},
            'irf':{'kind':'first-order local conditional-mean response to +1 innovation versus unconditional mean',
                   'horizon_months':36,'working_sigma':.001,'configured_sigma_comparison':.01,
                   'future_innovations_integrated_not_assumed_known':True,
                   'max_first_order_premium_identity_error':max(abs(r['first_order_premium_change']) for r in irfs['rows']),
                   'collateral_shock_local_response_zero':all(abs(v)<1e-12 for r in irfs['rows'] if r['shock']=='z_kappa' for k,v in r.items() if k.endswith('_change')),
                   'risk_premium_interpretation':'first-order premium changes are identically zero; no second-order premium or welfare inference'},
            'nonlinear_original_condition_audit_of_linear_candidate':audit,
            'amplitude_check':[{'sigma':s,'max_original_residual':a['max_original_residual'],
                                'domain_error_count':a['domain_error_count'],'minima':a['minima']}
                               for s,a in [(.0005,small_audit),(.001,audit),(.002,double_audit),(.01,large_audit)]],
            'sigma_doubling_error_ratios':[audit['max_original_residual']/small_audit['max_original_residual'],
                                           double_audit['max_original_residual']/audit['max_original_residual']],
            'full_positive_risk_nonlinear_policy_solved':False,
            'stationary_wealth_distribution_verified':False,
            'full_dynamic_rank_all_regimes_verified':False,
            'data_calibrated_or_estimated':False,
            'limitations':['three neutral wealth roots prevent claiming an ergodic invariant distribution',
                           'only one locally slack complementarity regime is linearized',
                           'holdings derivatives are not identified at first order and are set to zero in the candidate',
                           'linear IRFs are not nonlinear GIRFs, causal estimates, forecasts, FEVD or welfare'],
            'runtime':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},
            'economic_source_sha256':source}
    candidate={'model_id':report['model_id'],'result_kind':report['result_kind'],
               'parameters':m.p.to_dict(),'state_center':m.moving_center(selected['coefficients']),
               'state_scale':m.scale,'policy_coefficients':selected['coefficients'],
               'first_order_transition':solution['transition'],'first_order_policy':solution['policy'],
               'leading_holdings_IDF':solution['holdings'],
               'positive_control_anchor':m.positive_anchor,
               'full_nonlinear_policy_solved':False,'source_sha256':source}
    if args.fit_projection:report['nonlinear_projection_attempt']=nonlinear_attempt(m,selected,args.max_nfev)
    if args.write_report:
        out=ROOT/'results/local_stochastic';out.mkdir(parents=True,exist_ok=True)
        for filename,data in [('linear_solution_sigma_0p001.json',candidate)]:
            (out/filename).write_text(json.dumps(jsonable(data),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
        for filename,data in [('irf_sigma_0p001.csv',irfs),('irf_sigma_0p01.csv',large_irfs)]:
            with (out/filename).open('w',newline='') as handle:
                writer=csv.DictWriter(handle,fieldnames=list(data['rows'][0]));writer.writeheader();writer.writerows(data['rows'])
        # Infinite generalized eigenvalues are recorded as labels, not invalid JSON.
        payload=jsonable(report)
        for v in payload['generalized_eigenvalues']:
            if not np.isfinite(v['real']) or not np.isfinite(v['imag']):v.update(real='infinite',imag=0)
        (ROOT/'docs/validation/local_stochastic_20261126.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'linear_equation_max_residual':report['linear_equation_max_residual'],
                      'neutral_wealth_roots':report['neutral_wealth_root_count'],
                      'futures_tangent_rank':tangent['rank'],
                      'leading_holdings':solution['holdings'].tolist(),
                      'portfolio_scaled_residual':selected['portfolio_scaled_residual'],
                      'amplitude_check':report['amplitude_check'],
                      'sigma_doubling_error_ratios':report['sigma_doubling_error_ratios'],
                      'full_positive_risk_nonlinear_policy_solved':False,
                      'report_written':args.write_report},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
