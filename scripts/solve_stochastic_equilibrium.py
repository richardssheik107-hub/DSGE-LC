"""Project the common stochastic policy and persist a resumable run."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import scipy

from model.full_conditions import DomainError, evaluate_conditions
from model.stochastic_equilibrium import Problem, Projector, linear_start, load_config


def json_write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
                         encoding="utf-8")
    temporary.replace(path)


def arrays_write(path, **fields):
    temporary = path.with_suffix(".tmp.npz")
    np.savez_compressed(temporary, **fields)
    temporary.replace(path)


def solve(config_path, output, resume=False):
    config = load_config(config_path)
    problem = Problem(config)
    settings = config["solver"]
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "checkpoint.npz"
    log_path = output / "convergence.json"
    canonical_config = json.dumps(config, sort_keys=True, ensure_ascii=False)
    config_hash = sha256(canonical_config.encode()).hexdigest()
    module_path = Path(__file__).resolve().parents[1]/"model"/"stochastic_equilibrium.py"
    code_hash = sha256(Path(__file__).read_bytes()+module_path.read_bytes()).hexdigest()
    logs, progress, previous = [], None, None
    if resume:
        if load_config(output/"config.json") != config:
            raise ValueError("Resume requires the same numerical configuration")
        with np.load(checkpoint, allow_pickle=False) as saved:
            if saved["config_hash"].item() != config_hash or saved["code_hash"].item() != code_hash:
                raise ValueError("Checkpoint was produced by a different configuration or solver")
            progress = tuple(saved["progress"])
            previous = saved["coefficients"]
            logs = json.loads(saved["log_json"].item())
    else:
        if (output/"config.json").exists() or checkpoint.exists():
            raise ValueError("Existing run: use --resume or choose a fresh output path")
        json_write(output/"config.json", config)

    anchor_residual = evaluate_conditions(problem.anchor.state, problem.anchor.policy,
                                          problem.params, problem.anchor.kernel)
    if not anchor_residual["all_local_conditions_passed"]:
        raise ValueError("Configured structural parameters do not match the deterministic anchor")
    linearization = linear_start(problem)
    start = time.perf_counter()
    training = {}
    for degree, count in zip(settings["degrees"], settings["training_counts"], strict=True):
        rng = np.random.default_rng(settings["seed"] + degree)
        design_points = rng.uniform(-1, 1, (count-1, problem.state_dimension))
        training[degree] = np.vstack([problem.center, problem.center +
            settings["training_radius_fraction"]*design_points*problem.radius])
    alternate_start = settings.get("alternate_start_degree", max(settings["degrees"]))
    alternate_degrees = [degree for degree in settings["degrees"] if degree >= alternate_start]
    if not alternate_degrees:
        raise ValueError("alternate_start_degree exceeds the largest projection degree")
    sequence = ([("linear", degree) for degree in settings["degrees"]]
                + [("perturbed", degree) for degree in alternate_degrees])
    for run_index, (initialization, degree) in enumerate(sequence):
        if progress is not None and run_index < progress[0]:
            continue
        projector = Projector(problem, training[degree], degree, linearization)
        coefficient = projector.start.copy()
        if initialization == "perturbed" and degree == alternate_degrees[0]:
            rng = np.random.default_rng(settings["alternate_seed"])
            coefficient[0, 1:] += settings["alternate_perturbation"]*rng.normal(
                size=problem.policy_dimension-1)*np.maximum(abs(coefficient[0, 1:]), 0.1)
            coefficient[1:, 1:] *= 1+settings["alternate_perturbation"]*rng.normal(
                size=coefficient[1:, 1:].shape)
        elif previous is not None and (progress is None or run_index > progress[0]):
            coefficient[:len(previous)] = previous
        stages = settings["amplitude_stages"]
        for stage, amplitude in enumerate(stages):
            iteration_start = 0
            if progress is not None and run_index == progress[0]:
                if stage < progress[1]:
                    continue
                if stage == progress[1]:
                    coefficient = previous.copy()
                    iteration_start = int(progress[2])
                    if iteration_start == settings["max_iterations"]:
                        iteration_start = 0
            change = None
            converged = False
            for iteration in range(iteration_start, settings["max_iterations"]):
                residual = projector.residual(coefficient, amplitude)
                projected = projector.project @ residual
                correction = projector.correction(residual)
                size = float(np.max(np.abs(projected)))
                damping = 0.0
                change = float(np.max(np.abs(correction/problem.policy_scale)))
                if size <= settings["projected_tolerance"] and change <= config["tolerances"]["policy_change"]:
                    converged = True
                else:
                    damping = 1.0
                    while damping >= 1/512:
                        trial = coefficient-damping*correction
                        try:
                            trial_size = np.max(np.abs(projector.project @ projector.residual(trial, amplitude)))
                        except DomainError:
                            trial_size = np.inf
                        if trial_size < size:
                            coefficient = trial
                            break
                        damping *= 0.5
                    if damping < 1/512:
                        damping = 0.0
                logs.append(dict(initialization=initialization, degree=degree,
                                 amplitude=amplitude, iteration=iteration, step=damping,
                                 projected_residual=size, training_max=float(np.abs(residual).max()),
                                 normalized_coefficient_correction=change, converged=converged))
                if (iteration % settings["checkpoint_every"] == 0 or converged
                        or damping == 0 or iteration+1 == settings["max_iterations"]):
                    arrays_write(checkpoint, powers=projector.powers, coefficients=coefficient,
                                 training_states=projector.states, progress=[run_index, stage, iteration+1],
                                 log_json=json.dumps(logs), config_hash=config_hash, code_hash=code_hash,
                                 seed=settings["seed"]+degree, normalized_shock_amplitude=amplitude)
                    json_write(log_path, logs)
                if converged or damping == 0:
                    break
            print(f"{initialization} degree={degree} B×{amplitude:g}: "
                  f"projected={size:.3g} correction={change:.3g} converged={converged}", flush=True)
        previous = coefficient
        name = ("policy.npz" if degree == max(settings["degrees"]) and initialization == "linear"
                else f"policy_{initialization}_degree{degree}.npz")
        arrays_write(output/name, powers=projector.powers, coefficients=coefficient,
                     training_states=projector.states, normalized_shock_amplitude=stages[-1],
                     projected_converged=converged)
    final_stages = {(x["initialization"], x["degree"]): x for x in logs
                    if x["amplitude"] == settings["amplitude_stages"][-1]}
    target_failures = [f"{init}/degree{degree}" for (init, degree), row in final_stages.items()
                       if not row["converged"]]
    metadata = {
        "model_id": config["model_id"], "revision": config["revision"],
        "code_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1], text=True).strip(),
        "solver_sha256": code_hash, "configuration_sha256": config_hash,
        "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
        "method": "damped nonlinear projected residual iteration with a deterministic RE Schur preconditioner",
        "integration": "exact Walsh moments for the 512-branch Rademacher kernel",
        "state_dimension": problem.state_dimension, "independent_conditions": problem.policy_dimension,
        "initial_anchor_raw_residual": anchor_residual["max_equality_or_kkt_residual"],
        "seed": settings["seed"], "alternate_seed": settings["alternate_seed"], "steps": len(logs),
        "elapsed_seconds_current_invocation": time.perf_counter()-start,
        "target_projected_failures": target_failures,
        "status": "implemented_candidates_saved_requiring_independent_validation",
    }
    json_write(output/"solve_report.json", metadata)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/stochastic_baseline.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    output = args.output or Path(load_config(args.config)["solver"]["default_output"])
    solve(args.config, output, args.resume)


if __name__ == "__main__":
    main()
