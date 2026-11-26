"""Build the private R2 advisor draft from the canonical Markdown and verified R1 figures.

This is a publication step only. It neither estimates the model nor reads posterior
draw arrays. Commercial-derived figures and DOCX/PDF remain in ignored outputs/thesis.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import statistics
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
R1 = ROOT / "outputs/revisions/R1_20260916_190253"
PREFLIGHT = R1 / "preflight/inputs_before.json"
REGISTRY = R1 / "result_registry_final/result_registry.json"
REGISTRY_SHA = "2e8cb4678c3c11cd2d69c34c044bbcb24e500facaadf95219f47fa5d9991aef4"
MARKER = re.compile(r"<!-- R2_FIGURE:([A-Z0-9_]+) -->")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require_hash(path: Path, expected: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = digest(path)
    if actual != expected.lower():
        raise ValueError(f"SHA256 mismatch: {path}: expected {expected}, actual {actual}")


def input_checks() -> dict:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    items = [preflight["data_freeze"], preflight["transformed_panel"]]
    items += preflight["posterior_artifacts"] + preflight["posterior_sidecars"]
    for item in items:
        require_hash(ROOT / item["path"], item["sha256"])
    require_hash(REGISTRY, REGISTRY_SHA)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    unique_sources: dict[str, str] = {}
    for result in registry["results"]:
        source = result.get("source_file")
        sha = result.get("source_file_sha256")
        if source and sha:
            unique_sources[source] = sha
    for path, sha in unique_sources.items():
        require_hash(ROOT / path, sha)
    return {
        "frozen_inputs_checked": len(items),
        "registry_source_files_checked": len(unique_sources),
        "registry_sha256": REGISTRY_SHA,
        "data_freeze_sha256": preflight["data_freeze"]["sha256"],
        "transformed_panel_sha256": preflight["transformed_panel"]["sha256"],
        "posterior_sha256": {x["path"]: x["sha256"] for x in preflight["posterior_artifacts"]},
    }


def figures(run_id: str) -> dict[str, dict]:
    local = f"outputs/thesis/{run_id}/figures"
    return {
        "F3_1": {"path": "outputs/phase1/figures/01_lc_spot_level.png", "source": ["data/processed/core_monthly_panel.csv"], "sample": "2020-01—2025-09; N=69", "unit": "元/吨", "statistic": "月均报价", "interval": "无", "caption": "图3-1 电池级碳酸锂现货月均价格。样本：2020-01—2025-09；单位：元/吨；来源：Data Freeze v1，Phase 1原图。"},
        "F4_1": {"path": f"{local}/mechanism_core5_r2.png", "source": ["src/structural/equations.py"], "sample": "模型定义", "unit": "标准化状态", "statistic": "冻结顺序方程与时序机制示意", "interval": "不适用", "caption": "图4-1 五状态半结构机制。左框为滞后跨状态路径，右框为当期价格传导，下框为冻结顺序方程；n为标准化供需压力而非吨数库存。来源：M0_CORE5模型定义。"},
        "F4_2": {"path": "outputs/midterm/figure_03_data_model_map.png", "source": ["data/processed/phase1/monthly_structural_v1.csv"], "sample": "2021-01—2025-09; N=57", "unit": "月度dlog/同比log标准化", "statistic": "观测映射", "interval": "不适用", "caption": "图4-2 四条月度观测与五状态映射。结构样本：2021-01—2025-09，N=57；MIXED4是变换组合，不是混频。"},
        "F5_1": {"path": f"{local}/posterior_parameter_r2.png", "source": ["outputs/phase2/phase2d/baseline_posterior_summary.csv"], "sample": "2021-01—2025-09; N=57", "unit": "参数标准化单位", "statistic": "后验中位数", "interval": "边际90%可信区间", "caption": "图5-1 基线14参数后验中位数和边际90%可信区间。参数来自原draw汇总；R1修正后的收敛诊断见表5-1。"},
        "F6_1": {"path": f"{local}/irf_price_4shocks_r2.png", "source": ["outputs/phase2/phase2e/irf_price_summary.csv"], "sample": "原基线72,000后验draw", "unit": "标准化价格变化压力", "statistic": "后验中位IRF", "interval": "68%和90%边际可信区间", "caption": "图6-1 四类冲击对价格变化状态的后验IRF，0—24个月。实线为后验中位数；深/浅带分别为68%/90%边际可信区间；单位为标准化压力，不是价格水平。"},
        "F6_2": {"path": "outputs/revisions/R1_20260916_190253/fevd/fevd_price_horizons_mean_stacked.png", "source": ["outputs/revisions/R1_20260916_190253/fevd/fevd_corrected_summary.csv"], "sample": "基线72,000后验draw", "unit": "份额", "statistic": "逐draw份额的后验均值", "interval": "图中未展示边际区间", "caption": "图6-2 基线价格状态1/3/6/12/24个月FEVD。堆叠为逐draw份额的后验均值，逐期限加总为1；边际区间另见源表。"},
        "F6_3": {"path": "outputs/revisions/R1_20260916_190253/historical/historical_signed_mean_stack.png", "source": ["outputs/revisions/R1_20260916_190253/historical/historical_monthly_corrected.csv"], "sample": "2021-01—2025-09; N=57", "unit": "标准化价格变化压力", "statistic": "有符号后验均值", "interval": "图中未展示", "caption": "图6-3 基线逐月有符号历史分解。后验均值按正负分别堆叠，含初始条件；2021-01不分配转移冲击。"},
        "F6_4": {"path": "outputs/revisions/R1_20260916_190253/historical/historical_cumulative_draw_first.png", "source": ["outputs/revisions/R1_20260916_190253/historical/historical_cumulative_corrected.csv"], "sample": "2021-01—2025-09; N=57", "unit": "累计标准化价格变化压力", "statistic": "逐draw先累计后取分位", "interval": "蓝带仅价格残差的5%—95%条件平滑均值区间", "caption": "图6-4 基线累计历史贡献。各路径先逐draw累计再取统计量；蓝带仅价格残差冲击的5%—95%条件平滑均值区间，不是全部潜在状态区间。"},
        "F7_1": {"path": f"{local}/forecast_five_model.png", "source": ["outputs/revisions/R1_20260916_190253/forecast_verified/forecast_metric_revision.csv", "outputs/phase2/phase2g/structural_oos_metrics.csv"], "sample": "21起点; 56共同键", "unit": "RMSE/MAE元/吨; U2无量纲", "statistic": "同键历史点预测误差", "interval": "未做显著性区间", "caption": "图7-1 五模型三期限历史预测误差。相同(origin,target,horizon)键；N=21/19/16；RMSE/MAE为元/吨，U2相对同键RW；非前瞻验证。"},
        "F7_2": {"path": f"{local}/external_inventory_block.png", "source": ["outputs/revisions/R1_20260916_190253/external_validation_final/external_validation_block_bootstrap.csv"], "sample": "库存水平28月; 变化量27月", "unit": "Pearson相关", "statistic": "固定中位状态路径相关", "interval": "3/6月配对块95% percentile区间", "caption": "图7-2 库存构念对照。点为固定后验中位状态路径相关；线为3/6月配对块95%时间样本区间；水平与变化量对象分列，非联合后验。"},
        "F8_1": {"path": f"{local}/futures_lead_lag.png", "source": ["outputs/revisions/R1_20260916_190253/futures/lead_lag_specification_comparison.csv"], "sample": "月频26收益/日频534相邻收益", "unit": "Pearson相关", "statistic": "固定lag探索性描述", "interval": "无推断区间", "caption": "图8-1 同区间期现领先滞后相关。正lag为期货t与随后现货；同端点月频与相邻日频分列，主力规则分列；非因果或交易收益。"},
    }


def core_description_markdown() -> str:
    path = ROOT / "data/processed/core_monthly_panel.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 69 or rows[0]["month"] != "2020-01" or rows[-1]["month"] != "2025-09":
        raise ValueError("Core description must use the unchanged 69-month v1 panel")
    fields = [
        ("电池级碳酸锂现货", "lc_spot", "元/吨"),
        ("碳酸锂总产量", "lc_output_total", "吨/月"),
        ("SC6精矿报价", "spodumene_price", "美元/吨精矿"),
        ("人民币精矿价代理", "spodumene_cny_t", "元/吨精矿"),
        ("动力电池装车", "battery_install", "GWh/月"),
    ]
    lines = [
        "表3-2 冻结核心月度水平序列描述统计（2020-01—2025-09）",
        "",
        "| 变量 | 单位 | N | 均值 | 样本标准差 | 最小值 | 最大值 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for label, field, unit in fields:
        values = [float(row[field]) for row in rows if row[field].strip()]
        if len(values) != 69:
            raise ValueError(f"Unexpected missing v1 value in {field}")
        numbers = [len(values), statistics.mean(values), statistics.stdev(values), min(values), max(values)]
        lines.append(f"| {label} | {unit} | {numbers[0]} | {numbers[1]:,.2f} | {numbers[2]:,.2f} | {numbers[3]:,.2f} | {numbers[4]:,.2f} |")
    lines += ["", "来源：Data Freeze v1冻结水平面板；商业派生统计仅供本地导师讨论稿使用，不公开源序列。", ""]
    return "\n".join(lines)


def metadata_and_markdown(run_id: str, outdir: Path, checked: dict) -> tuple[Path, dict]:
    fig = figures(run_id)
    for item in fig.values():
        image = ROOT / item["path"]
        if not image.is_file():
            raise FileNotFoundError(image)
        item["sha256"] = digest(image)
        item["source_sha256"] = {}
        for source in item["source"]:
            path = ROOT / source
            if not path.is_file():
                raise FileNotFoundError(path)
            item["source_sha256"][source] = digest(path)
        item["license"] = "PRIVATE_ADVISOR_USE_ONLY_NOT_FOR_PUBLIC_GIT"
    source = (ROOT / "docs/thesis/advisor_draft.md").read_text(encoding="utf-8")
    used: set[str] = set()

    def embed(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in fig or key in used:
            raise ValueError(f"Unknown or duplicate figure marker: {key}")
        used.add(key)
        item = fig[key]
        return f'![{item["caption"]}]({item["path"]}){{width=15cm}}'

    source = MARKER.sub(embed, source)
    if used != set(fig):
        raise ValueError(f"Missing figure markers: {sorted(set(fig) - used)}")
    table_marker = "<!-- R2_TABLE:CORE_DESCRIPTION -->"
    if source.count(table_marker) != 1:
        raise ValueError("Expected exactly one core description table marker")
    source = source.replace(table_marker, core_description_markdown())
    source = source.replace("date: 2026年9月16日", "date: 2026年9月17日")
    source = source.replace(
        "# 摘要",
        "研究生：待学生填写　导师：待学生填写　学校：待确认\n\n导师审阅讨论稿；非学校送审定稿。\n\n# 摘要",
        1,
    )
    prepared = outdir / "advisor_draft_with_verified_figures.md"
    prepared.write_text(source, encoding="utf-8")
    manifest = {
        "schema": "r2_advisor_sources_v1",
        "run_id": run_id,
        "research_commit": "f1215880f6ce18e378dd9995ea7bf68fa765ffa9",
        "canonical_markdown": "docs/thesis/advisor_draft.md",
        "canonical_markdown_sha256": digest(ROOT / "docs/thesis/advisor_draft.md"),
        "input_checks": checked,
        "figures": fig,
        "permission": "Private figures and document outputs are local advisor-use artifacts; no public redistribution authorization inferred.",
    }
    (outdir / "文件与结果来源清单.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return prepared, manifest


def font_for_style(style, family: str, size: float, bold: bool | None = None) -> None:
    style.font.name = family
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for key in ("ascii", "hAnsi", "cs"):
        fonts.set(qn(f"w:{key}"), "Times New Roman")
    fonts.set(qn("w:eastAsia"), family)


def append_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    shown = OxmlElement("w:t")
    shown.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, separate, shown, end):
        run._r.append(node)


def polish_docx(path: Path, *, thesis: bool) -> dict:
    doc = Document(path)
    for section in doc.sections:
        section.page_width, section.page_height = Cm(21), Cm(29.7)
        section.top_margin = section.bottom_margin = Cm(2.4)
        section.left_margin, section.right_margin = Cm(3.0), Cm(2.5)
        section.header_distance, section.footer_distance = Cm(1.2), Cm(1.2)
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if not footer.text.strip():
            append_field(footer, " PAGE ")
    styles = doc.styles
    font_for_style(styles["Normal"], "SimSun", 10.5)
    font_for_style(styles["Title"], "SimHei", 20, True)
    font_for_style(styles["Heading 1"], "SimHei", 15, True)
    font_for_style(styles["Heading 2"], "SimHei", 12, True)
    if "Caption" in styles:
        font_for_style(styles["Caption"], "SimSun", 9)
    for style_name in ("Title", "Heading 1", "Heading 2", "TOC Heading"):
        if style_name in styles:
            styles[style_name].font.color.rgb = RGBColor(0, 0, 0)
    styles["Normal"].paragraph_format.line_spacing = 1.35
    styles["Normal"].paragraph_format.space_after = Pt(5)
    chapter = ""
    equation_counts: dict[str, int] = {}
    equations = 0
    previous_had_drawing = False
    for paragraph in doc.paragraphs:
        content = paragraph.text.strip()
        if paragraph.style.name == "Heading 1":
            chapter_match = re.match(r"第([一二三四五六七八九])章", content)
            if chapter_match:
                chapter = str("一二三四五六七八九".index(chapter_match.group(1)) + 1)
            elif content in {"摘要", "Abstract", "参考文献"} or content.startswith("附录"):
                chapter = "A" if content.startswith("附录A") else "B" if content.startswith("附录B") else ""
                paragraph.paragraph_format.page_break_before = content in {"摘要", "参考文献"}
            paragraph.paragraph_format.keep_with_next = True
        elif paragraph.style.name == "Heading 2":
            paragraph.paragraph_format.keep_with_next = True
        if re.match(r"^表\d+-\d+[A-Za-z]?\s", content):
            paragraph.paragraph_format.keep_with_next = True
        if previous_had_drawing and content.startswith("图") and re.match(r"图\d+-\d+", content):
            paragraph.style = styles["Caption"]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.keep_with_next = False
        if paragraph._p.xpath(".//m:oMathPara"):
            equations += 1
            if chapter and thesis:
                equation_counts[chapter] = equation_counts.get(chapter, 0) + 1
                paragraph.add_run(f"　（{chapter}-{equation_counts[chapter]}）")
        previous_had_drawing = bool(paragraph._p.xpath(".//w:drawing"))
    if thesis:
        body = doc.element.body
        toc = body.xpath("./w:sdt")
        if len(toc) != 1:
            raise ValueError("Expected exactly one editable Word table of contents")
        body.remove(toc[0])
        identity = [p for p in doc.paragraphs if p.text.startswith("研究生：")]
        if len(identity) != 1:
            raise ValueError("Expected one pending cover identity paragraph")
        identity_index = list(body).index(identity[0]._p)
        body.insert(identity_index + 2, toc[0])
        toc_content = toc[0].find(qn("w:sdtContent"))
        toc_first = toc_content.find(qn("w:p")) if toc_content is not None else None
        if toc_first is not None:
            ppr = toc_first.get_or_add_pPr()
            ppr.append(OxmlElement("w:pageBreakBefore"))
    for table in doc.tables:
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        for cell in table.rows[0].cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.bold = True
        trpr = table.rows[0]._tr.get_or_add_trPr()
        header = OxmlElement("w:tblHeader")
        header.set(qn("w:val"), "true")
        trpr.append(header)
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_after = Pt(0)
                    for run in paragraph.runs:
                        run.font.size = Pt(8.5)
    doc.save(path)
    return {"tables": len(doc.tables), "inline_shapes": len(doc.inline_shapes), "omml_paragraphs": equations}


def pandoc_to_docx(markdown: Path, docx: Path, *, toc: bool) -> None:
    command = [
        "pandoc", str(markdown), "--from=markdown+tex_math_dollars+pipe_tables+raw_html",
        "--to=docx", "--standalone",
        "--resource-path", str(ROOT), "--output", str(docx),
    ]
    if toc:
        command += ["--toc", "--toc-depth=2", "-M", "toc-title=目录"]
    subprocess.run(command, check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"R2_\d{8}_\d{6}", args.run_id):
        raise ValueError("run-id must be R2_YYYYMMDD_HHMMSS")
    outdir = ROOT / "outputs/thesis" / args.run_id
    if outdir.exists() and any(outdir.glob("*.docx")):
        raise FileExistsError(f"Existing generated documents will not be overwritten: {outdir}")
    outdir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "check-ignore", "-q", str(outdir / "论文初稿.docx")], check=True, cwd=ROOT)
    before = input_checks()
    prepared, manifest = metadata_and_markdown(args.run_id, outdir, before)
    thesis = outdir / "论文初稿.docx"
    pandoc_to_docx(prepared, thesis, toc=True)
    thesis_structure = polish_docx(thesis, thesis=True)
    note = outdir / "给导师审阅说明.docx"
    pandoc_to_docx(ROOT / "docs/thesis/advisor_review_note.md", note, toc=False)
    note_structure = polish_docx(note, thesis=False)
    after = input_checks()
    if before != after:
        raise ValueError("Frozen input changed during document generation")
    manifest["document_structure"] = {"thesis": thesis_structure, "advisor_note": note_structure}
    manifest["output_sha256"] = {"论文初稿.docx": digest(thesis), "给导师审阅说明.docx": digest(note)}
    (outdir / "文件与结果来源清单.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"outdir": str(outdir), "structure": manifest["document_structure"], "inputs": before}, ensure_ascii=False))


if __name__ == "__main__":
    main()
