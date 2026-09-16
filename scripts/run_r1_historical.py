"""R1 historical decomposition from the certified production posterior (no MCMC).

All revised outputs go to the ignored R1 directory; Phase 2F remains untouched.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.structural.historical_decomposition import (
    activity_shares, historical_contributions, reconstruct_smoothed_shocks,
    select_equal_per_chain,
)
from src.structural.historical_sensitivity import (
    classify_historical_window, evaluate_historical_gates,
)
from src.structural.kalman import kalman_filter, rts_smoother
from src.structural.measurement import build_measurements, load_frozen_panel
from src.structural.parameter_transform import PARAMETER_ORDER, load_phase2a_bounds
from src.structural.posterior_artifacts import file_sha256, load_posterior_artifact
from src.structural.state_space import from_phase2a_parameters

REV = ROOT / "outputs/revisions/R1_20260916_190253"
OUT = REV / "historical"
FREEZE = ROOT / "data/processed/core_monthly_panel.csv"
PANEL = ROOT / "data/processed/phase1/monthly_structural_v1.csv"
SHOCKS = ("demand", "cost", "supply", "price")
SPECS = {
    "BASELINE": ("baseline", .80, .25),
    "PRIOR_FLAT_BOUNDED": ("prior_flat_bounded", .80, .25),
    "PRIOR_MODERATE_SHRINK": ("prior_moderate_shrink", .80, .25),
    "BATTERY_SD_010": ("battery_sd_010", .80, .10),
    "BATTERY_SD_050": ("battery_sd_050", .80, .50),
    "RHO_N_050": ("rho_n_050", .50, .25),
    "RHO_N_095": ("rho_n_095", .95, .25),
}


def qrow(values):
    q = np.quantile(np.asarray(values, dtype=np.float64), [.05, .16, .5, .84, .95])
    return dict(zip(("q05", "q16", "median", "q84", "q95"), map(float, q)))


def posterior_cumulative_quantiles(paths):
    """Accumulate every draw before taking quantiles, never cumsum of medians."""
    paths = np.asarray(paths, dtype=np.float64)
    if paths.ndim != 2 or not np.isfinite(paths).all():
        raise ValueError("finite draw x month matrix required")
    cumulative = np.cumsum(paths, axis=1, dtype=np.float64)
    return np.quantile(cumulative, [.05, .16, .5, .84, .95], axis=0)


def split_signed_stack(values):
    """Separate positive/negative contributions for honest signed stacking."""
    values = np.asarray(values, dtype=np.float64)
    return np.maximum(values, 0.), np.minimum(values, 0.)


def checked_subset(theta, initial_n, fallback_n, seed, thresholds):
    full = theta.reshape(-1, theta.shape[-1]).astype(np.float64)
    sd = full.std(axis=0, ddof=1)
    if np.any(sd <= 0) or not np.isfinite(sd).all():
        raise ValueError("invalid full posterior SD")
    for attempt, n in enumerate((initial_n, fallback_n), 1):
        subset, indexes = select_equal_per_chain(theta, n, seed)
        sample = subset.reshape(-1, subset.shape[-1]).astype(np.float64)
        med = np.abs(np.median(sample, axis=0) - np.median(full, axis=0)) / sd
        tail = np.abs(np.quantile(sample, [.05, .95], axis=0)
                      - np.quantile(full, [.05, .95], axis=0)) / sd
        row = {
            "chains": int(theta.shape[0]), "draws_per_chain": int(n),
            "draws": int(len(sample)), "seed": int(seed), "attempt": attempt,
            "indices_sha256": hashlib.sha256(indexes.tobytes()).hexdigest(),
            "max_median_shift_full_sd": float(med.max()),
            "max_tail_shift_full_sd": float(tail.max()),
            "parameter_median_shift_full_sd": json.dumps(dict(zip(PARAMETER_ORDER, med.tolist()))),
            "parameter_tail_shift_full_sd": json.dumps(dict(zip(PARAMETER_ORDER, tail.max(axis=0).tolist()))),
        }
        passed = (med.max() <= thresholds["subset_median_shift_max_full_sd"]
                  and tail.max() <= thresholds["subset_tail_quantile_shift_max_full_sd"])
        row["status"] = "PASS" if passed else "FAIL"
        if passed or attempt == 2:
            return sample, row
    raise AssertionError("unreachable")


def run_draws(name, draws, rho_n, battery_sd, y, months, hcfg, spot_tolerance):
    count, T = len(draws), len(y)
    price = np.empty((count, T, 4), dtype=np.float64)
    initial = np.empty((count, T), dtype=np.float64)
    smoothed_p = np.empty((count, T), dtype=np.float64)
    shocks = np.empty((count, T - 1, 4), dtype=np.float64)
    maximum = {"reconstruction_abs": 0., "reconstruction_rel": 0.,
               "identity_abs": 0., "identity_rel": 0., "spot_state_abs": 0.,
               "jitter": 0.}
    minimum_cov = np.inf
    min_rank = 4
    for d, row in enumerate(draws):
        pars = dict(zip(PARAMETER_ORDER, map(float, row)))
        pars["rho_n"] = rho_n
        model = from_phase2a_parameters("M0_CORE5", pars, battery_sd)
        if model.B.shape != (5, 4):
            raise RuntimeError(f"{name} draw {d}: B shape {model.B.shape}")
        filtered = kalman_filter(model, y, time_index=months)
        if filtered.status != "OK":
            raise RuntimeError(f"{name} draw {d}: filter {filtered.failure_reason}")
        smooth = rts_smoother(model, filtered)
        if (smooth.status != "OK" or not np.isfinite(smooth.smoothed_mean).all()
                or not np.isfinite(smooth.smoothed_cov).all()
                or not np.isfinite(filtered.jitter_used).all()):
            raise RuntimeError(f"{name} draw {d}: smoother {smooth.failure_reason}")
        cov_min = float(np.linalg.eigvalsh(smooth.smoothed_cov).min())
        minimum_cov = min(minimum_cov, cov_min)
        maximum["jitter"] = max(maximum["jitter"], float(np.nanmax(filtered.jitter_used)))
        eps, residual, reconstruction_error, rank = reconstruct_smoothed_shocks(
            smooth.smoothed_mean, model.A, model.B)
        ic, parts = historical_contributions(model.A, model.B, smooth.smoothed_mean[0], eps)
        if not all(np.isfinite(value).all() for value in (eps, residual, ic, parts)):
            raise RuntimeError(f"{name} draw {d}: nonfinite reconstruction")
        reconstructed = ic + parts.sum(axis=1)
        error = np.abs(smooth.smoothed_mean - reconstructed)
        relative = error / np.maximum(1., np.abs(smooth.smoothed_mean))
        maximum["reconstruction_abs"] = max(maximum["reconstruction_abs"], reconstruction_error)
        maximum["reconstruction_rel"] = max(maximum["reconstruction_rel"],
                                             reconstruction_error / max(1., float(np.max(np.abs(residual)))))
        maximum["identity_abs"] = max(maximum["identity_abs"], float(error.max()))
        maximum["identity_rel"] = max(maximum["identity_rel"], float(relative.max()))
        maximum["spot_state_abs"] = max(maximum["spot_state_abs"],
                                         float(np.max(np.abs(smooth.smoothed_mean[:, 4] - y[:, 0]))))
        min_rank = min(min_rank, rank)
        price[d] = parts[:, :, 4]
        initial[d] = ic[:, 4]
        smoothed_p[d] = smooth.smoothed_mean[:, 4]
        shocks[d] = eps
        if (d + 1) % 250 == 0:
            print(f"historical {name}: {d + 1}/{count}", flush=True)
    checks = {
        "KALMAN_RTS": True,
        "COVARIANCE_NUMERICS": minimum_cov >= hcfg["minimum_covariance_eigenvalue_tolerance"],
        "B_RANK": min_rank == 4,
        "SHOCK_RECONSTRUCTION": maximum["reconstruction_abs"] <= hcfg["identity_absolute_tolerance"]
                                and maximum["reconstruction_rel"] <= hcfg["identity_relative_tolerance"],
        "DECOMPOSITION_IDENTITY": maximum["identity_abs"] <= hcfg["identity_absolute_tolerance"]
                                  and maximum["identity_rel"] <= hcfg["identity_relative_tolerance"],
        "SPOT_STATE_IDENTITY": maximum["spot_state_abs"] <= spot_tolerance,
    }
    audit = {"specification": name, "draws": count, "numeric_layer": "float64",
             "minimum_smoothed_covariance_eigenvalue": minimum_cov, "B_rank_min": min_rank,
             "spot_state_tolerance": spot_tolerance, **maximum, **checks}
    return {"price": price, "initial": initial, "smoothed_p": smoothed_p,
            "shocks": shocks, "audit": audit, "checks": checks}


def episode_rows(name, result, months, windows):
    rows, by_window = [], {}
    for window, (start, end) in windows.items():
        idx = np.flatnonzero((months >= start) & (months <= end))
        if not len(idx):
            raise RuntimeError(f"empty historical window: {window}")
        net = result["price"][:, idx, :].sum(axis=1, dtype=np.float64)
        activity, share = activity_shares(result["price"], idx)
        if not np.isfinite(share).all():
            raise RuntimeError(f"undefined activity share: {name}/{window}")
        initial = result["initial"][:, idx].sum(axis=1, dtype=np.float64)
        state = result["smoothed_p"][:, idx].sum(axis=1, dtype=np.float64)
        window_error = float(np.max(np.abs(initial + net.sum(axis=1) - state)))
        for j, shock in enumerate(SHOCKS):
            rows.append({"specification": name, "window": window, "start": start,
                         "end": end, "component": shock, "posterior_mean": float(net[:, j].mean()),
                         **qrow(net[:, j]), "p_positive": float(np.mean(net[:, j] > 0)),
                         "p_negative": float(np.mean(net[:, j] < 0)),
                         "activity_share_mean": float(share[:, j].mean()),
                         "activity_share_median": float(np.median(share[:, j])),
                         "window_identity_max_abs": window_error})
        for label, values in (("initial_condition", initial), ("smoothed_state", state)):
            rows.append({"specification": name, "window": window, "start": start,
                         "end": end, "component": label, "posterior_mean": float(values.mean()),
                         **qrow(values), "window_identity_max_abs": window_error})
        by_window[window] = (net, share)
    return rows, by_window


def write_baseline_monthly(result, months, observed):
    rows = []
    for t, month in enumerate(months):
        parts = [("initial_condition", result["initial"][:, t]),
                 ("smoothed_state", result["smoothed_p"][:, t])]
        parts += [(shock, result["price"][:, t, j]) for j, shock in enumerate(SHOCKS)]
        for label, values in parts:
            rows.append({"month": month, "component": label, "posterior_mean": float(values.mean()),
                         "observed_standardized_spot_dlog": float(observed[t]), **qrow(values)})
    pd.DataFrame(rows).to_csv(OUT / "historical_monthly_corrected.csv", index=False)
    shock_rows = []
    for t, month in enumerate(months):
        for j, shock in enumerate(SHOCKS):
            values = result["shocks"][:, t - 1, j] if t else None
            shock_rows.append({"month": month, "shock": shock,
                               "timing": "TRANSITION_FROM_PREVIOUS_MONTH" if t else "INITIAL_CONDITION_MONTH",
                               **(qrow(values) if values is not None else
                                  {k: np.nan for k in ("q05", "q16", "median", "q84", "q95")})})
    pd.DataFrame(shock_rows).to_csv(OUT / "historical_shocks_corrected.csv", index=False)
    cumulative_rows = []
    for label, path in [("initial_condition", result["initial"])] + [
        (shock, result["price"][:, :, j]) for j, shock in enumerate(SHOCKS)]:
        quantiles = posterior_cumulative_quantiles(path)
        means = np.cumsum(path, axis=1, dtype=np.float64).mean(axis=0)
        for t, month in enumerate(months):
            cumulative_rows.append({"month": month, "component": label,
                                    "posterior_mean": float(means[t]),
                                    **dict(zip(("q05", "q16", "median", "q84", "q95"),
                                               map(float, quantiles[:, t])))})
    pd.DataFrame(cumulative_rows).to_csv(OUT / "historical_cumulative_corrected.csv", index=False)


def make_figures(result, months, observed):
    names = ("initial",) + SHOCKS
    means = np.stack((result["initial"].mean(axis=0),
                      *[result["price"][:, :, j].mean(axis=0) for j in range(4)]))
    positive, negative = split_signed_stack(means)
    x = np.arange(len(months))
    fig, ax = plt.subplots(figsize=(11, 5))
    bottom_pos = np.zeros(len(months)); bottom_neg = np.zeros(len(months))
    for j, label in enumerate(names):
        ax.bar(x, positive[j], bottom=bottom_pos, width=.85, label=label)
        ax.bar(x, negative[j], bottom=bottom_neg, width=.85, color=f"C{j}")
        bottom_pos += positive[j]; bottom_neg += negative[j]
    ax.plot(x, observed, color="black", lw=1.1, label="observed")
    ax.plot(x, result["smoothed_p"].mean(axis=0), color="black", ls="--", lw=1,
            label="mean smoothed p")
    ax.axhline(0, color="black", lw=.5)
    ax.set_xticks(x[::6], months[::6], rotation=45)
    ax.set_ylabel("standardized price-change pressure")
    ax.legend(ncol=4, fontsize=7)
    fig.tight_layout()
    filename = OUT / "historical_signed_mean_stack.png"
    fig.savefig(filename, dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 4))
    for label, path in [("initial", result["initial"])] + [
        (shock, result["price"][:, :, j]) for j, shock in enumerate(SHOCKS)]:
        q = posterior_cumulative_quantiles(path)
        ax.plot(x, q[2], label=label)
        if label == "price":
            ax.fill_between(x, q[0], q[4], alpha=.15)
    ax.axhline(0, color="black", lw=.5)
    ax.set_xticks(x[::6], months[::6], rotation=45)
    ax.set_ylabel("draw-first cumulative pressure")
    ax.legend(ncol=5, fontsize=8)
    fig.tight_layout()
    cumulative_file = OUT / "historical_cumulative_draw_first.png"
    fig.savefig(cumulative_file, dpi=180)
    plt.close(fig)
    return [filename, cumulative_file]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p2f = json.loads((ROOT / "configs/phase2f.yaml").read_text())
    p2a = json.loads((ROOT / "configs/phase2a.yaml").read_text())
    hcfg = json.loads((ROOT / "configs/r1_revision.json").read_text())["historical"]
    assert list(SPECS) == hcfg["required_specifications"]
    input_paths = [FREEZE, PANEL, ROOT / "configs/phase2f.yaml",
                   ROOT / "configs/phase2a.yaml", ROOT / "configs/r1_revision.json",
                   REV / "posterior_audit_final/posterior_gate_by_spec.csv",
                   REV / "posterior_audit_final/posterior_hashes_before_after.json"]
    input_paths += [ROOT / f"outputs/phase2/phase2d/{stem}_posterior_draws.npz"
                   for stem, _, _ in SPECS.values()]
    input_paths += [ROOT / f"outputs/phase2/phase2d/{stem}_posterior_draws.metadata.json"
                    for stem, _, _ in list(SPECS.values())[1:]]
    before = {str(p.relative_to(ROOT)): file_sha256(p) for p in input_paths}
    if before[str(FREEZE.relative_to(ROOT))] != p2a["data_freeze_sha256"]:
        raise RuntimeError("Data Freeze SHA256 mismatch")
    certified_hashes = json.loads((REV / "posterior_audit_final/posterior_hashes_before_after.json").read_text())
    preflight = json.loads((REV / "preflight/inputs_before.json").read_text())
    if before[str(PANEL.relative_to(ROOT))] != preflight["transformed_panel"]["sha256"]:
        raise RuntimeError("transformed panel differs from R1-0 preflight")
    certified_sidecars = {item["path"]: item["sha256"] for item in preflight["posterior_sidecars"]}
    for stem, _, _ in list(SPECS.values())[1:]:
        sidecar = ROOT / f"outputs/phase2/phase2d/{stem}_posterior_draws.metadata.json"
        if before[str(sidecar.relative_to(ROOT))] != certified_sidecars.get(sidecar.relative_to(ROOT).as_posix()):
            raise RuntimeError(f"posterior sidecar differs from R1-0 preflight: {sidecar.name}")
    for stem, _, _ in SPECS.values():
        filename = f"{stem}_posterior_draws.npz"
        artifact = ROOT / "outputs/phase2/phase2d" / filename
        current = before[str(artifact.relative_to(ROOT))]
        certified = certified_hashes.get(filename, {})
        if certified.get("before") != current or certified.get("after") != current or certified.get("unchanged") is not True:
            raise RuntimeError(f"posterior differs from certified R1-1 artifact: {filename}")
    gate = pd.read_csv(REV / "posterior_audit_final/posterior_gate_by_spec.csv")
    if (len(gate) != len(SPECS) or set(gate.specification) != set(SPECS)
            or gate.specification.duplicated().any() or not gate.A01_GATE.eq("PASS").all()):
        raise RuntimeError("R1-1 posterior gate not passed for all required specifications")
    frame = load_frozen_panel(PANEL, p2f["sample_end"])
    measured = build_measurements(frame, p2f["measurement"])
    months = measured.month.to_numpy()
    y = measured[["spot", "ore_cost", "output", "battery"]].to_numpy(dtype=np.float64)
    if len(y) != 57 or months[0] != p2f["sample_start"] or months[-1] != p2f["sample_end"]:
        raise RuntimeError("sample definition mismatch")
    bounds = load_phase2a_bounds(ROOT / "configs/phase2a.yaml")
    results, subsets, audits, episode, windows_by_spec, checks = {}, [], [], [], {}, {}
    for name, (stem, rho_n, battery_sd) in SPECS.items():
        path = ROOT / f"outputs/phase2/phase2d/{stem}_posterior_draws.npz"
        if name == "BASELINE":
            with np.load(path, allow_pickle=False) as raw:
                theta = np.asarray(raw["theta"], dtype=np.float64)
        else:
            theta, _ = load_posterior_artifact(path, expected_specification=name,
                                               expected_rho_n=rho_n,
                                               expected_battery_sd=battery_sd, bounds=bounds)
            theta = theta["theta"]
        initial_n = p2f["baseline_draws_per_chain"] if name == "BASELINE" else p2f["sensitivity_draws_per_chain"]
        fallback_n = p2f["fallback_draws_per_chain"] if name == "BASELINE" else p2f["sensitivity_fallback_draws_per_chain"]
        draw_subset, subset = checked_subset(theta, initial_n, fallback_n, p2f["seed"], hcfg)
        subset.update({"specification": name, "posterior_sha256": before[str(path.relative_to(ROOT))]})
        subsets.append(subset)
        print("historical subset", name, subset["status"], subset["draws"], flush=True)
        if subset["status"] != "PASS":
            checks[name] = {"ARTIFACT_PROVENANCE": True, "REFERENCE_CONVERGENCE": True,
                            "POSTERIOR_SUBSET": False}
            continue
        result = run_draws(name, draw_subset, rho_n, battery_sd, y, months, hcfg,
                           p2f["spot_state_identity_tolerance"])
        if not all(result["checks"].values()):
            (OUT / "historical_numerical_failure.json").write_text(
                json.dumps(result["audit"], indent=2, ensure_ascii=False))
            raise RuntimeError(f"historical numerical gate failed for {name}; no interpretation output written")
        results[name] = result
        audits.append(result["audit"])
        erows, by_window = episode_rows(name, result, months, p2f["historical_windows"])
        episode.extend(erows)
        window_error = max(row["window_identity_max_abs"] for row in erows)
        result["audit"]["maximum_window_identity_abs"] = window_error
        result["checks"]["DECOMPOSITION_IDENTITY"] &= window_error <= hcfg["identity_absolute_tolerance"]
        result["audit"]["DECOMPOSITION_IDENTITY"] = result["checks"]["DECOMPOSITION_IDENTITY"]
        if not result["checks"]["DECOMPOSITION_IDENTITY"]:
            (OUT / "historical_numerical_failure.json").write_text(
                json.dumps(result["audit"], indent=2, ensure_ascii=False))
            raise RuntimeError(f"historical window identity failed for {name}")
        windows_by_spec[name] = by_window
        checks[name] = {"ARTIFACT_PROVENANCE": True, "REFERENCE_CONVERGENCE": True,
                        "POSTERIOR_SUBSET": True, **result["checks"]}
        print("historical finished", name, result["audit"], flush=True)
    sensitivity = []
    for name in SPECS:
        if name == "BASELINE":
            continue
        for window in p2f["historical_windows"]:
            baseline = windows_by_spec.get("BASELINE", {}).get(window, (None, None))
            alternative = windows_by_spec.get(name, {}).get(window, (None, None))
            verdict = classify_historical_window(baseline[0], alternative[0],
                                                 baseline[1], alternative[1], SHOCKS, hcfg)
            sensitivity.append({"specification": name, "window": window,
                                "classification": verdict["classification"],
                                "reason": verdict["reason"],
                                "evidence_json": json.dumps(verdict, ensure_ascii=False)})
    after = {str(p.relative_to(ROOT)): file_sha256(p) for p in input_paths}
    mean_error = None
    if "BASELINE" in results:
        baseline = results["BASELINE"]
        mean_error = float(np.max(np.abs(baseline["initial"].mean(axis=0)
                           + baseline["price"].mean(axis=0).sum(axis=1)
                           - baseline["smoothed_p"].mean(axis=0))))
        checks["BASELINE"]["DECOMPOSITION_IDENTITY"] &= mean_error <= hcfg["identity_absolute_tolerance"]
        if not checks["BASELINE"]["DECOMPOSITION_IDENTITY"]:
            (OUT / "historical_numerical_failure.json").write_text(
                json.dumps({"baseline_posterior_mean_additivity_max_abs": mean_error}, indent=2))
            raise RuntimeError("baseline posterior mean additivity failed")
    gates = evaluate_historical_gates(list(SPECS), list(p2f["historical_windows"]),
                                      checks, sensitivity, input_hashes_unchanged=before == after)
    gates["input_sha256_before"] = before
    gates["input_sha256_after"] = after
    gates["checks_by_spec"] = checks
    gates["baseline_posterior_mean_additivity_max_abs"] = mean_error
    pd.DataFrame(subsets).to_csv(OUT / "historical_subset_audit.csv", index=False)
    pd.DataFrame(audits).to_csv(OUT / "historical_identity_audit.csv", index=False)
    pd.DataFrame(episode).to_csv(OUT / "historical_episode_corrected.csv", index=False)
    pd.DataFrame(sensitivity).to_csv(OUT / "historical_story_sensitivity_corrected.csv", index=False)
    (OUT / "historical_gate_details.json").write_text(json.dumps(gates, indent=2, ensure_ascii=False))
    figures = []
    if "BASELINE" in results:
        baseline = results["BASELINE"]
        write_baseline_monthly(baseline, months, y[:, 0])
        figures = make_figures(baseline, months, y[:, 0])
        (OUT / "historical_gate_details.json").write_text(json.dumps(gates, indent=2, ensure_ascii=False))
    pd.DataFrame([{"figure": str(p.relative_to(ROOT)), "sha256": file_sha256(p),
                   "summary": "draw-first posterior mean; signed contributions separated" if "signed" in p.name
                   else "draw-first cumulative quantiles"} for p in figures]).to_csv(
                       OUT / "figure_revision_manifest.csv", index=False)
    print(json.dumps({k: gates[k] for k in ("IMPLEMENTATION_VALIDITY",
          "STATISTICAL_OR_ECONOMIC_SENSITIVITY", "DOWNSTREAM_INTERPRETATION_GATE")}), flush=True)


if __name__ == "__main__":
    main()
