"""R1-5 minimal external validation with existing posterior draws only.

Replicates the Phase 2H fixed-seed draw selection, computes filtered and RTS
smoothed state paths at the same parameters, then pairs the posterior-median
path with each external series for time-block bootstrap. No MCMC/refit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.structural.historical_decomposition import select_equal_per_chain
from src.structural.kalman import kalman_filter, rts_smoother
from src.structural.measurement import build_measurements, load_frozen_panel
from src.structural.parameter_transform import PARAMETER_ORDER, load_phase2a_bounds
from src.structural.posterior_artifacts import file_sha256, load_posterior_artifact
from src.structural.r1_external_validation import (
    comparison_series, paired_block_bootstrap_correlation,
    state_information_comparison,
)
from src.structural.state_space import from_phase2a_parameters

PANEL = ROOT / "data/processed/phase1/monthly_structural_v1.csv"
FREEZE = ROOT / "data/processed/core_monthly_panel.csv"
INVENTORY = ROOT / "data/processed/industry/lc_inventory_monthly.csv"
COST = ROOT / "data/processed/industry/lc_cost_margin_monthly.csv"
OLD = ROOT / "outputs/phase2/phase2h"
POST = ROOT / "outputs/phase2/phase2d"
SPECS = (("BASELINE", "baseline", .80), ("RHO_N_050", "rho_n_050", .50),
         ("RHO_N_095", "rho_n_095", .95))
INVENTORY_TRANSFORMS = ("raw_level", "log_level", "raw_change", "log_change",
                        "detrended_log_level", "state_change_vs_log_change")
OUTPUTS = ("external_validation_filtered_vs_smoothed.csv",
           "external_validation_transformation_comparison.csv",
           "external_validation_block_bootstrap.csv",
           "external_validation_limitations.md",
           "external_validation_input_hashes.json")


def require_contiguous_months(values, start: str, end: str, label: str) -> None:
    observed = list(map(str, values))
    expected = list(map(str, pd.period_range(start, end, freq="M")))
    if observed != expected:
        raise RuntimeError(f"{label} must have unique contiguous ordered months {start}..{end}")


def selected_paths(label: str, stem: str, rho_n: float, draws_per_chain: int,
                   seed: int, y: np.ndarray, months: np.ndarray,
                   bounds: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    path = POST / f"{stem}_posterior_draws.npz"
    if label == "BASELINE":
        with np.load(path, allow_pickle=False) as source:
            theta = np.asarray(source["theta"])
    else:
        arrays, _ = load_posterior_artifact(
            path, expected_specification=label, expected_rho_n=rho_n,
            expected_battery_sd=.25, bounds=bounds)
        theta = arrays["theta"]
    subset, indices = select_equal_per_chain(theta, draws_per_chain, seed)
    flat = subset.reshape(-1, len(PARAMETER_ORDER))
    filtered = np.empty((len(flat), len(months), 2), dtype=np.float32)
    smoothed = np.empty_like(filtered)
    max_jitter = 0.0
    for i, draw in enumerate(flat):
        params = dict(zip(PARAMETER_ORDER, map(float, draw)))
        params["rho_n"] = rho_n
        model = from_phase2a_parameters("M0_CORE5", params, .25)
        filt = kalman_filter(model, y, time_index=months)
        if filt.status != "OK" or not np.isfinite(filt.filtered_mean).all():
            raise RuntimeError(f"{label} draw {i}: filter failed: {filt.failure_reason}")
        smooth = rts_smoother(model, filt)
        if smooth.status != "OK" or not np.isfinite(smooth.smoothed_mean).all():
            raise RuntimeError(f"{label} draw {i}: smoother failed: {smooth.failure_reason}")
        filtered[i, :, 0] = filt.filtered_mean[:, 3]
        filtered[i, :, 1] = filt.filtered_mean[:, 1]
        smoothed[i, :, 0] = smooth.smoothed_mean[:, 3]
        smoothed[i, :, 1] = smooth.smoothed_mean[:, 1]
        max_jitter = max(max_jitter, float(np.max(filt.jitter_used)))
        if (i + 1) % 250 == 0:
            print(f"external {label}: {i + 1}/{len(flat)}", flush=True)
    return filtered, smoothed, {"draws": len(flat), "draws_per_chain": draws_per_chain,
                                "selected_index_sha256": hashlib.sha256(indices.tobytes()).hexdigest(),
                                "max_jitter": max_jitter}


def source_series(months: np.ndarray, config: dict) -> list[dict]:
    inv = pd.read_csv(INVENTORY)
    inv = inv.loc[inv.month.between(config["inventory_start"], config["inventory_end"])]
    cost = pd.read_csv(COST)
    # Include October 2022: its level is needed to form November's first dlog.
    cost_prior = str(pd.Period(config["cost_start"], freq="M") - 1)
    cost = cost.loc[cost.month.between(cost_prior, config["cost_end"])]
    pos = {month: i for i, month in enumerate(months)}
    if not set(inv.month).issubset(pos) or not set(cost.month).issubset(pos):
        raise RuntimeError("external months outside structural sample")
    require_contiguous_months(inv.month, config["inventory_start"], config["inventory_end"], "inventory")
    require_contiguous_months(cost.month, cost_prior, config["cost_end"], "cost")
    if len(inv) != 28 or len(cost) != 36:
        raise RuntimeError("R1 external fixed windows changed")
    return [
        {"block": "inventory", "external_series": "lc_inventory_total_mean",
         "state": "n", "state_index": 0, "months": inv.month.tolist(),
         "indices": [pos[m] for m in inv.month],
         "external_levels": inv[config["inventory_primary"]].to_numpy(float),
         "transformations": INVENTORY_TRANSFORMS,
         "primary_transform": "log_level",
         "specifications": ("BASELINE", "RHO_N_050", "RHO_N_095")},
        {"block": "cost", "external_series": "lc_cost_spodumene",
         "state": "c", "state_index": 1, "months": cost.month.tolist(),
         "indices": [pos[m] for m in cost.month],
         "external_levels": cost[config["cost_primary"]].to_numpy(float),
         "transformations": ("log_change", "raw_change", "detrended_log_level"),
         "primary_transform": "log_change", "specifications": ("BASELINE",)},
        {"block": "cost", "external_series": "lc_cost_lepidolite",
         "state": "c", "state_index": 1, "months": cost.month.tolist(),
         "indices": [pos[m] for m in cost.month],
         "external_levels": cost[config["cost_secondary"]].to_numpy(float),
         "transformations": ("log_change", "raw_change", "detrended_log_level"),
         "primary_transform": "log_change", "specifications": ("BASELINE",)},
    ]


def validation_tables(paths: dict, series: list[dict], cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    filtered_rows, transformed_rows, bootstrap_rows = [], [], []
    if cfg["bootstrap_interval_quantiles"] != [0.025, 0.975]:
        raise RuntimeError("bootstrap helper interval quantiles do not match R1 config")
    for item in series:
        for specification in item["specifications"]:
            filt, smooth, selection = paths[specification]
            idx = item["indices"]
            target = item["external_levels"]
            for transformation in item["transformations"]:
                summary = state_information_comparison(
                    filt[:, idx, item["state_index"]], smooth[:, idx, item["state_index"]],
                    target, transformation=transformation)
                base = {"specification": specification, "rho_n": dict((s[0], s[2]) for s in SPECS)[specification],
                        "block": item["block"], "state": item["state"],
                        "external_series": item["external_series"],
                        "transformation": transformation,
                        "information_source": "same frozen sample and same full-sample posterior draw parameters",
                        "n_draws": selection["draws"],
                        "n_months": len(target) - int(transformation in (
                            "raw_change", "log_change", "state_change_vs_log_change")),
                        "external_start": item["months"][0], "external_end": item["months"][-1],
                        "first_change_month": item["months"][1] if transformation in (
                            "raw_change", "log_change", "state_change_vs_log_change") else "",
                        "selected_index_sha256": selection["selected_index_sha256"]}
                filtered_rows.append({**base,
                                      "filtered_median": summary["filtered_median"],
                                      "filtered_q05": summary["filtered_q05"],
                                      "filtered_q95": summary["filtered_q95"],
                                      "filtered_valid_draws": summary["filtered_valid_draws"],
                                      "filtered_invalid_draws": summary["filtered_invalid_draws"],
                                      "smoothed_median": summary["smoothed_median"],
                                      "smoothed_q05": summary["smoothed_q05"],
                                      "smoothed_q95": summary["smoothed_q95"],
                                      "smoothed_valid_draws": summary["smoothed_valid_draws"],
                                      "smoothed_invalid_draws": summary["smoothed_invalid_draws"],
                                      "median_difference_filtered_minus_smoothed":
                                          summary["filtered_median"] - summary["smoothed_median"]})
                for info, state_paths in (("FILTERED", filt), ("SMOOTHED", smooth)):
                    representative = np.median(state_paths[:, idx, item["state_index"]], axis=0)
                    x, y = comparison_series(representative, target, transformation)
                    point = paired_block_bootstrap_correlation(
                        x, y, block_length=cfg["bootstrap_block_lengths_months"][0],
                        n_rep=cfg["bootstrap_replicates"], seed=cfg["bootstrap_seed"])
                    transformed_rows.append({**base, "information_use": info,
                                             "representative": "posterior median state path",
                                             "point_correlation": point["point_correlation"],
                                             "point_status": point["point_status"]})
                    # Time-sample uncertainty is attached to the median path, not
                    # mistaken for a full parameter × time joint confidence set.
                    for length in cfg["bootstrap_block_lengths_months"]:
                        sample = point if length == cfg["bootstrap_block_lengths_months"][0] else paired_block_bootstrap_correlation(
                            x, y, block_length=length, n_rep=cfg["bootstrap_replicates"],
                            seed=cfg["bootstrap_seed"])
                        bootstrap_rows.append({**base, "information_use": info,
                                               "representative": "posterior median state path",
                                               **{k: v for k, v in sample.items() if k != "replicate_correlations"}})
    return pd.DataFrame(filtered_rows), pd.DataFrame(transformed_rows), pd.DataFrame(bootstrap_rows)


def limitations() -> str:
    return """# R1-5 外部验证：解释边界

本轮沿用 Phase 2H 同一冻结样本、后验 draw、固定 seed、按链等量抽样和模型参数，
只比较同一 draw 的 filtered 与 smoothed 状态，不进行新 MCMC。
filtered 只使用截至各月的观测进行状态更新，但参数仍从全样本后验取得，
因此**不是历史实时预测状态**；smoothed 则进一步使用未来样本观测。
两者差异是信息使用方式对照，不是新增模型胜负。

原 Phase 2H 的 `q05/q95` 是给定时间序列、跨参数 draw 的条件区间，
不是时间样本置信区间。本轮另以 posterior 中位状态路径与外部序列配对，
固定 20260916 seed、2,000 次、3/6 个月非循环移动时间块，
输出 95% percentile 区间和常数/无效分母复制数；两条序列共用同一抽样索引。
它仅是该中位路径的时间抽样敏感性，**不是** 参数×时间完整联合区间。
28 个月库存与 35 个月成本很短；库存水平有趋势/制度口径风险，
不可凭水平相关区间独自宣称机制显著或因果。另报告原水平、log水平、
原变化、log变化、双方线性去趋势 log 水平及状态变化对照，
差分首月不补造数值，表内明确 N 和变化首月。

成本状态 `c` 的人民币矿价锚与锂辉石路线成本序列共用原料价格；
约 0.988 的旧高相关含机械共同成分，仅支持构念/计量口径，
不是独立因果验证。潜在 `n` 为标准化供需压力，不是吨数库存身份式。
此页不要求修正后的相关为正或显著，不选变换/窗口来维护旧叙事。
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-subdir", default="external_validation_final")
    args = parser.parse_args()
    if args.output_subdir in (".", "..") or "/" in args.output_subdir or "\\" in args.output_subdir:
        raise ValueError("output-subdir must be one directory name")
    rev = ROOT / "outputs/revisions" / args.run_id
    out = rev / args.output_subdir
    if not rev.is_dir() or any((out / name).exists() for name in OUTPUTS):
        raise FileExistsError("revision missing or R1-5 external outputs exist; never overwrite")
    cfg = json.loads((ROOT / "configs/r1_revision.json").read_text(encoding="utf-8"))["forecast_external_validation"]
    p2h = json.loads((ROOT / "configs/phase2h.yaml").read_text(encoding="utf-8-sig"))
    ledger = json.loads((rev / "preflight/inputs_before.json").read_text(encoding="utf-8"))
    if file_sha256(FREEZE) != ledger["data_freeze"]["sha256"] or file_sha256(PANEL) != ledger["transformed_panel"]["sha256"]:
        raise RuntimeError("frozen data changed")
    sources = [FREEZE, PANEL, INVENTORY, COST, OLD / "external_validation_correlations.csv",
               OLD / "external_validation_state_paths.csv", *(POST / f"{stem}_posterior_draws.npz" for _, stem, _ in SPECS)]
    before = {str(path.relative_to(ROOT)): file_sha256(path) for path in sources}
    frame = load_frozen_panel(PANEL, p2h["sample_end"])
    measurement = build_measurements(frame, p2h["measurement"])
    months = measurement.month.to_numpy(str)
    y = measurement[["spot", "ore_cost", "output", "battery"]].to_numpy(float)
    if len(months) != 57 or (months[0], months[-1]) != ("2021-01", "2025-09"):
        raise RuntimeError("structural measurement months changed")
    bounds = load_phase2a_bounds(ROOT / "configs/phase2a.yaml")
    paths = {}
    for label, stem, rho_n in SPECS:
        count = p2h["baseline_draws_per_chain"] if label == "BASELINE" else p2h["sensitivity_draws_per_chain"]
        paths[label] = selected_paths(label, stem, rho_n, count, p2h["seed"], y, months, bounds)
    series = source_series(months, p2h)
    filtered, transformed, bootstrap = validation_tables(paths, series, cfg)
    if filtered.empty or transformed.empty or bootstrap.empty:
        raise RuntimeError("R1-5 external comparison is empty")
    # The original smoothed posterior-draw marginal correlation is reproducible
    # under the same fixed selection, with no old artifact rewritten.
    old = pd.read_csv(OLD / "external_validation_correlations.csv")
    for label in (s[0] for s in SPECS):
        reference = old.loc[old.specification.eq(label) & old.validation_series.eq("log_inventory_mean") & old.statistic.eq("pearson")].iloc[0]
        updated = filtered.loc[filtered.specification.eq(label) & filtered.external_series.eq("lc_inventory_total_mean") & filtered.transformation.eq("log_level")].iloc[0]
        if abs(float(reference["median"]) - float(updated.smoothed_median)) > 1e-6:
            raise RuntimeError(f"old smoothed inventory correlation parity failed: {label}")
    old_cost = old.loc[old.specification.eq("BASELINE") & old.validation_series.eq("spodumene_route_cost_dlog") & old.statistic.eq("pearson")].iloc[0]
    updated_cost = filtered.loc[filtered.specification.eq("BASELINE") & filtered.external_series.eq("lc_cost_spodumene") & filtered.transformation.eq("log_change")].iloc[0]
    if abs(float(old_cost["median"]) - float(updated_cost.smoothed_median)) > 1e-6:
        raise RuntimeError("old smoothed cost correlation parity failed")
    after = {relative: file_sha256(ROOT / relative) for relative in before}
    if before != after:
        raise RuntimeError("R1-5 external inputs changed")
    out.mkdir(parents=True, exist_ok=False)
    filtered.to_csv(out / OUTPUTS[0], index=False)
    transformed.to_csv(out / OUTPUTS[1], index=False)
    bootstrap.to_csv(out / OUTPUTS[2], index=False)
    (out / OUTPUTS[3]).write_text(limitations(), encoding="utf-8")
    (out / OUTPUTS[4]).write_text(json.dumps({"before": before, "after": after,
                                             "draw_selections": {k: v[2] for k, v in paths.items()}}, indent=2) + "\n", encoding="utf-8")
    primary = filtered.loc[filtered.block.eq("inventory") & filtered.transformation.eq("log_level")]
    print(json.dumps({"filtered_rows": len(filtered), "transformation_rows": len(transformed),
                      "bootstrap_rows": len(bootstrap),
                      "invalid_bootstrap_replicates": int(bootstrap.invalid_replicates.sum()),
                      "inventory_primary": primary[["specification", "filtered_median", "smoothed_median"]].to_dict("records")}, indent=2))


if __name__ == "__main__":
    main()
