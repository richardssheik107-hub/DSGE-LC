"""Conservative structural-break screening with at most two mean breaks."""
from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd


EVENTS = {
    "2021-07": "2021–2022 LC price boom",
    "2023-01": "2022 late / 2023 peak and rapid correction",
    "2023-07": "GFEX LC futures listing (2023-07-21)",
    "2024-01": "2024–2025 lower-price adjustment period",
}


def _month_distance(left: str, right: str) -> int:
    return abs((pd.Period(left, freq="M") - pd.Period(right, freq="M")).n)


def nearest_event(month: str) -> tuple[str, int]:
    event_month = min(EVENTS, key=lambda candidate: _month_distance(month, candidate))
    return EVENTS[event_month], _month_distance(month, event_month)


def _segment_sse(values: np.ndarray, cuts: tuple[int, ...]) -> float:
    boundaries = (0, *cuts, len(values))
    total = 0.0
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        segment = values[start:end]
        total += float(np.square(segment - segment.mean()).sum())
    return max(total, np.finfo(float).tiny)


def bic_mean_segmentation(values: np.ndarray, max_breaks: int = 2, min_segment: int = 18) -> dict:
    """Select zero, one or two piecewise-mean breaks by BIC."""
    values = np.asarray(values, dtype=float)
    if max_breaks > 2:
        raise ValueError("Phase 1A-2 permits no more than two breaks")
    n = len(values)
    candidates: list[dict] = []
    for breaks in range(max_breaks + 1):
        if breaks == 0:
            choices = [()]
        else:
            grid = range(min_segment, n - min_segment + 1)
            choices = [cuts for cuts in itertools.combinations(grid, breaks)
                       if all(b - a >= min_segment for a, b in zip((0, *cuts), (*cuts, n)))]
        for cuts in choices:
            sse = _segment_sse(values, tuple(cuts))
            parameter_count = breaks + 1 + breaks
            bic = n * math.log(sse / n) + parameter_count * math.log(n)
            candidates.append({"breaks": tuple(cuts), "bic": bic, "sse": sse})
    return min(candidates, key=lambda item: item["bic"])


def break_screening_table(data: pd.DataFrame, za: pd.DataFrame, min_segment: int = 18) -> pd.DataFrame:
    rows: list[dict] = []
    mapping = {
        "lc_spot": "lc_spot_log",
        "spodumene_cny_t": "spodumene_cny_log",
        "lc_output": "lc_output_log",
        "battery_install": "battery_install_log",
    }
    for variable, column in mapping.items():
        values = data[column].to_numpy(dtype=float)
        selected = bic_mean_segmentation(values, max_breaks=2, min_segment=min_segment)
        bic_dates = [data.iloc[index]["month"] for index in selected["breaks"]]
        za_rows = za.loc[za.variable.eq(variable)]
        za_dates = list(za_rows.loc[za_rows.reject_5pct, "break_date"])
        agreement = any(_month_distance(left, right) <= 3 for left in bic_dates for right in za_dates)
        if bic_dates and agreement:
            strength = "STRONG_CANDIDATE"
        elif bic_dates and za_rows.reject_5pct.any():
            strength = "MODERATE_CANDIDATE"
        elif bic_dates or za_rows.reject_5pct.any():
            strength = "WEAK / METHOD_ONLY"
        else:
            strength = "NO_CLEAR_BREAK"
        for item in za_rows.itertuples(index=False):
            event, distance = nearest_event(item.break_date)
            rows.append({
                "variable": variable, "transform": "log", "method": f"ZIVOT_ANDREWS_{item.deterministic}",
                "break_date": item.break_date, "break_index": int(item.break_index),
                "score_or_stat": item.za_stat, "p_value_if_available": item.p_value,
                "nearby_event": event, "distance_months": distance, "strength": strength,
                "notes": "Single endogenous break; event date is contextual, not imposed",
            })
        for index in selected["breaks"]:
            month = data.iloc[index]["month"]
            event, distance = nearest_event(month)
            rows.append({
                "variable": variable, "transform": "log", "method": "BIC_MEAN_SEGMENTATION",
                "break_date": month, "break_index": int(index), "score_or_stat": selected["bic"],
                "p_value_if_available": np.nan, "nearby_event": event, "distance_months": distance,
                "strength": strength,
                "notes": f"Selected {len(selected['breaks'])} break(s); max=2; min segment={min_segment}",
            })
        if not selected["breaks"]:
            rows.append({
                "variable": variable, "transform": "log", "method": "BIC_MEAN_SEGMENTATION",
                "break_date": "", "break_index": np.nan, "score_or_stat": selected["bic"],
                "p_value_if_available": np.nan, "nearby_event": "", "distance_months": np.nan,
                "strength": strength, "notes": "BIC selected no mean break",
            })
    return pd.DataFrame(rows)
