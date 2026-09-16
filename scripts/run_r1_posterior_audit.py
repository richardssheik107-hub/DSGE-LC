"""R1 A01: audit saved production chains without resampling or editing artifacts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import arviz as az
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_posterior_independent import PARAMETERS, ARTIFACTS, audit_file, sha256
from src.structural.mcmc import PosteriorTarget
from src.structural.mcmc_diagnostics import DIAGNOSTIC_VERSION, diagnostic_table
from src.structural.measurement import build_measurements, load_frozen_panel
from src.structural.parameter_transform import ParameterTransform, load_phase2a_bounds
from src.structural.priors import prior_specs

ANCHOR = "d29f66e4775dbf73a52dd2a7b847bafaeea0c593"
PANEL = ROOT / "data/processed/phase1/monthly_structural_v1.csv"
FREEZE = ROOT / "data/processed/core_monthly_panel.csv"
ARTIFACT_DIR = ROOT / "outputs/phase2/phase2d"


def write_csv(path: Path, rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(path)
    if not rows:
        raise ValueError(f"empty output prohibited: {path.name}")
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, ensure_ascii=False, allow_nan=False)


def old_implementation(out: Path):
    raw = subprocess.check_output(["git", "show", f"{ANCHOR}:src/structural/mcmc_diagnostics.py"], cwd=ROOT)
    path = out / "legacy_mcmc_diagnostics.py"
    with path.open("xb") as handle:
        handle.write(raw)
    module = types.ModuleType("r1_legacy_diagnostics")
    exec(compile(raw, f"{ANCHOR}:mcmc_diagnostics.py", "exec"), module.__dict__)
    return module, hashlib.sha256(raw).hexdigest()


def expected_specs(config: dict) -> dict[str, tuple[str, str, float, float]]:
    result = {
        "baseline": ("BASELINE", config["baseline_prior"], config["rho_n_fixed"], config["battery_sd_fixed"]),
        "prior_flat_bounded": ("PRIOR_FLAT_BOUNDED", "PRIOR_FLAT_BOUNDED", config["rho_n_fixed"], config["battery_sd_fixed"]),
        "prior_moderate_shrink": ("PRIOR_MODERATE_SHRINK", "PRIOR_MODERATE_SHRINK", config["rho_n_fixed"], config["battery_sd_fixed"]),
    }
    for item in config["fixed_sensitivity"]:
        result[item["name"].lower()] = (item["name"], config["baseline_prior"], item["rho_n"], item["battery_sd"])
    if set(result) != set(ARTIFACTS):
        raise ValueError("expected specification table does not match seven artifacts")
    return result


def replay_components(theta, z, components, target, rng, count, tolerance, radius_tolerance):
    n = theta.shape[0] * theta.shape[1]
    indices = rng.choice(n, size=min(count, n), replace=False)
    flat_z, flat_components = z.reshape(n, 14), components.reshape(n, 5)
    rows = []
    for index in indices:
        evaluation = target(flat_z[index])
        observed = flat_components[index]
        replayed = np.array([evaluation.total, evaluation.loglik, evaluation.logprior,
                             evaluation.logjacobian, evaluation.spectral_radius])
        difference = np.abs(observed - replayed)
        passed = bool(evaluation.status == "OK" and np.isfinite(replayed).all()
                      and np.max(difference[:4]) <= tolerance and difference[4] <= radius_tolerance)
        rows.append({"chain": int(index // theta.shape[1]) + 1,
                     "draw": int(index % theta.shape[1]),
                     "target_status": evaluation.status,
                     "max_density_component_error": float(np.max(difference[:4])),
                     "radius_error": float(difference[4]), "passed": passed})
    return rows


def reconstruct_baseline(theta, accepted, audit_result, replay_rows, tolerance):
    """Bind metadata-free baseline to old runner and same-run summaries."""
    source = subprocess.check_output(["git", "show", "9d4bf73:scripts/run_phase2d_bayesian_estimation.py"], cwd=ROOT).decode()
    save_rule = 'np.savez_compressed(OUT/"baseline_posterior_draws.npz"' in source
    chain_summary = pd.read_csv(ARTIFACT_DIR / "baseline_chain_summary.csv").iloc[0]
    acceptance = pd.read_csv(ARTIFACT_DIR / "mcmc_acceptance_summary.csv")
    posterior = pd.read_csv(ARTIFACT_DIR / "baseline_posterior_summary.csv").set_index("parameter")
    medians = np.median(theta.reshape(-1, 14), axis=0)
    median_error = float(max(abs(medians[j] - posterior.loc[name, "median"])
                             for j, name in enumerate(PARAMETERS)))
    acceptance_error = float(max(abs(float(accepted[j].mean()) - float(acceptance.iloc[j].production_acceptance))
                                 for j in range(4)))
    radius_error = abs(float(chain_summary["max"]) - audit_result["max_recomputed_radius"])
    checks = {
        "old_runner_saves_only_production_arrays": save_rule and "run_adaptive_chain" in source,
        "old_recorded_chain_draw_count": int(chain_summary.chains) == 4 and int(chain_summary.production_per_chain) == theta.shape[1],
        "old_recorded_extension_count": int(chain_summary.extensions) == 1,
        "same_run_acceptance_fraction_match": acceptance_error <= tolerance,
        "same_run_parameter_median_match": median_error <= tolerance,
        "same_run_radius_max_match": radius_error <= 1e-10,
        "all_replayed_target_components_match": all(row["passed"] for row in replay_rows),
        "all_theta_z_transforms_match": audit_result["transform_gate"],
        "all_draws_stable_and_in_support": audit_result["stability_gate"] and audit_result["parameter_support_gate"],
    }
    return {"status": "RECONSTRUCTED" if all(checks.values()) else "UNVERIFIED",
            "checks": checks, "artifact_sha256": audit_result["sha256"],
            "runner_commit": "9d4bf73", "same_run_files": [
                "outputs/phase2/phase2d/baseline_chain_summary.csv",
                "outputs/phase2/phase2d/mcmc_acceptance_summary.csv",
                "outputs/phase2/phase2d/baseline_posterior_summary.csv",
                "docs/phase2d_bayesian_estimation.md"],
            "max_median_error": median_error, "max_acceptance_error": acceptance_error,
            "radius_max_error": radius_error,
            "limitation": "No contemporaneous external checksum or sidecar survives; preflight hash fixes the original file for this R1 audit. No original NPZ is edited."}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-subdir", default="posterior_audit")
    args = parser.parse_args()
    if "/" in args.output_subdir or "\\" in args.output_subdir or args.output_subdir in (".", ".."):
        raise ValueError("output-subdir must be one directory name")
    out = ROOT / "outputs/revisions" / args.run_id / args.output_subdir
    out.mkdir(parents=True, exist_ok=True)
    names = ("posterior_artifact_integrity.csv", "posterior_diagnostics_legacy.csv",
             "posterior_diagnostics_reference.csv", "posterior_diagnostics_corrected.csv",
             "posterior_diagnostics_comparison.csv", "posterior_gate_by_spec.csv",
             "posterior_hashes_before_after.json", "diagnostic_environment.json",
             "posterior_target_replay.csv", "baseline_reconstructed_metadata.json",
             "legacy_mcmc_diagnostics.py")
    if any((out / name).exists() for name in names):
        raise FileExistsError("R1 outputs already exist; choose a fresh run_id, never overwrite")
    preflight = json.loads((out.parent / "preflight/inputs_before.json").read_text(encoding="utf-8"))
    freeze_hash = sha256(FREEZE)
    if freeze_hash != "9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5" or freeze_hash != preflight["data_freeze"]["sha256"]:
        raise RuntimeError("Data Freeze mismatch")
    if sha256(PANEL) != preflight["transformed_panel"]["sha256"]:
        raise RuntimeError("transformed panel changed")
    original_hashes = {Path(row["path"]).name: row["sha256"] for row in preflight["posterior_artifacts"]}
    cfg = json.loads((ROOT / "configs/phase2d.yaml").read_text(encoding="utf-8"))
    revision = json.loads((ROOT / "configs/r1_revision.json").read_text(encoding="utf-8"))
    parity = revision["reference_parity"]
    replay_cfg = revision["artifact_replay"]
    bounds = load_phase2a_bounds(ROOT / "configs/phase2a.yaml")
    transform = ParameterTransform.full(bounds)
    specs = prior_specs(cfg)
    panel = load_frozen_panel(PANEL)
    measures = build_measurements(panel, cfg["measurement"])
    if len(measures) != 57 or (measures.month.iloc[0], measures.month.iloc[-1]) != ("2021-01", "2025-09"):
        raise RuntimeError("structural sample mismatch")
    y = measures[["spot", "ore_cost", "output", "battery"]].to_numpy()
    old, old_code_hash = old_implementation(out)
    expected = expected_specs(cfg)
    legacy_rows, reference_rows, corrected_rows = [], [], []
    integrity_rows, comparison_rows, gate_rows, target_rows = [], [], [], []
    baseline_reconstruction = None
    for index, name in enumerate(ARTIFACTS):
        label, prior_name, rho_n, battery_sd = expected[name]
        path = ARTIFACT_DIR / f"{name}_posterior_draws.npz"
        if sha256(path) != original_hashes[path.name]:
            raise RuntimeError(f"posterior changed since preflight: {path.name}")
        audited = audit_file(path, expected_specification=prior_name if name.startswith("prior_") or name == "baseline" else label,
                             expected_rho_n=rho_n, expected_battery_sd=battery_sd, bounds=bounds)
        with np.load(path, allow_pickle=False) as raw:
            theta = np.asarray(raw["theta"])
            z = np.asarray(raw["z"])
            components = np.asarray(raw["components"])
            accepted = np.asarray(raw["accepted"])
        target = PosteriorTarget(transform, y, specs[prior_name], rho_n, battery_sd, cfg["numerical_guard_abs_z"])
        replay = replay_components(theta, z, components, target,
                                   np.random.default_rng(replay_cfg["seed"] + index),
                                   replay_cfg["draws_per_spec"],
                                   replay_cfg["component_absolute_tolerance"],
                                   replay_cfg["radius_absolute_tolerance"])
        target_rows.extend({"specification": label, **row} for row in replay)
        target_pass = all(row["passed"] for row in replay)
        if name == "baseline":
            baseline_reconstruction = reconstruct_baseline(theta, accepted, audited, replay,
                                                            replay_cfg["summary_absolute_tolerance"])
            provenance = ("PASS_RECONSTRUCTED" if baseline_reconstruction["status"] == "RECONSTRUCTED"
                          else "UNVERIFIED")
        else:
            provenance = "PASS" if audited["metadata_verified"] else "UNVERIFIED"
        legacy = old.diagnostic_table(theta, PARAMETERS)
        corrected = diagnostic_table(theta, PARAMETERS)
        reference = audited["parameters"]
        if len(legacy) != 14 or len(corrected) != 14 or len(reference) != 14:
            raise ValueError("parameter diagnostic list incomplete")
        parity_pass = True
        for prior_row, ref, new in zip(legacy, reference, corrected):
            parameter = prior_row["parameter"]
            if parameter != ref["parameter"] or parameter != new["parameter"]:
                raise ValueError("diagnostic parameter order mismatch")
            old_row = {"specification": label, **prior_row}
            ref_row = {"specification": label, **ref}
            new_row = {"specification": label, **new}
            legacy_rows.append(old_row)
            reference_rows.append(ref_row)
            corrected_rows.append(new_row)
            rhat_error = abs(new["rhat"] - ref["rhat"])
            bulk_rel = abs(new["bulk_ess"] - ref["bulk_ess"]) / ref["bulk_ess"]
            tail_rel = abs(new["tail_ess"] - ref["tail_ess"]) / ref["tail_ess"]
            mean_rel = abs(new["mean_ess"] - ref["mean_ess"]) / ref["mean_ess"]
            mcse_rel = abs(new["mcse_sd"] - ref["mcse_sd"]) / ref["mcse_sd"]
            one_pass = (rhat_error <= parity["rhat_absolute_tolerance"]
                        and max(bulk_rel, tail_rel, mean_rel) <= parity["ess_relative_tolerance"]
                        and mcse_rel <= parity["mcse_sd_relative_tolerance"])
            parity_pass = bool(parity_pass and one_pass)
            comparison_rows.append({"specification": label, "parameter": parameter,
                                    "legacy_rhat": prior_row["rhat"], "reference_rhat": ref["rhat"], "corrected_rhat": new["rhat"],
                                    "legacy_bulk_ess": prior_row["bulk_ess"], "reference_bulk_ess": ref["bulk_ess"], "corrected_bulk_ess": new["bulk_ess"],
                                    "legacy_tail_ess": prior_row["tail_ess"], "reference_tail_ess": ref["tail_ess"], "corrected_tail_ess": new["tail_ess"],
                                    "legacy_mcse_sd": prior_row["mcse_sd"], "reference_mcse_sd": ref["mcse_sd"], "corrected_mcse_sd": new["mcse_sd"],
                                    "rhat_abs_error": rhat_error, "bulk_rel_error": bulk_rel,
                                    "tail_rel_error": tail_rel, "mean_rel_error": mean_rel,
                                    "mcse_sd_rel_error": mcse_rel, "parity_pass": one_pass})
        support = audited["parameter_support_gate"] and audited["transform_gate"] and target_pass
        stability = audited["stability_gate"] and "STORED_RADIUS_CONFLICT" not in audited["provenance_issues"]
        reference_pass = audited["passed"]
        overall = bool(provenance.startswith("PASS") and support and stability and reference_pass and parity_pass)
        integrity_rows.append({"specification": label, "artifact_sha256": audited["sha256"],
                               "sidecar_sha256": sha256(path.with_suffix(".metadata.json")) if path.with_suffix(".metadata.json").exists() else "",
                               "chains": audited["chains"], "draws_per_chain": audited["draws_per_chain"],
                               "provenance": provenance, "provenance_issues": "|".join(audited["provenance_issues"]),
                               "parameter_support": audited["parameter_support_gate"],
                               "theta_z_transform": audited["transform_gate"],
                               "max_transform_error": audited["max_transform_error"],
                               "max_recomputed_radius": audited["max_recomputed_radius"],
                               "max_stored_radius_error": audited["max_stored_radius_error"],
                               "target_component_replay": target_pass, "unchanged": audited["unchanged"]})
        gate_rows.append({"specification": label, "ARTIFACT_PROVENANCE_GATE": provenance,
                          "PARAMETER_SUPPORT_GATE": "PASS" if support else "FAIL",
                          "STABILITY_GATE": "PASS" if stability else "FAIL",
                          "REFERENCE_CONVERGENCE_GATE": "PASS" if reference_pass else "FAIL",
                          "IMPLEMENTATION_PARITY_GATE": "PASS" if parity_pass else "FAIL",
                          "A01_GATE": "PASS" if overall else "BLOCKED_OR_FAIL",
                          "draws_per_chain": audited["draws_per_chain"],
                          "max_rhat": max(row["rhat"] for row in reference),
                          "min_bulk_ess": min(row["bulk_ess"] for row in reference),
                          "min_tail_ess": min(row["tail_ess"] for row in reference),
                          "max_mcse_sd": max(row["mcse_sd"] for row in reference)})
        print(json.dumps({"specification": label, "draws_per_chain": audited["draws_per_chain"],
                          "provenance": provenance, "reference": reference_pass,
                          "parity": parity_pass, "target_replay": target_pass, "overall": overall}), flush=True)
    if baseline_reconstruction is None:
        raise RuntimeError("baseline not audited")
    write_csv(out / "posterior_artifact_integrity.csv", integrity_rows)
    write_csv(out / "posterior_diagnostics_legacy.csv", legacy_rows)
    write_csv(out / "posterior_diagnostics_reference.csv", reference_rows)
    write_csv(out / "posterior_diagnostics_corrected.csv", corrected_rows)
    write_csv(out / "posterior_diagnostics_comparison.csv", comparison_rows)
    write_csv(out / "posterior_gate_by_spec.csv", gate_rows)
    write_csv(out / "posterior_target_replay.csv", target_rows)
    write_json(out / "baseline_reconstructed_metadata.json", baseline_reconstruction)
    final_hashes = {p.name: sha256(p) for p in (ARTIFACT_DIR / f"{name}_posterior_draws.npz" for name in ARTIFACTS)}
    write_json(out / "posterior_hashes_before_after.json",
               {name: {"before": value, "after": final_hashes[name], "unchanged": final_hashes[name] == value}
                for name, value in original_hashes.items()})
    write_json(out / "diagnostic_environment.json",
               {"recorded_utc": datetime.now(timezone.utc).isoformat(),
                "python": sys.version, "executable": sys.executable,
                "packages": {name: importlib.metadata.version(name)
                             for name in ("arviz", "numpy", "scipy", "pandas", "xarray", "pytest")},
                "legacy_commit": ANCHOR, "legacy_code_sha256": old_code_hash,
                "corrected_diagnostic_version": DIAGNOSTIC_VERSION,
                "phase2d_config_sha256": sha256(ROOT / "configs/phase2d.yaml"),
                "r1_config_sha256": sha256(ROOT / "configs/r1_revision.json"),
                "freeze_sha256": freeze_hash, "transformed_panel_sha256": sha256(PANEL),
                "reference_url": "https://python.arviz.org/en/v0.22.0/",
                "stan_url": "https://mc-stan.org/docs/reference-manual/analysis.html",
                "vehtari_url": "https://avehtari.github.io/rhat_ess/rhat_ess.html"})
    if any(row["A01_GATE"] != "PASS" for row in gate_rows):
        raise SystemExit("A01 audit produced non-PASS gate; see revision outputs")


if __name__ == "__main__":
    main()
