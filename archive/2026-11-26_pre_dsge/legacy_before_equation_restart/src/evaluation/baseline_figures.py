"""Dependency-light scientific figures for Phase 1B forecast comparisons."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


COLORS = {"Actual": "#202020", "RW_NO_DRIFT": "#7F7F7F", "AR_BIC": "#1F4E79",
          "VAR_SPEC_A": "#C55A11", "BVAR_SPEC_A": "#548235", "VAR_SPEC_B": "#7030A0", "BVAR_SPEC_B": "#00A6A6"}


def _fonts():
    return (ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 27),
            ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15),
            ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 12))


def _save(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Sample", "2020-01 to 2025-09")
    metadata.add_text("InformationSet", "RELEASE_SAFE_APPROXIMATION")
    image.save(path, pnginfo=metadata)


def forecast_figure(predictions: pd.DataFrame, horizon: int, path: Path) -> None:
    models = ["RW_NO_DRIFT", "AR_BIC", "VAR_SPEC_A", "BVAR_SPEC_A"]
    frame = predictions.loc[
        predictions.information_set.eq("RELEASE_SAFE_APPROXIMATION")
        & predictions.window_variant.eq("PRIMARY_48") & predictions.horizon.eq(horizon)
        & predictions.model.isin(models)
    ].copy()
    actual = frame.drop_duplicates("target_month").sort_values("target_month")[["target_month", "actual_spot"]]
    image = Image.new("RGB", (1550, 880), "white")
    draw = ImageDraw.Draw(image)
    title, body, small = _fonts()
    draw.text((75, 32), f"LC Spot OOS Forecasts: H{horizon}", fill="#202020", font=title)
    draw.text((75, 73), "Expanding window; RELEASE_SAFE_APPROXIMATION; fixed SPEC_A comparison", fill="#555555", font=small)
    left, top, right, bottom = 145, 125, 1465, 745
    all_values = np.r_[actual.actual_spot.to_numpy(), frame.forecast_spot.to_numpy()]
    low, high = float(all_values.min()), float(all_values.max())
    pad = (high - low) * .08
    low, high = max(0, low - pad), high + pad
    for i in range(6):
        y = top + i * (bottom - top) / 5
        value = high - i * (high - low) / 5
        draw.line((left, y, right, y), fill="#D9E1E8", width=1)
        draw.text((60, y - 7), f"{value/1000:.0f}k", fill="#555555", font=small)
    months = list(actual.target_month)
    def points(values: list[float]):
        return [(left + i * (right-left)/max(len(months)-1, 1), bottom - (v-low)/(high-low)*(bottom-top)) for i, v in enumerate(values)]
    draw.line(points(actual.actual_spot.tolist()), fill=COLORS["Actual"], width=5)
    for model in models:
        subset = frame.loc[frame.model.eq(model)].set_index("target_month").reindex(months)
        draw.line(points(subset.forecast_spot.tolist()), fill=COLORS[model], width=3)
    for i in sorted(set([0, len(months)//2, len(months)-1])):
        x = left + i * (right-left)/max(len(months)-1, 1)
        draw.text((x-30, bottom+15), months[i], fill="#555555", font=small)
    labels = ["Actual", *models]
    for i, label in enumerate(labels):
        x, y = 900 + (i % 3) * 185, 105 + (i // 3) * 25
        draw.line((x, y+7, x+35, y+7), fill=COLORS[label], width=4)
        draw.text((x+43, y), label, fill="#333333", font=small)
    draw.text((75, 825), "Data Freeze v1: 2020-01 to 2025-09. Forecast targets are not removed after model instability flags.", fill="#666666", font=small)
    _save(image, path)


def metric_bars(metrics: pd.DataFrame, metric: str, path: Path, title_text: str) -> None:
    models = ["RW_NO_DRIFT", "AR_BIC", "VAR_SPEC_A", "VAR_SPEC_B", "BVAR_SPEC_A", "BVAR_SPEC_B"]
    frame = metrics.loc[
        metrics.information_set.eq("RELEASE_SAFE_APPROXIMATION")
        & metrics.window_variant.eq("PRIMARY_48") & metrics.model.isin(models)
    ]
    image = Image.new("RGB", (1550, 880), "white")
    draw = ImageDraw.Draw(image)
    title, _, small = _fonts()
    draw.text((75, 35), title_text, fill="#202020", font=title)
    draw.text((75, 75), "Primary expanding window and RELEASE_SAFE_APPROXIMATION", fill="#555555", font=small)
    left, top, right, bottom = 135, 145, 1460, 700
    values = frame[metric].to_numpy(float)
    high = max(float(np.nanmax(values)) * 1.15, 1.05 if metric == "theil_u2" else .01)
    if metric == "theil_u2":
        one_y = bottom - 1/high*(bottom-top)
        draw.line((left, one_y, right, one_y), fill="#A61C00", width=2)
    group_w = (right-left)/3
    bar_w = group_w/(len(models)+1)
    for h_i, horizon in enumerate((1, 3, 6)):
        for m_i, model in enumerate(models):
            row = frame.loc[frame.horizon.eq(horizon) & frame.model.eq(model)].iloc[0]
            value = float(row[metric])
            x0 = left + h_i*group_w + (m_i+.5)*bar_w
            y0 = bottom - value/high*(bottom-top)
            draw.rectangle((x0, y0, x0+bar_w*.72, bottom), fill=COLORS.get(model, "#777777"))
            draw.text((x0, y0-18), f"{value:.2f}" if metric != "rmse_level" else f"{value/1000:.0f}k", fill="#333333", font=small)
        draw.text((left+h_i*group_w+group_w/2-12, bottom+18), f"H{horizon}", fill="#333333", font=small)
    for i, model in enumerate(models):
        x, y = 190 + (i%3)*410, 745 + (i//3)*25
        draw.rectangle((x, y, x+18, y+14), fill=COLORS.get(model, "#777777"))
        draw.text((x+26, y-1), model, fill="#333333", font=small)
    draw.text(
        (75, 825),
        "Data Freeze v1: 2020-01 to 2025-09; primary information set: RELEASE_SAFE_APPROXIMATION.",
        fill="#666666", font=small,
    )
    _save(image, path)


def direction_bars(metrics: pd.DataFrame, path: Path) -> None:
    metric_bars(metrics, "direction_accuracy", path, "Direction Accuracy by Model and Horizon")


def forecast_error_figure(predictions: pd.DataFrame, path: Path) -> None:
    models = ["RW_NO_DRIFT", "AR_BIC", "VAR_SPEC_A", "BVAR_SPEC_A"]
    frame = predictions.loc[
        predictions.information_set.eq("RELEASE_SAFE_APPROXIMATION")
        & predictions.window_variant.eq("PRIMARY_48") & predictions.horizon.eq(1)
        & predictions.model.isin(models)
    ].copy()
    frame["error"] = frame.forecast_spot - frame.actual_spot
    image = Image.new("RGB", (1550, 880), "white")
    draw = ImageDraw.Draw(image)
    title, _, small = _fonts()
    draw.text((75, 35), "H1 Forecast Error over Time", fill="#202020", font=title)
    draw.text((75, 75), "Forecast minus actual spot level; RELEASE_SAFE_APPROXIMATION", fill="#555555", font=small)
    left, top, right, bottom = 145, 130, 1465, 745
    bound = max(abs(frame.error.min()), abs(frame.error.max())) * 1.1
    months = sorted(frame.target_month.unique())
    zero_y = (top+bottom)/2
    draw.line((left, zero_y, right, zero_y), fill="#555555", width=2)
    for model in models:
        values = frame.loc[frame.model.eq(model)].set_index("target_month").reindex(months).error.tolist()
        points = [(left+i*(right-left)/max(len(months)-1,1), zero_y-v/(2*bound)*(bottom-top)) for i,v in enumerate(values)]
        draw.line(points, fill=COLORS[model], width=3)
    for i, model in enumerate(models):
        draw.line((930, 115+i*24, 965, 115+i*24), fill=COLORS[model], width=4)
        draw.text((975, 107+i*24), model, fill="#333333", font=small)
    draw.text((75, 825), "Data Freeze v1: 2020-01 to 2025-09; all available H1 targets shown.", fill="#666666", font=small)
    _save(image, path)
