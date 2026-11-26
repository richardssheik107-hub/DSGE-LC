"""Recreate the large-box stress test with explicit branch and timing evidence."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from model.stochastic_domain_audit import audit_box
from model.stochastic_equilibrium import PolynomialPolicy, Problem, load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=Path("results/stochastic_baseline"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=177303)
    parser.add_argument("--count", type=int, default=64)
    args = parser.parse_args()
    config_path, policy_path = args.run_dir/"config.json", args.run_dir/"policy.npz"
    problem = Problem(load_config(config_path))
    provenance = {
        "code_commit_at_audit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                        text=True).strip(),
        "run_id": args.output.name,
        "source_run_id": args.run_dir.name,
        "saved_config_sha256": sha256(config_path.read_bytes()).hexdigest(),
        "saved_policy_sha256": sha256(policy_path.read_bytes()).hexdigest(),
    }
    with np.load(policy_path, allow_pickle=False) as saved:
        if float(saved["normalized_shock_amplitude"].item()) != 1.0:
            raise ValueError("Stress audit requires the frozen full-target policy")
        policy = PolynomialPolicy(problem, saved["powers"], saved["coefficients"])
        report = audit_box(problem, policy, saved["training_states"], args.output, count=args.count,
                           seed=args.seed, provenance=provenance)
    print(json.dumps({
        "result": str(args.output/"box_audit.json"), "sample": report["sample"],
        "reachability": report["reachability"], "successors": report["successors"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
