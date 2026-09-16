"""R1-3: audit aligned LC spot/futures returns without new downloads or old writes."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.futures.continuous_contract import (
    add_roll_safe_returns, select_daily_main_contract,
    select_lagged_volume_main_contract,
)
from src.futures.r1_alignment import (
    build_interval_audit, build_monthly_matched_eom,
    build_monthly_matched_mean, keyed_lead_lag,
)
from src.futures.spot_futures import reconcile_canonical_daily_spot

REV = ROOT / "outputs/revisions/R1_20260916_190253"
OUT = REV / "futures"
FREEZE = ROOT / "data/processed/core_monthly_panel.csv"
PHASE = ROOT / "outputs/phase2/phase2i"
FILES = {
    "contract_daily": PHASE / "daily_contract_aggregation.csv",
    "expost_main": PHASE / "main_contract_daily.csv",
    "legacy_monthly": PHASE / "spot_futures_monthly.csv",
    "legacy_lags": PHASE / "lead_lag_summary.csv",
    "cointegration": PHASE / "cointegration_diagnostics.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _lag_row(frame: pd.DataFrame, specification: str, main_rule: str, lag: int = 1) -> pd.Series:
    rows = frame.loc[(frame.specification == specification)
                     & (frame.main_rule == main_rule)
                     & frame.stratum.eq("ALL")
                     & frame.lag_spot_periods.eq(lag)]
    if len(rows) != 1:
        raise RuntimeError(f"missing or duplicate lag {lag}: {specification}/{main_rule}")
    return rows.iloc[0]


def classify_leading_evidence(comparison: pd.DataFrame, legacy_monthly: float,
                              legacy_daily: float, material_change: float,
                              minimum_n: int) -> tuple[str, dict]:
    """Exploratory *descriptive* classification, not a p-value or strategy test."""
    primary = [(spec, rule) for spec in ("MATCHED_EOM_PRIMARY", "DAILY_MATCHED_INTERVAL_PRIMARY")
               for rule in ("EX_POST_DESCRIPTIVE_MAIN", "LAGGED_VOLUME_MAIN")]
    evidence = {}
    for spec, rule in primary:
        row = _lag_row(comparison, spec, rule)
        evidence[f"{spec}/{rule}"] = {"lag_plus_one_pearson": float(row.pearson),
                                      "n": int(row.n)}
    values = [v["lag_plus_one_pearson"] for v in evidence.values()]
    ns = [v["n"] for v in evidence.values()]
    if any(n < minimum_n for n in ns) or not np.isfinite(values).all():
        return "NOT_EVALUABLE", evidence
    if all(value <= 0 for value in values):
        return "NO_CLEAR_LEAD", evidence
    if any(value <= 0 for value in values):
        return "DIRECTION_OR_PEAK_SENSITIVE", evidence
    eom = min(values[0], values[1])
    daily = min(values[2], values[3])
    evidence["monthly_drop_vs_legacy"] = float(legacy_monthly - eom)
    evidence["daily_drop_vs_legacy"] = float(legacy_daily - daily)
    peaks = {}
    for spec, rule in primary:
        rows = comparison.loc[(comparison.specification == spec)
                              & (comparison.main_rule == rule)
                              & comparison.stratum.eq("ALL")].dropna(subset="pearson")
        winner = rows.iloc[rows.pearson.abs().to_numpy().argmax()]
        peaks[f"{spec}/{rule}"] = int(winner.lag_spot_periods)
    evidence["absolute_peak_lags_exploratory"] = peaks
    if any(lag <= 0 for lag in peaks.values()) or len(set(peaks.values())) > 1:
        return "DIRECTION_OR_PEAK_SENSITIVE", evidence
    if (legacy_monthly - eom >= material_change
            or legacy_daily - daily >= material_change):
        return "EVIDENCE_WEAKENS_AFTER_ALIGNMENT", evidence
    return "LEADING_EVIDENCE_SURVIVES", evidence


def add_comparison(rows: list[pd.DataFrame], frame: pd.DataFrame, *, specification: str,
                   main_rule: str, frequency: str, key: str, future: str, spot: str,
                   switches: str, lags: list[int], stratum: str = "ALL",
                   calendar_index=None) -> None:
    table = keyed_lead_lag(frame, lags, frequency=frequency, key_column=key,
                           futures_column=future, spot_column=spot,
                           switch_column=switches, calendar_index=calendar_index)
    table.insert(0, "specification", specification)
    table.insert(1, "main_rule", main_rule)
    table.insert(2, "stratum", stratum)
    rows.append(table)


def run() -> dict:
    config_path = ROOT / "configs/r1_revision.json"
    phase_path = ROOT / "configs/phase2i.yaml"
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))["futures_alignment"]
    old_config = json.loads(phase_path.read_text(encoding="utf-8-sig"))
    if (config["analysis_start_date"] != old_config["analysis_start_date"]
            or config["sample_end"] != old_config["sample_end"]):
        raise RuntimeError("R1-3 range differs from frozen Phase 2I range")
    output_names = ("return_definition_registry.json", "spot_futures_interval_audit.csv",
                    "monthly_matched_eom.csv", "monthly_matched_mean.csv",
                    "daily_matched_returns.csv", "lagged_volume_main_audit.csv",
                    "lead_lag_specification_comparison.csv", "futures_claim_revision.csv")
    if any((OUT / name).exists() for name in output_names):
        raise FileExistsError("R1-3 output already exists; preserve earlier revision attempt")
    if (not (ROOT / ".gitignore").exists() or not str(OUT).startswith(str(REV))
            or subprocess.run(["git", "check-ignore", "-q", str(OUT / output_names[0])],
                              cwd=ROOT, check=False).returncode != 0):
        raise RuntimeError("unsafe R1-3 output location")
    spot_path = ROOT / old_config["canonical_daily_spot"]
    code_paths = [Path(__file__), ROOT / "src/futures/r1_alignment.py",
                  ROOT / "src/futures/continuous_contract.py",
                  ROOT / "src/futures/spot_futures.py"]
    inputs = [config_path, phase_path, FREEZE, spot_path, *FILES.values(), *code_paths]
    before = {path.relative_to(ROOT).as_posix(): sha256(path) for path in inputs}
    if before[FREEZE.relative_to(ROOT).as_posix()] != old_config["data_freeze_sha256"]:
        raise RuntimeError("Data Freeze mismatch")
    preflight = json.loads((REV / "preflight/inputs_before.json").read_text())
    old_hashes = {item["path"]: item["sha256"] for item in preflight["old_result_files"]}
    for label, path in FILES.items():
        relative = path.relative_to(ROOT).as_posix()
        if before[relative] != old_hashes.get(relative):
            raise RuntimeError(f"old Phase 2I input changed since R1-0: {label}")
    daily_contracts = pd.read_csv(FILES["contract_daily"])
    ex_post = pd.read_csv(FILES["expost_main"])
    ex_post["date"] = pd.to_datetime(ex_post.date)
    reconstructed = add_roll_safe_returns(select_daily_main_contract(
        daily_contracts, start_date=config["analysis_start_date"],
        end_date=config["sample_end"]), daily_contracts)
    if (not ex_post.date.equals(reconstructed.date)
            or not ex_post.main_contract.equals(reconstructed.main_contract)
            or not np.allclose(ex_post.main_close, reconstructed.main_close, rtol=0, atol=1e-10)
            or not np.allclose(ex_post.roll_safe_log_return,
                               reconstructed.roll_safe_log_return, equal_nan=True, rtol=0, atol=1e-12)):
        raise RuntimeError("stored ex-post main does not replay from daily contracts")
    lagged = select_lagged_volume_main_contract(
        daily_contracts, start_date=config["analysis_start_date"],
        end_date=config["sample_end"])
    if not ex_post.date.equals(lagged.date):
        raise RuntimeError("lagged main does not retain the complete futures trading calendar")
    daily_spot, reconciliation, spot_audit = reconcile_canonical_daily_spot(
        spot_path, FREEZE, sample_end=config["sample_end"],
        absolute_tolerance=old_config["daily_spot_monthly_absolute_tolerance"])
    if spot_audit["status"] != "PASS":
        raise RuntimeError("canonical SMM daily spot provenance failed")
    daily_spot = daily_spot.loc[daily_spot.date.ge(pd.Timestamp(config["analysis_start_date"]))]
    rules = {"EX_POST_DESCRIPTIVE_MAIN": ex_post, "LAGGED_VOLUME_MAIN": lagged}
    intervals_all, eom_all, mean_all, daily_all, comparisons = [], [], [], [], []
    for main_rule, main in rules.items():
        kwargs = {"analysis_start_date": config["analysis_start_date"],
                  "sample_end": config["sample_end"]}
        intervals = build_interval_audit(main, daily_spot, **kwargs)
        eom = build_monthly_matched_eom(intervals, main, daily_spot, **kwargs)
        mean = build_monthly_matched_mean(main, daily_spot,
                                          partial_listing_month=config["partial_listing_month"],
                                          **kwargs)
        for table in (intervals, eom, mean):
            table.insert(0, "main_rule", main_rule)
        intervals_all.append(intervals)
        eom_all.append(eom)
        mean_all.append(mean)
        eligible = intervals.loc[intervals.eligibility_reason.eq("ELIGIBLE_SINGLE_SESSION")].copy()
        daily_all.append(eligible)
        for table, specification, frequency, key, lags in (
            (eom, "MATCHED_EOM_PRIMARY", "monthly", "month", config["monthly_lags"]),
            (mean, "MATCHED_MONTHLY_MEAN_SECONDARY", "monthly", "month", config["monthly_lags"]),
            (intervals, "DAILY_MATCHED_INTERVAL_PRIMARY", "daily", "date", config["daily_lags"]),
        ):
            add_comparison(comparisons, table, specification=specification,
                           main_rule=main_rule, frequency=frequency, key=key,
                           future="futures_log_return", spot="spot_log_return",
                           switches="roll_flag", lags=lags,
                           calendar_index=ex_post.date if frequency == "daily" else None)
        # Return-pair means include either month's main switch and are kept
        # separate from the all-month inference instead of silently discarded.
        for stratum, selected in (("SWITCH_WINDOW", True), ("NO_SWITCH_WINDOW", False)):
            stratified = mean.copy()
            stratified.loc[stratified.switch_window_flag.ne(selected),
                           "futures_log_return"] = np.nan
            add_comparison(comparisons, stratified,
                           specification="MATCHED_MONTHLY_MEAN_SECONDARY",
                           main_rule=main_rule, frequency="monthly", key="month",
                           future="futures_log_return", spot="spot_log_return",
                           switches="roll_flag", lags=config["monthly_lags"], stratum=stratum)
    legacy = pd.read_csv(FILES["legacy_monthly"])
    legacy["roll_flag"] = legacy.switch_count.gt(0)
    add_comparison(comparisons, legacy,
                   specification="LEGACY_MISMATCHED_TEMPORAL_AGGREGATION",
                   main_rule="EX_POST_DESCRIPTIVE_MAIN", frequency="monthly", key="month",
                   future="futures_monthly_return", spot="spot_monthly_return",
                   switches="roll_flag", lags=config["monthly_lags"])
    comparison = pd.concat(comparisons, ignore_index=True)
    for rule in rules:
        monthly = comparison.loc[comparison.specification.eq("MATCHED_MONTHLY_MEAN_SECONDARY")
                                 & comparison.main_rule.eq(rule)]
        for lag in config["monthly_lags"]:
            rows = monthly.loc[monthly.lag_spot_periods.eq(lag)]
            all_n = int(rows.loc[rows.stratum.eq("ALL"), "n"].iloc[0])
            stratified_n = int(rows.loc[rows.stratum.ne("ALL"), "n"].sum())
            if all_n != stratified_n:
                raise RuntimeError(f"switch/no-switch monthly-mean sample partition failed: {rule}/{lag}")
    old_lags = pd.read_csv(FILES["legacy_lags"])
    old_month = old_lags.loc[old_lags.frequency.eq("monthly")
                             & old_lags.lag_spot_periods.eq(1)].iloc[0]
    old_day = old_lags.loc[old_lags.frequency.str.startswith("daily")
                           & old_lags.lag_spot_periods.eq(1)].iloc[0]
    replay = _lag_row(comparison, "LEGACY_MISMATCHED_TEMPORAL_AGGREGATION",
                      "EX_POST_DESCRIPTIVE_MAIN")
    if (int(replay.n) != int(old_month.n)
            or not np.isclose(replay.pearson, old_month.pearson, atol=1e-12, rtol=0)):
        raise RuntimeError("legacy +1 correlation did not replay")
    classification, evidence = classify_leading_evidence(
        comparison, float(old_month.pearson), float(old_day.pearson),
        config["material_absolute_correlation_change"],
        config["minimum_correlation_pairs"])
    claims = []
    for label, old in (("MONTHLY_LAG_PLUS_ONE", old_month), ("DAILY_LAG_PLUS_ONE", old_day)):
        spec = "MATCHED_EOM_PRIMARY" if label.startswith("MONTHLY") else "DAILY_MATCHED_INTERVAL_PRIMARY"
        x = _lag_row(comparison, spec, "EX_POST_DESCRIPTIVE_MAIN")
        z = _lag_row(comparison, spec, "LAGGED_VOLUME_MAIN")
        claims.append({"claim": label, "legacy_pearson": float(old.pearson),
                       "legacy_n": int(old.n), "matched_ex_post_pearson": float(x.pearson),
                       "matched_ex_post_n": int(x.n), "matched_lagged_main_pearson": float(z.pearson),
                       "matched_lagged_main_n": int(z.n),
                       "overall_revision_class": classification,
                       "limitation": "exploratory_multi_lag_not_ex_ante_discovery"})
    input_after = {path.relative_to(ROOT).as_posix(): sha256(path) for path in inputs}
    if before != input_after:
        raise RuntimeError("R1-3 input files changed during processing")
    registry = {
        "revision": "R1-3", "sample_start": config["analysis_start_date"],
        "sample_end": config["sample_end"], "lag_convention": "positive=futures(t)_vs_spot(t+lag)",
        "source_commit_before_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "specifications": {
            "LEGACY_MISMATCHED_TEMPORAL_AGGREGATION": "spot diff(log monthly mean price); futures within-month roll-safe daily-return sum; not temporally matched",
            "MATCHED_EOM_PRIMARY": "spot log shared current/previous month-end endpoint price ratio; futures roll-safe daily returns summed between identical endpoints",
            "MATCHED_MONTHLY_MEAN_SECONDARY": "both markets diff(log comparable full-month arithmetic price means); raw main-price mean includes contract-level switch effects",
            "DAILY_MATCHED_INTERVAL_PRIMARY": "both returns over same consecutive verified futures trading sessions; multi-session SMM gaps diagnostic only",
        },
        "main_rules": {
            "EX_POST_DESCRIPTIVE_MAIN": "same-day volume, known only after that day; descriptive, not pre-day executable",
            "LAGGED_VOLUME_MAIN": "t-1 volume and known expiry select t contract; close-to-close t-1 to t return is not itself an executable strategy after final t-1 volume is observed",
        },
        "partial_listing_month": config["partial_listing_month"],
        "spot_provenance_audit": {key: str(value) if isinstance(value, pd.Timestamp) else value
                                   for key, value in spot_audit.items()},
        "spot_monthly_reconciliation_rows": len(reconciliation),
        "old_cointegration_gate": pd.read_csv(FILES["cointegration"]).gate_status.iloc[0],
        "cointegration_interpretation": "not justified by this sample/I(1) gate, not proof of no long-run relation",
        "multiple_lag_interpretation": "exploratory descriptive family; no p-values claimed, no ex-ante lag-one discovery",
        "monthly_mean_stratification": "condition on the futures return interval's current-or-prior-month contract switch; target spot month is not separately required to share that stratum",
        "basis_rule": "only real price levels may define CNY basis; return index is not a price",
        "classification": classification,
        "classification_evidence": evidence,
        "classification_rule": config["claim_rule_note"],
        "input_sha256_before": before,
        "input_sha256_after": input_after,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    pd.concat(intervals_all, ignore_index=True).to_csv(OUT / output_names[1], index=False)
    pd.concat(eom_all, ignore_index=True).to_csv(OUT / output_names[2], index=False)
    pd.concat(mean_all, ignore_index=True).to_csv(OUT / output_names[3], index=False)
    pd.concat(daily_all, ignore_index=True).to_csv(OUT / output_names[4], index=False)
    lagged.to_csv(OUT / output_names[5], index=False)
    comparison.to_csv(OUT / output_names[6], index=False)
    pd.DataFrame(claims).to_csv(OUT / output_names[7], index=False)
    registry["output_sha256"] = {name: sha256(OUT / name) for name in output_names[1:]}
    (OUT / output_names[0]).write_text(json.dumps(registry, indent=2, ensure_ascii=False,
                                                 default=str), encoding="utf-8")
    print(json.dumps({"classification": classification, "rows_interval": sum(map(len, intervals_all)),
                      "rows_eom": sum(map(len, eom_all)), "rows_mean": sum(map(len, mean_all)),
                      "rows_daily_eligible": sum(map(len, daily_all)),
                      "rows_comparison": len(comparison)}, indent=2), flush=True)
    return registry


if __name__ == "__main__":
    run()
