"""Recompute R1 FEVD summaries from the seven accepted Phase 2D posteriors.

This script never estimates parameters and never writes Phase 2E outputs.
Run with ``--revision-dir outputs/revisions/<run_id>`` after A01 passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.structural.fevd import posterior_fevd_summary, structural_fevd
from src.structural.irf import SHOCK_ORDER, STATE_ORDER
from src.structural.matrices import system_matrices
from src.structural.parameter_transform import PARAMETER_ORDER


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_specs(phase2e: dict, phase2d: dict, required: list[str]) -> dict[str, dict]:
    baseline = {"rho_n": float(phase2d["rho_n_fixed"]),
                "battery_sd": float(phase2d["battery_sd_fixed"])}
    fixed = {item["name"]: item for item in phase2d["fixed_sensitivity"]}
    paths = {"BASELINE": phase2e["baseline_artifact"], **phase2e["sensitivity_artifacts"]}
    if set(paths) != set(required) or len(required) != len(set(required)):
        raise ValueError("R1 required FEVD specifications do not match Phase 2E artifacts")
    result = {}
    for name in required:
        if name in fixed:
            rho_n = float(fixed[name]["rho_n"])
            battery_sd = float(fixed[name]["battery_sd"])
        elif name in ("BASELINE", "PRIOR_FLAT_BOUNDED", "PRIOR_MODERATE_SHRINK"):
            rho_n, battery_sd = baseline["rho_n"], baseline["battery_sd"]
        else:
            raise ValueError(f"unrecognized FEVD specification: {name}")
        result[name] = {"path": ROOT / paths[name], "rho_n": rho_n,
                        "battery_sd": battery_sd}
    return result


def validate_a01_tables(gate: pd.DataFrame, integrity: pd.DataFrame,
                        required: list[str]) -> None:
    """Reject duplicate/missing specifications before selecting accepted draws."""
    if (not gate.index.is_unique or not integrity.index.is_unique
            or set(gate.index) != set(required) or set(integrity.index) != set(required)):
        raise RuntimeError("A01 gate/integrity specifications are duplicated or incomplete")
    if not gate.loc[required, "A01_GATE"].eq("PASS").all():
        raise RuntimeError("R1 FEVD requires all seven A01 posterior gates to PASS")


def covariance_identity_errors(A: np.ndarray, B: np.ndarray, contributions: np.ndarray,
                               horizons: tuple[int, ...]) -> np.ndarray:
    """Check diag(sum A^h B B' (A^h)') against column contributions at each H."""
    W = B @ B.T
    power = np.eye(A.shape[0])
    covariance = np.zeros_like(W)
    errors = np.empty((len(horizons), A.shape[0]), dtype=float)
    positions = {h: k for k, h in enumerate(horizons)}
    for h in range(1, max(horizons) + 1):
        covariance += power @ W @ power.T
        if h in positions:
            errors[positions[h]] = np.abs(np.diag(covariance) - contributions[positions[h]].sum(axis=-1))
        power = A @ power
    return errors


def draw_audit(shares: np.ndarray, contributions: np.ndarray,
               covariance_errors: np.ndarray, tolerance: float) -> dict[str, np.ndarray]:
    """Return horizon/state audit arrays for a single float64 draw."""
    total = contributions.sum(axis=-1)
    defined = total > 0
    expected = np.full_like(shares, np.nan)
    np.divide(contributions, total[..., None], out=expected, where=defined[..., None])
    sum_error = np.where(defined, np.abs(np.nansum(shares, axis=-1) - 1), 0.)
    # Use a zero-filled mask so an all-NaN undefined vector raises no warning.
    ratio_error = np.max(np.where(defined[..., None], np.abs(shares - expected), 0.), axis=-1)
    valid_defined = (np.isfinite(shares).all(axis=-1) == defined).all()
    valid_undefined = np.isnan(shares[~defined]).all()
    valid_bounds = np.all((shares[defined] >= -tolerance) & (shares[defined] <= 1 + tolerance))
    valid_contributions = np.isfinite(contributions).all() and np.all(contributions >= 0)
    valid = (valid_defined and valid_undefined and valid_bounds and valid_contributions
             and np.isfinite(total).all() and np.isfinite(covariance_errors).all())
    return {"total": total, "defined": defined, "sum_error": sum_error,
            "ratio_error": ratio_error, "covariance_error": covariance_errors,
            "valid": bool(valid)}


def summarize_specification(name: str, theta: np.ndarray, rho_n: float,
                            horizons: tuple[int, ...], tolerance: float,
                            artifact_hash: str) -> tuple[list[dict], list[dict]]:
    if theta.ndim != 3 or theta.shape[0] != 4 or theta.shape[2] != len(PARAMETER_ORDER):
        raise ValueError(f"invalid posterior draw shape: {name}")
    flat = theta.reshape(-1, len(PARAMETER_ORDER))
    count = len(flat)
    n_h, n_states, n_shocks = len(horizons), len(STATE_ORDER), len(SHOCK_ORDER)
    shares_all = np.empty((count, n_h, n_states, n_shocks), dtype=np.float64)
    zero_count = np.zeros((n_h, n_states), dtype=np.int64)
    min_denominator = np.full((n_h, n_states), np.inf)
    max_draw_sum_error = np.zeros((n_h, n_states))
    max_ratio_error = np.zeros((n_h, n_states))
    max_covariance_error = np.zeros((n_h, n_states))
    for draw, row in enumerate(flat):
        parameters = {parameter: float(row[j]) for j, parameter in enumerate(PARAMETER_ORDER)}
        parameters["rho_n"] = rho_n
        A, B, _, _ = system_matrices("M0_CORE5", parameters)
        if B.shape != (5, 4):
            raise ValueError(f"invalid structural impact matrix shape: {name} draw {draw}")
        shares, contributions = structural_fevd(A, B, horizons)
        covariance_errors = covariance_identity_errors(A, B, contributions, horizons)
        audit = draw_audit(shares, contributions, covariance_errors, tolerance)
        if not audit["valid"]:
            raise RuntimeError(f"invalid FEVD draw: {name} draw {draw}")
        totals = audit["total"]
        zero_count += (~audit["defined"]).astype(np.int64)
        min_denominator = np.minimum(min_denominator, totals)
        max_draw_sum_error = np.maximum(max_draw_sum_error, audit["sum_error"])
        max_ratio_error = np.maximum(max_ratio_error, audit["ratio_error"])
        max_covariance_error = np.maximum(max_covariance_error, audit["covariance_error"])
        shares_all[draw] = shares
        if (draw + 1) % 50000 == 0:
            print(f"{name}: {draw + 1}/{count} FEVD draws", flush=True)

    summaries = posterior_fevd_summary(shares_all, horizons, STATE_ORDER, SHOCK_ORDER)
    for row in summaries:
        row.update({"specification": name, "posterior_artifact_sha256": artifact_hash,
                    "summary_basis": "PER_DRAW_SHARES", "unit": "share"})
    audit_rows = []
    for k, horizon in enumerate(horizons):
        for i, state in enumerate(STATE_ORDER):
            defined = np.isfinite(shares_all[:, k, i, :]).all(axis=-1)
            if defined.any():
                mean_sum_error = float(abs(shares_all[defined, k, i, :].mean(axis=0).sum() - 1))
            else:
                mean_sum_error = np.nan
            price_positive = state != "p" or min_denominator[k, i] > 0
            numeric_ok = (price_positive and max_draw_sum_error[k, i] <= tolerance
                          and max_ratio_error[k, i] <= tolerance
                          and max_covariance_error[k, i] <= tolerance
                          and (not defined.any() or
                               (np.isfinite(mean_sum_error) and mean_sum_error <= tolerance)))
            status = ("FAIL" if not numeric_ok else
                      "NOT_DEFINED" if zero_count[k, i] == count else
                      "PARTIALLY_DEFINED" if zero_count[k, i] > 0 else "PASS")
            audit_rows.append({"specification": name, "horizon": horizon, "state": state,
                               "draws": count, "defined_draws": int(defined.sum()),
                               "zero_forecast_variance_draws": int(zero_count[k, i]),
                               "min_forecast_variance": float(min_denominator[k, i]),
                               "max_draw_share_sum_error": float(max_draw_sum_error[k, i]),
                               "max_share_ratio_error": float(max_ratio_error[k, i]),
                               "max_mean_share_sum_error": mean_sum_error,
                               "max_covariance_diagonal_error": float(max_covariance_error[k, i]),
                               "tolerance": tolerance, "status": status})
    del shares_all
    return summaries, audit_rows


def plot_baseline_mean_price(summary: pd.DataFrame, horizons: tuple[int, ...], path: Path) -> None:
    price = summary[(summary.specification == "BASELINE") & (summary.state == "p")]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bottom = np.zeros(len(horizons))
    colors = ("#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd")
    for shock, color in zip(SHOCK_ORDER, colors):
        section = price[price.shock == shock].set_index("horizon")
        height = section.loc[list(horizons), "mean"].to_numpy(float)
        ax.bar(np.arange(len(horizons)), height, bottom=bottom, label=shock, color=color)
        bottom += height
    if not np.allclose(bottom, 1, atol=1e-10):
        raise RuntimeError("baseline mean FEVD stack is not additive")
    ax.set_xticks(np.arange(len(horizons)), [str(h) for h in horizons])
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Forecast horizon (months)")
    ax.set_ylabel("Posterior mean of per-draw FEVD share")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(.5, 1.15), frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run(revision_dir: Path) -> dict:
    revision_root = (ROOT / "outputs/revisions").resolve()
    revision_dir = revision_dir.resolve()
    if revision_dir.parent != revision_root or not revision_dir.name.startswith("R1_"):
        raise ValueError("revision directory must be outputs/revisions/R1_<run_id>")
    output = revision_dir / "fevd"
    result_names = ("fevd_corrected_summary.csv", "fevd_additivity_audit.csv",
                    "fevd_price_horizons_mean_stacked.png", "fevd_manifest.json")
    if any((output / name).exists() for name in result_names):
        raise FileExistsError("R1 FEVD revision output already exists")
    if subprocess.run(["git", "check-ignore", "-q", str(output / result_names[0])],
                      cwd=ROOT, check=False).returncode != 0:
        raise RuntimeError("revision output is not Git-ignored")

    cfg_path = ROOT / "configs/r1_revision.json"
    phase2e_path = ROOT / "configs/phase2e.yaml"
    phase2d_path = ROOT / "configs/phase2d.yaml"
    gate_path = revision_dir / "posterior_audit_final/posterior_gate_by_spec.csv"
    integrity_path = revision_dir / "posterior_audit_final/posterior_artifact_integrity.csv"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    phase2e = json.loads(phase2e_path.read_text(encoding="utf-8-sig"))
    phase2d = json.loads(phase2d_path.read_text(encoding="utf-8-sig"))
    required = cfg["historical"]["required_specifications"]
    tolerance = float(cfg["historical"]["fevd_additivity_absolute_tolerance"])
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("invalid predeclared FEVD additivity tolerance")
    horizons = tuple(phase2e["fevd_horizons"])
    specs = load_specs(phase2e, phase2d, required)
    gate = pd.read_csv(gate_path).set_index("specification")
    integrity = pd.read_csv(integrity_path).set_index("specification")
    validate_a01_tables(gate, integrity, required)

    inputs = [cfg_path, phase2e_path, phase2d_path, gate_path, integrity_path,
              ROOT / "data/processed/core_monthly_panel.csv",
              ROOT / "data/processed/phase1/monthly_structural_v1.csv"]
    for spec in specs.values():
        inputs.append(spec["path"])
        sidecar = spec["path"].with_suffix(".metadata.json")
        if sidecar.exists():
            inputs.append(sidecar)
    before = {path.relative_to(ROOT).as_posix(): sha256(path) for path in inputs}
    if before["data/processed/core_monthly_panel.csv"] != json.loads(
            (ROOT / "configs/phase2a.yaml").read_text(encoding="utf-8-sig"))["data_freeze_sha256"].lower():
        raise RuntimeError("Data Freeze v1 hash mismatch")
    for name, spec in specs.items():
        expected_hash = str(integrity.loc[name, "artifact_sha256"])
        if sha256(spec["path"]) != expected_hash:
            raise RuntimeError(f"A01 posterior artifact hash mismatch: {name}")

    summaries, audits, artifact_manifest = [], [], []
    for name in required:
        spec = specs[name]
        with np.load(spec["path"], allow_pickle=False) as archive:
            theta = np.asarray(archive["theta"], dtype=float)
        if theta.shape[1] != int(gate.loc[name, "draws_per_chain"]):
            raise RuntimeError(f"A01 draw count mismatch: {name}")
        artifact_hash = before[spec["path"].relative_to(ROOT).as_posix()]
        rows, checks = summarize_specification(name, theta, spec["rho_n"],
                                               horizons, tolerance, artifact_hash)
        summaries.extend(rows)
        audits.extend(checks)
        artifact_manifest.append({"specification": name,
                                  "artifact": spec["path"].relative_to(ROOT).as_posix(),
                                  "sha256": artifact_hash, "chains": theta.shape[0],
                                  "draws_per_chain": theta.shape[1],
                                  "total_draws": int(theta.shape[0] * theta.shape[1]),
                                  "rho_n": spec["rho_n"], "battery_sd": spec["battery_sd"]})
        print(f"{name}: FEVD audit {set(row['status'] for row in checks)}", flush=True)
        del theta
    if any(row["status"] == "FAIL" for row in audits):
        raise RuntimeError("R1 FEVD numerical/additivity gate failed")
    after = {path.relative_to(ROOT).as_posix(): sha256(path) for path in inputs}
    if before != after:
        raise RuntimeError("R1 FEVD input hash changed during computation")

    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / result_names[0]
    audit_path = output / result_names[1]
    figure_path = output / result_names[2]
    summary = pd.DataFrame(summaries)
    audit = pd.DataFrame(audits)
    summary.to_csv(summary_path, index=False)
    audit.to_csv(audit_path, index=False)
    plot_baseline_mean_price(summary, horizons, figure_path)
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = {"revision": "R1", "component": "A05_FEVD", "status": "TECHNICAL_PASS",
                "source_commit": source_commit,
                "script_sha256": sha256(Path(__file__)),
                "model": "M0_CORE5/M0_FULL14", "measurement": "OBS_MIXED4",
                "fevd_definition": "mean of each posterior draw's structural-column share",
                "horizons": horizons, "states": STATE_ORDER, "shocks": SHOCK_ORDER,
                "zero_forecast_variance": "NA/NOT_DEFINED",
                "posterior_medians": "marginal and not required to sum to one",
                "tolerance": tolerance, "artifacts": artifact_manifest,
                "input_hashes_before": before, "input_hashes_after": after,
                "output_hashes": {path.name: sha256(path) for path in (summary_path, audit_path, figure_path)},
                "audit_rows": len(audit), "summary_rows": len(summary),
                "max_covariance_diagonal_error": float(audit.max_covariance_diagonal_error.max()),
                "max_draw_share_sum_error": float(audit.max_draw_share_sum_error.max()),
                "max_mean_share_sum_error": float(audit.max_mean_share_sum_error.max(skipna=True))}
    (output / result_names[3]).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = run((ROOT / args.revision_dir) if not args.revision_dir.is_absolute() else args.revision_dir)
    print(json.dumps({key: manifest[key] for key in ("status", "summary_rows", "audit_rows",
                                                 "max_covariance_diagonal_error",
                                                 "max_draw_share_sum_error", "max_mean_share_sum_error")}, indent=2))


if __name__ == "__main__":
    main()
