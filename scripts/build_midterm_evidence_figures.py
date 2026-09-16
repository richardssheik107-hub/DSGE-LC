"""Render presentation-ready figures from frozen Phase 1/2 result artifacts."""
from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/midterm"


def _box(axis, xy, width, height, text, color):
    patch = FancyBboxPatch(
        xy, width, height, boxstyle="round,pad=0.02", linewidth=1.4,
        edgecolor="#333333", facecolor=color,
    )
    axis.add_patch(patch)
    axis.text(xy[0] + width / 2, xy[1] + height / 2, text, ha="center", va="center", fontsize=10)
    return patch


def _arrow(axis, start, end, label="", style="-", connectionstyle="arc3"):
    arrow = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12,
                            linewidth=1.3, linestyle=style, color="#444444",
                            connectionstyle=connectionstyle)
    axis.add_patch(arrow)
    if label:
        axis.text((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + .025,
                  label, ha="center", va="bottom", fontsize=9)


def mechanism_diagram():
    figure, axis = plt.subplots(figsize=(10, 5.5))
    axis.set_xlim(0, 1); axis.set_ylim(0, 1); axis.axis("off")
    _box(axis, (.05, .67), .18, .13, "Latent demand\n$d_t$", "#D9EAF7")
    _box(axis, (.05, .37), .18, .13, "Cost pressure\n$c_t$", "#FCE1C5")
    _box(axis, (.38, .67), .18, .13, "Short-run output\n$q_t$", "#DDF2D8")
    _box(axis, (.38, .30), .18, .13, "Inventory pressure\n$n_t$", "#E8DFF5")
    _box(axis, (.74, .47), .20, .15, "Spot-price pressure\n$p_t$", "#F8D7DA")
    _arrow(axis, (.23, .735), (.74, .59), connectionstyle="arc3,rad=-.20")
    _arrow(axis, (.23, .435), (.74, .52))
    _arrow(axis, (.56, .735), (.74, .60))
    _arrow(axis, (.56, .365), (.74, .50))
    _arrow(axis, (.20, .67), (.38, .37))
    _arrow(axis, (.47, .67), (.47, .43))
    _arrow(axis, (.84, .47), (.56, .70), style="--", connectionstyle="arc3,rad=.16")
    axis.text(.48, .84, "+ $b_d$", fontsize=10)
    axis.text(.48, .46, "+ $b_c$", fontsize=10)
    axis.text(.64, .70, "- $b_q$", fontsize=10)
    axis.text(.65, .39, "- $b_n$", fontsize=10)
    axis.text(.24, .53, "- demand", fontsize=9)
    axis.text(.49, .53, "+ output", fontsize=9)
    axis.text(.69, .72, "+ lagged price", fontsize=9)
    axis.text(.5, .14, "Four structural shocks: demand, cost, supply, residual price", ha="center", fontsize=11)
    axis.text(.5, .06, "Semi-structural linear state-space model; not a fully micro-founded DSGE", ha="center", fontsize=10, color="#555555")
    axis.set_title("M0_CORE5 research mechanism", fontsize=16)
    figure.tight_layout()
    figure.savefig(OUT / "figure_02_research_mechanism.png", dpi=180)
    plt.close(figure)


def data_model_map():
    figure, axis = plt.subplots(figsize=(11, 5.5))
    axis.set_xlim(0, 1); axis.set_ylim(0, 1); axis.axis("off")
    labels = (
        ("SMM LC spot dlog", "Spot observation", "#F8D7DA", .68),
        ("SMM SC6 CNY dlog", "Cost observation", "#FCE1C5", .50),
        ("SMM output YoY log", "Supply observation", "#DDF2D8", .32),
        ("Battery installation YoY", "Demand measurement", "#D9EAF7", .14),
    )
    for source, role, color, y in labels:
        _box(axis, (.04, y), .24, .11, source, color)
        _box(axis, (.38, y), .20, .11, role, "#F5F5F5")
        _arrow(axis, (.28, y + .055), (.38, y + .055))
        _arrow(axis, (.58, y + .055), (.70, .55))
    _box(axis, (.70, .32), .25, .34,
         "Kalman / RTS state-space\n\nStates: d, c, q, n, p\nBayesian posterior\nIRF / FEVD / HD / OOS",
         "#EFEFEF")
    axis.text(.50, .91, "Data Freeze v1: 2020-01—2025-09 (69 months)", ha="center", fontsize=12)
    axis.text(.50, .85, "Structural OBS_MIXED4 sample: 2021-01—2025-09 (N=57)", ha="center", fontsize=12)
    axis.text(.50, .035, "External inventory / route-cost and GFEX futures remain validation or extension layers", ha="center", fontsize=10, color="#555555")
    axis.set_title("Data-to-model evidence map", fontsize=16)
    figure.tight_layout()
    figure.savefig(OUT / "figure_03_data_model_map.png", dpi=180)
    plt.close(figure)


def posterior_parameters():
    data = pd.read_csv(ROOT / "outputs/phase2/phase2d/baseline_posterior_summary.csv")
    figure, axis = plt.subplots(figsize=(10, 7))
    y = np.arange(len(data))
    axis.errorbar(
        data["median"], y,
        xerr=np.vstack([data["median"] - data["q05"], data["q95"] - data["median"]]),
        fmt="o", capsize=3, color="#1f77b4", ecolor="#7aaed6",
    )
    axis.set_yticks(y, data.parameter)
    axis.invert_yaxis()
    axis.axvline(0, color="black", linewidth=.7)
    axis.set_xlabel("Posterior median and 90% credible interval")
    axis.set_title("M0_FULL14 baseline posterior summary")
    axis.text(.99, .01, "All R-hat <= 1.008; weakest loadings remain near the lower boundary",
              transform=axis.transAxes, ha="right", va="bottom", fontsize=9, color="#555555")
    figure.tight_layout()
    figure.savefig(OUT / "figure_04_posterior_parameter_summary.png", dpi=180)
    plt.close(figure)


def structural_oos():
    data = pd.read_csv(ROOT / "outputs/phase2/phase2g/structural_oos_u2_table.csv")
    models = ["STRUCTURAL_MAP_M0", "BVAR_SPEC_B", "AR_BIC", "VAR_SPEC_B", "RW_NO_DRIFT"]
    labels = ["Structural M0", "BVAR", "AR", "VAR", "RW"]
    colors = ["#d62728", "#1f77b4", "#ff7f0e", "#2ca02c", "#7f7f7f"]
    x = np.arange(len(data)); width = .15
    figure, axis = plt.subplots(figsize=(10, 5))
    for index, (model, label, color) in enumerate(zip(models, labels, colors)):
        axis.bar(x + (index - 2) * width, data[model], width, label=label, color=color)
    axis.axhline(1, color="black", linewidth=1, linestyle="--", label="RW threshold")
    axis.set_xticks(x, [f"H{int(h)}" for h in data.horizon])
    axis.set_ylabel("Theil U2 (lower is better; RW = 1)")
    axis.set_title("Strict common-sample structural OOS comparison")
    axis.legend(ncol=3)
    figure.tight_layout()
    figure.savefig(OUT / "figure_08_structural_oos_comparison.png", dpi=180)
    plt.close(figure)


def external_validation_panel():
    inventory = plt.imread(ROOT / "outputs/phase2/phase2h/inventory_external_validation.png")
    cost = plt.imread(ROOT / "outputs/phase2/phase2h/cost_external_validation.png")
    figure, axes = plt.subplots(2, 1, figsize=(10, 8))
    axes[0].imshow(inventory); axes[0].axis("off"); axes[0].set_title("Inventory-state validation")
    axes[1].imshow(cost); axes[1].axis("off"); axes[1].set_title("Cost-state validation")
    figure.suptitle("External validation of latent structural states", fontsize=16)
    figure.tight_layout()
    figure.savefig(OUT / "figure_09_external_validation.png", dpi=180)
    plt.close(figure)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mechanism_diagram()
    data_model_map()
    posterior_parameters()
    structural_oos()
    external_validation_panel()
    for name in (
        "figure_02_research_mechanism.png",
        "figure_03_data_model_map.png",
        "figure_04_posterior_parameter_summary.png",
        "figure_08_structural_oos_comparison.png",
        "figure_09_external_validation.png",
    ):
        path = OUT / name
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"figure generation failed: {path}")
        print(path.relative_to(ROOT), path.stat().st_size)


if __name__ == "__main__":
    main()
