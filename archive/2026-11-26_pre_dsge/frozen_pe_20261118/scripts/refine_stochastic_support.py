"""Reproject a frozen policy on prespecified feasible starts and reached states."""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import scipy

from model.full_conditions import DomainError
from model.stochastic_equilibrium import Problem, PolynomialPolicy, Projector, linear_start, load_config
from scripts.solve_stochastic_equilibrium import arrays_write, json_write


def training_states(problem, source, spec):
    """The seed and collection schedule never depend on validation outcomes."""
    rng = np.random.default_rng(spec["training_seed"])
    width = np.asarray(spec["local_radius_fraction"])
    local = problem.center + rng.uniform(-1, 1, (spec["local_points"], len(width)))*width*problem.radius
    random = np.tile(problem.center, (spec["random_path_count"], 1))
    constant = np.tile(problem.center, (len(problem.kernel.branches), 1))
    capture_random = set(spec["random_capture_periods"])
    capture_constant = set(spec["constant_shock_capture_periods"])
    points = [problem.center[None], local]
    for period in range(1, spec["random_path_horizon"]+1):
        random = problem.successors(random, source.predict(random),
                                    rng.integers(len(problem.kernel.branches), size=len(random)))
        if period in capture_random:
            points.append(random)
        if period <= max(capture_constant):
            constant = problem.successors(constant, source.predict(constant), np.arange(len(constant)))
            if period in capture_constant:
                points.append(constant)
    result = np.vstack(points)
    inherited = result[:, 9:]
    if not np.all(np.isfinite(result)) or np.any(inherited < 0) or np.any(problem.environment(result)["margin"] <= 0):
        raise DomainError("Non-feasible training state generated at declared support")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training", type=Path, default=ROOT/"configs/stochastic_reaudit.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    spec = load_config(args.training)
    config_path = ROOT/spec["source_config"]
    config = load_config(config_path)
    source_path = ROOT/spec["source_policy"]
    problem = Problem(config)
    with np.load(source_path, allow_pickle=False) as data:
        if data["normalized_shock_amplitude"].item() != 1:
            raise ValueError("Refinement requires a full-target starting policy")
        source = PolynomialPolicy(problem, data["powers"], data["coefficients"])
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    (output/"config.json").write_bytes(config_path.read_bytes())
    json_write(output/"training_spec.json", spec)
    states = training_states(problem, source, spec)
    degree = int(source.powers.sum(axis=1).max())
    print(f"Fitting {len(states)} prespecified points, degree={degree}", flush=True)
    projector = Projector(problem, states, degree, linear_start(problem))
    coefficient = source.coefficients.copy()
    design = source.design(states)
    projected_tolerance = config["solver"]["projected_tolerance"]
    policy_change_tolerance = config["tolerances"]["policy_change"]
    log = []
    converged = False
    for k in range(spec["maximum_iterations"]):
        residual = projector.residual(coefficient, 1.0)
        norm = float(np.abs(projector.project @ residual).max())
        correction = projector.correction(residual)
        change = float(np.abs((design @ correction)/problem.policy_scale).max())
        converged = norm <= projected_tolerance and change <= policy_change_tolerance
        log.append({"iteration": k, "projected_residual": norm,
                    "training_residual": float(np.abs(residual).max()),
                    "max_normalized_policy_correction_at_training_states": change})
        print(log[-1], flush=True)
        if converged:
            break
        step = 1.0
        while step >= 1/512:
            next_coefficient = coefficient-step*correction
            try:
                next_norm = np.abs(projector.project @ projector.residual(next_coefficient, 1.0)).max()
            except DomainError:
                next_norm = np.inf
            if next_norm < norm:
                coefficient = next_coefficient
                break
            step *= 0.5
        log[-1]["step"] = step if step >= 1/512 else 0
        arrays_write(output/"checkpoint.npz", powers=source.powers, coefficients=coefficient,
                     training_states=states, normalized_shock_amplitude=1.0)
        json_write(output/"convergence.json", log)
        if step < 1/512:
            break
    artifact = dict(powers=source.powers, coefficients=coefficient, training_states=states,
                    normalized_shock_amplitude=1.0, projected_converged=converged)
    arrays_write(output/"policy.npz", **artifact)
    arrays_write(output/"checkpoint.npz", **artifact)
    json_write(output/"convergence.json", log)
    json_write(output/"refinement.json", {
        "run_id": output.name, "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "refinement_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "source_policy_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "policy_sha256": hashlib.sha256((output/"policy.npz").read_bytes()).hexdigest(),
        "training_points": len(states), "training_seed": spec["training_seed"],
        "projected_tolerance": projected_tolerance, "policy_change_tolerance": policy_change_tolerance,
        "projected_converged": converged, "target_amplitude": 1.0,
        "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
        "elapsed_seconds": time.perf_counter()-started,
    })


if __name__ == "__main__":
    main()
