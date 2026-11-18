"""Check fixed sequences of sustained permitted shocks from the feasible anchor."""
import argparse
import hashlib
import os
from pathlib import Path
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from model.stochastic_equilibrium import Problem, PolynomialPolicy, load_config
from model.stochastic_path_audit import FrozenMoments, period_audit, state_names
from model.stochastic_validation import audit_states
from scripts.solve_stochastic_equilibrium import json_write


BLOCK_MONTHS = 24
XOR_MASKS = (0, 511, 170, 341, 85)
CHECKPOINTS = ((0, 0), (24, 31), (25, 511), (48, 63), (49, 159), (72, 287),
               (73, 0), (96, 511), (97, 300), (120, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    directory = args.run_dir
    config = load_config(directory/"config.json")
    problem = Problem(config)
    policy_path = directory/"policy.npz"
    if args.output.exists():
        raise FileExistsError(args.output)
    with np.load(policy_path, allow_pickle=False) as saved:
        if saved["normalized_shock_amplitude"].item() != 1:
            raise ValueError("Structured target audit requires full-amplitude coefficients")
        policy = PolynomialPolicy(problem, saved["powers"], saved["coefficients"])
    moments = FrozenMoments(policy)
    tolerances = config["tolerances"]
    axes = state_names(problem)
    n = len(problem.kernel.branches)
    path_index = np.arange(n)
    horizon = BLOCK_MONTHS*len(XOR_MASKS)
    states = np.tile(problem.center, (n, 1))
    visited_counts = {key: 0 for key in ("domain", "economic", "primal", "dual", "other_residual")}
    first = {key: {} for key in visited_counts}
    maxima = {}
    radius = 0.0
    saved_states = []
    for month in range(horizon+1):
        for period, index in CHECKPOINTS:
            if month == period:
                saved_states.append(states[index].copy())
        decisions = policy.predict(states)
        result = period_audit(problem, policy, moments, states, decisions)
        radius = max(radius, float(np.max(result.domain_fraction)))
        flags = {"domain": result.domain_fraction > 1+tolerances["feasibility"],
                 "economic": ~result.lawful}
        flags.update({key: np.zeros(n, dtype=bool) for key in ("primal", "dual", "other_residual")})
        for name, scaled in result.scaled.items():
            category = result.categories[name]
            key = category if category in ("primal", "dual") else "other_residual"
            tol_key = ("feasibility" if key != "other_residual" else
                       "complementarity" if category == "complementarity" else "equilibrium")
            flags[key] |= ~np.isfinite(scaled) | (scaled > tolerances[tol_key])
            scores = np.where(np.isfinite(scaled), scaled, -1)
            index = int(np.argmax(scores))
            if name not in maxima or scores[index] > maxima[name]["normalized"]:
                maxima[name] = {"normalized": float(scores[index]), "signed_raw": float(result.raw[name][index]),
                                "month": month, "path": index}
        for key, indices in flags.items():
            visited_counts[key] += int(np.count_nonzero(indices))
            for index in np.flatnonzero(indices):
                if int(index) in first[key]:
                    continue
                prefix = [int(index ^ XOR_MASKS[t//BLOCK_MONTHS]) for t in range(month)]
                first[key][int(index)] = {
                    "month": month, "state": dict(zip(axes, states[index].tolist())),
                    "shock_branch_indices_from_anchor": prefix,
                    "raw_residuals": {name: float(rows[index]) if np.isfinite(rows[index]) else None
                                      for name, rows in result.raw.items()},
                }
        if month < horizon:
            states = problem.successors(states, decisions, path_index ^ XOR_MASKS[month//BLOCK_MONTHS])
    explicit = audit_states(problem, policy, None, np.asarray(saved_states), tolerances)
    report = {
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "paths": n, "months": horizon, "evaluations": n*(1+horizon),
        "month_block_length": BLOCK_MONTHS, "shock_branch_xor_masks": XOR_MASKS,
        "maximum_box_radius_fraction": radius, "counts": visited_counts,
        "first_failures": first, "maxima": maxima, "predeclared_checkpoints_month_path": CHECKPOINTS,
        "explicit_checkpoints": explicit, "only_finite_sequences_tested": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    json_write(args.output, report)
    print(visited_counts, "domain fraction", radius)


if __name__ == "__main__":
    main()
