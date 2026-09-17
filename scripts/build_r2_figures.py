"""Render selected R2 advisor-draft figures from frozen, verified R1 tables.

This is a read-only presentation step. It never estimates parameters, modifies
R1 artifacts, or downloads data. Figures and their provenance stay in an
ignored private outputs/thesis/<run_id>/figures directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
R1_RUN = "R1_20260916_190253"
R1_ROOT = Path("outputs/revisions") / R1_RUN
FINAL_REGISTRY = R1_ROOT / "result_registry_final/result_registry.json"
FINAL_REGISTRY_SHA256 = "2e8cb4678c3c11cd2d69c34c044bbcb24e500facaadf95219f47fa5d9991aef4"
EQUATIONS_SOURCE_SHA256 = "a88eb5e634451a1e8819525b5e2a3c95462e9443bb630c02f00bf254d2daccbe"
MODELS = ("RW_NO_DRIFT", "AR_BIC", "VAR_SPEC_B", "BVAR_SPEC_B", "STRUCTURAL_MAP_M0")
MODEL_LABELS = ("RW", "AR", "VAR", "BVAR", "Structural M0")
MODEL_COLORS = ("#747b85", "#3b82b7", "#56a676", "#d7954b", "#bc5261")
HORIZONS = (1, 3, 6)
MECHANISM_LAG_LINKS = (
    (r"$p_{t-1}$", r"$q_t$", r"$+a_p$"),
    (r"$c_{t-1}$", r"$q_t$", r"$-a_c$"),
    (r"$q_{t-1}$", r"$n_t$", r"$+1$"),
    (r"$d_{t-1}$", r"$n_t$", r"$-1$"),
)
MECHANISM_PRICE_LINKS = (
    (r"$d_t$", r"$+b_d$"),
    (r"$c_t$", r"$+b_c$"),
    (r"$q_t$", r"$-b_q$"),
    (r"$n_t$", r"$-b_n$"),
    (r"$p_{t-1}$", r"$+\rho_p$"),
)
MECHANISM_EQUATIONS = (
    r"$d_t=\rho_d d_{t-1}+\sigma_d\varepsilon_t^d$",
    r"$c_t=\rho_c c_{t-1}+\sigma_c\varepsilon_t^c$",
    r"$q_t=\rho_q q_{t-1}+a_p p_{t-1}-a_c c_{t-1}+\sigma_q\varepsilon_t^q$",
    r"$n_t=\rho_n n_{t-1}+q_{t-1}-d_{t-1}$",
    r"$p_t=\rho_p p_{t-1}+b_d d_t+b_c c_t-b_q q_t-b_n n_t+\sigma_p\varepsilon_t^p$",
)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_file(root: Path, relative: str | Path, expected: str) -> Path:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = file_hash(path)
    if actual != expected.lower():
        raise ValueError(f"R1 input hash mismatch: {relative}: {actual} != {expected}")
    return path


def registry_source(registry: dict, suffix: str) -> tuple[str, str]:
    matches = {(r["source_file"], r["source_file_sha256"])
               for r in registry["results"] if r["source_file"].endswith(suffix)}
    if len(matches) != 1:
        raise ValueError(f"Expected one final registry source for {suffix}; got {matches}")
    return matches.pop()


def select_forecast(revision: pd.DataFrame, archive: pd.DataFrame) -> pd.DataFrame:
    expected = {(m, h) for m in MODELS for h in HORIZONS}
    keys = set(zip(revision.model, revision.horizon))
    if len(revision) != 15 or keys != expected or revision.duplicated(["model", "horizon"]).any():
        raise ValueError("Final forecast revision is not the 5-model × 3-horizon grid")
    if len(archive) != 15 or set(zip(archive.model, archive.horizon)) != expected:
        raise ValueError("Frozen forecast metric archive grid mismatch")
    merged = revision.merge(archive, on=["model", "horizon"], validate="one_to_one")
    for field in ("rmse_level", "mae_level", "theil_u2"):
        delta = (merged[f"{field}_r1"] - merged[field]).abs() if field != "mae_level" else merged["mae_level_absolute_difference"]
        if not np.isfinite(delta).all() or (delta > 1e-7).any():
            raise ValueError(f"R1-verified forecast {field} does not match frozen archive")
    if (merged.status != "PASS").any() or not (merged.n_r1 == merged.n_archived).all() or not (merged.n_r1 == merged.n).all():
        raise ValueError("Forecast verification status/N mismatch")
    if merged.groupby("horizon").n.nunique().max() != 1 or list(merged[merged.model == "RW_NO_DRIFT"].sort_values("horizon").n) != [21, 19, 16]:
        raise ValueError("Expected same-key N=21/19/16 forecast comparison")
    if not np.allclose(merged.loc[merged.model == "RW_NO_DRIFT", "theil_u2"], 1.0):
        raise ValueError("RW U2 denominator is not 1")
    return merged


def select_inventory(blocks: pd.DataFrame) -> pd.DataFrame:
    selected = blocks.loc[
        (blocks.specification == "BASELINE")
        & (blocks.external_series == "lc_inventory_total_mean")
        & (blocks.information_use == "SMOOTHED")
        & (blocks.transformation.isin(["log_level", "log_change"]))
        & (blocks.block_length.isin([3, 6]))
    ].copy()
    if len(selected) != 4 or selected.duplicated(["transformation", "block_length"]).any():
        raise ValueError("Expected exactly four baseline smoothed inventory block rows")
    if (selected.interval_status != "COMPUTED").any() or (selected.point_status != "OK").any():
        raise ValueError("Inventory interval is not validated")
    if not (selected.valid_replicates == selected.n_rep).all() or not (selected.invalid_replicates == 0).all():
        raise ValueError("Inventory block replication count invalid")
    if not ((selected.ci025 <= selected.point_correlation) & (selected.point_correlation <= selected.ci975)).all():
        raise ValueError("Inventory point estimate falls outside displayed interval")
    if selected.groupby("transformation").point_correlation.agg(lambda x: x.max() - x.min()).max() > 1e-10:
        raise ValueError("Same correlation differs across block lengths")
    expected_n = {"log_level": 28, "log_change": 27}
    if any(set(selected.loc[selected.transformation == name, "n_months"]) != {n} for name, n in expected_n.items()):
        raise ValueError("Inventory sample length mismatch")
    return selected


def select_lags(lags: pd.DataFrame, claims: pd.DataFrame) -> pd.DataFrame:
    selected = lags.loc[
        (lags.stratum == "ALL")
        & (lags.specification.isin(["MATCHED_EOM_PRIMARY", "DAILY_MATCHED_INTERVAL_PRIMARY"]))
        & (lags.main_rule.isin(["EX_POST_DESCRIPTIVE_MAIN", "LAGGED_VOLUME_MAIN"]))
    ].copy()
    for spec, frequency, expected_lags in (
        ("MATCHED_EOM_PRIMARY", "monthly", set(range(-3, 4))),
        ("DAILY_MATCHED_INTERVAL_PRIMARY", "daily", set(range(-5, 6))),
    ):
        for rule in ("EX_POST_DESCRIPTIVE_MAIN", "LAGGED_VOLUME_MAIN"):
            rows = selected.loc[(selected.specification == spec) & (selected.main_rule == rule)]
            if set(rows.lag_spot_periods) != expected_lags or len(rows) != len(expected_lags) or set(rows.frequency) != {frequency}:
                raise ValueError(f"Incomplete final full-lag series: {spec}/{rule}")
            claim_name = "MONTHLY_LAG_PLUS_ONE" if frequency == "monthly" else "DAILY_LAG_PLUS_ONE"
            col = "matched_ex_post_pearson" if rule == "EX_POST_DESCRIPTIVE_MAIN" else "matched_lagged_main_pearson"
            claim = claims.loc[claims.claim == claim_name].iloc[0]
            plus_one = rows.loc[rows.lag_spot_periods == 1].iloc[0]
            if not np.isclose(plus_one.pearson, claim[col], atol=1e-12):
                raise ValueError(f"Full-lag +1 does not match R1 final claim: {spec}/{rule}")
    if selected.duplicated(["specification", "main_rule", "lag_spot_periods"]).any() or not np.isfinite(selected.pearson).all():
        raise ValueError("Futures lag rows duplicated or non-finite")
    return selected


def select_posterior(summary: pd.DataFrame) -> pd.DataFrame:
    if len(summary) != 14 or summary.parameter.duplicated().any():
        raise ValueError("Baseline posterior summary is not FULL14")
    if not np.isfinite(summary[["median", "q05", "q95"]].to_numpy()).all():
        raise ValueError("Non-finite posterior interval")
    if not ((summary.q05 <= summary["median"]) & (summary["median"] <= summary.q95)).all():
        raise ValueError("Posterior quantile order invalid")
    return summary


def select_price_irf(summary: pd.DataFrame) -> pd.DataFrame:
    """Validate the archived posterior-integrated price-state IRF grid."""
    shocks = ("demand", "cost", "supply", "price")
    if len(summary) != 100 or set(summary.state) != {"p"} or set(summary.shock) != set(shocks):
        raise ValueError("Expected four 25-month posterior price IRF summaries")
    if summary.duplicated(["shock", "horizon"]).any():
        raise ValueError("Duplicated price IRF shock/horizon")
    for shock in shocks:
        rows = summary.loc[summary.shock == shock]
        if set(rows.horizon) != set(range(25)):
            raise ValueError(f"Incomplete 0–24 month price IRF: {shock}")
    quantiles = summary[["q05", "q16", "median", "q84", "q95"]].to_numpy()
    if not np.isfinite(quantiles).all() or not (np.diff(quantiles, axis=1) >= 0).all():
        raise ValueError("Non-finite or unordered posterior price IRF quantiles")
    return summary


def style_axes(axis: plt.Axes) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", alpha=0.2, linewidth=0.7)
    axis.set_axisbelow(True)


def plot_forecast(data: pd.DataFrame, output: Path) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(15.4, 5.0), sharex=True)
    for ax, (field, title, ylabel) in zip(axes, (
        ("rmse_level", "RMSE", "CNY / tonne"),
        ("mae_level", "MAE", "CNY / tonne"),
        ("theil_u2", "Theil U2", "RMSE / same-key RW RMSE"),
    )):
        for model, label, color in zip(MODELS, MODEL_LABELS, MODEL_COLORS):
            rows = data.loc[data.model == model].sort_values("horizon")
            ax.plot(rows.horizon, rows[field], marker="o", linewidth=2, markersize=5, color=color, label=label)
        ax.set_title(title, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_xticks(HORIZONS, ["1\nN=21", "3\nN=19", "6\nN=16"])
        ax.set_xlabel("Forecast horizon (months)", fontsize=9)
        if field == "theil_u2":
            ax.axhline(1, color="#747b85", linestyle="--", linewidth=1)
        style_axes(ax)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, ncol=5, loc="lower center", bbox_to_anchor=(0.5, 0.015), frameon=False)
    figure.suptitle("Five-model recursive historical OOS comparison", fontsize=14, y=0.99)
    figure.text(0.5, 0.095, "56 common origin–target–horizon keys; selected specifications; not prospective model selection or a real-time vintage.", ha="center", fontsize=8, color="#555")
    figure.tight_layout(rect=(0, 0.13, 1, 0.95))
    figure.savefig(output, dpi=210)
    plt.close(figure)


def plot_inventory(data: pd.DataFrame, output: Path) -> None:
    figure, ax = plt.subplots(figsize=(10.4, 5.0))
    colors = {"log_level": "#3b82b7", "log_change": "#bc5261"}
    for i, transformation in enumerate(("log_level", "log_change")):
        for j, block in enumerate((3, 6)):
            row = data.loc[(data.transformation == transformation) & (data.block_length == block)].iloc[0]
            y = i * 2.1 + j * 0.7
            ax.plot([row.ci025, row.ci975], [y, y], color=colors[transformation], lw=5, solid_capstyle="round", alpha=0.78)
            ax.scatter([row.point_correlation], [y], color="#20252b", marker="D", s=38, zorder=3)
            ax.text(row.ci975 + 0.015, y, f"[{row.ci025:.3f}, {row.ci975:.3f}]", va="center", fontsize=9)
    ax.axvline(0, color="#747b85", linestyle="--", linewidth=1)
    ax.set_yticks([0, 0.7, 2.1, 2.8], [
        "n vs log inventory (N=28): 3-month block",
        "n vs log inventory (N=28): 6-month block",
        "n vs Δlog inventory (N=27): 3-month block",
        "n vs Δlog inventory (N=27): 6-month block",
    ])
    ax.set_xlim(-0.58, 1.08)
    ax.set_ylim(-0.5, 3.4)
    ax.invert_yaxis()
    ax.set_xlabel("Pearson correlation; diamond = fixed posterior-median-path point estimate")
    ax.set_title("Smoothed n versus external inventory: paired moving-block 95% intervals", fontsize=12)
    ax.tick_params(axis="y", length=0)
    figure.text(0.5, 0.055,
                "Same point estimate under two block lengths; intervals measure time-sample sensitivity, not posterior uncertainty.\n"
                "Short 2023-06–2025-09 sample; log-change comparison uses 27 paired months, not 28.",
                ha="center", va="center", fontsize=8, color="#555")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=0.2)
    figure.tight_layout(rect=(0, 0.14, 1, 1))
    figure.savefig(output, dpi=210)
    plt.close(figure)


def plot_futures(data: pd.DataFrame, output: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(13.8, 5.1), sharey=True)
    for ax, spec, title in zip(axes,
                               ("MATCHED_EOM_PRIMARY", "DAILY_MATCHED_INTERVAL_PRIMARY"),
                               ("Matched month-end returns", "Matched daily intervals")):
        subset = data.loc[data.specification == spec]
        for rule, label, color, linestyle, marker in (
            ("EX_POST_DESCRIPTIVE_MAIN", "Same-day-volume main (ex post)", "#3b82b7", "-", "o"),
            ("LAGGED_VOLUME_MAIN", "Previous-day-volume main", "#bc5261", "--", "s"),
        ):
            rows = subset.loc[subset.main_rule == rule].sort_values("lag_spot_periods")
            ax.plot(rows.lag_spot_periods, rows.pearson, marker=marker, markersize=4, lw=1.8,
                    linestyle=linestyle, label=label, color=color)
        ax.axhline(0, color="#777", linewidth=0.8)
        ax.axvline(0, color="#777", linewidth=0.8, linestyle=":")
        ax.set_title(title)
        ax.set_xlabel("Spot periods after futures period (positive lag)")
        ax.set_xticks(sorted(subset.lag_spot_periods.unique()))
        ax.set_ylim(-0.2, 0.8)
        style_axes(ax)
    axes[0].set_ylabel("Pearson correlation of matched log returns")
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 0.025), frameon=False)
    figure.suptitle("Spot–futures lead–lag correlations: complete R1 corrected lag families", fontsize=13, y=0.99)
    figure.text(0.5, 0.105, "Monthly lag 0 is largest; daily +1 is largest. Exploratory correlations only: no causality, information share, or trading return claim.", ha="center", fontsize=8, color="#555")
    figure.tight_layout(rect=(0, 0.15, 1, 0.94))
    figure.savefig(output, dpi=210)
    plt.close(figure)


def plot_posterior(data: pd.DataFrame, output: Path) -> None:
    figure, ax = plt.subplots(figsize=(10.1, 6.7))
    y = np.arange(len(data))
    ax.errorbar(data["median"], y,
                xerr=np.vstack([data["median"] - data.q05, data.q95 - data["median"]]),
                fmt="o", capsize=3, color="#28678d", ecolor="#88b6cc", markersize=5)
    ax.set_yticks(y, data.parameter)
    ax.invert_yaxis()
    ax.set_xlabel("Posterior median and marginal 90% credible interval (q05–q95)")
    ax.set_title("M0_FULL14 baseline posterior parameters", fontsize=13)
    ax.text(0, -0.105, "Frozen Phase 2D parameter quantiles; R1 corrected diagnostic table is separate. Support-constrained intervals are not two-sided significance tests.",
            transform=ax.transAxes, fontsize=8, color="#555")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.2)
    figure.tight_layout(rect=(0, 0.08, 1, 1))
    figure.savefig(output, dpi=210)
    plt.close(figure)


def plot_price_irf(data: pd.DataFrame, output: Path) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(8.6, 6.7))
    labels = (
        ("demand", "Demand shock"), ("cost", "Cost shock"),
        ("supply", "Supply shock"), ("price", "Price-residual shock"),
    )
    for ax, (shock, label) in zip(axes.flat, labels):
        rows = data.loc[data.shock == shock].sort_values("horizon")
        horizon = rows.horizon.to_numpy()
        ax.fill_between(horizon, rows.q05, rows.q95, color="#a6c5d5", alpha=0.47,
                        linewidth=0, label="90% interval (q05–q95)")
        ax.fill_between(horizon, rows.q16, rows.q84, color="#5b9bbd", alpha=0.48,
                        linewidth=0, label="68% interval (q16–q84)")
        ax.plot(horizon, rows["median"], color="#184e70", linewidth=2,
                label="Posterior median")
        ax.axhline(0, color="#777", linewidth=0.8, linestyle="--")
        ax.set_title(label, fontsize=11)
        ax.set_xlim(0, 24)
        ax.set_xticks([0, 6, 12, 18, 24])
        ax.set_xlabel("Months after shock", fontsize=9)
        ax.set_ylabel("Standardized p response", fontsize=9)
        ax.tick_params(labelsize=8)
        style_axes(ax)
    handles, legends = axes.flat[0].get_legend_handles_labels()
    figure.legend(handles, legends, ncol=3, frameon=False, loc="lower center",
                  bbox_to_anchor=(0.5, 0.015), fontsize=8.5)
    figure.suptitle("Price-state impulse responses from the accepted posterior", fontsize=12.5)
    figure.tight_layout(rect=(0, 0.07, 1, 0.95), h_pad=1.6, w_pad=1.0)
    figure.savefig(output, dpi=220)
    plt.close(figure)


def plot_mechanism(_unused: None, output: Path) -> None:
    """Diagram the exact M0_CORE5 timing and coefficients, not estimated effects."""
    figure, ax = plt.subplots(figsize=(8.8, 7.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    figure.suptitle("M0_CORE5 monthly semi-structural mechanism", fontsize=13, y=0.985)

    def panel(x: float, y: float, width: float, height: float, color: str) -> None:
        ax.add_patch(FancyBboxPatch((x, y), width, height,
                                   boxstyle="round,pad=0.01,rounding_size=0.014",
                                   edgecolor="#b7c3cd", linewidth=1,
                                   facecolor=color))

    panel(0.045, 0.505, 0.435, 0.405, "#f3f7fa")
    panel(0.52, 0.505, 0.435, 0.405, "#f6f8f4")
    panel(0.045, 0.105, 0.91, 0.355, "#fbfbfa")
    ax.text(0.263, 0.875, "Lagged cross-effects  (t−1 → t)",
            ha="center", va="center", fontsize=10.5, fontweight="bold")
    ax.text(0.738, 0.875, "Price links  (within t, except own lag)",
            ha="center", va="center", fontsize=10.5, fontweight="bold")

    for i, (source, target, coefficient) in enumerate(MECHANISM_LAG_LINKS):
        y = 0.81 - i * 0.075
        ax.text(0.108, y, source, ha="center", va="center", fontsize=12)
        ax.text(0.264, y + 0.013, coefficient, ha="center", va="bottom", fontsize=10, color="#214e68")
        ax.add_patch(FancyArrowPatch((0.16, y), (0.36, y), arrowstyle="-|>",
                                     mutation_scale=11, linewidth=1.3, color="#446c82"))
        ax.text(0.415, y, target, ha="center", va="center", fontsize=12)

    for i, (source, coefficient) in enumerate(MECHANISM_PRICE_LINKS):
        y = 0.82 - i * 0.059
        ax.text(0.585, y, source, ha="center", va="center", fontsize=11.5)
        ax.text(0.739, y + 0.012, coefficient, ha="center", va="bottom", fontsize=9.5, color="#476d50")
        ax.add_patch(FancyArrowPatch((0.63, y), (0.85, y), arrowstyle="-|>",
                                     mutation_scale=10, linewidth=1.2, color="#64876a"))
        ax.text(0.905, y, r"$p_t$", ha="center", va="center", fontsize=11.5)

    ax.text(0.065, 0.435, "Exact transition order and innovation terms", fontsize=10.5,
            fontweight="bold", va="center")
    for i, equation in enumerate(MECHANISM_EQUATIONS):
        ax.text(0.075, 0.393 - i * 0.058, equation, fontsize=10.8,
                ha="left", va="center")
    ax.text(0.5, 0.064,
            "n is standardized supply–demand pressure, not physical inventory in tonnes; p is a standardized price-change state.",
            ha="center", va="center", fontsize=8.2, color="#555")
    ax.text(0.5, 0.033,
            "Supply uses lagged price/cost; price uses current d, c, q and n. No contemporaneous price–supply algebraic loop.",
            ha="center", va="center", fontsize=8.2, color="#555")
    figure.tight_layout(rect=(0, 0, 1, 0.96))
    figure.savefig(output, dpi=220)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="New R2 run ID; source R1 outputs stay read-only")
    parser.add_argument("--replace-known", action="store_true",
                        help="Regenerate only if every existing output still matches this run's recorded figure hash")
    args = parser.parse_args()
    if not args.run_id.startswith("R2_") or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for c in args.run_id):
        raise ValueError("run-id must be a simple R2_... identifier")
    outdir = ROOT / "outputs/thesis" / args.run_id / "figures"
    filenames = (
        "forecast_five_model.png",
        "external_inventory_block.png",
        "futures_lead_lag.png",
        "posterior_parameter_r2.png",
        "irf_price_4shocks_r2.png",
        "mechanism_core5_r2.png",
        "r2_figure_provenance.json",
    )
    existing = [name for name in filenames if (outdir / name).exists()]
    if existing:
        if not args.replace_known:
            raise FileExistsError(f"Will not overwrite existing R2 figure artifact: {outdir / existing[0]}")
        manifest_path = outdir / filenames[6]
        if not manifest_path.is_file():
            raise ValueError("Cannot replace figures without this run's provenance record")
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        known = {Path(r["path"]).name: r["sha256"] for r in old["figures"]}
        if old.get("run_id") != args.run_id or any(name != filenames[6] and
            (name not in known or file_hash(outdir / name) != known[name]) for name in existing):
            raise ValueError("Existing figure modified or not produced by this R2 run")
    ignored = subprocess.run(["git", "check-ignore", "-q", str(outdir / filenames[0])], cwd=ROOT, check=False)
    if ignored.returncode != 0:
        raise ValueError(f"Private figure destination is not gitignored: {outdir}")

    registry_path = checked_file(ROOT, FINAL_REGISTRY, FINAL_REGISTRY_SHA256)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("run_id") != R1_RUN or registry.get("result_count") != 85:
        raise ValueError("Not the accepted R1 final result registry")
    sources: dict[str, dict[str, str]] = {}

    def register(name: str, relative: str | Path, expected: str) -> Path:
        path = checked_file(ROOT, relative, expected)
        sources[name] = {"path": Path(relative).as_posix(), "sha256": expected.lower()}
        return path

    sources["r1_final_registry"] = {"path": FINAL_REGISTRY.as_posix(), "sha256": FINAL_REGISTRY_SHA256}
    forecast_rel, forecast_hash = registry_source(registry, "forecast_metric_revision.csv")
    forecast_revision = pd.read_csv(register("forecast_verified", forecast_rel, forecast_hash))
    forecast_hashes_rel = R1_ROOT / "forecast_verified/forecast_audit_input_hashes.json"
    forecast_hashes_path = ROOT / forecast_hashes_rel
    forecast_hashes = json.loads(forecast_hashes_path.read_text(encoding="utf-8"))
    archived_rel = "outputs/phase2/phase2g/structural_oos_metrics.csv"
    archived_key = archived_rel.replace("/", "\\")
    if forecast_hashes["before"][archived_key] != forecast_hashes["after"][archived_key]:
        raise ValueError("Forecast archive changed during R1 audit")
    archived = pd.read_csv(register("forecast_metric_archive_r1_audited", archived_rel, forecast_hashes["before"][archived_key]))
    forecast = select_forecast(forecast_revision, archived)

    block_rel, block_hash = registry_source(registry, "external_validation_block_bootstrap.csv")
    inventory = select_inventory(pd.read_csv(register("external_inventory_blocks", block_rel, block_hash)))

    claim_rel, claim_hash = registry_source(registry, "futures_claim_revision.csv")
    claims = pd.read_csv(register("futures_claim_revision", claim_rel, claim_hash))
    definition_rel = R1_ROOT / "futures/return_definition_registry.json"
    definition_path = ROOT / definition_rel
    definition = json.loads(definition_path.read_text(encoding="utf-8"))
    sources["futures_return_definition"] = {"path": definition_rel.as_posix(), "sha256": file_hash(definition_path)}
    lag_rel = R1_ROOT / "futures/lead_lag_specification_comparison.csv"
    lags = select_lags(pd.read_csv(register("futures_full_lag", lag_rel, definition["output_sha256"][lag_rel.name])), claims)

    preflight_rel = R1_ROOT / "preflight/inputs_before.json"
    preflight_path = ROOT / preflight_rel
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    sources["r1_preflight"] = {"path": preflight_rel.as_posix(), "sha256": file_hash(preflight_path)}
    register("m0_core5_equations_source", "src/structural/equations.py", EQUATIONS_SOURCE_SHA256)
    posterior_rel = "outputs/phase2/phase2d/baseline_posterior_summary.csv"
    frozen = [item for item in preflight["old_result_files"] if item["path"] == posterior_rel]
    if len(frozen) != 1:
        raise ValueError("R1 preflight lacks frozen baseline posterior summary")
    posterior = select_posterior(pd.read_csv(register("posterior_quantiles_r1_frozen", posterior_rel, frozen[0]["sha256"])))

    irf_rel = "outputs/phase2/phase2e/irf_price_summary.csv"
    frozen_irf = [item for item in preflight["old_result_files"] if item["path"] == irf_rel]
    if len(frozen_irf) != 1:
        raise ValueError("R1 preflight lacks frozen posterior price IRF summary")
    price_irf = select_price_irf(pd.read_csv(register("posterior_price_irf_r1_frozen", irf_rel, frozen_irf[0]["sha256"])))

    outdir.mkdir(parents=True, exist_ok=True)
    plots = (
        ("R2_FC", filenames[0], plot_forecast, forecast, "15 model–horizon rows; RMSE/MAE CNY/t, U2 ratio; historical same-key OOS"),
        ("R2_EV", filenames[1], plot_inventory, inventory, "Baseline smoothed n and inventory; fixed median path, paired 3/6-month moving-block 95% percentile intervals"),
        ("R2_SF", filenames[2], plot_futures, lags, "Full -3…+3 monthly and -5…+5 daily matched-return Pearson lag families; exploratory"),
        ("R2_POST", filenames[3], plot_posterior, posterior, "Frozen FULL14 posterior median and marginal q05–q95 intervals; diagnostic claims excluded"),
        ("R2_IRF", filenames[4], plot_price_irf, price_irf, "Frozen Phase 2E posterior-integrated standardized price-state IRFs, four shocks, months 0–24, median and 68%/90% marginal bands"),
        ("R2_MECH", filenames[5], plot_mechanism, None, "Exact frozen M0_CORE5 lagged and within-month links, own persistence and innovation terms; standardized n is not physical inventory"),
    )
    records = []
    for figure_id, name, plotter, data, description in plots:
        path = outdir / name
        plotter(data, path)
        records.append({"id": figure_id, "path": path.relative_to(ROOT).as_posix(), "sha256": file_hash(path),
                        "description": description, "license": "private_advisor_review_only_not_for_public_git"})
    provenance = {"schema": "r2_figure_provenance_v1", "run_id": args.run_id, "source_r1_run_id": R1_RUN,
                  "inputs": sources, "figures": records,
                  "method": "Read-only plotting of R1 verified/frozen aggregates; no MLE, MCMC, private data download or synthetic replacement"}
    (outdir / filenames[6]).write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(outdir), "figures": records}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
