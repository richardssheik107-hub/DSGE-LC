"""Pillow figures for Phase 1A-2; avoids optional plotting backends."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


COLORS = ["#1F4E79", "#C55A11", "#548235", "#7030A0", "#00A6A6"]


def _fonts():
    return (
        ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 28),
        ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16),
        ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13),
    )


def _save(image: Image.Image, path: Path, sample_start: str, sample_end: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Sample", f"{sample_start} to {sample_end}")
    meta.add_text("Source", "Data Freeze v1; diagnostic calculations by author")
    image.save(path, pnginfo=meta)


def _line_chart(frame: pd.DataFrame, x_col: str, series: list[tuple[str, str]], path: Path,
                title: str, subtitle: str, sample_start: str, sample_end: str,
                x_is_lag: bool = False) -> None:
    image = Image.new("RGB", (1500, 850), "white")
    draw = ImageDraw.Draw(image)
    title_font, body, small = _fonts()
    draw.text((80, 35), title, fill="#202020", font=title_font)
    draw.text((80, 78), subtitle, fill="#555555", font=small)
    left, top, right, bottom = 140, 130, 1420, 720
    values = np.concatenate([frame[c].dropna().to_numpy(float) for c, _ in series])
    lo, hi = float(values.min()), float(values.max())
    lo, hi = min(lo, 0.0), max(hi, 0.0)
    pad = max((hi - lo) * 0.08, 0.05)
    lo, hi = lo - pad, hi + pad
    for i in range(6):
        y = top + i * (bottom - top) / 5
        val = hi - i * (hi - lo) / 5
        draw.line((left, y, right, y), fill="#D9E1E8", width=1)
        draw.text((80, y - 7), f"{val:.2f}", fill="#555555", font=small)
    zero_y = bottom - (0 - lo) / (hi - lo) * (bottom - top)
    draw.line((left, zero_y, right, zero_y), fill="#777777", width=2)
    n = len(frame)
    for j, (column, label) in enumerate(series):
        points = []
        for i, value in enumerate(frame[column]):
            if pd.isna(value):
                continue
            x = left + i * (right - left) / max(n - 1, 1)
            y = bottom - (float(value) - lo) / (hi - lo) * (bottom - top)
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=COLORS[j], width=4)
        draw.line((right - 310, top + 22 + j * 28, right - 270, top + 22 + j * 28), fill=COLORS[j], width=4)
        draw.text((right - 260, top + 13 + j * 28), label, fill="#333333", font=small)
    tick_indexes = sorted(set([0, n // 4, n // 2, 3 * n // 4, n - 1]))
    for i in tick_indexes:
        x = left + i * (right - left) / max(n - 1, 1)
        label = str(frame.iloc[i][x_col])
        draw.text((x - draw.textlength(label, font=small) / 2, bottom + 14), label, fill="#555555", font=small)
    footer = f"Sample: {sample_start} to {sample_end}. " + ("Positive lag = X leads Y." if x_is_lag else "24-month rolling Pearson correlation of dlog.")
    draw.text((80, 805), footer, fill="#666666", font=small)
    _save(image, path, sample_start, sample_end)


def save_rolling_corr(data: pd.DataFrame, left_col: str, right_col: str, path: Path,
                      title: str, sample_start: str, sample_end: str) -> None:
    work = pd.DataFrame({"month": data.month, "rolling_corr": data[left_col].rolling(24).corr(data[right_col])})
    _line_chart(work, "month", [("rolling_corr", "Rolling correlation")], path, title,
                "Primary transform: monthly log difference; 24-month window", sample_start, sample_end)


def save_lag_profile(correlations: pd.DataFrame, mechanism: str, path: Path,
                     sample_start: str, sample_end: str, margin: bool = False) -> None:
    transform = "yoy_log" if margin else "dlog"
    group = correlations.loc[
        correlations.mechanism.eq(mechanism)
        & correlations["transform"].eq(transform)
        & correlations.sample_variant.eq("FULL_SAMPLE")
    ].copy()
    if margin:
        group = group.loc[group.x.eq("margin_proxy_zlevel")]
    _line_chart(group, "lag", [("pearson", "Pearson"), ("spearman", "Spearman")], path,
                f"{mechanism} Lag Profile", f"Transform: {transform}; diagnostic correlation profile",
                sample_start, sample_end, x_is_lag=True)


def save_heatmap(correlations: pd.DataFrame, path: Path, sample_start: str, sample_end: str) -> None:
    mechanisms = ["Cost → Price", "Demand → Price", "Supply → Price", "Price → Future Supply"]
    table = correlations.loc[
        correlations.mechanism.isin(mechanisms)
        & correlations["transform"].eq("dlog")
        & correlations.sample_variant.eq("FULL_SAMPLE")
    ].pivot(index="mechanism", columns="lag", values="pearson").reindex(mechanisms)
    image = Image.new("RGB", (1700, 610), "white")
    draw = ImageDraw.Draw(image)
    title_font, _, small = _fonts()
    draw.text((60, 25), "Lead-Lag Correlations (dlog)", fill="#202020", font=title_font)
    draw.text((60, 68), "Pearson values shown in cells; positive lag = X leads Y", fill="#555555", font=small)
    left, top, cell_w, cell_h = 300, 120, 52, 82
    for j, lag in enumerate(table.columns):
        draw.text((left + j * cell_w + 12, top - 28), str(lag), fill="#333333", font=small)
    for i, mechanism in enumerate(mechanisms):
        draw.text((35, top + i * cell_h + 30), mechanism, fill="#333333", font=small)
        for j, lag in enumerate(table.columns):
            value = float(table.loc[mechanism, lag])
            intensity = min(abs(value), 1.0)
            if value >= 0:
                fill = (int(245 - 115 * intensity), int(249 - 75 * intensity), int(255 - 25 * intensity))
            else:
                fill = (255, int(248 - 105 * intensity), int(240 - 120 * intensity))
            x0, y0 = left + j * cell_w, top + i * cell_h
            draw.rectangle((x0, y0, x0 + cell_w - 2, y0 + cell_h - 2), fill=fill)
            text = f"{value:.2f}"
            draw.text((x0 + (cell_w - draw.textlength(text, font=small)) / 2, y0 + 31), text, fill="#202020", font=small)
    draw.text((60, 565), f"Data Freeze v1 sample: {sample_start} to {sample_end}; no future tail.", fill="#666666", font=small)
    _save(image, path, sample_start, sample_end)


def save_break_overview(data: pd.DataFrame, breaks: pd.DataFrame, path: Path,
                        sample_start: str, sample_end: str) -> None:
    image = Image.new("RGB", (1500, 950), "white")
    draw = ImageDraw.Draw(image)
    title_font, _, small = _fonts()
    draw.text((70, 25), "Structural Break Candidate Overview", fill="#202020", font=title_font)
    mapping = [("lc_spot_log", "lc_spot", "Spot"), ("spodumene_cny_log", "spodumene_cny_t", "Ore CNY"),
               ("lc_output_log", "lc_output", "Output"), ("battery_install_log", "battery_install", "Battery")]
    n = len(data)
    for panel, (column, variable, label) in enumerate(mapping):
        top, bottom, left, right = 105 + panel * 195, 250 + panel * 195, 145, 1430
        z = (data[column] - data[column].mean()) / data[column].std(ddof=1)
        lo, hi = float(z.min()) - .2, float(z.max()) + .2
        points = [(left + i * (right-left)/(n-1), bottom - (float(v)-lo)/(hi-lo)*(bottom-top)) for i, v in enumerate(z)]
        draw.line(points, fill=COLORS[panel], width=3)
        draw.text((25, top + 55), label, fill="#333333", font=small)
        selected = breaks.loc[(breaks.variable == variable) & (breaks.method == "BIC_MEAN_SEGMENTATION") & breaks.break_date.ne("")]
        for item in selected.itertuples(index=False):
            x = left + int(item.break_index) * (right-left)/(n-1)
            draw.line((x, top, x, bottom), fill="#A61C00", width=3)
            draw.text((x + 4, top + 4), item.break_date, fill="#A61C00", font=small)
        draw.line((left, bottom, right, bottom), fill="#777777", width=1)
    draw.text((70, 910), f"BIC piecewise-mean candidates; max 2 breaks, minimum segment 18 months. Sample: {sample_start} to {sample_end}.", fill="#666666", font=small)
    _save(image, path, sample_start, sample_end)
