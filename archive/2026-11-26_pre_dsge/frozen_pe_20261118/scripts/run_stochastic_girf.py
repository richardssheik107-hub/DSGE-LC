"""Conditional sign GIRFs under the released, frozen stochastic LC policy."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import scipy

from model.full_conditions import EXTERNAL_NAMES
from model.stochastic_equilibrium import load_config, PolynomialPolicy, Problem
from model.stochastic_path_audit import FrozenMoments, period_audit, VARIABLE_NAMES, state_names
from model.stochastic_validation import audit_states


DISPLAY = ("P", "F", "Q", "I", "J", "K_e", "C", "risk_premium")
VARIABLES = DISPLAY + ("D_s", "expected_spot", "price_variance", "net_hedge_exposure",
                       "risk_premium_E27", "unit_cost", "demand_scale")
SHOCKS = ("zA_id", "zm_id")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, content):
    path.write_text(json.dumps(content, ensure_ascii=False, allow_nan=False, indent=2)+"\n", encoding="utf-8")


def load_release(spec):
    run = ROOT/spec["policy_run"]
    index_path, config_path = run/"run_index.json", run/"config.json"
    index = load_config(index_path)
    if not index["independent_local_validation_passed"] or not index["refined_policy_exactly_reproduced"]:
        raise ValueError("This GIRF needs the independently validated refined release")
    policy_path = run/"policy.npz"
    report_path = run/"validation.json"
    warm_report_key = spec["warmup_report_release_key"]
    paths = {"refined_policy": policy_path, "refined_canonical_validation": report_path,
             warm_report_key: ROOT/index["files"][warm_report_key]["path"]}
    fingerprints = {key: sha(path) for key, path in paths.items()}
    if any(value != index["files"][key]["sha256"] for key, value in fingerprints.items()):
        raise ValueError("Released policy or report SHA-256 mismatch")
    validation = load_config(report_path)
    warm_validation = load_config(paths[warm_report_key])
    config = load_config(config_path)
    config_sha = sha(config_path)
    if (not validation["numerical_acceptance_passed"] or
            not warm_validation["all_sampled_paths_and_checkpoints_passed"] or
            validation["policy_sha256"] != fingerprints["refined_policy"] or
            warm_validation["frozen_policy_sha256"] != fingerprints["refined_policy"] or
            validation["config_sha256"] != config_sha or warm_validation["config_sha256"] != config_sha):
        raise ValueError("Policy, economic config and warm-up validation must all match")
    problem = Problem(config)
    with np.load(policy_path, allow_pickle=False) as archive:
        if float(archive["normalized_shock_amplitude"]) != 1 or not bool(archive["projected_converged"]):
            raise ValueError("Policy is not the full-amplitude converged solution")
        policy = PolynomialPolicy(problem, archive["powers"], archive["coefficients"])
    policy.coefficients.flags.writeable = policy.powers.flags.writeable = False
    value_coefficients = np.array(validation["producer_value_projection"]["coefficients"])
    release = dict(run_index_sha256=sha(index_path), config_sha256=config_sha,
                   frozen_policy_code_commit=index["code_commit"], **fingerprints)
    if any(problem.amplitudes <= 0) or len(problem.kernel.branches) != 512:
        raise ValueError("Expected the full nine-dimensional target kernel")
    return problem, policy, value_coefficients, release


def choose_starts(problem, policy, spec):
    source = ROOT/spec["warmup_archive"]
    if sha(source) != spec["warmup_archive_sha256"]:
        raise ValueError("Warm-up archive SHA-256 mismatch")
    starts = {"anchor": {"state": problem.center.tolist(), "label": "确定性锚"}}
    if spec["warmup_index_rule"] != "first_and_last_burnin_path_indices":
        raise ValueError("Unexpected initial state selection rule")
    with np.load(source, allow_pickle=False) as archive:
        indices = archive["burnin_path_indices"]
        positions = (0, len(indices)-1)
        rows = indices[list(positions)]
        roots = archive["roots"][rows]
        states = archive["starts"][rows]
        shocks = archive["burnin_shock_indices"][:, positions]
    replay = roots.copy()
    for branch in shocks:
        replay = problem.successors(replay, policy.predict(replay), branch)
    errors = np.max(np.abs(replay-states), axis=1)
    if np.any(errors > problem.config["tolerances"]["feasibility"]):
        raise ValueError("Archived warm-up path replay mismatch")
    for k, row in enumerate(rows):
        starts[f"warm_{k}"] = dict(state=states[k].tolist(), label=f"预热起点 {k+1}", archive_path_index=int(row),
                                   archive_burnin_column=positions[k], warmup_root=roots[k].tolist(),
                                   warmup_branch_indices=shocks[:, k].tolist(), max_replay_error=float(errors[k]))
    return starts


def sign_pairs(problem, shock):
    index = EXTERNAL_NAMES.index(shock)
    plus = np.flatnonzero(problem.innovations[:, index] == 1)
    minus = np.flatnonzero(problem.innovations[:, index] == -1)
    equal_coordinates = [i for i in range(len(EXTERNAL_NAMES)) if i != index]
    if len(plus) != 256 or not np.array_equal(problem.innovations[plus][:, equal_coordinates],
                                              problem.innovations[minus][:, equal_coordinates]):
        raise ValueError("Non-target innovations do not agree across opposite-sign pairs")
    return plus, minus


def audit_period(problem, policy, moments, states, decisions, audit):
    result = period_audit(problem, policy, moments, states, decisions)
    tol = problem.config["tolerances"]
    flags = {"domain": result.domain_fraction > 1+tol["feasibility"], "economic": ~result.lawful}
    maxima = audit["max_normalized"]
    for key, scaled in result.scaled.items():
        category = result.categories[key]
        limit = (tol["feasibility"] if category in {"primal", "dual"} else
                 tol["complementarity"] if category == "complementarity" else tol["equilibrium"])
        flags[key] = ~np.isfinite(scaled) | (scaled > limit)
        finite = scaled[np.isfinite(scaled)]
        if len(finite):
            maxima[category] = max(maxima.get(category, 0), float(finite.max()))
    audit["states_checked"] += len(states)
    audit["max_box_radius_fraction"] = max(audit["max_box_radius_fraction"], float(np.nanmax(result.domain_fraction)))
    audit["failure_counts"].update({key: int(flag.sum()) for key, flag in flags.items() if flag.any()})
    return result, np.logical_or.reduce(list(flags.values()))


def full_failure_path(problem, policy, root, branch_sequence):
    states = [root.copy()]
    s = root[None, :]
    for branch in branch_sequence:
        s = problem.successors(s, policy.predict(s), np.array([branch]))
        states.append(s[0].copy())
    return np.asarray(states)


def summarize_section(positive, negative):
    paired = (positive-negative)/2
    if len(paired) < 2:
        raise ValueError("At least two future draws per stratum are required for a Monte Carlo standard error")
    # Each of the 256 strata has an equal exact weight and independent repeated future draws.
    mc_se = np.sqrt(paired.var(axis=0, ddof=1).sum(axis=0)/len(paired))/paired.shape[1]
    return positive.mean(axis=(0, 1)), negative.mean(axis=(0, 1)), paired.mean(axis=(0, 1)), mc_se


def simulate_case(problem, policy, moments, root, future, signs, spec, explicit, explicit_labels, output):
    audit = dict(states_checked=0, max_box_radius_fraction=0.0, max_normalized={}, failure_counts=Counter())
    h, reps, strata = future.shape
    samples = np.empty((2, reps, strata, h+1, len(VARIABLES)), dtype=float)
    failures = {}
    checkpoint = spec["checkpoints"]
    record_months = set(checkpoint["months"]) | {h}
    root_decision = policy.predict(root[None, :])
    env_names = ("m", "A")
    variable_index = [VARIABLE_NAMES.index(k) for k in VARIABLES[:-2]]
    strata_indices = np.arange(strata)
    previous_reps = 0
    stages = []
    for rep_count in spec["replications_per_initial_stratum"]:
        for offset in range(previous_reps*strata, rep_count*strata, spec["batch_pairs"]):
            end = min(offset+spec["batch_pairs"], rep_count*strata)
            pairs = np.arange(offset, end)
            rep, stratum = np.divmod(pairs, strata)
            paths = np.concatenate([pairs, pairs])
            sign_index = np.repeat([0, 1], len(pairs))
            pair_strata = np.tile(stratum, 2)
            start_branches = np.concatenate([branches[stratum] for branches in signs])
            states = problem.successors(np.repeat(root[None], len(paths), axis=0),
                                        np.repeat(root_decision, len(paths), axis=0), start_branches)
            repetitions = np.tile(rep, 2)
            for month in range(h+1):
                decisions = policy.predict(states)
                result, bad = audit_period(problem, policy, moments, states, decisions, audit)
                environment = problem.environment(states)
                values = np.column_stack((result.variables[:, variable_index],
                                          *(environment[key] for key in env_names)))
                samples[sign_index, repetitions, pair_strata, month] = values
                for index in np.flatnonzero(bad):
                    label = (int(sign_index[index]), int(paths[index]))
                    if label not in failures:
                        failures[label] = dict(month=month, state=states[index].tolist(), decision=decisions[index].tolist(),
                                               raw_residual={key: float(v[index]) if np.isfinite(v[index]) else None
                                                             for key, v in result.raw.items()})
                if month in record_months:
                    for index in np.flatnonzero((repetitions == checkpoint["replication"]) &
                                                np.isin(pair_strata, checkpoint["strata"])):
                        explicit.append(states[index].copy())
                        explicit_labels.append(dict(case=output.name, sign=int(1-2*sign_index[index]), month=month,
                                                    stratum=int(pair_strata[index]), replication=int(repetitions[index])))
                if month < h:
                    downstream = future[month, rep, stratum]
                    states = problem.successors(states, decisions, np.tile(downstream, 2))
        stage = summarize_section(samples[0, :rep_count], samples[1, :rep_count])
        stages.append(stage)
        print(f"{output.name}: {rep_count*strata} pairs, {h} months, {sum(audit['failure_counts'].values())} flags",
              flush=True)
        previous_reps = rep_count
    if failures:
        audit["failed_paths"] = len(failures)
        records = []
        for (sign, pair), first in failures.items():
            rep, stratum = divmod(pair, strata)
            sequence = [int(signs[sign][stratum]), *future[:, rep, stratum].tolist()]
            history = full_failure_path(problem, policy, root, sequence)
            records.append(dict(first=first, sign=1-2*sign, pair=pair, shock_branches=sequence,
                                entire_path_including_pre_shock_state=history.tolist()))
        write_json(output.with_suffix(".failures.json"), records)
    return stages, audit


def run_horizon(problem, policy, value, starts, spec, horizon, output):
    output.mkdir(exist_ok=False)
    moments = FrozenMoments(policy, value)
    reps = spec["replications_per_initial_stratum"]
    audits, case_stats, explicit, labels, responses, convergence = {}, [], [], [], [], []
    for shock in SHOCKS:
        signs = sign_pairs(problem, shock)
        future = np.random.default_rng(spec["seeds"][shock]).integers(
            len(problem.kernel.branches), size=(horizon, reps[-1], len(signs[0])), dtype=np.uint16)
        np.savez_compressed(output/f"draws_{shock}.npz", future_branches=future,
                            positive_initial_branches=signs[0], negative_initial_branches=signs[1])
        for start_id, start in starts.items():
            case = f"{shock}_{start_id}"
            stages, audit = simulate_case(problem, policy, moments, np.array(start["state"]),
                                           future, signs, spec, explicit, labels, output/case)
            audits[case] = audit
            plus, minus, girf, se = stages[-1]
            for h in range(horizon+1):
                for k, var in enumerate(VARIABLES):
                    responses.append(dict(shock=shock, start_id=start_id, horizon=h, variable=var,
                                          m_plus=plus[h, k], m_minus=minus[h, k],
                                          m_base=(plus[h, k]+minus[h, k])/2,
                                          girf_plus=girf[h, k], mc_se=se[h, k],
                                          paired_paths_per_case=reps[-1]*len(signs[0])))
            for k, var in enumerate(VARIABLES):
                peak = float(np.max(np.abs(girf[:, k])))
                tail = float(np.max(np.abs(girf[-spec["terminal_window_months"]:, k])))
                floor = spec["tail_absolute_floor"]
                threshold = max(floor, peak*spec["tail_relative_to_peak"])
                significant_tail = tail > threshold and bool(
                    np.any(np.abs(girf[-spec["terminal_window_months"]:, k]) >
                           threshold+2*se[-spec["terminal_window_months"]:, k]))
                change = []
                for i in range(1, len(stages)):
                    absolute = float(np.max(np.abs(stages[i][2][:, k]-stages[i-1][2][:, k])))
                    change.append(absolute)
                    convergence.append(dict(shock=shock, start_id=start_id, variable=var,
                                            pairs_before=reps[i-1]*len(signs[0]), pairs_after=reps[i]*len(signs[0]),
                                            max_abs_change=absolute, change_as_fraction_of_peak=absolute/max(floor, peak),
                                            max_mc_se=float(np.max(stages[i][3][:, k]))))
                case_stats.append(dict(shock=shock, start_id=start_id, variable=var, response_at_0=girf[0, k],
                                       peak_month=int(np.argmax(np.abs(girf[:, k]))), absolute_peak=peak, tail=tail,
                                       tail_significant=significant_tail,
                                       last_stage_difference_fraction=change[-1]/max(floor, peak),
                                       last_stage_stable=change[-1] <= max(floor, peak*spec["sampling_stability_relative_to_peak"])))
    start_rows = [start["state"] for start in starts.values()]
    labels = [dict(pre_shock_start=k) for k in starts] + labels
    scalar = audit_states(problem, policy, value, np.vstack([start_rows, explicit]), problem.config["tolerances"])
    scalar["checkpoint_labels_in_order"] = labels
    write_json(output/"explicit_512_checks.json", scalar)
    for filename, items in (("response.csv", responses), ("sampling_stability.csv", convergence)):
        with (output/filename).open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(items[0]))
            writer.writeheader()
            writer.writerows(items)
    report = dict(months=horizon, acceptance_passed=all(scalar["checks"].values()) and
                  all(not row["failure_counts"] for row in audits.values()),
                  each_period=audits, case_statistics=case_stats,
                  all_display_series_sampling_stable=all(row["last_stage_stable"] for row in case_stats
                                                         if row["variable"] in DISPLAY),
                  checkpoint_states=len(labels), checkpoint_successors=scalar["successors_tested"])
    write_json(output/"simulation.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=ROOT/"configs/stochastic_girf.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = load_config(args.experiment)
    start_time = time.perf_counter()
    problem, policy, value, provenance = load_release(spec)
    starts = choose_starts(problem, policy, spec)
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/"experiment.json", spec)
    write_json(output/"economic_config.json", problem.config)
    write_json(output/"starts.json", {"order": state_names(problem), "starts": starts})
    config = problem.config
    provenance.update(dict(experiment_sha256=sha(args.experiment),
                           source_file_sha256=sha(Path(__file__).resolve()),
                           execution_git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                           python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                           shock_transmission={shock: dict(zero_based_index=EXTERNAL_NAMES.index(shock),
                               loading=config["shock_amplitudes"][EXTERNAL_NAMES.index(shock)],
                               persistence=config["transition_diagonal"][EXTERNAL_NAMES.index(shock)],
                               primitive="A, A_s, A_c" if shock == "zA_id" else "m",
                               primitive_multiplier_plus_vs_same_AR_location=float(np.exp(config["shock_amplitudes"][EXTERNAL_NAMES.index(shock)])))
                                               for shock in SHOCKS}))
    write_json(output/"provenance.json", provenance)
    months = spec["horizon_months"]
    initial_result = run_horizon(problem, policy, value, starts, spec, months, output/f"months_{months}")
    result = initial_result
    tail = [row for row in result["case_statistics"] if row["variable"] in DISPLAY and row["tail_significant"]]
    if tail and result["acceptance_passed"]:
        months = spec["extended_horizon_months"]
        result = run_horizon(problem, policy, value, starts, spec, months, output/f"months_{months}")
    final_folder = output/f"months_{months}"
    for filename in ("response.csv", "sampling_stability.csv", "simulation.json", "explicit_512_checks.json"):
        (output/filename).write_bytes((final_folder/filename).read_bytes())
    write_json(output/"run.json", dict(run_id=output.name, displayed_months=months, extension_trigger=tail,
                                      hours_definition="Month zero is first decision after sign intervention; all later shocks are iid.",
                                      paired_se="Stratified Monte Carlo standard error of the half paired difference.",
                                      acceptance_passed=result["acceptance_passed"],
                                      all_display_series_sampling_stable=result["all_display_series_sampling_stable"],
                                      elapsed_seconds=time.perf_counter()-start_time))
    return 0 if result["acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
