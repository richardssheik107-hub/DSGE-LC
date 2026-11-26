from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROBUSTNESS = ROOT / "data" / "processed" / "robustness"
VALIDATION = ROOT / "data" / "processed" / "validation"
METADATA = ROOT / "data" / "metadata"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def months(start: tuple[int, int], end: tuple[int, int]) -> list[str]:
    y, m = start
    out = []
    while (y, m) <= end:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


MYSTEEL_URLS = {
    "2025-01": "https://xny.mysteel.com/a/25021017/5D6DC08872AD6070.html",
    "2025-06": "https://xny.m.mysteel.com/a/25081117/0D2EA61EA397F455_abc.html",
    "2025-07": "https://xny.m.mysteel.com/a/25081117/0D2EA61EA397F455_abc.html",
    "2025-08": "https://xny.m.mysteel.com/a/25091017/0CDF9FB14D61BEE9_abc.html",
    "2025-09": "https://xny.mysteel.com/a/25101110/A248DFB91BB1025E.html",
    "2025-12": "https://xny.mysteel.com/a/26021308/77F1B425A1185750.html",
    "2026-01": "https://xny.mysteel.com/a/26021308/77F1B425A1185750.html",
    "2026-03": "https://xny.mysteel.com/a/26051214/AF52D7031628451A.html",
    "2026-04": "https://xny.mysteel.com/a/26051214/AF52D7031628451A.html",
    "2026-05": "https://m.mysteel.com/hot/1598883.html",
}

# Values are official Mysteel monthly-table observations. Lithium-carbonate
# values in ten-thousand CNY/t are converted to CNY/t by multiplying by 10,000.
MYSTEEL_PRICES = {
    "2025-01": (76400, 871, "OK"),
    "2025-06": (60600, 616, "OK"),
    "2025-07": (66500, 735, "OK"),
    "2025-08": (77500, 892, "OK"),
    "2025-09": (73400, 833, "OK"),
    "2025-12": (102500, 1342, "OK"),
    # The same report also states 154,400 CNY/t and 2,157.25 USD/t in prose.
    "2026-01": (152700, 2136, "INTRA_SOURCE_CONFLICT_REVIEW; LEVEL_JUMP_REVIEW"),
    "2026-03": (156200, 2178, "OK"),
    "2026-04": (166600, 2372, "OK"),
    "2026-05": (186100, None, "LC_ONLY_SECONDARY_MYSTEEL_INDEX_PAGE"),
}


def build_mysteel_prices() -> list[dict]:
    rows = []
    for month in months((2025, 1), (2026, 6)):
        lc, spod, flag = MYSTEEL_PRICES.get(month, (None, None, "NOT_AVAILABLE"))
        url = MYSTEEL_URLS.get(month, "")
        rows.append({
            "month": month,
            "lc_spot_mysteel": "" if lc is None else lc,
            "spodumene_mysteel": "" if spod is None else spod,
            "lc_spot_statistic": "MONTHLY_MEAN" if lc is not None else "NA",
            "spodumene_statistic": "MONTHLY_MEAN" if spod is not None else "NA",
            "source_url_lc": url if lc is not None else "",
            "source_url_spodumene": url if spod is not None else "",
            "source_grade": "SOURCE_A" if url and "mysteel.com/a/" in url else ("SOURCE_B" if url else ""),
            "quality_flag": flag,
        })
    write_csv(
        ROBUSTNESS / "mysteel_price_monthly.csv",
        ["month", "lc_spot_mysteel", "spodumene_mysteel", "lc_spot_statistic",
         "spodumene_statistic", "source_url_lc", "source_url_spodumene", "source_grade", "quality_flag"],
        rows,
    )
    return rows


def reconcile(prices: list[dict]) -> list[dict]:
    core = {r["month"]: r for r in read_csv(ROOT / "data" / "processed" / "core_monthly_panel.csv")}
    rows = []
    for variable, core_name, mysteel_name, definition in [
        ("lc_spot", "lc_spot", "lc_spot_mysteel", "PARTIAL_MATCH: SMM assessment vs Mysteel ex-factory tax-included"),
        ("spodumene_price", "spodumene_price", "spodumene_mysteel", "MATCH: SC6 Li2O CIF China USD/t"),
    ]:
        pairs = []
        variable_rows = []
        for item in prices:
            smm_raw = core.get(item["month"], {}).get(core_name, "")
            mysteel_raw = item[mysteel_name]
            both = bool(smm_raw and mysteel_raw)
            if both:
                smm = float(smm_raw)
                mysteel = float(mysteel_raw)
                diff = mysteel - smm
                diff_pct = diff / smm
                pairs.append((smm, mysteel, diff, diff_pct))
            else:
                smm = float(smm_raw) if smm_raw else None
                mysteel = float(mysteel_raw) if mysteel_raw else None
                diff = diff_pct = None
            variable_rows.append({
                "variable": variable,
                "month": item["month"],
                "smm_value": "" if smm is None else smm,
                "mysteel_value": "" if mysteel is None else mysteel,
                "difference": "" if diff is None else round(diff, 6),
                "difference_pct": "" if diff_pct is None else round(diff_pct, 8),
                "both_available": str(both).upper(),
                "definition_match": "TRUE" if variable == "spodumene_price" else "PARTIAL",
                "notes": definition,
                "mean_difference": "",
                "median_difference": "",
                "mape": "",
                "correlation": "",
            })
        if pairs:
            variable_rows[0]["mean_difference"] = round(statistics.mean(p[2] for p in pairs), 6)
            variable_rows[0]["median_difference"] = round(statistics.median(p[2] for p in pairs), 6)
            variable_rows[0]["mape"] = round(statistics.mean(abs(p[3]) for p in pairs), 8)
            xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
            if len(pairs) >= 2 and statistics.pstdev(xs) and statistics.pstdev(ys):
                mx, my = statistics.mean(xs), statistics.mean(ys)
                covariance = statistics.mean((x - mx) * (y - my) for x, y in zip(xs, ys))
                variable_rows[0]["correlation"] = round(covariance / (statistics.pstdev(xs) * statistics.pstdev(ys)), 8)
        rows.extend(variable_rows)
    write_csv(
        METADATA / "smm_mysteel_price_reconciliation.csv",
        ["variable", "month", "smm_value", "mysteel_value", "difference", "difference_pct",
         "both_available", "definition_match", "notes", "mean_difference", "median_difference", "mape", "correlation"],
        rows,
    )
    return rows


COST_MARGIN = [
    ("2025-01-24", 96700, -19250, "https://xny.mysteel.com/a/25012415/9120AE14D7F9D518.html", "2025-01-24"),
    ("2025-02-28", 95700, -20036, "https://xny.mysteel.com/a/25022815/28FBBC81419987C4.html", "2025-02-28"),
    ("2025-06-27", 60900, -298, "https://xny.mysteel.com/a/25062717/F687E9B301F8FDA8.html", "2025-06-27"),
    ("2025-10-17", 72500, 713, "https://xny.mysteel.com/a/25101723/C790BE300B7B2925.html", "2025-10-17"),
    ("2025-12-05", 94100, -568.29, "https://xny.mysteel.com/a/25120523/B90CC1D74DF4777C.html", "2025-12-05"),
    ("2025-12-12", 101000, -7400, "https://xny.mysteel.com/a/25121416/C56A57FCEF3FC683.html", "2025-12-14"),
    ("2025-12-26", 123700, -3200, "https://xny.mysteel.com/a/25122618/B40C943F6CC5BF54.html", "2025-12-26"),
    ("2026-01-04", 123700, -3200, "https://xny.mysteel.com/a/26010608/D7E3D7258C4B72A2.html", "2026-01-06"),
    ("2026-01-16", 156200, 5800, "https://xny.mysteel.com/a/26011622/1D45A807FB973518.html", "2026-01-16"),
    ("2026-01-30", 137500, 2700, "https://xny.mysteel.com/a/26013018/3AE30B3131B94EA8.html", "2026-01-30"),
    ("2026-02-06", 137000, 1300, "https://xny.mysteel.com/a/26020617/F6D4D31A02D1845E.html", "2026-02-06"),
    ("2026-03-20", 155300, -2300, "https://xny.mysteel.com/a/26032021/C812202935563DBD.html", "2026-03-20"),
]


def build_cost_margin() -> tuple[list[dict], list[dict]]:
    weekly = [{
        "date": d,
        "lc_cost_spodumene_mysteel": cost,
        "lc_margin_spodumene_mysteel": margin,
        "source_url": url,
        "source_date": source_date,
        "definition": "Mysteel disclosed Australian SC6 route lithium-carbonate cost and spot profit; CNY/t LC",
        "quality_flag": "OK",
    } for d, cost, margin, url, source_date in COST_MARGIN]
    write_csv(
        VALIDATION / "mysteel_spodumene_route_cost_margin_weekly.csv",
        ["date", "lc_cost_spodumene_mysteel", "lc_margin_spodumene_mysteel", "source_url",
         "source_date", "definition", "quality_flag"], weekly,
    )
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in weekly:
        grouped[row["date"][:7]].append(row)
    monthly = []
    for month, items in sorted(grouped.items()):
        costs = [float(x["lc_cost_spodumene_mysteel"]) for x in items]
        margins = [float(x["lc_margin_spodumene_mysteel"]) for x in items]
        eom = max(items, key=lambda x: x["date"])
        monthly.append({
            "month": month,
            "cost_mean": round(statistics.mean(costs), 6),
            "cost_median": round(statistics.median(costs), 6),
            "cost_eom": eom["lc_cost_spodumene_mysteel"],
            "margin_mean": round(statistics.mean(margins), 6),
            "margin_median": round(statistics.median(margins), 6),
            "margin_eom": eom["lc_margin_spodumene_mysteel"],
            "weekly_obs": len(items),
            "quality_flag": "OK",
        })
    write_csv(
        VALIDATION / "mysteel_spodumene_route_cost_margin_monthly.csv",
        ["month", "cost_mean", "cost_median", "cost_eom", "margin_mean", "margin_median", "margin_eom", "weekly_obs", "quality_flag"],
        monthly,
    )
    return weekly, monthly


IMPORTS = [
    ("2025-10", 652000, 531000, None, "DIRECT_SMM_VALUE", "https://www.hicend.com/ftpfile/static/file/upload/file/202512/07/5wB3osQQnC6gALb5.pdf", "SOURCE_C", "ACCEPTABLE_WITH_REVIEW"),
    ("2025-11", 729000, 678000, 0.93, "DIRECT_SMM_VALUE", "https://news.smm.cn/news/103685276", "SOURCE_A", "ACCEPTED"),
    ("2025-12", 788500, 628000, 0.80, "DIRECT_SMM_VALUE", "https://news.smm.cn/news/103734442", "SOURCE_A", "ACCEPTED"),
    ("2026-01", 832000, 636000, 0.76, "DIRECT_SMM_VALUE", "https://news.smm.cn/news/103818016", "SOURCE_A", "ACCEPTED"),
    ("2026-02", 558000, 438000, 0.79, "DIRECT_SMM_VALUE", "https://news.smm.cn/news/103818016", "SOURCE_A", "ACCEPTED"),
    ("2026-03", 837400, 602928, 0.72, "DERIVED_FROM_SMM_SHARE", "https://news.smm.cn/news/103877072", "SOURCE_A", "ACCEPTED_DERIVED"),
    ("2026-04", 758000, 507860, 0.67, "DERIVED_FROM_SMM_SHARE", "https://news.smm.cn/news/103918218", "SOURCE_A", "ACCEPTED_DERIVED"),
    ("2026-05", 681000, None, None, "NOT_AVAILABLE", "https://news.smm.cn/news/103965632", "SOURCE_A", "TOTAL_ONLY"),
    ("2026-06", 768000, 552960, 0.72, "DERIVED_FROM_SMM_SHARE", "https://news.smm.cn/news/104016985", "SOURCE_A", "ACCEPTED_DERIVED"),
]


def build_imports() -> list[dict]:
    rows = [{
        "month": month,
        "total_lithium_ore_import": total,
        "filtered_concentrate_import": "" if filtered is None else filtered,
        "filtered_share": "" if share is None else share,
        "value_origin": origin,
        "underlying_source": "China Customs; SMM filtered estimate",
        "smm_source_url": url,
        "source_grade": grade,
        "quality_flag": status,
    } for month, total, filtered, share, origin, url, grade, status in IMPORTS]
    write_csv(
        ROBUSTNESS / "smm_filtered_lithium_concentrate_import.csv",
        ["month", "total_lithium_ore_import", "filtered_concentrate_import", "filtered_share",
         "value_origin", "underlying_source", "smm_source_url", "source_grade", "quality_flag"], rows,
    )
    return rows


def build_inventory() -> list[dict]:
    # Only public observations are written here. The commercial legacy history
    # remains in the ignored industry layer and is deliberately not replicated.
    rows = [
        {"date": "2026-05-14", "inventory_smelter": "", "inventory_downstream": "", "inventory_other": "",
         "inventory_old_total": 101418, "inventory_up_down_total": "", "inventory_full_chain_total": "",
         "inventory_regime": "LEGACY_SAMPLE", "methodology_start_date": "",
         "source_url": "https://news.smm.cn/news/103907167", "quality_flag": "TOTAL_ONLY"},
        {"date": "2026-05-21", "inventory_smelter": 18374, "inventory_downstream": 42729, "inventory_other": 76157,
         "inventory_old_total": "", "inventory_up_down_total": 61103, "inventory_full_chain_total": 137260,
         "inventory_regime": "EXPANDED_SAMPLE_2026", "methodology_start_date": "2026-05-21",
         "source_url": "https://news.smm.cn/news/103914978", "quality_flag": "OK; EXPANDED_OTHER_SAMPLE"},
    ]
    write_csv(
        VALIDATION / "lc_inventory_weekly_regime_aware.csv",
        ["date", "inventory_smelter", "inventory_downstream", "inventory_other", "inventory_old_total",
         "inventory_up_down_total", "inventory_full_chain_total", "inventory_regime", "methodology_start_date",
         "source_url", "quality_flag"], rows,
    )
    changes = [
        {"effective_date": "2026-05-21", "old_definition": "Legacy weekly sample; upstream, downstream and other as then sampled",
         "new_definition": "Expanded weekly other sample including more traders and cell makers; legacy series remains in parallel",
         "sample_change": "Other-link sample expanded; trader coverage stated at 70%-80%",
         "comparability": "NOT_DIRECTLY_COMPARABLE", "recommended_action": "Compare latent inventory only within regime; retain both tracks",
         "source_url": "https://news.smm.cn/news/103898322", "notes": "Announcement 2026-05-13; first expanded observation 2026-05-21"},
        {"effective_date": "2026-05-01", "old_definition": "Monthly total labelled total and defined as smelter plus downstream",
         "new_definition": "Renamed up-down total; new full-chain total equals smelter plus downstream plus other",
         "sample_change": "Adds other monthly inventory including traders and cell makers",
         "comparability": "PARTIALLY_COMPARABLE", "recommended_action": "Do not splice old total to full-chain total",
         "source_url": "https://news.smm.cn/news/103950943", "notes": "Published 2026-06-11; effective from 2026-05; historical data unchanged"},
        {"effective_date": "2026-09-04", "old_definition": "Three categories under expanded-sample framework",
         "new_definition": "Four ownership categories; China customs territory; actual-title principle",
         "sample_change": "Adds slag-route upstream samples and revises downstream, trader and cell-maker samples",
         "comparability": "NOT_DIRECTLY_COMPARABLE", "recommended_action": "Use separate post-2026-09-04 regime; note backcast to 2026-04-30",
         "source_url": "https://news.smm.cn/news/104096214", "notes": "Outside current data window but material for future updates"},
    ]
    write_csv(
        METADATA / "lc_inventory_methodology_changes.csv",
        ["effective_date", "old_definition", "new_definition", "sample_change", "comparability", "recommended_action", "source_url", "notes"],
        changes,
    )
    return rows


def build_methodology() -> list[dict]:
    rows = [
        {
            "provider": "SMM",
            "series": "Spodumene concentrate 6% Li2O CIF China price index",
            "announcement_date": "2025-10-13",
            "effective_date": "",
            "old_method": "Methodology then in force; individual transaction threshold above 2,000 dry metric tons",
            "new_method": "Formal consultation on assessment fitness and transaction-size requirement",
            "possible_break": "PENDING_AT_ANNOUNCEMENT",
            "source_url": "https://news.smm.cn/news/104042055",
            "notes": "Official page date 2025-10-13; consultation window 2025-10-15 to 2025-11-15",
        },
        {
            "provider": "SMM",
            "series": "Spodumene concentrate 6% Li2O CIF China price index",
            "announcement_date": "2026-01-09",
            "effective_date": "2026-01-01",
            "old_method": "Methodology reviewed under reference SMMSCMC2024-2025",
            "new_method": "Reviewed methodology retained as fit for the China spodumene spot market",
            "possible_break": "YES_REVIEW_WINDOW",
            "source_url": "https://news.smm.cn/keywords/%E9%94%82%E8%BE%89%E7%9F%B3",
            "notes": "Official SMM index listing records validity 2026-01-01 through 2026-12-31; no statistical adjustment applied",
        },
    ]
    write_csv(
        METADATA / "spodumene_price_methodology.csv",
        ["provider", "series", "announcement_date", "effective_date", "old_method", "new_method", "possible_break", "source_url", "notes"],
        rows,
    )
    return rows


def build_output_verification() -> list[dict]:
    candidates = [
        ("2025-10", 92260, "SOURCE_A", "https://news.smm.cn/news/103599641", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "Official page gives >90kt and rounded growth, not exact absolute value"),
        ("2025-11", 95350, "SOURCE_C", "https://news.smm.cn/news/103647188", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "No new official exact absolute value found"),
        ("2025-12", 99200, "SOURCE_C", "https://www.thqh.com.cn/A_UpLoad/upload_file/20260120171910_6397.pdf", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "One formal report citing SMM; unchanged"),
        ("2026-03", 106620, "SOURCE_C", "https://www.hicend.com/ftpfile/static/file/upload/file/202604/24/PEtz6sWy4s6dQDG4.pdf", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "SMM public retrospective only rounds to 106.6kt"),
        ("2026-04", 110030, "SOURCE_C", "https://www.ccbfutures.com/upload/20260511/20260511142513677.pdf", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "No second exact authoritative citation found"),
        ("2026-05", 113295, "SOURCE_C", "https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/11/rptid/836511257711/index.phtml", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "No second exact authoritative citation found"),
        ("2026-06", 115320, "SOURCE_C", "https://finance.sina.cn/2026-07-07/detail-inihapna8101086.d.html", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "No second exact authoritative citation found"),
    ]
    rows = [{"month": m, "candidate_value": v, "source_grade": grade, "source_url": url,
             "previous_status": old, "new_status": new, "notes": note} for m, v, grade, url, old, new, note in candidates]
    write_csv(METADATA / "lc_output_tail_verification.csv",
              ["month", "candidate_value", "source_grade", "source_url", "previous_status", "new_status", "notes"], rows)
    return rows


def build_manifest(prices, weekly, imports, inventory, methodology, output_rows) -> None:
    rows = []
    for row in prices:
        for variable, value_key, unit, statistic_key, url_key in [
            ("lc_spot_mysteel", "lc_spot_mysteel", "CNY/t", "lc_spot_statistic", "source_url_lc"),
            ("spodumene_mysteel", "spodumene_mysteel", "USD/t", "spodumene_statistic", "source_url_spodumene"),
        ]:
            rows.append({"variable": variable, "period": row["month"], "value": row[value_key], "unit": unit,
                         "statistic": row[statistic_key], "provider": "Mysteel", "underlying_source": "Mysteel",
                         "source_grade": row["source_grade"], "source_url": row[url_key], "publication_date": "",
                         "definition": "Battery-grade LC ex-factory tax-included" if variable.startswith("lc_") else "SC6 Li2O CIF China",
                         "value_origin": "DIRECT_PROVIDER_VALUE" if row[value_key] != "" else "NOT_AVAILABLE",
                         "methodology_regime": "MYSTEEL_OFFICIAL_MONTHLY_TABLE", "accepted_status": row["quality_flag"], "notes": ""})
    for row in weekly:
        for variable, key in [("lc_cost_spodumene_mysteel", "lc_cost_spodumene_mysteel"), ("lc_margin_spodumene_mysteel", "lc_margin_spodumene_mysteel")]:
            rows.append({"variable": variable, "period": row["date"], "value": row[key], "unit": "CNY/t LC",
                         "statistic": "WEEKLY_POINT", "provider": "Mysteel", "underlying_source": "Mysteel",
                         "source_grade": "SOURCE_A", "source_url": row["source_url"], "publication_date": row["source_date"],
                         "definition": row["definition"], "value_origin": "DIRECT_PROVIDER_VALUE",
                         "methodology_regime": "MYSTEEL_DISCLOSED_ROUTE_ESTIMATE", "accepted_status": "VALIDATION_ONLY", "notes": ""})
    for row in imports:
        rows.append({"variable": "spodumene_concentrate_import_smm_filtered", "period": row["month"],
                     "value": row["filtered_concentrate_import"], "unit": "physical metric tons", "statistic": "MONTHLY_ACTUAL",
                     "provider": "SMM", "underlying_source": "China Customs", "source_grade": row["source_grade"],
                     "source_url": row["smm_source_url"], "publication_date": "", "definition": "SMM-filtered effective lithium concentrate",
                     "value_origin": row["value_origin"], "methodology_regime": "SMM_FILTERED_ESTIMATE",
                     "accepted_status": row["quality_flag"], "notes": "Not customs pure-spodumene series"})
    for row in inventory:
        for variable, key in [
            ("lc_inventory_smelter", "inventory_smelter"),
            ("lc_inventory_downstream", "inventory_downstream"),
            ("lc_inventory_other", "inventory_other"),
            ("lc_inventory_old_total", "inventory_old_total"),
            ("lc_inventory_up_down_total", "inventory_up_down_total"),
            ("lc_inventory_full_chain_total", "inventory_full_chain_total"),
        ]:
            rows.append({"variable": variable, "period": row["date"], "value": row[key], "unit": "metric tons",
                         "statistic": "WEEKLY_POINT", "provider": "SMM", "underlying_source": "SMM survey",
                         "source_grade": "SOURCE_A", "source_url": row["source_url"], "publication_date": row["date"],
                         "definition": f"Regime-aware SMM inventory field: {key}", "value_origin": "DIRECT_SMM_VALUE" if row[key] != "" else "NOT_AVAILABLE",
                         "methodology_regime": row["inventory_regime"], "accepted_status": "VALIDATION_ONLY",
                         "notes": row["quality_flag"]})
    for row in methodology:
        rows.append({"variable": "spodumene_price_methodology", "period": row["effective_date"], "value": "", "unit": "NA",
                     "statistic": "METHODOLOGY_EVENT", "provider": "SMM", "underlying_source": "SMM",
                     "source_grade": "SOURCE_A", "source_url": row["source_url"], "publication_date": row["announcement_date"],
                     "definition": row["new_method"], "value_origin": "OFFICIAL_METHODOLOGY_NOTICE",
                     "methodology_regime": row["possible_break"], "accepted_status": "METADATA_ONLY", "notes": row["notes"]})
    for row in output_rows:
        rows.append({"variable": "lc_output", "period": row["month"], "value": row["candidate_value"], "unit": "metric tons",
                     "statistic": "MONTHLY_ACTUAL", "provider": "SMM", "underlying_source": "SMM", "source_grade": row["source_grade"],
                     "source_url": row["source_url"], "publication_date": "", "definition": "China LC actual total output",
                     "value_origin": "SEARCH_TARGET_VERIFICATION", "methodology_regime": "EXISTING_TAIL_CANDIDATE",
                     "accepted_status": row["new_status"], "notes": row["notes"]})
    write_csv(
        METADATA / "high_value_industry_source_manifest.csv",
        ["variable", "period", "value", "unit", "statistic", "provider", "underlying_source", "source_grade",
         "source_url", "publication_date", "definition", "value_origin", "methodology_regime", "accepted_status", "notes"], rows,
    )


def build_coverage(prices, weekly, imports, inventory) -> None:
    specs = []
    def add(variable, provider, values, periods, frequency, definition, use, status):
        observed = [(p, v) for p, v in zip(periods, values) if v not in ("", None)]
        specs.append({"variable": variable, "provider": provider,
                      "start": observed[0][0] if observed else "", "end": observed[-1][0] if observed else "",
                      "frequency": frequency, "obs_count": len(observed), "missing": len(values) - len(observed),
                      "definition": definition, "recommended_use": use, "status": status})
    add("lc_spot_mysteel", "Mysteel", [r["lc_spot_mysteel"] for r in prices], [r["month"] for r in prices], "monthly",
        "Battery-grade LC, China, ex-factory tax-included, monthly mean", "ROBUSTNESS", "PARTIAL_PUBLIC_COVERAGE")
    add("spodumene_mysteel", "Mysteel", [r["spodumene_mysteel"] for r in prices], [r["month"] for r in prices], "monthly",
        "Spodumene concentrate 6% Li2O CIF China USD/t monthly mean", "ROBUSTNESS", "PARTIAL_PUBLIC_COVERAGE")
    add("lc_cost_spodumene_mysteel", "Mysteel", [r["lc_cost_spodumene_mysteel"] for r in weekly], [r["date"] for r in weekly], "weekly",
        "Disclosed Australian SC6 route LC production cost", "VALIDATION_ONLY", "SPARSE_PUBLIC_POINTS")
    add("lc_margin_spodumene_mysteel", "Mysteel", [r["lc_margin_spodumene_mysteel"] for r in weekly], [r["date"] for r in weekly], "weekly",
        "Disclosed Australian SC6 route spot profit", "VALIDATION_ONLY", "SPARSE_PUBLIC_POINTS")
    add("spodumene_concentrate_import_smm_filtered", "SMM", [r["filtered_concentrate_import"] for r in imports], [r["month"] for r in imports], "monthly",
        "China Customs total further filtered by SMM", "ROBUSTNESS", "DIRECT_AND_DERIVED")
    add("lc_inventory_full_chain_total", "SMM", [r["inventory_full_chain_total"] for r in inventory], [r["date"] for r in inventory], "weekly",
        "Regime-aware full-chain total; never spliced across breaks", "VALIDATION_ONLY", "METHODOLOGY_BREAK")
    write_csv(METADATA / "alternative_series_coverage.csv",
              ["variable", "provider", "start", "end", "frequency", "obs_count", "missing", "definition", "recommended_use", "status"], specs)


def main() -> None:
    prices = build_mysteel_prices()
    reconcile(prices)
    weekly, _ = build_cost_margin()
    imports = build_imports()
    inventory = build_inventory()
    methodology = build_methodology()
    output_rows = build_output_verification()
    build_manifest(prices, weekly, imports, inventory, methodology, output_rows)
    build_coverage(prices, weekly, imports, inventory)


if __name__ == "__main__":
    main()
