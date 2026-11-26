"""Tie the stored validation to a frozen policy and its independent reproduction."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.full_conditions import advance_state  # noqa: E402
from model.stochastic_equilibrium import PolynomialPolicy, Problem, load_config  # noqa: E402


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def canonical_digest(config):
    return sha256(json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def archive(path):
    with np.load(path, allow_pickle=False) as data:
        return {name: data[name] for name in data.files}


def compare_archives(a, b):
    keys = ("powers", "training_states", "coefficients", "normalized_shock_amplitude")
    return {
        "array_values_exactly_equal": {name: bool(np.array_equal(a[name], b[name])) for name in keys},
        "coefficient_max_abs_difference": float(np.max(np.abs(a["coefficients"] - b["coefficients"])))
        if a["coefficients"].shape == b["coefficients"].shape else None,
    }


def describe_run(folder):
    config_path = folder / "config.json"
    config = load_config(config_path)
    main = archive(folder / "policy.npz")
    alternate = archive(folder / "policy_perturbed_degree4.npz")
    checkpoint = archive(folder / "checkpoint.npz")
    solve = load_config(folder / "solve_report.json")
    validation = load_config(folder / "validation.json")
    log = json.loads(checkpoint["log_json"].item())
    other = compare_archives(checkpoint, alternate)
    checks = {
        "reported_policy_hash_matches_archive": validation["policy_file"] == "policy.npz"
        and validation["policy_sha256"] == digest(folder / "policy.npz"),
        "reported_config_hash_matches_run_copy": validation["config_sha256"] == digest(config_path),
        "solver_config_hash_matches_canonical_copy": solve["configuration_sha256"] == canonical_digest(config)
        and checkpoint["config_hash"].item() == solve["configuration_sha256"],
        "terminal_checkpoint_solver_hash_matches_run": checkpoint["code_hash"].item() == solve["solver_sha256"],
        "terminal_checkpoint_matches_perturbed_quartic": all(other["array_values_exactly_equal"].values())
        and log[-1]["initialization"] == "perturbed" and log[-1]["degree"] == 4,
        "target_amplitude_and_512_branches": all(float(c["normalized_shock_amplitude"]) == 1
        for c in (main, alternate, checkpoint)) and validation["full_target_nodes_per_state"] == 512,
        "validation_seed_scales_and_tolerances_match": validation["independent_state_seed"]
        == config["validation"]["seed"] and validation["fixed_scales"] == config["scales"]
        and validation["tolerances"] == config["tolerances"],
    }
    summary = {
        "run_id": folder.name,
        "path": str(folder.resolve()),
        "solve_commit": solve["code_base_commit"],
        "validation_commit": validation["code_commit"],
        "config_raw_sha256": digest(config_path),
        "config_canonical_sha256": canonical_digest(config),
        "solver_raw_sha256": solve["solver_sha256"],
        "artifact_sha256": {name: digest(folder / name) for name in (
            "policy.npz", "policy_perturbed_degree4.npz", "checkpoint.npz", "validation.json",
        )},
        "main_basis_order": int(main["powers"].sum(axis=1).max()),
        "main_basis_terms": len(main["powers"]),
        "solver_log_steps": len(log),
        "checkpoint_progress_zero_based": checkpoint["progress"].tolist(),
        "checkpoint_projection_seed": checkpoint["seed"].item(),
        "checkpoint_terminal_log": log[-1],
        "checkpoint_vs_main": compare_archives(checkpoint, main),
        "checkpoint_vs_alternate": other,
        "validation_normalized_maxima": validation["conditions"]["maxima_normalized"],
        "worst_condition": validation["conditions"]["worst_economic_condition"],
        "originally_accepted": validation["numerical_acceptance_passed"],
        "checks": checks,
    }
    return summary, config, validation, main, alternate, checkpoint


def original_scale_rules(report):
    return {
        category: {name: statistics["fixed_scale"]
                   for name, statistics in conditions.items()}
        for category, conditions in report["conditions"]["per_condition"].items()
    }


def representative_moments(problem, policy_archive, points):
    p = problem
    policy = PolynomialPolicy(p, policy_archive["powers"], policy_archive["coefficients"])
    weights = [branch.probability for branch in p.kernel.branches]
    rows = {}
    for name, values in points.items():
        values = np.asarray(values)
        state = p.array_to_state(values)
        decision = p.decision(values, policy.predict(values[None, :])[0])
        successors = np.asarray([
            p.state_to_array(advance_state(state, decision, p.params, p.kernel, branch))
            for branch in p.kernel.branches
        ])
        future_spot = policy.predict(successors)[:, 5]
        mean = math.fsum(w * x for w, x in zip(weights, future_spot))
        variance = math.fsum(w * (x - mean)**2 for w, x in zip(weights, future_spot))
        exposure = p.params.alpha_I * decision.inventory - decision.c
        risk_capacity = 1 / p.params.a_I + 1 / p.params.a_D + 1 / p.environment(values[None, :])["a_f"][0]
        rows[name] = {
            "state": values.tolist(), "spot": decision.spot, "futures": decision.futures,
            "conditional_spot_mean": mean, "conditional_price_variance": variance,
            "net_hedging_exposure_alphaI_I_minus_C": exposure,
            "risk_premium_mu_minus_F": mean - decision.futures,
            "risk_premium_from_E27": variance * exposure / risk_capacity,
        }
    return rows


def compare_validation(reference, candidate):
    metrics = reference["conditions"]["maxima_normalized"]
    comparison = candidate["conditions"]["maxima_normalized"]
    return {
        "scope_matches": all(reference[key] == candidate[key] for key in (
            "sample", "acceptance_gates", "independent_state_seed", "full_target_nodes_per_state")),
        "normalized_maxima_exactly_equal": metrics == comparison,
        "normalized_maxima_absolute_differences": {
            name: abs(value - comparison[name]) for name, value in metrics.items()
        },
        "original_scale_rules_equal": original_scale_rules(reference) == original_scale_rules(candidate),
        "worst_condition_equal": reference["conditions"]["worst_economic_condition"]
        == candidate["conditions"]["worst_economic_condition"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--baseline-frozen-validation", type=Path, required=True)
    parser.add_argument("--reproduction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    old, x, old_report, old_main, old_alt, old_ckpt = describe_run(args.baseline)
    new, y, new_report, new_main, new_alt, new_ckpt = describe_run(args.reproduction)
    frozen_report = load_config(args.baseline_frozen_validation)
    config = load_config(args.config)
    p = Problem(config)
    source_digest = sha256(
        (ROOT / "scripts/solve_stochastic_equilibrium.py").read_bytes()
        + (ROOT / "model/stochastic_equilibrium.py").read_bytes()
    ).hexdigest()
    comparison = {
        "config_content_exactly_equal": x == y == config,
        "current_solver_raw_hash_matches_both_runs": old["solver_raw_sha256"] == new["solver_raw_sha256"] == source_digest,
        "baseline_frozen_validation_uses_baseline_main_and_config": (
            frozen_report["policy_sha256"] == old["artifact_sha256"]["policy.npz"]
            and frozen_report["config_sha256"] == old["config_raw_sha256"]
        ),
        "main": compare_archives(old_main, new_main),
        "alternate": compare_archives(old_alt, new_alt),
        "terminal_checkpoint": compare_archives(old_ckpt, new_ckpt),
        "historical_vs_baseline_new_process": compare_validation(old_report, frozen_report),
        "historical_vs_reproduced_policy": compare_validation(old_report, new_report),
    }
    report = {
        "audit_git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "input_config": {"path": str(args.config.resolve()), "raw_sha256": digest(args.config),
                         "canonical_sha256": canonical_digest(config)},
        "baseline": old,
        "reproduction": new,
        "baseline_frozen_recheck": {"path": str(args.baseline_frozen_validation.resolve()),
                                    "sha256": digest(args.baseline_frozen_validation),
                                    "validation_commit": frozen_report["code_commit"],
                                    "normalized_maxima": frozen_report["conditions"]["maxima_normalized"]},
        "comparison": comparison,
        "seeds": {"training_base": config["solver"]["seed"], "training_per_degree": "training_base + degree",
                  "alternate_initialization": config["solver"]["alternate_seed"],
                  "independent_cross_section": config["validation"]["seed"],
                  "independent_paths": config["validation"]["path_seed"]},
        "residual_scaling_rule": "absolute raw residual divided by fixed scale",
        "scale_constants": config["scales"],
        "scale_by_condition": original_scale_rules(old_report),
        "tolerances": config["tolerances"],
        "loaded_policy_rule": "PolynomialPolicy.predict for current and successor decisions, without online solving",
        "target_kernel": {"amplitudes": p.amplitudes.tolist(), "branches": len(p.kernel.branches),
                          "branch_probability": p.kernel.branches[0].probability},
        "baseline_moments_explicit_scalar_transitions": representative_moments(p, old_main, {
            "deterministic_anchor_state_with_target_stochastic_kernel": p.center,
            "historical_worst_equilibrium_residual": old_report["conditions"]["worst_economic_condition_statistics"]["worst_state"],
        }),
    }
    satisfied = (
        all(s["originally_accepted"] and all(s["checks"].values()) for s in (old, new))
        and frozen_report["numerical_acceptance_passed"]
        and all(comparison[k] for k in ("config_content_exactly_equal", "current_solver_raw_hash_matches_both_runs",
                                      "baseline_frozen_validation_uses_baseline_main_and_config"))
        and all(all(comparison[k]["array_values_exactly_equal"].values())
                for k in ("main", "alternate", "terminal_checkpoint"))
        and all(all(value for k, value in comparison[key].items() if k != "normalized_maxima_absolute_differences")
                for key in ("historical_vs_baseline_new_process", "historical_vs_reproduced_policy"))
    )
    report["exact_reproduction_verified"] = satisfied
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"exact_reproduction_verified": satisfied, "report": str(args.output)}, ensure_ascii=False))
    return 0 if satisfied else 1


if __name__ == "__main__":
    raise SystemExit(main())
