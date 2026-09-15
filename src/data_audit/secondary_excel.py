"""Read-only audit helpers for the September 2026 secondary Excel delivery."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl
import pandas as pd


DONGWU_FILENAME = "【东吴电新数据库】锂电池材料价格周报-20260612.xlsx"
BATTERY_FILENAME = "动力电池行业数据库-20260819.xlsx"
DONGWU_SHA256 = "5DFD059C9224CF735BEF5A4B544B43C560A756220FBF7DDAF42A17A4D38966A2"
BATTERY_SHA256 = "E00614C96C88D3426FFE89FE75DE60124D3EFCEC8430DE06ED8D011A62C7AFF9"
V1_SHA256 = "9146B3C858AA0F1BE5FA59720B0446515F0A21C60FA032712F76DD248AEAB7F5"
UNIT_STATUS = "UNIT_INFERRED_WITH_HIGH_CONFIDENCE"
UNIT_CONVERSION = "raw × 10000 (万元/吨 to CNY/t)"

PUBLIC_SMM_MONTHLY = {
    "2025-10": 75291.18,
    "2025-11": 86457.50,
    "2026-01": 156000.00,
    "2026-02": 149600.00,
    "2026-03": 156700.00,
}


def _date_range(start: date, end: date) -> set[date]:
    return {start + timedelta(days=step) for step in range((end - start).days + 1)}


# Explicit calendar closures, not a generic weekday assumption. The dates reconcile
# the source-row calendar to the disclosed 2025-10 SMM monthly mean and explain the
# source workbook's later holiday gaps.
KNOWN_NON_QUOTE_DATES = (
    _date_range(date(2025, 10, 1), date(2025, 10, 8))
    | _date_range(date(2026, 1, 1), date(2026, 1, 2))
    | _date_range(date(2026, 2, 16), date(2026, 2, 23))
    | {date(2026, 4, 6)}
    | _date_range(date(2026, 5, 1), date(2026, 5, 5))
)


@dataclass(frozen=True)
class AuditPaths:
    root: Path

    @property
    def dongwu(self) -> Path:
        return self.root / "data" / DONGWU_FILENAME

    @property
    def battery(self) -> Path:
        return self.root / "data" / BATTERY_FILENAME


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def workbook_inventory(path: Path) -> dict:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheets = [sheet.title for sheet in workbook.worksheets]
    finally:
        workbook.close()
    stat = path.stat()
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "sha256": sha256(path),
        "modified_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "sheet_count": len(sheets),
        "sheet_names": ";".join(sheets),
        "access_mode": "READ_ONLY",
    }


def read_dongwu_spot(path: Path) -> tuple[pd.DataFrame, dict]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook["锂"]
        if sheet["F3"].value != "SMM电池级碳酸锂":
            raise ValueError("Expected Dongwu SMM battery-grade LC series was not found at 锂!F3")
        rows = []
        dated_rows = []
        for values in sheet.iter_rows(min_row=4, max_col=6, values_only=True):
            raw_date, raw_value = values[0], values[5]
            if isinstance(raw_date, datetime):
                raw_date = raw_date.date()
            if isinstance(raw_date, date):
                dated_rows.append((raw_date, raw_value))
                if raw_value is not None:
                    rows.append((raw_date, float(raw_value)))
    finally:
        workbook.close()
    frame = pd.DataFrame(rows, columns=["date", "raw_value"]).sort_values("date").reset_index(drop=True)
    first, last = frame.date.min(), frame.date.max()
    within = [(d, value) for d, value in dated_rows if first <= d <= last]
    metadata = {
        "source_label": "SMM (transcribed in Dongwu workbook)",
        "series_label": "SMM电池级碳酸锂",
        "unit_status": UNIT_STATUS,
        "raw_unit": "万元/吨 (inferred from overlap and workbook magnitude)",
        "conversion_rule": UNIT_CONVERSION,
        "date_column": "锂!A",
        "value_column": "锂!F",
        "first_date": first.isoformat(),
        "last_date": last.isoformat(),
        "observation_count": len(frame),
        "missing_count_within_coverage": sum(value is None for _, value in within),
        "duplicate_dates": int(frame.date.duplicated().sum()),
    }
    return frame, metadata


def quote_day_decision(day: date, canonical_dates: set[date], canonical_end: date) -> tuple[bool, bool, str]:
    """Apply the immutable canonical calendar in overlap, then explicit closures."""
    if day <= canonical_end:
        if day in canonical_dates:
            return True, day in KNOWN_NON_QUOTE_DATES, "CANONICAL_SMM_QUOTE_DATE"
        return False, day in KNOWN_NON_QUOTE_DATES, "EXCLUDED_BY_CANONICAL_SMM_QUOTE_CALENDAR"
    if day in KNOWN_NON_QUOTE_DATES:
        return False, True, "EXCLUDED_KNOWN_CHINA_HOLIDAY"
    if day.weekday() >= 5:
        return False, False, "EXCLUDED_WEEKEND"
    return True, False, "POST_CANONICAL_SOURCE_ROW_ON_EXPECTED_QUOTE_DAY"


def build_quote_calendar_audit(raw: pd.DataFrame, canonical_daily: pd.DataFrame) -> pd.DataFrame:
    canonical_dates = set(pd.to_datetime(canonical_daily["date"]).dt.date)
    canonical_end = max(canonical_dates)
    rows = []
    previous = None
    for record in raw.itertuples(index=False):
        effective, holiday, reason = quote_day_decision(record.date, canonical_dates, canonical_end)
        rows.append({
            "date": record.date.isoformat(),
            "raw_value": record.raw_value,
            "previous_value": previous,
            "same_as_previous": bool(previous is not None and record.raw_value == previous),
            "weekday": record.date.strftime("%A"),
            "holiday_flag_if_known": holiday,
            "effective_quote_day": effective,
            "decision_reason": reason,
        })
        previous = record.raw_value
    return pd.DataFrame(rows)


def match_status(canonical: float, candidate: float) -> str:
    difference = abs(candidate - canonical)
    relative = difference / abs(canonical) * 100
    if difference <= 1e-8:
        return "EXACT_MATCH"
    if relative <= 0.1:
        return "ROUNDING_MATCH"
    if relative <= 0.5:
        return "SMALL_DIFFERENCE"
    return "REVIEW_REQUIRED"


def build_spot_reconciliation(raw: pd.DataFrame, quote_audit: pd.DataFrame,
                              canonical_daily: pd.DataFrame) -> pd.DataFrame:
    source = raw.copy()
    source["date_text"] = source.date.map(date.isoformat)
    source = source.merge(
        quote_audit[["date", "effective_quote_day"]], left_on="date_text", right_on="date", how="left"
    ).drop(columns=["date_y"]).rename(columns={"date_x": "date"})
    source["month"] = source.date.map(lambda value: value.strftime("%Y-%m"))
    source["value_cny_t"] = source.raw_value * 10000.0

    canonical = canonical_daily.copy()
    canonical["date"] = pd.to_datetime(canonical.date).dt.date
    canonical["month"] = canonical.date.map(lambda value: value.strftime("%Y-%m"))
    rows = []
    for month in pd.period_range("2020-01", "2025-09", freq="M").astype(str):
        canonical_month = canonical.loc[canonical.month.eq(month)]
        source_month = source.loc[source.month.eq(month)]
        effective = source_month.loc[source_month.effective_quote_day]
        canonical_value = float(canonical_month.lc_spot.mean())
        dongwu_value = float(effective.value_cny_t.mean())
        rows.append(_reconciliation_row(
            month, canonical_value, dongwu_value, len(source_month), len(effective),
            "CANONICAL_SMM_QUOTE_DATE_SET",
        ))
    for month, canonical_value in PUBLIC_SMM_MONTHLY.items():
        source_month = source.loc[source.month.eq(month)]
        effective = source_month.loc[source_month.effective_quote_day]
        rows.append(_reconciliation_row(
            month, canonical_value, float(effective.value_cny_t.mean()), len(source_month), len(effective),
            "EXPLICIT_CHINA_HOLIDAY_CLOSURES_PLUS_SOURCE_ROWS",
        ))
    return pd.DataFrame(rows)


def _reconciliation_row(month: str, canonical_value: float, dongwu_value: float,
                        raw_count: int, effective_count: int, rule: str) -> dict:
    difference = dongwu_value - canonical_value
    return {
        "month": month,
        "canonical_value": canonical_value,
        "dongwu_monthly_value": dongwu_value,
        "difference": difference,
        "abs_difference": abs(difference),
        "relative_difference_pct": difference / canonical_value * 100,
        "n_raw_rows": raw_count,
        "n_effective_quote_days": effective_count,
        "calendar_rule": rule,
        "match_status": match_status(canonical_value, dongwu_value),
    }


def expected_quote_dates(month: str) -> set[date]:
    period = pd.Period(month, freq="M")
    first = period.start_time.date()
    last = period.end_time.date()
    return {
        first + timedelta(days=offset)
        for offset in range((last - first).days + 1)
        if (first + timedelta(days=offset)).weekday() < 5
        and first + timedelta(days=offset) not in KNOWN_NON_QUOTE_DATES
    }


def build_spot_candidates(raw: pd.DataFrame, quote_audit: pd.DataFrame) -> pd.DataFrame:
    audit = quote_audit.set_index("date")
    rows = []
    for month in ("2025-12", "2026-04", "2026-05", "2026-06"):
        subset = raw.loc[raw.date.map(lambda value: value.strftime("%Y-%m") == month)].copy()
        subset["effective"] = subset.date.map(lambda value: bool(audit.loc[value.isoformat(), "effective_quote_day"]))
        effective = subset.loc[subset.effective]
        observed = set(effective.date)
        expected = expected_quote_dates(month)
        complete = observed == expected
        coverage = "FULL_MONTH_CANDIDATE" if complete else "PARTIAL_MONTH"
        decision = "ACCEPTABLE_WITH_REVIEW" if complete else "PARTIAL_MONTH_DO_NOT_USE"
        rows.append({
            "month": month,
            "value_cny_t": float(effective.raw_value.mean() * 10000),
            "raw_mean": float(effective.raw_value.mean()),
            "unit_conversion": UNIT_CONVERSION,
            "n_effective_quote_days": len(effective),
            "source_file": DONGWU_FILENAME,
            "sheet": "锂",
            "source_series": "SMM电池级碳酸锂",
            "coverage_status": coverage,
            "reconciliation_status": "HIGH_QUALITY_TRANSCRIPTION_WITH_REVIEW",
            "decision": decision,
            "notes": (
                "Complete quote calendar; promotion awaits direct unit confirmation and review of >0.5% benchmark differences"
                if complete else "Workbook ends 2026-06-12; partial month cannot be promoted"
            ),
        })
    return pd.DataFrame(rows)


def _find_year_row(sheet, anchor: str, year: int) -> int:
    anchor_row = next(
        row[0].row
        for row in sheet.iter_rows(min_col=2, max_col=2)
        if str(row[0].value).strip() == anchor
    )
    for row in range(anchor_row + 1, min(anchor_row + 15, sheet.max_row) + 1):
        if sheet.cell(row, 2).value == year:
            return row
    raise ValueError(f"Year {year} not found after {anchor}")


def read_battery_install(path: Path) -> dict[str, dict[str, float]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook["全球&中国动力电池行业装机规模-月度"]
        anchors = {
            "total": "中国（GWh）",
            "ncm": "其中：三元（GWh）",
            "lfp": "其中：铁锂（GWh）",
        }
        result = {}
        for name, anchor in anchors.items():
            row = _find_year_row(sheet, anchor, 2026)
            result[name] = {
                f"2026-{month:02d}": float(sheet.cell(row, month + 2).value)
                for month in range(1, 8)
            }
    finally:
        workbook.close()
    return result


def build_battery_reconciliation(battery: dict[str, dict[str, float]], existing: pd.DataFrame) -> pd.DataFrame:
    existing = existing.set_index("month")
    rows = []
    for month in pd.period_range("2026-03", "2026-07", freq="M").astype(str):
        total, lfp, ncm = battery["total"][month], battery["lfp"][month], battery["ncm"][month]
        component_sum = lfp + ncm
        has_existing = month in existing.index
        existing_total = float(existing.loc[month, "battery_install_total"]) if has_existing else None
        difference = total - existing_total if has_existing else None
        rows.append({
            "month": month,
            "workbook_total_gwh": total,
            "workbook_lfp_gwh": lfp,
            "workbook_ncm_gwh": ncm,
            "lfp_plus_ncm_gwh": component_sum,
            "implied_other_or_rounding_gwh": total - component_sum,
            "existing_total_gwh": existing_total,
            "difference_vs_existing_gwh": difference,
            "total_reconciliation_status": "EXACT_MATCH" if has_existing and abs(difference) <= 1e-12 else "NEW_TAIL_CANDIDATE",
            "chemistry_reconciliation_status": (
                "EXACT_COMPONENT_SUM" if abs(total - component_sum) <= 1e-12
                else "OTHER_CHEMISTRIES_OR_ROUNDING"
            ),
        })
    return pd.DataFrame(rows)


def battery_auxiliary_catalog(path: Path) -> dict:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        production = workbook["中国锂电池产量规模"]
        catalog = {}
        for label in ("动力和储能电池合计产量", "三元电池产量", "铁锂电池产量"):
            row = _find_year_row(production, label, 2026)
            values = [production.cell(row, month + 2).value for month in range(1, 8)]
            catalog[label] = {
                "coverage": "2026-01—2026-07", "unit": "GWh",
                "observations": len([value for value in values if value is not None]), "usage": "ROBUSTNESS",
            }
        average = workbook["中国新能源单车平均带电量"]
        headers = [average.cell(2, column).value for column in range(3, 10)]
        catalog["单车平均带电量"] = {
            "coverage": "2026-01—2026-07", "unit": "kWh",
            "observations": 7, "usage": "MECHANISM_SUPPORT / ROBUSTNESS",
            "metric_type": "CUMULATIVE_YTD_METRIC" if all("平均带电量" in str(value) for value in headers) else "REVIEW_REQUIRED",
        }
        return catalog
    finally:
        workbook.close()


def search_valid_series(paths: list[Path]) -> tuple[list[dict], list[dict]]:
    sc6_hits, output_hits = [], []
    sc6_terms = ("锂辉石", "精矿", "sc6", "cif", "li2o")
    output_terms = ("中国碳酸锂总产量", "smm碳酸锂产量", "碳酸锂产量")
    for path in paths:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row, max_col=min(sheet.max_column, 100)):
                    for cell in row:
                        text = "" if cell.value is None else str(cell.value).lower()
                        if any(term in text for term in sc6_terms):
                            sc6_hits.append({"file": path.name, "sheet": sheet.title, "cell": cell.coordinate, "text": str(cell.value)})
                        if any(term in text for term in output_terms):
                            output_hits.append({"file": path.name, "sheet": sheet.title, "cell": cell.coordinate, "text": str(cell.value)})
        finally:
            workbook.close()
    return sc6_hits, output_hits


def build_gap_status() -> pd.DataFrame:
    rows = [
        {
            "variable": "lc_spot", "target_end": "2026-06",
            "months_missing_before": "2025-12;2026-04;2026-05;2026-06",
            "new_candidates": "2025-12;2026-04;2026-05",
            "accepted_secondary": "",
            "still_missing": "2025-12;2026-04;2026-05;2026-06",
            "canonical_status": "V1_UNCHANGED; SECONDARY_CANDIDATES_REQUIRE_REVIEW",
            "next_action": "Confirm unit directly and review known-month differences; obtain complete 2026-06 month",
        },
        {
            "variable": "spodumene_price", "target_end": "2026-06",
            "months_missing_before": "2025-10;2025-11;2025-12;2026-01;2026-02;2026-04;2026-05;2026-06",
            "new_candidates": "", "accepted_secondary": "",
            "still_missing": "2025-10;2025-11;2025-12;2026-01;2026-02;2026-04;2026-05;2026-06",
            "canonical_status": "NO_MATCHING_SC6_CIF_CHINA_SERIES",
            "next_action": "Obtain definition-matched SMM SC6 CIF China export",
        },
        {
            "variable": "lc_output", "target_end": "2026-06",
            "months_missing_before": "2025-10;2025-11;2025-12;2026-03;2026-04;2026-05;2026-06",
            "new_candidates": "", "accepted_secondary": "",
            "still_missing": "2025-10;2025-11;2025-12;2026-03;2026-04;2026-05;2026-06",
            "canonical_status": "NO_CANONICAL_OUTPUT_FILL",
            "next_action": "Obtain exact monthly SMM China total LC output series",
        },
        {
            "variable": "battery_install", "target_end": "2026-06",
            "months_missing_before": "", "new_candidates": "2026-07",
            "accepted_secondary": "2026-03;2026-04;2026-05;2026-06", "still_missing": "",
            "canonical_status": "COMPLETE_THROUGH_2026-06; JULY_CANDIDATE_ONLY",
            "next_action": "Retain 2026-07 outside Data Freeze v1 and register for a future candidate panel",
        },
    ]
    return pd.DataFrame(rows)
