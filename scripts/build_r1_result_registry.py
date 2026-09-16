"""Build a machine-readable R1 claim/result registry from certified outputs.

Only aggregate metadata go into this ignored JSON. Source files remain in the
ignored revision directory or the pre-existing private Phase 2 output tree.
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
RUN_ID = "R1_20260916_190253"
REV = ROOT / "outputs/revisions" / RUN_ID
FREEZE_HASH = "9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5"
PANEL_HASH = "0e96ab7f096a6a69e2f11b4e925e86fb2e9892c87b37a5900a159454fdb28f5f"
SCALER_ID = "LEGACY_V1_PER_SERIES_SCALER"
STAGE_COMMITS = {
    "R1-1": "2dc537caf0c22722530a05d61b6ee10db5e85058",
    "R1-2": "5681423031ce8dc9c0199eb5a46ab4a03d1ae2f5",
    "R1-3": "52d704f15ca7271e680dc9373a53665127982a85",
    "R1-4": "21a90abedcc66d02314bfe7b0049f767028f6026",
    "R1-5": "ef2eb3785b8dad58b7d4532298f5a184972b8260",
}
REQUIRED = (
    "claim_id", "experiment_id", "source_commit", "data_hash",
    "measurement/scaler_id", "posterior_artifact_hash", "diagnostic_version",
    "sample_start", "sample_end", "n", "statistic", "mean_or_median",
    "unit", "source_file", "source_row_or_key", "technical_status",
    "interpretation_status", "supersedes_which_old_result", "interval_definition",
)


def read(relative: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / relative)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def pick(frame: pd.DataFrame, **key):
    selected = frame
    for column, value in key.items():
        selected = selected.loc[selected[column].eq(value)]
    if len(selected) != 1:
        raise ValueError(f"expected one source row, found {len(selected)}: {key}")
    return selected.iloc[0]


def add(items: list, *, claim_id: str, experiment_id: str, stage: str,
        measurement: str | None, posterior_hash: str | None,
        sample_start: str, sample_end: str, n: int,
        statistic: str, mean_or_median: str, value: float | int | str,
        interval_definition: str, unit: str, source_file: str,
        source_row_or_key: dict | str, technical_status: str,
        interpretation_status: str, supersedes: str | None,
        data_hash: str = FREEZE_HASH, **extra) -> None:
    if not (ROOT / source_file).exists():
        raise FileNotFoundError(source_file)
    if isinstance(value, (int, float)) and not np.isfinite(value):
        raise ValueError(f"nonfinite registered result: {claim_id}")
    item = {
        "claim_id": claim_id, "experiment_id": experiment_id,
        "source_commit": STAGE_COMMITS[stage], "data_hash": data_hash,
        "measurement/scaler_id": measurement,
        "posterior_artifact_hash": posterior_hash,
        "diagnostic_version": "geyer_pairs_v3" if stage == "R1-1" else stage,
        "sample_start": sample_start,
        "sample_end": sample_end, "n": int(n), "statistic": statistic,
        "mean_or_median": mean_or_median, "value": value,
        "interval_definition": interval_definition, "unit": unit,
        "source_file": source_file, "source_file_sha256": hashlib.sha256((ROOT / source_file).read_bytes()).hexdigest(),
        "source_row_or_key": source_row_or_key,
        "technical_status": technical_status,
        "interpretation_status": interpretation_status,
        "supersedes_which_old_result": supersedes,
        **extra,
    }
    if any(field not in item for field in REQUIRED):
        raise AssertionError("registry item missing required field")
    items.append(item)


def claim_revisions(items: list[dict] | None = None) -> list[dict]:
    rows = [
        {"claim_id": "COST_FUNDAMENTAL_CHANNEL", "revision": "WEAKENED",
         "old_claim": "成本是最稳定且外部独立验证充分的基本面机制",
         "new_claim": "成本通道在结构模型内保持正向且历史窗口有贡献；外部路线成本同源，不构成独立因果验证，后期历史解释仍敏感"},
        {"claim_id": "DEMAND_BATTERY_MEASUREMENT", "revision": "UNCHANGED",
         "old_claim": "需求方向有支持但幅度依赖装车测量假设",
         "new_claim": "保留方向描述；d 是带噪需求代理，不等于总锂需求，幅度对 battery_sd 敏感"},
        {"claim_id": "DIRECT_SUPPLY_AND_A_C", "revision": "UNCHANGED",
         "old_claim": "直接供给/a_c 方向较弱",
         "new_claim": "仍属弱方向；不能由产量状态或受限符号声称独立识别供给扩张机制"},
        {"claim_id": "INVENTORY_EXTERNAL", "revision": "WEAKENED",
         "old_claim": "库存压力与外部库存正相关且区间狭窄",
         "new_claim": "水平/log水平相关为正但高度依赖 rho_n；变化量配对时间块区间跨零，原区间仅为条件参数分布"},
        {"claim_id": "FEVD_PRICE_12M", "revision": "NUMERICALLY_REVISED",
         "old_claim": "旧 FEVD 展示统计可直接加总",
         "new_claim": "逐 draw 份额的后验均值依次 0.0891/0.2130/0.0490/0.6489 合计1；四边际中位数合计0.9645不要求等于1"},
        {"claim_id": "HISTORICAL_EPISODES", "revision": "NUMERICALLY_REVISED",
         "old_claim": "历史标准化贡献可直接作为实际价格涨跌",
         "new_claim": "原后验条件分解重算并恢复 raw log 单位，另列 N×mu 与初始条件；晚期窗口解释仍 AMBIGUOUS"},
        {"claim_id": "HISTORICAL_HIGH_SENSITIVITY", "revision": "WEAKENED",
         "old_claim": "没有 HIGH 即可声称全部历史故事稳健",
         "new_claim": "0 HIGH、6 AMBIGUOUS（均晚期）；技术门槛通过但不允许无条件稳健叙事"},
        {"claim_id": "STRUCTURAL_OOS", "revision": "WEAKENED",
         "old_claim": "严格前瞻 OOS 且结构预测可泛化领先",
         "new_claim": "给定已选规格的历史递归 OOS、发布滞后近似；结构模型不全面胜过 BVAR/RW，指数化 log 点预测不是 E[P]"},
        {"claim_id": "FUTURES_LEADING", "revision": "WEAKENED",
         "old_claim": "错配月频 +1 相关0.710证明稳定领先价格发现",
         "new_claim": "同端点月频+1约0.526且峰值转同期，日频+1约0.475仍保留；均仅探索性描述"},
        {"claim_id": "EXTERNAL_COST_INDEPENDENCE", "revision": "WEAKENED",
         "old_claim": "成本状态与路线成本0.988属完全独立验证",
         "new_claim": "高相关保留但共用矿价锚，主要支持构念/计量口径，非独立因果验证"},
    ]
    if items is None:
        return rows
    related_ids = {"COST_FUNDAMENTAL_CHANNEL":
                   {"FEVD_PRICE_12M", "HISTORICAL_EPISODES", "EXTERNAL_COST_INDEPENDENCE"}}
    archived_evidence = {
        "DEMAND_BATTERY_MEASUREMENT": [
            ("outputs/phase2/phase2d/fixed_assumption_sensitivity.csv",
             {"specification": "BATTERY_SD_050", "parameter": "sigma_d",
              "column": "standardized_posterior_shift"})],
        "DIRECT_SUPPLY_AND_A_C": [
            ("outputs/phase2/phase2d/posterior_identification.csv",
             {"parameter": "a_c", "column": "classification"})],
    }
    for row in rows:
        ids = related_ids.get(row["claim_id"], {row["claim_id"]})
        row["evidence_result_keys"] = [
            {key: result[key] for key in ("claim_id", "experiment_id", "statistic")}
            for result in items if result["claim_id"] in ids
            and (row["claim_id"] != "COST_FUNDAMENTAL_CHANNEL"
                 or result["statistic"] in {"share_cost_h12", "cost_net_contribution",
                                               "smoothed_c_vs_spodumene_route_cost_dlog_pearson"})
        ]
        row["archived_evidence"] = [
            {"source_file": path, "source_row_or_key": key,
             "source_file_sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
            for path, key in archived_evidence.get(row["claim_id"], [])
        ]
        if not row["evidence_result_keys"] and not row["archived_evidence"]:
            raise RuntimeError(f"claim has no traceable evidence: {row['claim_id']}")
    return rows


def build() -> dict:
    preflight = json.loads((REV / "preflight/inputs_before.json").read_text(encoding="utf-8"))
    if preflight["data_freeze"]["sha256"] != FREEZE_HASH or preflight["transformed_panel"]["sha256"] != PANEL_HASH:
        raise RuntimeError("R1 source data hash mismatch")
    posterior = {Path(row["path"]).stem.replace("_posterior_draws", "").upper(): row["sha256"]
                 for row in preflight["posterior_artifacts"]}
    base_hash = posterior["BASELINE"]
    manifest_path = rel(REV / "measurement_final/measurement_scaler_manifest.csv")
    manifest = read(manifest_path)
    spot_scaler = pick(manifest, scaler_id=SCALER_ID, label="spot")
    scaler_hash = json.loads((REV / "measurement_final/measurement_definition_registry.json").read_text(encoding="utf-8"))["versions"][SCALER_ID]["scaler_sha256"]
    items = []
    diag_path = rel(REV / "posterior_audit_final/posterior_gate_by_spec.csv")
    diag = read(diag_path)
    for spec in diag.specification:
        row = pick(diag, specification=spec)
        for metric, kind in (("max_rhat", "max_over_parameters"),
                             ("min_bulk_ess", "min_over_parameters"),
                             ("min_tail_ess", "min_over_parameters"),
                             ("max_mcse_sd", "max_over_parameters")):
            add(items, claim_id="POSTERIOR_CONVERGENCE", experiment_id=f"R1_A01_{spec}",
                stage="R1-1", measurement=f"OBS_MIXED4::{SCALER_ID}",
                posterior_hash=posterior[spec], sample_start="2021-01", sample_end="2025-09",
                n=int(row.draws_per_chain) * 4, statistic=metric, mean_or_median=kind,
                value=float(row[metric]), interval_definition="not_applicable_gate_extremum",
                unit="dimensionless" if metric in ("max_rhat", "max_mcse_sd") else "effective_draws",
                source_file=diag_path, source_row_or_key={"specification": spec, "column": metric},
                technical_status=str(row.A01_GATE),
                interpretation_status="PASS_RECONSTRUCTED_SOURCE_CAVEAT" if spec == "BASELINE" else "PASS",
                supersedes="outputs/phase2/phase2d/rhat_ess_diagnostics.csv",
                measurement_scaler_hash=scaler_hash)
    fevd_path = rel(REV / "fevd/fevd_corrected_summary.csv")
    fevd = read(fevd_path)
    for shock in ("demand", "cost", "supply", "price"):
        row = pick(fevd, specification="BASELINE", state="p", shock=shock, horizon=12)
        add(items, claim_id="FEVD_PRICE_12M", experiment_id="R1_A05_FEVD_BASELINE",
            stage="R1-2", measurement=f"OBS_MIXED4::{SCALER_ID}", posterior_hash=base_hash,
            sample_start="2021-01", sample_end="2025-09", n=int(row.valid_draws),
            statistic=f"share_{shock}_h12", mean_or_median="posterior_mean_of_per_draw_share",
            value=float(row["mean"]), interval_definition="posterior_draw_q05_q95_conditional_on_model",
            interval=[float(row.q05), float(row.q95)], unit="forecast_error_variance_share",
            source_file=fevd_path,
            source_row_or_key={"specification": "BASELINE", "state": "p", "shock": shock, "horizon": 12},
            technical_status="PASS", interpretation_status="DESCRIPTIVE_MODEL_CONDITIONAL",
            supersedes="outputs/phase2/phase2e/fevd_price_summary.csv",
            marginal_median=float(row["median"]), measurement_scaler_hash=scaler_hash)
    episode_path = rel(REV / "historical/historical_episode_corrected.csv")
    episode = read(episode_path)
    windows = {"RISE_2021_2022": ("2021-02", "2022-12", 23),
               "DECLINE_2023": ("2023-01", "2023-12", 12),
               "LATER_2024_2025": ("2024-01", "2025-09", 21)}
    for window, (start, end, count) in windows.items():
        for component in ("demand", "cost", "supply", "price", "initial_condition"):
            row = pick(episode, specification="BASELINE", window=window, component=component)
            add(items, claim_id="HISTORICAL_EPISODES", experiment_id=f"R1_A02_HD_{window}",
                stage="R1-2", measurement=f"OBS_MIXED4::{SCALER_ID}", posterior_hash=base_hash,
                sample_start=start, sample_end=end, n=count,
                statistic=f"{component}_net_contribution", mean_or_median="posterior_mean_of_window_sum",
                value=float(row.posterior_mean), interval_definition="conditional_smoothed_parameter_draw_q05_q95",
                interval=[float(row.q05), float(row.q95)], unit="standardized_price_change_pressure_sum",
                source_file=episode_path,
                source_row_or_key={"specification": "BASELINE", "window": window, "component": component},
                technical_status="PASS", interpretation_status="INTERPRETATION_REVIEW_REQUIRED" if window.startswith("LATER") else "MODEL_CONDITIONAL",
                supersedes="outputs/phase2/phase2f/episode_net_contributions.csv",
                measurement_scaler_hash=scaler_hash)
    sensitivity_path = rel(REV / "historical/historical_story_sensitivity_corrected.csv")
    sensitivity = read(sensitivity_path)
    counts = sensitivity.classification.value_counts().to_dict()
    if counts != {"STABLE": 10, "AMBIGUOUS": 6, "MODERATE": 2}:
        raise RuntimeError(f"historical sensitivity classification changed: {counts}")
    sensitivity_posterior_hashes = {spec: posterior[spec] for spec in
                                    ["BASELINE", *sorted(sensitivity.specification.unique())]}
    add(items, claim_id="HISTORICAL_HIGH_SENSITIVITY", experiment_id="R1_A02_HD_SEVEN_SPECS",
        stage="R1-2", measurement=f"OBS_MIXED4::{SCALER_ID}", posterior_hash=None,
        sample_start="2021-02", sample_end="2025-09", n=len(sensitivity),
        statistic="ambiguous_alternative_window_count", mean_or_median="exact_count", value=counts["AMBIGUOUS"],
        interval_definition="not_applicable_classification_count", unit="specification_window_pairs",
        source_file=sensitivity_path, source_row_or_key="all 18 rows",
        technical_status="PASS", interpretation_status="INTERPRETATION_REVIEW_REQUIRED",
        supersedes="outputs/phase2/phase2f/historical_sensitivity_summary.csv",
        classification_counts=counts, measurement_scaler_hash=scaler_hash,
        posterior_artifact_hashes=sensitivity_posterior_hashes)
    log_path = rel(REV / "measurement_final/historical_log_unit_decomposition.csv")
    log_units = read(log_path)
    for window, (start, end, count) in windows.items():
        for component in ("DETERMINISTIC_MEAN_COMPONENT", "TOTAL_RAW_LOG_CHANGE"):
            row = pick(log_units, level="EPISODE", specification="BASELINE", window=window, component=component)
            add(items, claim_id="HISTORICAL_RAW_LOG_UNIT", experiment_id=f"R1_A04_LOG_{window}",
                stage="R1-4", measurement=f"OBS_MIXED4::{SCALER_ID}", posterior_hash=base_hash,
                sample_start=start, sample_end=end, n=count, statistic=component,
                mean_or_median="deterministic" if component.startswith("DETERMINISTIC") else "posterior_mean_total_identity",
                value=float(row.raw_log_change_contribution), interval_definition="not_applicable_identity",
                unit="dimensionless_log_change", source_file=log_path,
                source_row_or_key={"specification": "BASELINE", "window": window, "component": component},
                technical_status="PASS", interpretation_status="ADDITIVE_LOG_UNIT_ONLY",
                supersedes="outputs/phase2/phase2f/episode_net_contributions.csv",
                measurement_scaler_hash=scaler_hash)
    for label in ("spot", "ore_cost", "output", "battery"):
        row = pick(manifest, scaler_id=SCALER_ID, label=label)
        add(items, claim_id="MEASUREMENT_SCALER", experiment_id="R1_A04_LEGACY_INPUT",
            stage="R1-4", measurement=f"OBS_MIXED4::{SCALER_ID}", posterior_hash=base_hash,
            sample_start=str(row.fit_start_month), sample_end=str(row.fit_end_month), n=int(row.fit_n),
            statistic=f"{label}_sample_sd", mean_or_median="sample_sd_ddof_1", value=float(row.sample_sd),
            interval_definition="not_applicable_deterministic_scaler",
            unit="raw_source_log_change", source_file=manifest_path,
            source_row_or_key={"scaler_id": SCALER_ID, "label": label},
            technical_status="PASS_RECONSTRUCTED", interpretation_status="LEGACY_POSTERIOR_ONLY",
            supersedes="docs/midterm_report_2026.md#measurement",
            fit_mean=float(row["mean"]), measurement_scaler_hash=scaler_hash)
    future_path = rel(REV / "futures/futures_claim_revision.csv")
    future = read(future_path)
    future_input = json.loads((REV / "futures/return_definition_registry.json").read_text(encoding="utf-8"))["input_sha256_before"]
    future_hash = hashlib.sha256(json.dumps(future_input, sort_keys=True).encode("utf-8")).hexdigest()
    for claim, start in (("MONTHLY_LAG_PLUS_ONE", "2023-08"),
                         ("DAILY_LAG_PLUS_ONE", "2023-07-24")):
        row = pick(future, claim=claim)
        for rule, column, n_column in (("EX_POST_DESCRIPTIVE_MAIN", "matched_ex_post_pearson", "matched_ex_post_n"),
                                       ("LAGGED_VOLUME_MAIN", "matched_lagged_main_pearson", "matched_lagged_main_n")):
            add(items, claim_id="FUTURES_LEADING", experiment_id=f"R1_A03_{claim}_{rule}",
                stage="R1-3", measurement="MATCHED_EOM_PRIMARY" if claim.startswith("MONTHLY") else "DAILY_MATCHED_INTERVAL_PRIMARY",
                posterior_hash=None, sample_start=start, sample_end="2025-09", n=int(row[n_column]),
                statistic="lag_plus_one_pearson", mean_or_median="sample_pearson", value=float(row[column]),
                interval_definition="not_reported_exploratory_multi_lag", unit="correlation",
                source_file=future_path, source_row_or_key={"claim": claim, "column": column},
                technical_status="PASS", interpretation_status="DIRECTION_OR_PEAK_SENSITIVE_DESCRIPTIVE",
                supersedes="outputs/phase2/phase2i/lead_lag_summary.csv", data_hash=future_hash,
                input_hashes=future_input, source_n_column=n_column)
    forecast_inputs = json.loads((REV / "forecast_verified/forecast_audit_input_hashes.json").read_text(encoding="utf-8"))
    if forecast_inputs["before"] != forecast_inputs["after"]:
        raise RuntimeError("forecast input hashes changed during R1-5")
    forecast_input_hashes = {path.replace("\\", "/"): digest for path, digest in forecast_inputs["before"].items()}
    for path, expected in forecast_input_hashes.items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"forecast source changed: {path}")
    forecast_keys = read(rel(REV / "forecast_verified/forecast_common_key_audit.csv"))
    forecast_path = rel(REV / "forecast_verified/forecast_metric_revision.csv")
    forecast = read(forecast_path)
    for _, row in forecast.iterrows():
        keys = forecast_keys.loc[(forecast_keys.model == row.model) &
                                 (forecast_keys.horizon == int(row.horizon))]
        if len(keys) != int(row.n_r1):
            raise RuntimeError(f"forecast key count differs for {row.model} H{row.horizon}")
        add(items, claim_id="STRUCTURAL_OOS", experiment_id=f"R1_A07_{row.model}_H{int(row.horizon)}",
            stage="R1-5", measurement="RELEASE_SAFE_APPROXIMATION::TRAINING_WINDOW_SCALER",
            posterior_hash=None, sample_start=str(keys.target_month.min()),
            sample_end=str(keys.target_month.max()), n=int(row.n_r1),
            statistic="theil_u2_level", mean_or_median="RMSE_ratio_to_same_key_RW",
            value=float(row.theil_u2_r1), interval_definition="not_reported_point_forecast_loss",
            unit="dimensionless_rmse_ratio", source_file=forecast_path,
            source_row_or_key={"model": row.model, "horizon": int(row.horizon)},
            technical_status=str(row.status), interpretation_status="HISTORICAL_RECURSIVE_NOT_PROSPECTIVE",
            supersedes="outputs/phase2/phase2g/structural_oos_metrics.csv",
            origin_start=str(keys.forecast_origin.min()), origin_end=str(keys.forecast_origin.max()),
            target_start=str(keys.target_month.min()), target_end=str(keys.target_month.max()),
            input_hashes=forecast_input_hashes, data_hash=PANEL_HASH)
    external_input = json.loads((REV / "external_validation_final/external_validation_input_hashes.json").read_text(encoding="utf-8"))
    if external_input["before"] != external_input["after"]:
        raise RuntimeError("external validation input hashes changed during R1-5")
    def external_data_bundle(series: str) -> tuple[str, dict]:
        names = ("data\\processed\\core_monthly_panel.csv",
                 "data\\processed\\phase1\\monthly_structural_v1.csv",
                 f"data\\processed\\industry\\{series}")
        source_hashes = {name.replace("\\", "/"): external_input["before"][name] for name in names}
        for path, expected in source_hashes.items():
            if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"external validation source changed: {path}")
        combined = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode("utf-8")).hexdigest()
        return combined, source_hashes
    inventory_data_hash, inventory_input_hashes = external_data_bundle("lc_inventory_monthly.csv")
    cost_data_hash, cost_input_hashes = external_data_bundle("lc_cost_margin_monthly.csv")
    external_path = rel(REV / "external_validation_final/external_validation_filtered_vs_smoothed.csv")
    external = read(external_path)
    for spec in ("BASELINE", "RHO_N_050", "RHO_N_095"):
        row = pick(external, specification=spec, external_series="lc_inventory_total_mean", transformation="log_level")
        add(items, claim_id="INVENTORY_EXTERNAL", experiment_id=f"R1_A08_INVENTORY_{spec}",
            stage="R1-5", measurement=f"OBS_MIXED4::{SCALER_ID}", posterior_hash=posterior[spec],
            sample_start="2023-06", sample_end="2025-09", n=int(row.n_months),
            statistic="smoothed_n_vs_log_inventory_pearson", mean_or_median="median_across_parameter_draw_correlations",
            value=float(row.smoothed_median), interval_definition="conditional_parameter_draw_q05_q95_not_time_sample_CI",
            interval=[float(row.smoothed_q05), float(row.smoothed_q95)], unit="correlation",
            source_file=external_path,
            source_row_or_key={"specification": spec, "external_series": "lc_inventory_total_mean", "transformation": "log_level"},
            technical_status="PASS", interpretation_status="RHO_SENSITIVE_LEVEL_ASSOCIATION_NOT_CAUSAL",
            supersedes="outputs/phase2/phase2h/external_validation_correlations.csv",
            filtered_median=float(row.filtered_median), measurement_scaler_hash=scaler_hash,
            data_hash=inventory_data_hash, input_hashes=inventory_input_hashes)
    block_path = rel(REV / "external_validation_final/external_validation_block_bootstrap.csv")
    block = read(block_path)
    for transformation in ("log_level", "log_change"):
        for length in (3, 6):
            row = pick(block, specification="BASELINE", external_series="lc_inventory_total_mean",
                       transformation=transformation, information_use="SMOOTHED", block_length=length)
            add(items, claim_id="INVENTORY_EXTERNAL", experiment_id=f"R1_A08_TIME_{transformation}_B{length}",
                stage="R1-5", measurement=f"OBS_MIXED4::{SCALER_ID}", posterior_hash=base_hash,
                sample_start="2023-06" if transformation == "log_level" else "2023-07",
                sample_end="2025-09", n=int(row.n_months), statistic=f"n_vs_inventory_{transformation}_pearson",
                mean_or_median="posterior_median_path_point_correlation", value=float(row.point_correlation),
                interval_definition=f"paired_moving_block_bootstrap_95pct_B{length}_2000_seed20260916",
                interval=[float(row.ci025), float(row.ci975)], unit="correlation", source_file=block_path,
                source_row_or_key={"specification": "BASELINE", "external_series": "lc_inventory_total_mean", "transformation": transformation, "information_use": "SMOOTHED", "block_length": length},
                technical_status="PASS", interpretation_status="SHORT_SAMPLE_TIME_SENSITIVITY_NOT_CAUSAL",
                supersedes="outputs/phase2/phase2h/external_validation_correlations.csv",
                invalid_bootstrap_replicates=int(row.invalid_replicates), measurement_scaler_hash=scaler_hash,
                data_hash=inventory_data_hash, input_hashes=inventory_input_hashes)
    cost_row = pick(external, specification="BASELINE", external_series="lc_cost_spodumene", transformation="log_change")
    add(items, claim_id="EXTERNAL_COST_INDEPENDENCE", experiment_id="R1_A08_COST_ROUTE",
        stage="R1-5", measurement=f"OBS_MIXED4::{SCALER_ID}", posterior_hash=base_hash,
        sample_start="2022-11", sample_end="2025-09", n=int(cost_row.n_months),
        statistic="smoothed_c_vs_spodumene_route_cost_dlog_pearson",
        mean_or_median="median_across_parameter_draw_correlations", value=float(cost_row.smoothed_median),
        interval_definition="conditional_parameter_draw_q05_q95_not_time_sample_CI",
        interval=[float(cost_row.smoothed_q05), float(cost_row.smoothed_q95)], unit="correlation",
        source_file=external_path,
        source_row_or_key={"specification": "BASELINE", "external_series": "lc_cost_spodumene", "transformation": "log_change"},
        technical_status="PASS", interpretation_status="SHARED_ORE_PRICE_CONSTRUCT_NOT_INDEPENDENT_CAUSAL_VALIDATION",
        supersedes="outputs/phase2/phase2h/external_validation_correlations.csv",
        measurement_scaler_hash=scaler_hash, data_hash=cost_data_hash, input_hashes=cost_input_hashes)
    identity = [(item["claim_id"], item["experiment_id"], item["statistic"],
                 json.dumps(item["source_row_or_key"], sort_keys=True)) for item in items]
    if len(identity) != len(set(identity)):
        raise RuntimeError("duplicate result registry identity")
    return {"schema": "r1_result_registry_v1", "run_id": RUN_ID,
            "data_freeze_sha256": FREEZE_HASH, "transformed_panel_sha256": PANEL_HASH,
            "legacy_scaler_sha256": scaler_hash, "stage_commits": STAGE_COMMITS,
            "source_files_present_and_hashed": True,
            "result_count": len(items), "results": items,
            "claim_revisions": claim_revisions(items)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-subdir", default="result_registry")
    args = parser.parse_args()
    if args.output_subdir in (".", "..") or "/" in args.output_subdir or "\\" in args.output_subdir:
        raise ValueError("output-subdir must be a directory name")
    out = REV / args.output_subdir
    path = out / "result_registry.json"
    if path.exists():
        raise FileExistsError("result registry already exists; never overwrite")
    registry = build()
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"results": registry["result_count"],
                      "claims": len(registry["claim_revisions"]),
                      "output": rel(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
