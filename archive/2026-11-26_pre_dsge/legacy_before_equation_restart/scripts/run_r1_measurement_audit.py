"""R1-4: replay frozen measurement inputs and restore historical log units.

This runner never estimates a model or writes to old Phase 2 outputs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.structural.mcmc import PosteriorTarget
from src.structural.measurement import build_measurements, load_frozen_panel
from src.structural.parameter_transform import ParameterTransform, load_phase2a_bounds
from src.structural.posterior_artifacts import file_sha256
from src.structural.priors import prior_specs
from src.structural.r1_historical_units import restore_historical_log_units
from src.structural.r1_measurement_scaler import (
    LEGACY_SCALER_ID, COMMON_SCALER_ID, MEASUREMENT_FIELDS,
    assert_legacy_measurements_match_original, assert_posterior_measurement_binding,
    build_measurement_versions, compare_measurement_versions,
)

FREEZE = ROOT / "data/processed/core_monthly_panel.csv"
PANEL = ROOT / "data/processed/phase1/monthly_structural_v1.csv"
POSTERIOR = ROOT / "outputs/phase2/phase2d/baseline_posterior_draws.npz"
R1_CONFIG = ROOT / "configs/r1_revision.json"
PHASE2D_CONFIG = ROOT / "configs/phase2d.yaml"
PRE_FLIGHT = "preflight/inputs_before.json"
HISTORICAL = "historical"
OUTPUT_NAMES = (
    "measurement_scaler_manifest.csv", "measurement_definition_registry.json",
    "legacy_measurement_reconstruction_audit.csv",
    "common_support_scaler_comparison.csv", "historical_log_unit_decomposition.csv",
    "historical_log_reconstruction_audit.csv", "measurement_revision_decision.md",
    "r1_measurement_input_hashes.json",
)


def verified_inputs(revision: Path) -> dict:
    preflight = json.loads((revision / PRE_FLIGHT).read_text(encoding="utf-8"))
    expected = {
        str(FREEZE.relative_to(ROOT)): preflight["data_freeze"]["sha256"],
        str(PANEL.relative_to(ROOT)): preflight["transformed_panel"]["sha256"],
    }
    for row in preflight["posterior_artifacts"]:
        if Path(row["path"]).name == POSTERIOR.name:
            expected[str(POSTERIOR.relative_to(ROOT))] = row["sha256"]
    if len(expected) != 3:
        raise RuntimeError("baseline posterior is missing from R1-0 input ledger")
    for relative, digest in expected.items():
        if file_sha256(ROOT / relative) != digest:
            raise RuntimeError(f"frozen input changed: {relative}")
    gate = json.loads((revision / HISTORICAL / "historical_gate_details.json").read_text(encoding="utf-8"))
    if gate["IMPLEMENTATION_VALIDITY"] != "PASS" or not gate["technical_ready"]:
        raise RuntimeError("R1-2 historical technical gate is not PASS")
    return expected


def legacy_reconstruction(frame: pd.DataFrame, legacy, tolerance: float,
                          phase2d: dict) -> tuple[pd.DataFrame, float]:
    original = build_measurements(frame, "OBS_MIXED4")
    assert_legacy_measurements_match_original(frame, legacy)
    rows = []
    for label, _, _ in MEASUREMENT_FIELDS:
        for month, a, b in zip(original.month, original[label], legacy.measurements[label]):
            error = float(abs(a - b))
            rows.append({"audit_type": "MEASUREMENT_ARRAY", "month": month,
                         "label": label, "original_value": float(a),
                         "reconstructed_value": float(b), "absolute_error": error,
                         "passed": error <= tolerance})

    # Original Phase 2D uses precisely this builder, y-order and PosteriorTarget.
    # Replay archived production z, never run MCMC or change its arrays.
    bounds = load_phase2a_bounds(ROOT / "configs/phase2a.yaml")
    target = PosteriorTarget(
        ParameterTransform.full(bounds),
        legacy.measurements[["spot", "ore_cost", "output", "battery"]].to_numpy(float),
        prior_specs(phase2d)[phase2d["baseline_prior"]],
        phase2d["rho_n_fixed"], phase2d["battery_sd_fixed"],
        phase2d["numerical_guard_abs_z"],
    )
    with np.load(POSTERIOR, allow_pickle=False) as raw:
        z = raw["z"]
        components = raw["components"]
        if z.shape[:2] != components.shape[:2] or components.shape[2] != 5:
            raise RuntimeError("posterior component layout changed")
        indices = (0, z.shape[1] // 2, z.shape[1] - 1)
        for chain in range(z.shape[0]):
            for draw in indices:
                evaluation = target(z[chain, draw])
                archived = float(components[chain, draw, 1])
                error = float(abs(evaluation.loglik - archived))
                rows.append({"audit_type": "ARCHIVED_LOGLIK_REPLAY",
                             "chain": chain, "draw": draw, "target_status": evaluation.status,
                             "archived_loglik": archived,
                             "replayed_loglik": evaluation.loglik,
                             "absolute_error": error,
                             "passed": evaluation.status == "OK" and np.isfinite(error)
                                       and error <= tolerance})
    audit = pd.DataFrame(rows)
    if not audit.passed.all():
        raise RuntimeError("legacy measurement or archived likelihood replay failed")
    return audit, float(audit.absolute_error.max())


def definition_registry(legacy, common, panel_hash: str, code_hash: str,
                        replay_max_error: float) -> dict:
    return {
        "model": "M0_CORE5", "measurement": "OBS_MIXED4",
        "frequency": "monthly; mixed transformations, NOT mixed-frequency",
        "observation_order": ["spot", "ore_cost", "output", "battery"],
        "state_order": ["d", "c", "q", "n", "p"],
        "shock_order": ["demand", "cost", "supply", "price"],
        "source_panel_sha256": panel_hash, "original_measurement_code_sha256": code_hash,
        "versions": {
            LEGACY_SCALER_ID: {"scaler_sha256": legacy.scaler_sha256,
                               "measurement_sha256": legacy.measurement_sha256,
                               "status": "PRODUCTION_POSTERIOR_INPUT_RECONSTRUCTED",
                               "model_months": [str(legacy.measurements.month.iloc[0]), str(legacy.measurements.month.iloc[-1])],
                               "model_n": len(legacy.measurements)},
            COMMON_SCALER_ID: {"scaler_sha256": common.scaler_sha256,
                               "measurement_sha256": common.measurement_sha256,
                               "status": "CONSTRUCTED_UNESTIMATED_CONTRAST",
                               "posterior_compatible_with_legacy": False},
        },
        "posterior_binding_evidence": {
            "method": "Phase2D original builder exact array equality plus archived baseline production likelihood replay",
            "max_absolute_replay_error": replay_max_error,
            "historical_sidecar_caveat": "Original Phase2D posterior sidecar did not embed scaler ID/hash; R1 binding is reconstructed, not original embedded metadata.",
        },
        "observations": {
            "spot": {"source": "lc_spot_dlog", "unit_before_zscore": "monthly log change", "state": "p", "measurement_sd": 0},
            "ore_cost": {"source": "spodumene_cny_dlog", "unit_before_zscore": "monthly RMB ore-price proxy log change", "state": "c", "measurement_sd": 0},
            "output": {"source": "lc_output_yoy_log", "unit_before_zscore": "12-month overlapping YoY log change", "state": "q", "measurement_sd": 0},
            "battery": {"source": "battery_install_yoy_log", "unit_before_zscore": "12-month overlapping YoY log change", "state": "d", "measurement_sd": "fixed 0.25 baseline in standardized units"},
        },
        "states": {
            "p": "standardized price-change pressure, not a price level",
            "c": "RMB ore-price-change anchored cost proxy, not full production cost for all routes",
            "q": "supply state corresponding to output YoY transform",
            "d": "latent demand anchored noisily by battery installations YoY, not total lithium demand",
            "n": "dynamic standardized supply-minus-demand pressure, not a tonnes inventory accounting identity",
        },
        "structural_restrictions": [
            "cost process c_t = rho_c*c_(t-1) + sigma_c*epsilon_cost,t",
            "price equation has nonnegative cost and demand loading supports and nonpositive supply/inventory terms by design",
            "impact sign concentration partly follows parameter support, not independent causal identification",
            "cost innovations cannot automatically be labeled exogenous mine-supply shocks",
            "YoY series overlap for 12 months; observed persistence is not entirely economic state persistence",
        ],
        "historical_log_unit_rule": "raw spot dlog = mu_spot + sd_spot*(initial condition + four shocks); report deterministic mean separately",
        "forbidden_unit_claims": ["additive individual shock simple-percent contributions",
                                  "RMB/tonne contributions without nonlinear allocation",
                                  "tonnes or GWh units for standardized latent state n or d"],
    }


def historical_audit(monthly_units: pd.DataFrame, episode_units: pd.DataFrame,
                     identity_atol: float, endpoint_atol: float) -> pd.DataFrame:
    rows = []
    for level, data, keys in (
        ("MONTH", monthly_units, ["month"]),
        ("EPISODE", episode_units, ["specification", "window", "start", "end"]),
    ):
        for key, group in data.groupby(keys, sort=True):
            total = group.loc[group.component.eq("TOTAL_RAW_LOG_CHANGE")]
            if len(total) != 1:
                raise RuntimeError(f"historical total row not unique: {level}/{key}")
            addends = group.loc[group.component_role.eq("ADDEND"), "raw_log_change_contribution"]
            t = total.iloc[0]
            additive_error = float(addends.sum() - t.raw_log_change_contribution)
            observed_error = float(t.raw_log_change_contribution - t.observed_raw_log_change)
            endpoint_error = float(t.observed_raw_log_change - t.frozen_price_endpoint_log_change)
            passed = (abs(additive_error) <= identity_atol and
                      abs(observed_error) <= identity_atol and
                      abs(endpoint_error) <= endpoint_atol)
            rows.append({"level": level, "key": str(key),
                         "start_endpoint_month": t.return_start_endpoint_month,
                         "end_endpoint_month": t.return_end_endpoint_month,
                         "n_months": int(t.n_months) if level == "EPISODE" else 1,
                         "additive_error": additive_error,
                         "restoration_minus_observed": observed_error,
                         "observed_minus_price_endpoint": endpoint_error,
                         "identity_absolute_tolerance": identity_atol,
                         "endpoint_absolute_tolerance": endpoint_atol,
                         "passed": passed})
    result = pd.DataFrame(rows)
    if not result.passed.all():
        raise RuntimeError("historical raw-log reconstruction failed")
    return result


def decision_text(legacy, common, audit: pd.DataFrame, historical: pd.DataFrame) -> str:
    return f"""# R1-4 测量修订决策：A，保留 LEGACY v1

日期：2026-09-16。结果是本轮对冻结数据和既有后验的审计，不是新规格的后验估计。

## 证据与决定

原 Phase 2D 用 `build_measurements(frame, 'OBS_MIXED4')` 逐列标准化再取共同有效月。
R1 重建 {len(legacy.measurements)} 个月、四列共 {len(legacy.measurements)*4} 个值，逐值完全一致；
存档基线后验的 {len(audit.loc[audit.audit_type.eq('ARCHIVED_LOGLIK_REPLAY')])} 个生产 draw 似然回放均通过。
故为情形 A：原估计输入可复现，仅原文“所有 scaler 均在 57 期内拟合”表述错误。
原 posterior 继续绑定 `{LEGACY_SCALER_ID}`（hash `{legacy.scaler_sha256}`）。
这是证据重建的绑定；旧 NPZ/sidecar 没有原生嵌入 scaler hash，不伪称原始元数据完整。

`{COMMON_SCALER_ID}`（hash `{common.scaler_sha256}`）已构建对照，但未做 MLE、合成验证或 MCMC；
不是“更新后后验”或已完成稳健性检验。该版本改变 spot 与 ore_cost 测量、
固定 loading、噪声及有效先验的单位意义，不能直接使用旧 posterior。
若导师或后续研究选择其为正式主规格，先单列 measurement revision protocol，
明确 battery_sd、参数单位、状态归一化和先验，按原门槛走新目标估计；本轮不自动执行。

本次历史恢复核对 {len(historical)} 个逐月/窗口键，所有原始 log 变化、均值项与价格端点检查通过。
各冲击乘原 spot 标准差后仍是可加的对数变化，不是可加的单项百分比或人民币/吨贡献。
全历史分解仍受 R1-2 后期窗口敏感性 `INTERPRETATION_REVIEW_REQUIRED` 约束。

## 解释边界

全历史样本的逐列 scaler 拟合约定不等同于递归 OOS 的未来泄漏。
现有 OOS 路径按各 origin 的训练窗口拟合 scaler；未来行扰动不改变已训练 scaler 的专项测试已执行。
本决策不改变模型结构、数据、参数范围、seed、后验 draw 或旧产物。
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-subdir", default="measurement_final")
    args = parser.parse_args()
    if args.output_subdir in (".", "..") or "/" in args.output_subdir or "\\" in args.output_subdir:
        raise ValueError("output-subdir must be one directory name")
    revision = ROOT / "outputs/revisions" / args.run_id
    out = revision / args.output_subdir
    if not revision.is_dir() or any((out / name).exists() for name in OUTPUT_NAMES):
        raise FileExistsError("revision missing or R1-4 output already exists; never overwrite")
    expected_hashes = verified_inputs(revision)
    config = json.loads(R1_CONFIG.read_text(encoding="utf-8"))["measurement_audit"]
    phase2d = json.loads(PHASE2D_CONFIG.read_text(encoding="utf-8"))
    frame = load_frozen_panel(PANEL)
    panel_hash = file_sha256(PANEL)
    code_hash = file_sha256(ROOT / "src/structural/measurement.py")
    legacy, common = build_measurement_versions(
        frame, source_panel_sha256=panel_hash, code_version=f"measurement.py SHA256:{code_hash}")
    comparison = compare_measurement_versions(legacy, common)
    reconstruction, replay_max_error = legacy_reconstruction(
        frame, legacy, config["posterior_loglik_replay_absolute_tolerance"], phase2d)
    if reconstruction.loc[reconstruction.audit_type.eq("MEASUREMENT_ARRAY"), "absolute_error"].max() > config["legacy_reconstruction_absolute_tolerance"]:
        raise RuntimeError("legacy measurement difference exceeds configured threshold")
    binding = {"measurement_scaler_id": LEGACY_SCALER_ID, "scaler_sha256": legacy.scaler_sha256}
    assert_posterior_measurement_binding(binding, legacy)
    try:
        assert_posterior_measurement_binding(binding, common)
    except ValueError:
        pass
    else:
        raise RuntimeError("common scaler incorrectly accepted for legacy posterior")

    historical_dir = revision / HISTORICAL
    historical_sources = {
        str(path.relative_to(ROOT)): file_sha256(path)
        for path in (historical_dir / "historical_monthly_corrected.csv",
                     historical_dir / "historical_episode_corrected.csv")
    }
    monthly = pd.read_csv(historical_dir / "historical_monthly_corrected.csv")
    episodes = pd.read_csv(historical_dir / "historical_episode_corrected.csv")
    frozen = pd.read_csv(FREEZE)
    spot = legacy.scaler_table.set_index("label").loc["spot"]
    monthly_units, episode_units = restore_historical_log_units(
        monthly, episodes, frame[["month", "lc_spot_dlog"]], frozen[["month", "lc_spot"]],
        spot_mean=float(spot["mean"]), spot_sd=float(spot.sample_sd),
        identity_atol=config["historical_log_identity_absolute_tolerance"],
        endpoint_atol=config["historical_endpoint_absolute_tolerance"],
    )
    historical_units = pd.concat((monthly_units.assign(level="MONTH"),
                                  episode_units.assign(level="EPISODE")), ignore_index=True)
    h_audit = historical_audit(monthly_units, episode_units,
                               config["historical_log_identity_absolute_tolerance"],
                               config["historical_endpoint_absolute_tolerance"])
    registry = definition_registry(legacy, common, panel_hash, code_hash, replay_max_error)
    before = {**expected_hashes, **historical_sources}
    after = {relative: file_sha256(ROOT / relative) for relative in before}
    if after != before:
        raise RuntimeError("frozen inputs changed during R1-4")
    out.mkdir(parents=True, exist_ok=False)
    pd.concat((legacy.scaler_table, common.scaler_table), ignore_index=True).to_csv(out / OUTPUT_NAMES[0], index=False)
    (out / OUTPUT_NAMES[1]).write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reconstruction.to_csv(out / OUTPUT_NAMES[2], index=False)
    comparison.to_csv(out / OUTPUT_NAMES[3], index=False)
    historical_units.to_csv(out / OUTPUT_NAMES[4], index=False)
    h_audit.to_csv(out / OUTPUT_NAMES[5], index=False)
    (out / OUTPUT_NAMES[6]).write_text(decision_text(legacy, common, reconstruction, h_audit), encoding="utf-8")
    (out / OUTPUT_NAMES[7]).write_text(json.dumps({"before": before, "after": after,
                                                  "R1_config_sha256": file_sha256(R1_CONFIG)}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": "A", "legacy_scaler_sha256": legacy.scaler_sha256,
                      "common_scaler_sha256": common.scaler_sha256,
                      "measurement_replay_rows": len(reconstruction),
                      "historical_audit_rows": len(h_audit),
                      "max_replay_error": replay_max_error,
                      "max_historical_endpoint_error": float(h_audit.observed_minus_price_endpoint.abs().max())}, indent=2))


if __name__ == "__main__":
    main()
