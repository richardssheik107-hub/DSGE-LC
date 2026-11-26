"""Replay longer independent paths under the saved, unmodified policy."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from model.stochastic_equilibrium import PolynomialPolicy, Problem, load_config
from model.stochastic_path_audit import DEFAULT_SEED, DEFAULT_TIERS, simulate_tier, state_names


def parse_tier(specification):
    try:
        paths, months = map(int, specification.split("x"))
        if paths < 3 or months < 3:
            raise ValueError()
    except ValueError as error:
        raise argparse.ArgumentTypeError("use PATHSxMONTHS with both values >= 3") from error
    return paths, months


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--validation", type=Path, help="verified Bellman value coefficients for the policy")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--tier", type=parse_tier, action="append", help="PATHSxMONTHS; repeat for independent tiers")
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    config_path = run_dir/"config.json"
    config = load_config(config_path)
    config_hash = sha256(config_path)
    policy_path = args.policy.resolve() if args.policy else run_dir/"policy.npz"
    policy_hash = sha256(policy_path)
    problem = Problem(config)
    with np.load(policy_path, allow_pickle=False) as archive:
        amplitude = float(archive["normalized_shock_amplitude"])
        if amplitude != 1.0:
            raise ValueError("This audit requires the target-amplitude frozen policy")
        powers, coefficients = archive["powers"], archive["coefficients"]
        policy = PolynomialPolicy(problem, powers, coefficients)
        training = archive["training_states"]
    powers.flags.writeable = coefficients.flags.writeable = False
    validation_path = args.validation or run_dir/"validation.json"
    values, value_source = None, None
    if validation_path.is_file():
        validation = load_config(validation_path)
        if validation.get("policy_sha256") != policy_hash or validation.get("config_sha256") != config_hash:
            raise ValueError("Stored Bellman values were generated using another policy or config")
        values = np.asarray(validation["producer_value_projection"]["coefficients"], dtype=float)
        if values.shape != (len(powers),):
            raise ValueError("Stored Bellman coefficients are dimensionally inconsistent")
        values.flags.writeable = False
        value_source = {"path": str(validation_path.resolve()), "sha256": sha256(validation_path)}
    else:
        if args.validation:
            raise FileNotFoundError(validation_path)

    args.output.mkdir(parents=True, exist_ok=False)
    tiers = args.tier or DEFAULT_TIERS
    report = {
        "run_id": args.output.name, "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "frozen_policy_sha256": policy_hash, "policy_path": str(policy_path),
        "config_sha256": config_hash, "config_path": str(config_path),
        "value_coefficients_source": value_source, "uses_online_root_solving": False,
        "policy_shared_by_current_and_future": True,
        "normalized_shock_amplitude": amplitude, "physical_shock_amplitudes": problem.amplitudes.tolist(),
        "joint_branches": len(problem.kernel.branches),
        "branch_index_order": problem.innovations.tolist(),
        "state_order": state_names(problem), "approximation_radius": problem.radius.tolist(),
        "residual_scales": config["scales"], "tolerances": config["tolerances"],
        "previous_32_path_states_definition": "32 distinct path indices at a single month (month 24), seeded before traversal.",
        "master_seed": args.seed, "preassigned_tiers": tiers,
        "all_path_integrator": "Exact polynomial sign moments with vectorized original residuals",
        "checkpoint_integrator": "Explicit canonical 512 branches, original scalar evaluator",
        "tiers": [],
    }
    started = time.perf_counter()
    for i, ((paths, horizon), child_seed) in enumerate(zip(tiers, np.random.SeedSequence(args.seed).spawn(len(tiers)))):
        tier, arrays = simulate_tier(problem, policy, training, child_seed, paths, horizon, values)
        prefix = f"tier_{i+1}_{paths}x{horizon}"
        failure_path = args.output/(prefix+"_failures.json")
        with failure_path.open("x", encoding="utf-8") as f:
            json.dump(tier.pop("first_failure_records_by_path_and_category"), f, ensure_ascii=False, indent=2, allow_nan=False)
        np.savez_compressed(args.output/(prefix+"_shocks.npz"), **arrays)
        tier["first_failures_file"] = failure_path.name
        tier["path_replay_file"] = prefix+"_shocks.npz"
        report["tiers"].append(tier)
        print(json.dumps({
            "paths": paths, "months": horizon, "counts": tier["counts_at_all_periods"],
            "checkpoint_checks": tier["checkpoint_explicit_512_original_audit"]["checks"],
        }, ensure_ascii=False), flush=True)
    report["elapsed_seconds"] = time.perf_counter()-started
    report["frozen_policy_unchanged_during_audit"] = sha256(policy_path) == policy_hash
    report["configuration_unchanged_during_audit"] = sha256(config_path) == config_hash
    report["all_sampled_paths_and_checkpoints_passed"] = (
        report["frozen_policy_unchanged_during_audit"] and report["configuration_unchanged_during_audit"]
        and all(not any(tier["number_of_paths_with_either_burnin_or_simulation_failure"].values())
                and all(tier["checkpoint_explicit_512_original_audit"]["checks"].values())
                for tier in report["tiers"])
    )
    with (args.output/"validation.json").open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
    return 0 if report["all_sampled_paths_and_checkpoints_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
