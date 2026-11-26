"""Inventory and extract the two protected industry workbooks to interim CSVs."""
from __future__ import annotations

import re
from datetime import date, datetime

import numpy as np
import openpyxl
import pandas as pd
from openpyxl.utils import get_column_letter

from industry_common import (
    BATTERY_FILE,
    INTERIM_DIR,
    LITHIUM_FILE,
    METADATA_DIR,
    ROOT,
    ensure_dirs,
    sha256,
    write_csv,
)


def _date_value(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return None


def _frequency(dates: list[datetime]) -> str:
    if len(dates) < 2:
        return "UNKNOWN"
    ordered = sorted(set(dates))
    gaps = np.diff([item.toordinal() for item in ordered])
    median = float(np.median(gaps))
    if median <= 3:
        return "DAILY"
    if median <= 10:
        return "WEEKLY"
    if median <= 40:
        return "MONTHLY"
    return "IRREGULAR"


def inventory_workbooks() -> pd.DataFrame:
    records = []
    keywords = {
        "lc_spot": ("碳酸锂", "价格"),
        "lc_output": ("碳酸锂", "产量"),
        "spodumene_price": ("锂辉石", "价格"),
        "battery_install": ("动力电池", "装机", "装车"),
        "inventory": ("库存",),
        "cost_margin": ("成本", "利润", "毛利"),
        "trade": ("进出口", "进口", "出口"),
    }
    for path in (LITHIUM_FILE, BATTERY_FILE):
        workbook = openpyxl.load_workbook(path, read_only=False, data_only=True)
        for sheet in workbook.worksheets:
            text_cells = []
            date_by_col: dict[int, list[tuple[int, datetime]]] = {}
            for row in sheet.iter_rows():
                for cell in row:
                    value = cell.value
                    parsed = _date_value(value)
                    if parsed is not None:
                        date_by_col.setdefault(cell.column, []).append((cell.row, parsed))
                    elif isinstance(value, str) and value.strip():
                        text_cells.append((cell.row, cell.coordinate, value.strip()))
            date_column = None
            dated = []
            if date_by_col:
                date_column, dated = max(date_by_col.items(), key=lambda item: len(item[1]))
            first_data_row = min((row for row, _ in dated), default=None)
            dates = [value for _, value in dated]
            sample_text = " | ".join(value for _, _, value in text_cells[:150])
            candidates = []
            for canonical, terms in keywords.items():
                if canonical == "battery_install":
                    if "动力电池" in sample_text and ("装机" in sample_text or "装车" in sample_text):
                        candidates.append(canonical)
                elif all(term in sample_text for term in terms[:2]):
                    candidates.append(canonical)
                elif len(terms) == 1 and terms[0] in sample_text:
                    candidates.append(canonical)
            source_notes = [value for _, _, value in text_cells if "来源" in value][:3]
            unit_notes = [value for _, _, value in text_cells if "单位" in value or re.search(r"[（(].*(吨|GWh|美元|元/吨).*[）)]", value)][:5]
            footnotes = [value for _, _, value in text_cells if value.startswith(("注", "*"))][:3]
            hidden_cols = [letter for letter, dim in sheet.column_dimensions.items() if dim.hidden]
            records.append(
                {
                    "file_name": path.name,
                    "sheet_name": sheet.title,
                    "n_rows": sheet.max_row,
                    "n_cols": sheet.max_column,
                    "first_data_row": first_data_row,
                    "date_column": get_column_letter(date_column) if date_column else "",
                    "date_start": min(dates).date().isoformat() if dates else "",
                    "date_end": max(dates).date().isoformat() if dates else "",
                    "frequency_guess": _frequency(dates),
                    "source_note": " | ".join(source_notes),
                    "unit_note": " | ".join(unit_notes),
                    "candidate_variables": ";".join(candidates),
                    "status": "RELEVANT" if candidates else "INVENTORIED",
                    "notes": f"header_rows=1-{first_data_row - 1 if first_data_row else 'unresolved'}; merged_ranges={len(sheet.merged_cells.ranges)}; hidden_columns={','.join(hidden_cols) or 'none'}; footnotes={' | '.join(footnotes) or 'none'}",
                }
            )
        workbook.close()
    return pd.DataFrame(records)


def _sheet_frame(workbook, sheet_name: str, min_row: int, min_col: int, max_col: int) -> pd.DataFrame:
    sheet = workbook[sheet_name]
    rows = list(sheet.iter_rows(min_row=min_row, min_col=min_col, max_col=max_col, values_only=True))
    return pd.DataFrame(rows)


def extract_lithium() -> None:
    workbook = openpyxl.load_workbook(LITHIUM_FILE, read_only=True, data_only=True)

    prices = _sheet_frame(workbook, "SMM钴锂新能源价格", 4, 2, 6)
    prices.columns = ["date", "lc_spot", "industrial_lc", "lithium_hydroxide", "spodumene_price"]
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    prices = prices.loc[prices.date.notna()].copy()
    for col in ("lc_spot", "spodumene_price"):
        prices[col] = pd.to_numeric(prices[col], errors="coerce")
    spot = prices[["date", "lc_spot"]].copy()
    spot["source"] = "SMM"
    spot["series_name"] = "碳酸锂（99.5%电池级/国产,元/吨）"
    spot["original_unit"] = "CNY/t"
    spot["currency"] = "CNY"
    spot["quality_flag"] = np.where(spot.lc_spot > 0, "OK", "ZERO_OR_MISSING")
    spot.loc[spot.lc_spot <= 0, "lc_spot"] = np.nan
    spot["date"] = spot.date.dt.strftime("%Y-%m-%d")
    write_csv(spot, INTERIM_DIR / "lc_spot_daily.csv")

    spod = prices[["date", "spodumene_price"]].copy()
    spod["source"] = "SMM"
    spod["series_name"] = "锂辉石精矿（6%,CIF中国,美元/吨）"
    spod["grade"] = "6% Li2O"
    spod["delivery_basis"] = "CIF China"
    spod["original_unit"] = "USD/t"
    spod["currency"] = "USD"
    spod["quality_flag"] = np.where(spod.spodumene_price > 0, "OK", "ZERO_PLACEHOLDER")
    spod.loc[spod.spodumene_price <= 0, "spodumene_price"] = np.nan
    spod["date"] = spod.date.dt.strftime("%Y-%m-%d")
    write_csv(spod, INTERIM_DIR / "spodumene_price_daily.csv")

    output = _sheet_frame(workbook, "SMM月度新能源金属材料产量", 8, 2, 8)
    output.columns = ["month", "lc_output_industrial", "lc_output_battery", "lc_output_brine", "lc_output_lepidolite", "lc_output_spodumene", "lc_output_total"]
    output["month"] = pd.to_datetime(output.month, errors="coerce")
    output = output.loc[output.month.notna()].copy()
    output["source"] = "SMM"
    output["unit"] = "metric tons"
    output["month"] = output.month.dt.to_period("M").astype(str)
    write_csv(output, INTERIM_DIR / "lc_output_monthly_raw.csv")

    inv = _sheet_frame(workbook, "SMM碳酸锂周度产量库存&天数", 3, 1, 46)
    inventory = pd.DataFrame({
        "date": pd.to_datetime(inv.iloc[:, 0], errors="coerce"),
        "lc_inventory_downstream": pd.to_numeric(inv.iloc[:, 1], errors="coerce"),
        "lc_inventory_smelter": pd.to_numeric(inv.iloc[:, 2], errors="coerce"),
        "lc_inventory_other": pd.to_numeric(inv.iloc[:, 3], errors="coerce"),
        "lc_inventory_total": pd.to_numeric(inv.iloc[:, 4], errors="coerce"),
        "route_date": pd.to_datetime(inv.iloc[:, 17], errors="coerce"),
        "lc_output_brine_weekly": pd.to_numeric(inv.iloc[:, 18], errors="coerce"),
        "lc_output_lepidolite_weekly": pd.to_numeric(inv.iloc[:, 19], errors="coerce"),
        "lc_output_spodumene_weekly": pd.to_numeric(inv.iloc[:, 20], errors="coerce"),
        "lc_output_total_weekly": pd.to_numeric(inv.iloc[:, 21], errors="coerce"),
    })
    inventory = inventory.loc[inventory.date.notna()].copy()
    inventory["source"] = "SMM"
    inventory["unit"] = "metric tons"
    inventory["date"] = inventory.date.dt.strftime("%Y-%m-%d")
    inventory["route_date"] = inventory.route_date.dt.strftime("%Y-%m-%d")
    write_csv(inventory, INTERIM_DIR / "lc_inventory_weekly_raw.csv")

    costs = _sheet_frame(workbook, "SMM锂冶炼利润", 2, 1, 5)
    costs.columns = ["date", "lc_cost_lepidolite", "lc_cost_spodumene", "lc_margin_lepidolite", "lc_margin_spodumene"]
    costs["date"] = pd.to_datetime(costs.date, errors="coerce")
    costs = costs.loc[costs.date.notna()].copy()
    costs["source"] = "SMM"
    costs["unit"] = "CNY/t lithium carbonate"
    costs["date"] = costs.date.dt.strftime("%Y-%m-%d")
    write_csv(costs, INTERIM_DIR / "lc_cost_margin_daily_raw.csv")

    trade = _sheet_frame(workbook, "中国碳酸锂进出口数据", 4, 2, 9)
    trade.columns = ["month", "lc_export_qty", "export_value_10k_cny", "export_unit_price_10k_cny_t", "lc_import_qty", "import_value_10k_cny", "import_unit_price_10k_cny_t", "lc_net_import_qty"]
    trade["month"] = pd.to_datetime(trade.month, errors="coerce")
    trade = trade.loc[trade.month.notna()].copy()
    trade["original_source"] = "China Customs"
    trade["unit"] = "metric tons"
    trade["month"] = trade.month.dt.to_period("M").astype(str)
    write_csv(trade, INTERIM_DIR / "lc_trade_monthly_raw.csv")

    concentrate = _sheet_frame(workbook, "中国锂矿进口数据(分国别)", 3, 1, 17)
    concentrate.columns = ["month", "lithium_concentrate_import_total", "lithium_concentrate_import_price_total", "lithium_concentrate_import_australia", "australia_price", "lithium_concentrate_import_brazil", "brazil_price", "lithium_concentrate_import_canada", "canada_price", "lithium_concentrate_import_nigeria", "nigeria_price", "lithium_concentrate_import_zimbabwe", "zimbabwe_price", "lithium_concentrate_import_rwanda", "rwanda_price", "lithium_chloride_import", "lithium_chloride_price"]
    concentrate["month"] = pd.to_datetime(concentrate.month, errors="coerce")
    concentrate = concentrate.loc[concentrate.month.notna()].copy()
    concentrate["original_source"] = "SMM; underlying customs definition not independently verified"
    concentrate["quantity_unit"] = "metric tons"
    concentrate["price_unit"] = "USD/t"
    concentrate["month"] = concentrate.month.dt.to_period("M").astype(str)
    write_csv(concentrate, INTERIM_DIR / "lithium_concentrate_import_monthly_raw.csv")
    workbook.close()


def _matrix_series(sheet, label: str) -> dict[str, float]:
    label_row = next(row for row in range(1, sheet.max_row + 1) if str(sheet.cell(row, 2).value).strip() == label)
    output = {}
    for row in range(label_row + 1, sheet.max_row + 1):
        year = sheet.cell(row, 2).value
        if isinstance(year, str) and row > label_row + 1 and (year.startswith("其中：") or "数据来源" in year):
            break
        if not isinstance(year, int):
            continue
        for month in range(1, 13):
            value = sheet.cell(row, month + 2).value
            if isinstance(value, (int, float)):
                output[f"{year:04d}-{month:02d}"] = float(value)
    return output


def extract_battery() -> None:
    workbook = openpyxl.load_workbook(BATTERY_FILE, read_only=True, data_only=True)
    sheet = workbook["全球&中国动力电池行业装机规模-月度"]
    total = _matrix_series(sheet, "中国（GWh）")
    ncm = _matrix_series(sheet, "其中：三元（GWh）")
    lfp = _matrix_series(sheet, "其中：铁锂（GWh）")
    months = sorted(set(total) | set(ncm) | set(lfp))
    frame = pd.DataFrame({
        "month": months,
        "battery_install_total": [total.get(month) for month in months],
        "battery_install_lfp": [lfp.get(month) for month in months],
        "battery_install_ncm": [ncm.get(month) for month in months],
    })
    frame["source"] = "China Automotive Power Battery Industry Innovation Alliance"
    frame["unit"] = "GWh"
    write_csv(frame, INTERIM_DIR / "battery_install_monthly_raw.csv")
    workbook.close()


def write_hash_ledger() -> None:
    rows = []
    for path in (LITHIUM_FILE, BATTERY_FILE):
        stat = path.stat()
        rows.append({
            "file": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path),
            "size": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
            "protected_status": "BASELINE_RECORDED",
        })
    write_csv(pd.DataFrame(rows), METADATA_DIR / "manual_industry_raw_hashes.csv")


def main() -> None:
    ensure_dirs()
    for path in (LITHIUM_FILE, BATTERY_FILE):
        if not path.exists():
            raise FileNotFoundError(path)
    write_hash_ledger()
    write_csv(inventory_workbooks(), METADATA_DIR / "manual_excel_sheet_inventory.csv")
    extract_lithium()
    extract_battery()


if __name__ == "__main__":
    main()
