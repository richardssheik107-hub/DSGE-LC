"""Plot only the recorded synthetic local first-order responses.

No noise, smoothing, fitted confidence bands, or historical PE results are used.
The source CSV contains exact linear conditional-mean differences, not nonlinear
GIRFs or estimated responses. Requires the optional report dependencies.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator, ScalarFormatter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/local_stochastic/irf_sigma_0p001.csv"
DEST = ROOT / "reports/2026-11-26_weekly_dsge/figures"


def main():
    rows = list(csv.DictReader(SOURCE.open(encoding="utf-8")))
    if len(rows) != 148 or {float(r["sigma"]) for r in rows} != {.001}:
        raise ValueError("Unexpected source shape or shock scale")
    fonts = {f.name for f in font_manager.fontManager.ttflist}
    candidates = [name for name in ("Noto Sans CJK SC", "Source Han Sans SC", "SimHei", "Noto Sans CJK JP") if name in fonts]
    if not candidates:
        raise RuntimeError("A Chinese font is required; do not render missing glyphs")
    plt.rcParams.update({
        "font.family": candidates[0], "font.size": 10,
        "axes.titlesize": 11, "axes.labelsize": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#777777", "axes.linewidth": .7,
        "axes.unicode_minus": False, "xtick.labelsize": 9,
        "ytick.labelsize": 9, "savefig.facecolor": "white",
        "svg.fonttype": "path", "pdf.fonttype": 42,
    })
    DEST.mkdir(parents=True, exist_ok=True)
    shades = ("#1D4D73", "#C47427", "#3B7B71")
    groups = {shock: [r for r in rows if r["shock"] == shock and int(r["month"]) <= 24]
              for shock in ("z_omega", "z_m", "z_pj", "z_kappa")}
    names = ("终端组合权重冲击", "经营成本冲击", "开工成本冲击", "抵押要求冲击")
    fig, axes = plt.subplots(2, 2, figsize=(7.05, 4.75))
    for ax, (shock, data), title in zip(axes.ravel(), groups.items(), names):
        months = [int(r["month"]) for r in data]
        ax.axhline(0, color="#999999", linewidth=.7, zorder=0)
        for key, label, color, style in (("P_percent", "现货 P", shades[0], "-"),
                                          ("F_percent", "一期合约 F", shades[1], "--")):
            ax.plot(months, [float(r[key]) for r in data], label=label, color=color,
                    linestyle=style, linewidth=1.8)
        ax.set_title(title, loc="left", pad=8)
        ax.set_xlim(0, 24)
        ax.set_xticks([0, 6, 12, 18, 24])
        ax.set_xlabel("冲击后月数")
        ax.set_ylabel("相对锚值的变化  %")
        ax.grid(axis="y", color="#E5E5E5", linewidth=.55)
        ax.yaxis.set_major_locator(MaxNLocator(4))
        if shock == "z_kappa":
            ax.set_ylim(-.01, .01)
            ax.text(12, .005, "本局部松弛分支的响应为零", ha="center", fontsize=9, color="#555555")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(.5, 1.005))
    fig.subplots_adjust(top=.88, bottom=.12, left=.105, right=.98, wspace=.30, hspace=.62)
    out = []
    for ext in ("png", "svg"):
        path = DEST / ("local_price_responses." + ext)
        fig.savefig(path, dpi=230)
        out.append(path)
    plt.close(fig)

    data = groups["z_pj"]
    months = np.array([int(r["month"]) for r in data])
    fig, axes = plt.subplots(3, 1, figsize=(7.05, 5.0), sharex=True)
    for ax, key, title, color in zip(axes,
            ("J_percent", "K_effective_percent", "Q_percent"),
            ("新开工 J", "有效产能 K", "当期产量 Q"), shades):
        y = np.array([float(r[key]) for r in data])
        ax.axhline(0, color="#999999", linewidth=.7)
        ax.plot(months, y, color=color, linewidth=1.9)
        ax.set_title(title, loc="left", fontsize=10, pad=5)
        ax.set_ylabel("变化  %")
        ax.grid(axis="y", color="#E5E5E5", linewidth=.55)
        ax.yaxis.set_major_locator(MaxNLocator(3))
        ax.axvline(3, color="#A8A8A8", linestyle=":", linewidth=.9)
    axes[1].annotate("第3月首次出现产能变化", xy=(3, float(data[3]["K_effective_percent"])),
                     xytext=(8.5, -.025), fontsize=9,
                     arrowprops={"arrowstyle": "->", "color": "#666666", "lw": .7})
    axes[2].set_xticks([0, 3, 6, 12, 18, 24])
    axes[2].set_xlim(0, 24)
    axes[2].set_xlabel("冲击后月数")
    fig.subplots_adjust(left=.115, right=.98, top=.94, bottom=.09, hspace=.52)
    for ext in ("png", "svg"):
        path = DEST / ("construction_transmission." + ext)
        fig.savefig(path, dpi=230)
        out.append(path)
    plt.close(fig)
    # Matplotlib places trailing spaces inside SVG path attributes. Newlines
    # remain valid coordinate separators after stripping those spaces.
    for path in out:
        if path.suffix == ".svg":
            path.write_text("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    manifest = {
        "model_id": "LC_DSGE_EQCHAIN_20261126",
        "result_kind": "LOCAL_FIRST_ORDER_RE_WITH_LEADING_RISKY_PORTFOLIO",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "plot_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sigma_each": .001, "innovation": 1, "horizon_displayed_months": 24,
        "horizon_in_source_months": 36, "synthetic_parameters": True,
        "selected_regime": "zero inventory, slack output/debt/collateral constraints",
        "future_innovations": "integrated in the linear conditional mean",
        "nonlinear_girf": False, "estimated_uncertainty_bands": False,
        "sources": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in out},
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"created": [str(p.relative_to(ROOT)) for p in out], "source_rows": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
