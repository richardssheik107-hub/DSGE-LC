"""Run the read-only Phase 2I preliminary GFEX LC spot-futures extension."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.futures.continuous_contract import (  # noqa: E402
    add_roll_safe_returns,
    aggregate_main_monthly,
    select_daily_main_contract,
)
from src.futures.data_audit import (  # noqa: E402
    aggregate_contract_daily,
    audit_contract_file,
    build_raw_manifest,
    discover_contract_directory,
    list_contract_files,
)
from src.futures.spot_futures import (  # noqa: E402
    basis_inventory_summary,
    build_daily_return_alignment,
    build_monthly_spot_futures,
    cointegration_and_vecm,
    hac_granger_diagnostics,
    lead_lag_correlations,
    reconcile_canonical_daily_spot,
    stationarity_diagnostics,
)
from src.structural.historical_decomposition import select_equal_per_chain  # noqa: E402
from src.structural.kalman import kalman_filter, rts_smoother  # noqa: E402
from src.structural.measurement import build_measurements, load_frozen_panel  # noqa: E402
from src.structural.parameter_transform import PARAMETER_ORDER, load_phase2a_bounds  # noqa: E402
from src.structural.posterior_artifacts import load_posterior_artifact  # noqa: E402
from src.structural.state_space import from_phase2a_parameters  # noqa: E402


OUT = ROOT / "outputs/phase2/phase2i"
FREEZE = ROOT / "data/processed/core_monthly_panel.csv"
PANEL = ROOT / "data/processed/phase1/monthly_structural_v1.csv"
CONFIG = ROOT / "configs/phase2i.yaml"
SPECS = {
    "BASELINE": ("outputs/phase2/phase2d/baseline_posterior_draws.npz", .80),
    "RHO_N_050": ("outputs/phase2/phase2d/rho_n_050_posterior_draws.npz", .50),
    "RHO_N_095": ("outputs/phase2/phase2d/rho_n_095_posterior_draws.npz", .95),
}


def _freeze_hash() -> str:
    return hashlib.sha256(FREEZE.read_bytes()).hexdigest()


def _load_theta(name: str, path: str, rho_n: float, bounds) -> np.ndarray:
    if name == "BASELINE":
        with np.load(ROOT / path, allow_pickle=False) as artifact:
            theta = np.asarray(artifact["theta"])
        if theta.ndim != 3 or theta.shape[0] != 4 or theta.shape[2] != len(PARAMETER_ORDER):
            raise ValueError("baseline posterior shape mismatch")
        return theta
    arrays, _ = load_posterior_artifact(
        ROOT / path,
        expected_specification=name,
        expected_rho_n=rho_n,
        expected_battery_sd=.25,
        bounds=bounds,
    )
    return arrays["theta"]


def _smooth_inventory_paths(cfg: dict) -> tuple[dict[str, tuple[np.ndarray, np.ndarray]], pd.DataFrame]:
    phase2a = json.loads((ROOT / "configs/phase2a.yaml").read_text(encoding="utf-8-sig"))
    bounds = load_phase2a_bounds(ROOT / "configs/phase2a.yaml")
    panel = load_frozen_panel(PANEL, cfg["sample_end"])
    measurements = build_measurements(panel, cfg["measurement"])
    months = measurements.month.astype(str).to_numpy()
    y = measurements[["spot", "ore_cost", "output", "battery"]].to_numpy()
    if len(y) != 57 or months[0] != "2021-01" or months[-1] != cfg["sample_end"]:
        raise ValueError("unexpected structural sample for inventory smoothing")
    results: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    audit: list[dict[str, object]] = []
    for name, (path, rho_n) in SPECS.items():
        draws_per_chain = cfg["baseline_draws_per_chain"] if name == "BASELINE" else cfg["sensitivity_draws_per_chain"]
        theta = _load_theta(name, path, rho_n, bounds)
        subset, indices = select_equal_per_chain(theta, draws_per_chain, cfg["seed"])
        flat = subset.reshape(-1, len(PARAMETER_ORDER))
        paths = np.empty((len(flat), len(months)), np.float32)
        maximum_jitter = 0.0
        minimum_covariance = np.inf
        maximum_radius = 0.0
        for draw_index, row in enumerate(flat):
            parameters = {name_: float(row[index]) for index, name_ in enumerate(PARAMETER_ORDER)}
            parameters["rho_n"] = rho_n
            model = from_phase2a_parameters("M0_CORE5", parameters, cfg["battery_sd"])
            filtered = kalman_filter(model, y, time_index=months)
            smoothed = rts_smoother(model, filtered)
            if filtered.status != "OK" or smoothed.status != "OK" or not np.isfinite(smoothed.smoothed_mean).all():
                raise RuntimeError(f"inventory smoother failed for {name} draw {draw_index}")
            paths[draw_index] = smoothed.smoothed_mean[:, 3]
            maximum_jitter = max(maximum_jitter, float(np.nanmax(filtered.jitter_used)))
            minimum_covariance = min(minimum_covariance, float(np.linalg.eigvalsh(smoothed.smoothed_cov).min()))
            maximum_radius = max(maximum_radius, float(max(abs(np.linalg.eigvals(model.A)))))
        results[name] = (paths, months)
        audit.append({
            "specification": name,
            "rho_n": rho_n,
            "chains": int(subset.shape[0]),
            "draws_per_chain": int(draws_per_chain),
            "total_draws": int(len(flat)),
            "seed": int(cfg["seed"]),
            "selection": "FIXED_SEED_EQUAL_PER_CHAIN_POSTERIOR_INTEGRATION",
            "selection_indices_sha256": hashlib.sha256(indices.tobytes()).hexdigest(),
            "maximum_filter_jitter": maximum_jitter,
            "minimum_smoothed_covariance_eigenvalue": minimum_covariance,
            "maximum_spectral_radius": maximum_radius,
            "data_freeze_sha256": phase2a["data_freeze_sha256"],
        })
    return results, pd.DataFrame(audit)


def _plot_contract_coverage(audit: pd.DataFrame) -> None:
    figure, axis = plt.subplots(figsize=(10, 8))
    data = audit.loc[audit.schema_status.eq("PASS_5MIN_OHLC")].sort_values("contract").reset_index(drop=True)
    starts = pd.to_datetime(data.first_trading_day)
    ends = pd.to_datetime(data.last_trading_day)
    for index, row in data.iterrows():
        axis.hlines(index, starts.iloc[index], ends.iloc[index], color="#1f77b4", linewidth=2)
    axis.set_yticks(range(len(data)), data.contract)
    axis.set_title("GFEX LC 5-minute contract coverage (raw audit window)")
    axis.set_xlabel("Trading date")
    axis.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(OUT / "futures_contract_coverage.png", dpi=180)
    plt.close(figure)


def _plot_normalized_prices(monthly: pd.DataFrame) -> None:
    figure, axis = plt.subplots(figsize=(9, 4.5))
    spot = monthly.spot_mean / monthly.spot_mean.iloc[0] * 100
    futures = monthly.futures_mean / monthly.futures_mean.iloc[0] * 100
    axis.plot(monthly.month, spot, label="SMM spot mean", linewidth=2)
    axis.plot(monthly.month, futures, label="GFEX main-futures mean", linewidth=2)
    axis.axhline(100, color="grey", linewidth=.8)
    axis.set_title("Spot and roll-aware main futures (first overlap month = 100)")
    axis.set_ylabel("Index")
    axis.tick_params(axis="x", rotation=45)
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUT / "spot_futures_normalized_prices.png", dpi=180)
    plt.close(figure)


def _plot_basis(monthly: pd.DataFrame) -> None:
    figure, axis = plt.subplots(figsize=(9, 4.5))
    axis.plot(monthly.month, monthly.basis_mean_pct * 100, marker="o", label="monthly-mean basis")
    axis.plot(monthly.month, monthly.basis_month_end_pct * 100, marker=".", label="month-end basis")
    axis.axhline(0, color="black", linewidth=.8)
    axis.set_title("Simple GFEX LC basis (F/S - 1; not carry-adjusted)")
    axis.set_ylabel("Percent")
    axis.tick_params(axis="x", rotation=45)
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUT / "spot_futures_basis.png", dpi=180)
    plt.close(figure)


def _plot_main_timeline(main_daily: pd.DataFrame) -> None:
    figure, axis = plt.subplots(figsize=(10, 4.5))
    contracts = sorted(main_daily.main_contract.unique())
    mapping = {contract: index for index, contract in enumerate(contracts)}
    axis.step(main_daily.date, main_daily.main_contract.map(mapping), where="post", linewidth=1.3)
    axis.scatter(main_daily.loc[main_daily.switch_flag.eq(1), "date"],
                 main_daily.loc[main_daily.switch_flag.eq(1), "main_contract"].map(mapping),
                 color="#d62728", s=13, label="switch")
    axis.set_yticks(range(len(contracts)), contracts)
    axis.set_title("Deterministic daily volume-main LC contract")
    axis.set_xlabel("Trading date")
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUT / "main_contract_timeline.png", dpi=180)
    plt.close(figure)


def _plot_lead_lag(monthly_lags: pd.DataFrame, daily_lags: pd.DataFrame | None) -> None:
    panels = 2 if daily_lags is not None else 1
    figure, axes = plt.subplots(1, panels, figsize=(11 if panels == 2 else 6, 4.5), squeeze=False)
    axis = axes[0, 0]
    axis.plot(monthly_lags.lag_spot_periods, monthly_lags.pearson, marker="o", label="Pearson")
    axis.plot(monthly_lags.lag_spot_periods, monthly_lags.spearman, marker="s", label="Spearman")
    axis.axhline(0, color="black", linewidth=.7)
    axis.set_title("Monthly lead-lag")
    axis.set_xlabel("Lag; + means futures leads spot")
    axis.legend()
    if daily_lags is not None:
        axis = axes[0, 1]
        axis.plot(daily_lags.lag_spot_periods, daily_lags.pearson, marker="o", label="Pearson")
        axis.plot(daily_lags.lag_spot_periods, daily_lags.spearman, marker="s", label="Spearman")
        axis.axhline(0, color="black", linewidth=.7)
        axis.set_title("Daily common-date lead-lag")
        axis.set_xlabel("Lag; + means futures leads spot")
        axis.legend()
    figure.suptitle("Return cross-correlations (descriptive)")
    figure.tight_layout()
    figure.savefig(OUT / "lead_lag_correlation.png", dpi=180)
    plt.close(figure)


def _plot_basis_inventory(state_paths, monthly: pd.DataFrame) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    colors = {"BASELINE": "#1f77b4", "RHO_N_050": "#ff7f0e", "RHO_N_095": "#2ca02c"}
    basis = monthly[["month", "basis_mean_pct"]].dropna()
    for name, (paths, months) in state_paths.items():
        median = pd.DataFrame({"month": months, "inventory_state": np.median(paths, axis=0)})
        aligned = median.merge(basis, on="month")
        axis.scatter(aligned.inventory_state, aligned.basis_mean_pct * 100, s=22, alpha=.65, label=name, color=colors[name])
        if len(aligned) >= 3:
            slope, intercept = np.polyfit(aligned.inventory_state, aligned.basis_mean_pct * 100, 1)
            grid = np.linspace(aligned.inventory_state.min(), aligned.inventory_state.max(), 100)
            axis.plot(grid, intercept + slope * grid, color=colors[name], linewidth=1)
    axis.axhline(0, color="black", linewidth=.7)
    axis.set_xlabel("Posterior-median latent inventory pressure")
    axis.set_ylabel("Simple monthly-mean basis (%)")
    axis.set_title("Basis vs latent inventory pressure (rho_n sensitivity)")
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUT / "basis_inventory_relationship.png", dpi=180)
    plt.close(figure)


def _validate_roll_returns(main_daily: pd.DataFrame) -> bool:
    same = main_daily.roll_return_status.eq("SAME_CONTRACT")
    switches = main_daily.roll_return_status.eq("SWITCH_NEW_CONTRACT_REFERENCE")
    missing = main_daily.roll_return_status.eq("SWITCH_REFERENCE_MISSING")
    same_ok = np.allclose(
        main_daily.loc[same, "roll_safe_log_return"],
        main_daily.loc[same, "raw_main_close_log_change"],
        equal_nan=False,
    )
    expected_switch = np.log(
        main_daily.loc[switches, "main_close"] / main_daily.loc[switches, "roll_reference_close"]
    )
    switch_ok = np.allclose(main_daily.loc[switches, "roll_safe_log_return"], expected_switch, equal_nan=False)
    missing_ok = bool(main_daily.loc[missing, "roll_safe_log_return"].isna().all())
    return bool(same_ok and switch_ok and missing_ok)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    before_freeze = _freeze_hash()
    if before_freeze != cfg["data_freeze_sha256"]:
        raise RuntimeError("Data Freeze v1 hash mismatch before Phase 2I")

    source_directory, candidates = discover_contract_directory(
        cfg["discovery_roots"], minimum_contracts=cfg["minimum_contracts"]
    )
    candidates.to_csv(OUT / "futures_directory_candidates.csv", index=False)
    files = list_contract_files(source_directory)
    manifest_before = build_raw_manifest(files)
    manifest_before.to_csv(OUT / "futures_raw_manifest.csv", index=False)
    contract_audit = pd.DataFrame([audit_contract_file(path) for path in files])
    contract_audit.to_csv(OUT / "contract_audit.csv", index=False)

    daily_contracts = aggregate_contract_daily(files)
    daily_contracts["analysis_eligible"] = daily_contracts.date.between(
        pd.Timestamp(cfg["analysis_start_date"]), pd.Period(cfg["sample_end"], freq="M").end_time.normalize()
    )
    daily_contracts.to_csv(OUT / "daily_contract_aggregation.csv", index=False)
    main_daily = select_daily_main_contract(
        daily_contracts,
        start_date=cfg["analysis_start_date"],
        end_date=cfg["sample_end"],
    )
    main_daily = add_roll_safe_returns(main_daily, daily_contracts)
    main_daily.to_csv(OUT / "main_contract_daily.csv", index=False)
    main_monthly = aggregate_main_monthly(main_daily)
    main_monthly.to_csv(OUT / "main_contract_monthly.csv", index=False)

    daily_spot, spot_reconciliation, spot_audit = reconcile_canonical_daily_spot(
        ROOT / cfg["canonical_daily_spot"],
        FREEZE,
        sample_end=cfg["sample_end"],
        absolute_tolerance=cfg["daily_spot_monthly_absolute_tolerance"],
    )
    spot_reconciliation.to_csv(OUT / "daily_spot_reconciliation.csv", index=False)
    pd.DataFrame([spot_audit]).to_csv(OUT / "daily_spot_provenance_audit.csv", index=False)
    daily_available = spot_audit["status"] == "PASS"
    monthly = build_monthly_spot_futures(
        FREEZE,
        main_monthly,
        start_month=cfg["monthly_start"],
        end_month=cfg["sample_end"],
        canonical_daily_spot=daily_spot if daily_available else None,
    )
    monthly.to_csv(OUT / "spot_futures_monthly.csv", index=False)

    stationarity = stationarity_diagnostics(
        monthly,
        maxlag=cfg["stationarity_maxlag"],
        autolag=cfg["stationarity_autolag"],
        alpha=cfg["stationarity_alpha"],
    )
    stationarity.to_csv(OUT / "stationarity_diagnostics.csv", index=False)
    cointegration, vecm = cointegration_and_vecm(
        monthly,
        stationarity,
        minimum_n=cfg["cointegration_minimum_n"],
        maxlag=cfg["cointegration_maxlag"],
        autolag=cfg["cointegration_autolag"],
        alpha=cfg["cointegration_alpha"],
        vecm_k_ar_diff=cfg["vecm_k_ar_diff"],
    )
    cointegration.to_csv(OUT / "cointegration_diagnostics.csv", index=False)
    vecm.to_csv(OUT / "vecm_diagnostics.csv", index=False)

    monthly_lags = lead_lag_correlations(
        monthly.futures_monthly_return,
        monthly.spot_monthly_return,
        range(-cfg["monthly_lead_lag_months"], cfg["monthly_lead_lag_months"] + 1),
        frequency="monthly",
    )
    daily_lags = None
    daily_granger = pd.DataFrame()
    if daily_available:
        daily_aligned = build_daily_return_alignment(main_daily, daily_spot)
        daily_aligned.to_csv(OUT / "daily_spot_futures.csv", index=False)
        daily_lags = lead_lag_correlations(
            daily_aligned.roll_safe_log_return,
            daily_aligned.spot_log_return,
            range(-cfg["daily_lead_lag_sessions"], cfg["daily_lead_lag_sessions"] + 1),
            frequency="daily_common_quote_date",
        )
        daily_granger = hac_granger_diagnostics(daily_aligned, max_lag=cfg["daily_lead_lag_sessions"])
        daily_granger.to_csv(OUT / "daily_granger_summary.csv", index=False)
        lead_lag = pd.concat([monthly_lags, daily_lags], ignore_index=True)
    else:
        lead_lag = monthly_lags
    lead_lag.to_csv(OUT / "lead_lag_summary.csv", index=False)

    state_paths, smoother_audit = _smooth_inventory_paths(cfg)
    smoother_audit.to_csv(OUT / "basis_inventory_smoother_audit.csv", index=False)
    basis_inventory = basis_inventory_summary(
        state_paths,
        monthly,
        lags=range(-cfg["basis_inventory_lag_months"], cfg["basis_inventory_lag_months"] + 1),
    )
    basis_inventory.to_csv(OUT / "basis_inventory_summary.csv", index=False)

    _plot_contract_coverage(contract_audit)
    _plot_normalized_prices(monthly)
    _plot_basis(monthly)
    _plot_main_timeline(main_daily)
    _plot_lead_lag(monthly_lags, daily_lags)
    _plot_basis_inventory(state_paths, monthly)

    manifest_after = build_raw_manifest(files)
    raw_unchanged = manifest_before[["contract", "bytes", "sha256"]].equals(
        manifest_after[["contract", "bytes", "sha256"]]
    )
    freeze_unchanged = _freeze_hash() == before_freeze
    contract_audit_complete = len(contract_audit) >= cfg["minimum_contracts"] and contract_audit.schema_status.eq("PASS_5MIN_OHLC").all()
    daily_valid = bool(
        daily_contracts.ohlc_envelope_valid.all()
        and daily_contracts.prices_positive.all()
        and daily_contracts.daily_volume.ge(0).all()
    )
    deterministic = select_daily_main_contract(
        daily_contracts,
        start_date=cfg["analysis_start_date"],
        end_date=cfg["sample_end"],
    )[["date", "main_contract", "main_close", "main_volume"]].equals(
        main_daily[["date", "main_contract", "main_close", "main_volume"]]
    )
    roll_valid = _validate_roll_returns(main_daily)
    monthly_valid = bool(
        len(monthly) >= cfg["cointegration_minimum_n"]
        and monthly.month.min() == cfg["monthly_start"]
        and monthly.month.max() == cfg["sample_end"]
        and monthly[["spot_mean", "futures_mean", "futures_month_end", "basis_mean_pct"]].notna().all().all()
    )
    tracked_lc = subprocess.run(
        ["git", "ls-files", "--", "*LC[0-9][0-9][0-9][0-9].csv"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    no_raw_tracked = tracked_lc == "" and ROOT.resolve() not in source_directory.resolve().parents and source_directory.resolve() != ROOT.resolve()
    core_ready = all((contract_audit_complete, daily_valid, deterministic, roll_valid, monthly_valid, freeze_unchanged, raw_unchanged, no_raw_tracked))
    gates = pd.DataFrame([
        {"gate": "FUTURES_FILES_FOUND", "status": "PASS" if len(files) >= cfg["minimum_contracts"] else "FAIL"},
        {"gate": "CONTRACT_AUDIT_COMPLETE", "status": "PASS" if contract_audit_complete else "FAIL"},
        {"gate": "DAILY_AGGREGATION_VALID", "status": "PASS" if daily_valid else "FAIL"},
        {"gate": "MAIN_CONTRACT_DETERMINISTIC", "status": "PASS" if deterministic else "FAIL"},
        {"gate": "ROLL_SAFE_RETURN_VALID", "status": "PASS" if roll_valid else "FAIL"},
        {"gate": "MONTHLY_SPOT_ALIGNMENT_VALID", "status": "PASS" if monthly_valid else "FAIL"},
        {"gate": "DAILY_CANONICAL_SPOT", "status": "PASS" if daily_available else "DAILY_CANONICAL_SPOT_NOT_AVAILABLE"},
        {"gate": "FREEZE_UNCHANGED", "status": "PASS" if freeze_unchanged else "FAIL"},
        {"gate": "FUTURES_RAW_UNCHANGED", "status": "PASS" if raw_unchanged else "FAIL"},
        {"gate": "NO_FUTURES_RAW_TRACKED", "status": "PASS" if no_raw_tracked else "FAIL"},
        {"gate": "PHASE_2I_READY", "status": "YES" if core_ready else "NO"},
    ])
    gates.to_csv(OUT / "phase2i_gate_summary.csv", index=False)

    baseline_basis = basis_inventory.loc[
        basis_inventory.specification.eq("BASELINE")
        & basis_inventory.statistic.eq("pearson")
        & basis_inventory.lag_basis_months.eq(0)
    ].iloc[0]
    monthly_peak = monthly_lags.iloc[monthly_lags.pearson.abs().argmax()]
    daily_peak = daily_lags.iloc[daily_lags.pearson.abs().argmax()] if daily_lags is not None else None
    summary = {
        "selected_directory_fingerprint": candidates.loc[candidates.selected, "source_directory_fingerprint"].iloc[0],
        "contracts": len(files),
        "raw_total_bytes": int(manifest_before.bytes.sum()),
        "raw_first_timestamp": contract_audit.first_timestamp.min(),
        "raw_last_timestamp": contract_audit.last_timestamp.max(),
        "analysis_start": main_daily.date.min(),
        "analysis_end": main_daily.date.max(),
        "analysis_trading_days": len(main_daily),
        "main_contract_switches": int(main_daily.switch_flag.sum()),
        "monthly_overlap_n": len(monthly),
        "basis_mean_average": float(monthly.basis_mean_pct.mean()),
        "basis_mean_average_excluding_partial_listing_month": float(monthly.loc[monthly.coverage_status.ne("PARTIAL_LISTING_MONTH"), "basis_mean_pct"].mean()),
        "basis_mean_minimum": float(monthly.basis_mean_pct.min()),
        "basis_mean_maximum": float(monthly.basis_mean_pct.max()),
        "cointegration_gate": cointegration.gate_status.iloc[0],
        "cointegration_p_value": cointegration.eg_p_value.iloc[0],
        "vecm_status": vecm.status.iloc[0],
        "monthly_peak_abs_pearson_lag": int(monthly_peak.lag_spot_periods),
        "monthly_peak_abs_pearson": float(monthly_peak.pearson),
        "daily_spot_available": daily_available,
        "daily_overlap_n": int(len(daily_aligned)) if daily_available else 0,
        "daily_peak_abs_pearson_lag": int(daily_peak.lag_spot_periods) if daily_peak is not None else np.nan,
        "daily_peak_abs_pearson": float(daily_peak.pearson) if daily_peak is not None else np.nan,
        "daily_futures_to_spot_min_hac_p": float(daily_granger.loc[daily_granger.direction.eq("FUTURES_TO_SPOT"), "hac_p_value"].min()) if daily_available else np.nan,
        "baseline_basis_inventory_pearson_median": float(baseline_basis["median"]),
        "baseline_basis_inventory_pearson_q05": float(baseline_basis.q05),
        "baseline_basis_inventory_pearson_q95": float(baseline_basis.q95),
        "phase_decision": "PASS_WITH_SHORT_SAMPLE_WARNING" if core_ready else "FAIL",
    }
    pd.DataFrame([summary]).to_csv(OUT / "phase2i_result_summary.csv", index=False)
    print(pd.DataFrame([summary]).T.to_string(header=False))
    print(gates.to_string(index=False))
    if not core_ready:
        raise RuntimeError("Phase 2I core gate failed")


if __name__ == "__main__":
    main()
