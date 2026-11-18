"""Read a saved policy and run independent original-condition validation."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.full_conditions import MODEL_ID, REVISION  # noqa: E402
from model.stochastic_equilibrium import PolynomialPolicy, Problem, load_config  # noqa: E402
from model.stochastic_validation import validate_policy  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--policy", type=Path, help="alternate policy archive; default is RUN_DIR/policy.npz")
    parser.add_argument("--output", type=Path, help="alternate report; default is RUN_DIR/validation.json")
    parser.add_argument("--residual-only", action="store_true",
                        help="compare independent cross-sectional residuals without Bellman or path acceptance")
    parser.add_argument("--compare-policy", action="append", type=Path, default=[],
                        help="compare an additional saved policy on identical states; repeat for multiple policies")
    parser.add_argument("--validation-radius-fraction", type=float, help="diagnostic sampling box radius as fraction of policy radius")
    parser.add_argument("--validation-count", type=int, help="diagnostic sampling count")
    parser.add_argument("--validation-seed", type=int, help="diagnostic cross-sectional sampling seed")
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    policy_path = args.policy or run_dir / "policy.npz"
    config_path = run_dir / "config.json"
    default_report = "residual_comparison.json" if args.residual_only else "validation.json"
    output = args.output or run_dir / default_report
    raw_policy = policy_path.read_bytes()
    config = load_config(config_path)
    overrides = {name: getattr(args, f"validation_{name}") for name in ("radius_fraction", "count", "seed")
                 if getattr(args, f"validation_{name}") is not None}
    if overrides and not args.residual_only:
        parser.error("changing the declared validation sample requires --residual-only")
    config["validation"].update(overrides)
    problem = Problem(config)
    started = time.perf_counter()
    alternatives = []
    for source in args.compare_policy:
        with np.load(source, allow_pickle=False) as comparison:
            alternatives.append((str(source), PolynomialPolicy(problem, comparison["powers"], comparison["coefficients"]),
                                 comparison["training_states"]))
    with np.load(policy_path, allow_pickle=False) as saved:
        policy = PolynomialPolicy(problem, saved["powers"], saved["coefficients"])
        report = validate_policy(problem, policy, saved["training_states"], config,
                                 residual_only=args.residual_only, alternatives=alternatives)
        saved_amplitude = float(saved["normalized_shock_amplitude"]) if "normalized_shock_amplitude" in saved else None
    if not args.residual_only:
        target = saved_amplitude == 1.0 and len(problem.kernel.branches) == 512 and bool(np.all(problem.amplitudes > 0))
        report["acceptance_gates"]["target_amplitude_policy_and_full_nine_shock_kernel"] = target
        report["numerical_acceptance_passed"] = all(report["acceptance_gates"].values())
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=ROOT,
                           text=True, capture_output=True, check=False)
    report.update({
        "model_id": MODEL_ID, "revision": REVISION, "code_commit": commit.stdout.strip() or None,
        "worktree_had_uncommitted_changes_at_validation": bool(dirty.stdout.strip()),
        "python": platform.python_version(), "numpy": np.__version__,
        "policy_file": policy_path.name, "policy_sha256": hashlib.sha256(raw_policy).hexdigest(),
        "saved_policy_normalized_shock_amplitude": saved_amplitude,
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "validation_overrides_for_diagnostic_only": overrides,
        "elapsed_seconds": time.perf_counter() - started,
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "validation": str(output), "numerical_acceptance_passed": report["numerical_acceptance_passed"],
        "failed_gates": [name for name, passed in report["acceptance_gates"].items() if not passed],
        "maxima_normalized": report["conditions"]["maxima_normalized"],
        "worst_economic_condition": report["conditions"]["worst_economic_condition"],
        "elapsed_seconds": report["elapsed_seconds"],
    }, ensure_ascii=False))
    passed = (all(report["acceptance_gates"].values()) if args.residual_only else report["numerical_acceptance_passed"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
