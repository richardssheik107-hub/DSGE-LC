"""Render the paired stochastic GIRF results as meeting figures."""

import argparse
import csv
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import font_manager, pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402


SHOCKS = {
    "zA_id": ("需求冲击响应", "需求规模创新", "demand_girf"),
    "zm_id": ("单位生产成本冲击响应", "单位生产成本创新", "cost_girf"),
}
VARIABLES = {
    "P": "现货价格 P",
    "F": "期货价格 F",
    "risk_premium": "风险溢价 E[P′] − F",
    "C": "新采购承诺 C",
    "Q": "产量 Q",
    "I": "库存 I",
    "J": "新开工 J",
    "K_e": r"有效产能 $K_e$",
}
STARTS = {
    "anchor": ("确定性锚", "#213d6c", "-", 2.35),
    "warm_0": ("预热起点 1", "#c45924", (0, (5, 3)), 1.75),
    "warm_1": ("预热起点 2", "#188676", (0, (2, 2)), 1.75),
}


def read_response(path):
    """Read complete curves and check that each panel uses the same horizon."""
    fields = {"shock", "start_id", "horizon", "variable", "girf_plus", "mc_se"}
    grouped = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not fields.issubset(reader.fieldnames or ()):
            raise ValueError(f"{path} must contain {', '.join(sorted(fields))}")
        for row in reader:
            key = row["shock"], row["start_id"], row["variable"]
            if key[0] not in SHOCKS or key[1] not in STARTS or key[2] not in VARIABLES:
                continue
            horizon = int(row["horizon"])
            response = float(row["girf_plus"])
            error = float(row["mc_se"])
            if not np.isfinite(response) or not np.isfinite(error) or error < 0:
                raise ValueError(f"{key}, month {horizon}: response and MC error must be finite")
            curve = grouped.setdefault(key, {})
            if horizon in curve:
                raise ValueError(f"{key}, month {horizon}: duplicate response row")
            curve[horizon] = (response, error)

    horizons = {}
    curves = {}
    for shock in SHOCKS:
        series = {key: grouped.get(key, {}) for key in
                  ((shock, start, variable) for start in STARTS for variable in VARIABLES)}
        if not all(series.values()):
            missing = [key for key, values in series.items() if not values]
            raise ValueError(f"Missing response curves: {missing}")
        last = max(max(values) for values in series.values())
        months = np.arange(last + 1)
        expected = set(months.tolist())
        for key, values in series.items():
            if set(values) != expected:
                raise ValueError(f"{key}: expected complete months 0 through {last}")
            curves[key] = np.asarray([values[month] for month in months])
        horizons[shock] = months
    return horizons, curves


def figure_font(name):
    installed = {font.name for font in font_manager.fontManager.ttflist}
    preferred = ("Microsoft YaHei", "Noto Sans SC", "SimHei", "PingFang SC")
    if name:
        if name not in installed:
            raise ValueError(f"The requested Chinese font {name!r} is not installed")
        return name
    for option in preferred:
        if option in installed:
            return option
    raise ValueError("Install Noto Sans SC or select an installed Chinese font with --font")


def plot_panel(ax, shock, variable, months, curves):
    anchor = curves[shock, "anchor", variable]
    series = [curves[shock, start, variable][:, 0] for start in STARTS]
    span = max(np.max(np.abs(series)), np.max(np.abs(anchor[:, 0]) + 2 * anchor[:, 1]))
    exponent = int(np.floor(np.log10(span))) if span > 0 else 0
    factor = 10.0 ** exponent
    ax.fill_between(
        months, (anchor[:, 0] - 2 * anchor[:, 1]) / factor,
        (anchor[:, 0] + 2 * anchor[:, 1]) / factor, color="#b6c9e6", alpha=0.68,
        linewidth=0, zorder=2,
    )
    for start, (_, color, linestyle, linewidth) in STARTS.items():
        ax.plot(months, curves[shock, start, variable][:, 0] / factor,
                color=color, linestyle=linestyle, linewidth=linewidth, zorder=3)
    ax.axhline(0, color="#718196", linewidth=0.8, zorder=1.5)
    ax.set_title(VARIABLES[variable], loc="left", color="#20334a", fontweight="bold", pad=11)
    if exponent != 0:
        ax.set_title(f"×$10^{{{exponent}}}$", loc="right", color="#4b5c70",
                     fontsize=10, pad=11)
    last = int(months[-1])
    step = 12 if last <= 72 else 24 if last <= 144 else 60
    ticks = list(range(0, last + 1, step))
    if ticks[-1] != last and last - ticks[-1] >= step / 2:
        ticks.append(last)
    ax.set_xticks(ticks)
    ax.set_xlim(-0.5, last + 0.5)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, min_n_ticks=3))
    ax.margins(y=0.13)
    ax.grid(axis="y", color="#e3e9f0", linewidth=0.75)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#aebdcc")
    ax.tick_params(axis="both", length=0, pad=6, labelcolor="#45566a")


def plot_shock(output, shock, months, curves):
    title, innovation, stem = SHOCKS[shock]
    fig, axes = plt.subplots(2, 4, figsize=(16, 8.5))
    fig.subplots_adjust(left=0.065, right=0.976, top=0.754,
                        bottom=0.136, wspace=0.33, hspace=0.53)
    fig.text(0.065, 0.941, title, color="#172c43", fontsize=27, fontweight="bold")
    fig.text(
        0.065, 0.885, f"{innovation} · 正向条件均值减去正负两支的等权均值",
        color="#475b73", fontsize=13,
    )

    for index, (ax, variable) in enumerate(zip(axes.flat, VARIABLES)):
        plot_panel(ax, shock, variable, months, curves)
        if index >= 4:
            ax.set_xlabel("冲击后月份", color="#475b73", fontsize=10, labelpad=4)

    legend_handles = [Line2D([0], [0], label=label, color=color, linestyle=style,
                             linewidth=width)
                      for label, color, style, width in STARTS.values()]
    legend_handles.append(Patch(facecolor="#b6c9e6", alpha=0.68, edgecolor="none",
                                label="锚点 ±2 蒙特卡洛标准误"))
    fig.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(0.065, 0.858),
               ncols=4, frameon=False, borderaxespad=0, fontsize=11,
               handlelength=2.8, columnspacing=1.9, labelcolor="#293d55")
    fig.text(
        0.065, 0.056, "第 0 月为冲击实现后的首次决策。纵轴为模型归一化单位的水平差，各图倍率见右上角。"
        "使用合成参数作机制演示。",
        color="#546981", fontsize=10,
    )
    premium_note = (
        "风险溢价响应接近政策的数值精度，结合 E27 隐含响应核对。"
        if shock == "zA_id" else
        "风险溢价面板保留 E[P′] − F。它与 E27 隐含响应的差异大于响应本身，方向仅作数值诊断。"
    )
    fig.text(0.065, 0.026, premium_note, color="#546981", fontsize=10)
    try:
        fig.savefig(output / f"{stem}.png", dpi=220)
        fig.savefig(output / f"{stem}.pdf", metadata={"Title": title})
    finally:
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--font", help="override the Matplotlib Chinese font family")
    args = parser.parse_args()
    horizons, curves = read_response(args.run_dir / "response.csv")
    with plt.rc_context({
        "font.family": figure_font(args.font),
        "font.size": 11,
        "axes.titlesize": 13,
        "pdf.fonttype": 42,
        "axes.unicode_minus": True,
        "figure.facecolor": "white",
    }):
        for shock, months in horizons.items():
            plot_shock(args.run_dir, shock, months, curves)


if __name__ == "__main__":
    main()
