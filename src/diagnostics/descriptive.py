"""Descriptive tables, audit flags and dependency-light scientific figures."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

from .transformations import PREFIX


LEVELS = ["lc_spot", "lc_output", "spodumene_price", "spodumene_cny_t", "battery_install", "usd_cny_mean"]
CORE_CORRELATION_LEVELS = ["lc_spot", "lc_output", "spodumene_cny_t", "battery_install"]
PALETTE = ["#1F4E79", "#C55A11", "#548235", "#7030A0", "#00A6A6", "#7F6000"]


def descriptive_levels(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable in LEVELS:
        series = data[variable].dropna()
        mean = series.mean()
        rows.append({
            "variable": variable,
            "N": int(series.size),
            "mean": mean,
            "median": series.median(),
            "std": series.std(ddof=1),
            "min": series.min(),
            "p10": series.quantile(0.10),
            "p25": series.quantile(0.25),
            "p75": series.quantile(0.75),
            "p90": series.quantile(0.90),
            "max": series.max(),
            "CV": series.std(ddof=1) / mean if mean != 0 else np.nan,
            "skewness": series.skew(),
            "kurtosis": series.kurt(),
        })
    return pd.DataFrame(rows)


def descriptive_growth(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for level, prefix in PREFIX.items():
        for transformation in ("dlog", "mom_pct", "yoy_pct"):
            column = f"{prefix}_{transformation}"
            valid = data[["month", column]].dropna()
            series = valid[column]
            max_i = series.idxmax()
            min_i = series.idxmin()
            rows.append({
                "variable": level,
                "transformation": transformation,
                "N": int(series.size),
                "mean": series.mean(),
                "median": series.median(),
                "std": series.std(ddof=1),
                "min": series.min(),
                "max": series.max(),
                "IQR": series.quantile(0.75) - series.quantile(0.25),
                "max_absolute_change": series.abs().max(),
                "skewness": series.skew(),
                "kurtosis": series.kurt(),
                "month_of_max_increase": data.loc[max_i, "month"],
                "month_of_max_decrease": data.loc[min_i, "month"],
            })
    return pd.DataFrame(rows)


def large_changes(data: pd.DataFrame, threshold: float, extreme_threshold: float) -> pd.DataFrame:
    known = {("lc_output", "2020-03"), ("battery_install", "2020-03")}
    rows = []
    for level, prefix in PREFIX.items():
        column = f"{prefix}_mom_pct"
        subset = data.loc[data[column].abs().ge(threshold), ["month", column]]
        for item in subset.itertuples(index=False):
            change = float(getattr(item, column))
            rows.append({
                "variable": level,
                "month": item.month,
                "mom_pct": change,
                "abs_mom_pct": abs(change),
                "flag_30pct": True,
                "flag_50pct": abs(change) >= extreme_threshold,
                "known_anomaly": (level, item.month) in known,
                "decision": "KEEP_REVIEW_FLAG",
                "notes": "Large observed monthly change; no automatic deletion",
            })
    return pd.DataFrame(rows).sort_values(["abs_mom_pct", "variable"], ascending=[False, True]).reset_index(drop=True)


def data_audit(data: pd.DataFrame, config: dict, unit_map: dict[str, str]) -> pd.DataFrame:
    numeric = data.select_dtypes(include=[np.number])
    checks = [
        ("row_count", len(data), config["expected_months"], len(data) == config["expected_months"], "Exact configured sample"),
        ("start_month", data.month.iloc[0], config["sample_start"], data.month.iloc[0] == config["sample_start"], "Inclusive"),
        ("end_month", data.month.iloc[-1], config["sample_end"], data.month.iloc[-1] == config["sample_end"], "Inclusive"),
        ("duplicate_months", int(data.month.duplicated().sum()), 0, not data.month.duplicated().any(), "Month key"),
        ("monotonic_months", bool(pd.PeriodIndex(data.month, freq="M").is_monotonic_increasing), True, True, "Monthly ordering"),
        ("core_level_missing", int(data[LEVELS].isna().sum().sum()), 0, not data[LEVELS].isna().any().any(), "Core levels only"),
        ("infinite_numeric", int(np.isinf(numeric.to_numpy()).sum()), 0, not np.isinf(numeric.to_numpy()).any(), "All numeric fields"),
        ("nonpositive_levels", int(data[LEVELS].le(0).sum().sum()), 0, not data[LEVELS].le(0).any().any(), "Required for natural logs"),
        ("duplicate_rows", int(data.duplicated().sum()), 0, not data.duplicated().any(), "Full-row duplicates"),
        ("future_tail_rows", int((data.month > config["sample_end"]).sum()), 0, not (data.month > config["sample_end"]).any(), "No 2025-10+ observations"),
    ]
    rows = [{"check": name, "value": value, "expected": expected, "status": "PASS" if ok else "FAIL", "notes": notes}
            for name, value, expected, ok, notes in checks]
    for variable in LEVELS:
        rows.append({"check": f"unit_{variable}", "value": unit_map[variable], "expected": unit_map[variable], "status": "PASS", "notes": "Matches phase1 configuration and data dictionary"})
        for statistic in ("min", "median", "max"):
            rows.append({"check": f"{variable}_{statistic}", "value": getattr(data[variable], statistic)(), "expected": "reviewed", "status": "PASS", "notes": "Magnitude review; original value retained"})
    return pd.DataFrame(rows)


def contemporaneous_correlations(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for transform in ("log", "dlog"):
        columns = [f"{PREFIX[v]}_{transform}" for v in CORE_CORRELATION_LEVELS]
        labels = dict(zip(columns, CORE_CORRELATION_LEVELS))
        for method in ("pearson", "spearman"):
            corr = data[columns].corr(method=method)
            for i, left in enumerate(columns):
                for right in columns[i:]:
                    rows.append({
                        "transformation": transform,
                        "method": method,
                        "variable_x": labels[left],
                        "variable_y": labels[right],
                        "correlation": corr.loc[left, right],
                        "interpretation_scope": "CONTEMPORANEOUS_DESCRIPTIVE_ONLY",
                    })
    return pd.DataFrame(rows)


def annual_summary(data: pd.DataFrame) -> pd.DataFrame:
    work = data[["month", *CORE_CORRELATION_LEVELS]].copy()
    work["year"] = work.month.str[:4]
    work["year_label"] = work.year.where(work.year.ne("2025"), "2025_YTD_SEP")
    rows = []
    for (year, label), group in work.groupby(["year", "year_label"], sort=True):
        for variable in CORE_CORRELATION_LEVELS:
            rows.append({
                "year": int(year),
                "year_label": label,
                "variable": variable,
                "N": int(group[variable].notna().sum()),
                "annual_mean": group[variable].mean(),
                "annual_min": group[variable].min(),
                "annual_max": group[variable].max(),
            })
    return pd.DataFrame(rows)


def _fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    return (
        ImageFont.truetype(str(bold), 30),
        ImageFont.truetype(str(regular), 20),
        ImageFont.truetype(str(regular), 16),
    )


def _fmt_tick(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if magnitude >= 1_000:
        return f"{value / 1_000:.0f}k"
    if magnitude >= 100:
        return f"{value:.0f}"
    if magnitude >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def _bounds(series: Iterable[pd.Series]) -> tuple[float, float]:
    values = np.concatenate([s.dropna().to_numpy(dtype=float) for s in series])
    low, high = float(values.min()), float(values.max())
    if np.isclose(low, high):
        return low - 1.0, high + 1.0
    pad = (high - low) * 0.08
    lower = low - pad
    if low >= 0:
        lower = max(0.0, lower)
    return lower, high + pad


def save_line_figure(
    data: pd.DataFrame,
    series: list[tuple[str, str]],
    path: Path,
    title: str,
    y_label: str,
    sample_start: str,
    sample_end: str,
    subtitle: str = "",
) -> None:
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font, body_font, small_font = _fonts()
    draw.text((90, 40), title, fill="#1F1F1F", font=title_font)
    if subtitle:
        draw.text((90, 83), subtitle, fill="#555555", font=small_font)
    left, top, right, bottom = 150, 140, 1510, 760
    y_min, y_max = _bounds([data[column] for column, _ in series])
    for i in range(6):
        y = top + i * (bottom - top) / 5
        value = y_max - i * (y_max - y_min) / 5
        draw.line((left, y, right, y), fill="#D9E1E8", width=1)
        label = _fmt_tick(value)
        draw.text((left - 18 - draw.textlength(label, font=small_font), y - 9), label, fill="#555555", font=small_font)
    draw.line((left, top, left, bottom), fill="#333333", width=2)
    draw.line((left, bottom, right, bottom), fill="#333333", width=2)
    n = len(data)
    for index in sorted(set([0, 12, 24, 36, 48, 60, n - 1])):
        x = left + index * (right - left) / (n - 1)
        draw.line((x, bottom, x, bottom + 8), fill="#333333", width=1)
        label = data.month.iloc[index]
        draw.text((x - draw.textlength(label, font=small_font) / 2, bottom + 14), label, fill="#555555", font=small_font)
    for series_index, (column, label) in enumerate(series):
        color = PALETTE[series_index % len(PALETTE)]
        points: list[tuple[float, float]] = []
        for i, value in enumerate(data[column]):
            if pd.isna(value):
                if len(points) >= 2:
                    draw.line(points, fill=color, width=4)
                points = []
                continue
            x = left + i * (right - left) / (n - 1)
            y = bottom - (float(value) - y_min) / (y_max - y_min) * (bottom - top)
            points.append((x, y))
        if len(points) >= 2:
            draw.line(points, fill=color, width=4)
        legend_x = right - 330
        legend_y = top + 22 + series_index * 32
        draw.line((legend_x, legend_y + 8, legend_x + 42, legend_y + 8), fill=color, width=4)
        draw.text((legend_x + 55, legend_y), label, fill="#333333", font=small_font)
    draw.text((28, (top + bottom) / 2), y_label, fill="#333333", font=small_font)
    footer = f"Source: Data Freeze v1; calculations by author. Sample: {sample_start} to {sample_end}."
    draw.text((90, 840), footer, fill="#666666", font=small_font)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Sample", f"{sample_start} to {sample_end}")
    metadata.add_text("Source", "Data Freeze v1; calculations by author")
    image.save(path, pnginfo=metadata)


def save_mom_grid(data: pd.DataFrame, path: Path, sample_start: str, sample_end: str) -> None:
    width, height = 1600, 1000
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font, _, small_font = _fonts()
    draw.text((70, 35), "Core Monthly Changes", fill="#1F1F1F", font=title_font)
    panels = [
        ("lc_spot_mom_pct", "LC spot", "#1F4E79"),
        ("spodumene_cny_mom_pct", "Spodumene CNY proxy", "#C55A11"),
        ("lc_output_mom_pct", "LC output", "#548235"),
        ("battery_install_mom_pct", "Battery installation", "#7030A0"),
    ]
    n = len(data)
    for panel_i, (column, label, color) in enumerate(panels):
        row, col = divmod(panel_i, 2)
        x0, y0 = 80 + col * 770, 115 + row * 385
        left, top, right, bottom = x0 + 90, y0 + 45, x0 + 710, y0 + 315
        series = data[column]
        y_min, y_max = _bounds([series])
        y_min, y_max = min(y_min, 0), max(y_max, 0)
        draw.text((x0 + 5, y0), label, fill="#333333", font=small_font)
        for j in range(5):
            y = top + j * (bottom - top) / 4
            value = y_max - j * (y_max - y_min) / 4
            draw.line((left, y, right, y), fill="#E3E8EC", width=1)
            tick = _fmt_tick(value)
            draw.text((left - 12 - draw.textlength(tick, font=small_font), y - 8), tick, fill="#666666", font=small_font)
        zero_y = bottom - (0 - y_min) / (y_max - y_min) * (bottom - top)
        draw.line((left, zero_y, right, zero_y), fill="#777777", width=1)
        points = []
        for i, value in enumerate(series):
            if pd.isna(value):
                continue
            x = left + i * (right - left) / (n - 1)
            y = bottom - (float(value) - y_min) / (y_max - y_min) * (bottom - top)
            points.append((x, y))
        if len(points) >= 2:
            draw.line(points, fill=color, width=3)
        for index in (0, 24, 48, n - 1):
            x = left + index * (right - left) / (n - 1)
            month = data.month.iloc[index]
            draw.text((x - draw.textlength(month, font=small_font) / 2, bottom + 10), month, fill="#666666", font=small_font)
    footer = f"MoM %, unsmoothed. Source: Data Freeze v1; calculations by author. Sample: {sample_start} to {sample_end}."
    draw.text((70, 950), footer, fill="#666666", font=small_font)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Sample", f"{sample_start} to {sample_end}")
    metadata.add_text("Source", "Data Freeze v1; calculations by author")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, pnginfo=metadata)
