"""Run Phase 2A structural design and local numerical prechecks only."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.structural.identification import (capacity_input_sensitivity, jacobian_metrics,
    numerical_jacobian, weak_pairs)
from src.structural.matrices import system_matrices
from src.structural.measurement import (build_measurements, capacity_effective_coverage,
    load_frozen_panel, measurement_coverage)
from src.structural.observability import observability_metrics, reachability_metrics
from src.structural.simulation import simulate, simulation_summary
from src.structural.spec import MODEL_SPECS, baseline_parameters, parameter_registry
from src.structural.stability import draw_parameters, random_stability_scan, stability_metrics


CONFIG_PATH = ROOT / "configs/phase2a.yaml"
FREEZE = ROOT / "data/processed/core_monthly_panel.csv"
PANEL = ROOT / "data/processed/phase1/monthly_structural_v1.csv"
OUTPUT = ROOT / "outputs/phase2/phase2a"


def stable_draws(model: str, count: int, seed: int, rho_n_grid, rho_k_grid):
    rng = np.random.default_rng(seed); accepted = []; attempts = 0
    while len(accepted) < count and attempts < count * 200:
        rn = rho_n_grid[attempts % len(rho_n_grid)]
        rk = rho_k_grid[attempts % len(rho_k_grid)]
        p = draw_parameters(rng, model, rn, rk)
        A, B, G, H = system_matrices(model, p)
        if stability_metrics(A)["stable"]:
            accepted.append((p, A, B, G, H))
        attempts += 1
    if len(accepted) < count:
        raise RuntimeError(f"only {len(accepted)} stable {model} draws")
    return accepted


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if hashlib.sha256(FREEZE.read_bytes()).hexdigest().lower() != cfg["data_freeze_sha256"].lower():
        raise RuntimeError("Data Freeze v1 hash mismatch")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    frame = load_frozen_panel(PANEL, cfg["sample_end"])
    primary = build_measurements(frame, "OBS_MIXED4")
    secondary = build_measurements(frame, "OBS_DLOG_MOY4")
    p0 = {**baseline_parameters(), **cfg["baseline"]}

    model_rows = []
    for name, spec in MODEL_SPECS.items():
        A, B, G, H = system_matrices(name, p0)
        model_rows.append({"record_type": "model", "name": name, "states": "|".join(spec.states), "observations": "|".join(spec.observations), "shocks": "|".join(spec.shocks), "free_parameter_count": len(spec.free_parameters), "steady_state": "centered_zero", "spectral_radius": stability_metrics(A)["spectral_radius"]})
    for m, data in (("OBS_MIXED4", primary), ("OBS_DLOG_MOY4", secondary)):
        model_rows.append({"record_type": "measurement", "name": m, **measurement_coverage(data, m)})
    for lag in cfg["capacity_lag_grid"]:
        model_rows.append({"record_type": "capacity_coverage", "name": f"margin_lag_{lag}", **capacity_effective_coverage(frame, primary, lag)})
    pd.DataFrame(model_rows).to_csv(OUTPUT / "model_spec_summary.csv", index=False)
    pd.DataFrame(parameter_registry()).to_csv(OUTPUT / "parameter_registry.csv", index=False)

    stability_rows = []
    for i, model in enumerate(MODEL_SPECS):
        A, _, _, _ = system_matrices(model, p0)
        stability_rows.append({"model": model, "draw": "baseline", "rho_n": p0["rho_n"], "rho_k": p0["rho_k"] if model.startswith("M1") else np.nan, "capacity_lag": p0["capacity_lag"] if model.startswith("M1") else np.nan, **stability_metrics(A), "dominant_pattern": "baseline"})
        stability_rows.extend(random_stability_scan(model, cfg["draws_per_model"], cfg["seed"] + i, cfg["rho_n_grid"], cfg["rho_k_grid"], cfg["capacity_lag_grid"]))
    pd.DataFrame(stability_rows).to_csv(OUTPUT / "stability_diagnostics.csv", index=False)

    obs_rows, reach_rows = [], []
    stable_sets = {}
    for i, model in enumerate(MODEL_SPECS):
        A, B, G, H = system_matrices(model, p0)
        obs_rows.append({"model": model, "case": "baseline", "draw": -1, **observability_metrics(A, H)})
        weak = dict(p0); weak["b_n"] = 0.0
        Aw, _, _, Hw = system_matrices(model, weak)
        obs_rows.append({"model": model, "case": "b_n_zero", "draw": -1, **observability_metrics(Aw, Hw)})
        reach_rows.append({"model": model, "case": "structural_shocks_B", **reachability_metrics(A, B)})
        if model == "M1_CAPACITY6": reach_rows.append({"model": model, "case": "shocks_plus_margin_BG", **reachability_metrics(A, np.hstack([B, G]))})
        stable_sets[model] = stable_draws(model, max(cfg["observability_draws"], cfg["jacobian_draws"]), cfg["seed"] + 100 + i, cfg["rho_n_grid"], cfg["rho_k_grid"])
        for j, (_, Aj, _, _, Hj) in enumerate(stable_sets[model][:cfg["observability_draws"]]):
            obs_rows.append({"model": model, "case": "stable_random", "draw": j, **observability_metrics(Aj, Hj)})
    pd.DataFrame(obs_rows).to_csv(OUTPUT / "observability_diagnostics.csv", index=False)
    pd.DataFrame(reach_rows).to_csv(OUTPUT / "reachability_diagnostics.csv", index=False)

    jac_rows, pair_rows = [], []
    for model in MODEL_SPECS:
        scopes = [("autonomous_moments", False)] + ([("moments_plus_margin_input", True)] if model == "M1_CAPACITY6" else [])
        for scope, include_input in scopes:
            J, names = numerical_jacobian(model, p0, p0["battery_measurement_sd"], cfg["finite_difference_step"], include_input)
            jac_rows.append({"model": model, "case": "baseline", "scope": scope, "draw": -1, "battery_sd": p0["battery_measurement_sd"], "moment_count": J.shape[0], **jacobian_metrics(J)})
            for row in weak_pairs(J, names): pair_rows.append({"model": model, "case": "baseline", "scope": scope, "draw": -1, **row})
        for battery_sd in cfg["battery_measurement_sd_grid"]:
            J, _ = numerical_jacobian(model, p0, battery_sd, cfg["finite_difference_step"], model == "M1_CAPACITY6")
            jac_rows.append({"model": model, "case": "battery_sd_sensitivity", "scope": "combined" if model.startswith("M1") else "autonomous_moments", "draw": -1, "battery_sd": battery_sd, "moment_count": J.shape[0], **jacobian_metrics(J)})
        for j, (p, _, _, _, _) in enumerate(stable_sets[model][:cfg["jacobian_draws"]]):
            include = model == "M1_CAPACITY6"
            J, names = numerical_jacobian(model, p, p0["battery_measurement_sd"], cfg["finite_difference_step"], include)
            jac_rows.append({"model": model, "case": "stable_random", "scope": "combined" if include else "autonomous_moments", "draw": j, "battery_sd": p0["battery_measurement_sd"], "moment_count": J.shape[0], **jacobian_metrics(J)})
            for row in weak_pairs(J, names): pair_rows.append({"model": model, "case": "stable_random", "scope": "combined" if include else "autonomous_moments", "draw": j, **row})
    pd.DataFrame(jac_rows).to_csv(OUTPUT / "moment_jacobian_diagnostics.csv", index=False)
    pd.DataFrame(pair_rows, columns=["model","case","scope","draw","parameter_1","parameter_2","absolute_column_cosine","threshold"]).to_csv(OUTPUT / "weak_identification_pairs.csv", index=False)

    sensitivity = []
    for lag in cfg["capacity_lag_grid"]:
        for rk in cfg["rho_k_grid"]:
            pp = dict(p0); pp["rho_k"] = rk
            sensitivity.append(capacity_input_sensitivity(pp, lag, seed=cfg["seed"] + lag))
    pd.DataFrame(sensitivity).to_csv(OUTPUT / "capacity_input_sensitivity.csv", index=False)

    sim_rows = []
    for model in MODEL_SPECS:
        values = simulate(model, p0, cfg["simulation_periods"], cfg["simulation_burn"], cfg["seed"], p0["capacity_lag"])
        sim_rows.extend(simulation_summary(model, values))
    pd.DataFrame(sim_rows).to_csv(OUTPUT / "synthetic_simulation_summary.csv", index=False)

    decision = [
        {"model": "M0_CORE5", "role": "PRIMARY_FOR_PHASE2B", "decision": "SELECT", "reason": "parsimonious 14-parameter core; stable/observable at baseline; no extra predetermined-input identification burden"},
        {"model": "M1_CAPACITY6", "role": "PRE_SPECIFIED_EXTENSION", "decision": "RETAIN_NOT_PRIMARY", "reason": "economically motivated slow channel, but gamma_m is absent from autonomous covariance moments and needs margin-input variation"},
    ]
    pd.DataFrame(decision).to_csv(OUTPUT / "model_decision_table.csv", index=False)
    print(f"Phase 2A complete: {OUTPUT}")


if __name__ == "__main__":
    main()
