"""Emit a reproducible theory check report, never use private economic data."""
from pathlib import Path
from dataclasses import asdict,replace
import argparse,json,hashlib,sys
import numpy as np
import scipy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.rebuild_theory.capacity_storage_v1 import Parameters,solve,euler_residuals,reference_residuals


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    cfg=json.loads((ROOT/'configs/capacity_storage_synthetic_v1.json').read_text())
    if cfg['purpose']!='SYNTHETIC_NUMERICAL_CHECK_ONLY_NOT_LITHIUM_CALIBRATION':
        raise ValueError('not an authorised synthetic fixture')
    p=Parameters(**cfg['parameters']);s=solve(p)
    comparisons=[]
    for lead in (1,2,3,6,12,24):
        for mode in ('joint','capacity_only','storage_only'):
            other=solve(replace(p,lead=lead),mode)
            comparisons.append(dict(lead=lead,mode=mode,states=len(other.state_order),
                                    max_euler_residual=max(euler_residuals(other).values()),
                                    spectral_radius=other.spectral_radius))
    sources=['src/rebuild_theory/capacity_storage_v1.py','tests/test_capacity_storage_v1.py',
             'scripts/check_capacity_storage_v1.py','configs/capacity_storage_synthetic_v1.json']
    report=dict(scope=cfg['purpose'],new_empirical_estimation=False,parameter_recovery_run=False,
                global_constrained_solution=False,software=dict(numpy=np.__version__,scipy=scipy.__version__),
                parameters=asdict(p),reference=asdict(s.ref),steady_residuals=reference_residuals(p,s.ref),
                state_order=s.state_order,control_order=s.control_order,output_order=['P','Y','Q','I','J'],
                transition=s.transition.tolist(),shock_loading=s.shocks.tolist(),policy=s.policy.tolist(),
                outputs=s.outputs.tolist(),euler_residuals=euler_residuals(s),
                riccati_residual=s.riccati_residual,spectral_radius=s.spectral_radius,
                comparisons=comparisons,sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in sources})
    text=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text,encoding='utf-8')
    else: print(text,end='')
    return 0


if __name__=='__main__': raise SystemExit(main())
