"""Build the editable weekly Word report from its reviewed Markdown.

Requires Pandoc, python-docx and a Chinese serif font. The style follows the
previous group reports: A4, 2 cm margins, plain headings, 11 pt body text and
native editable Office Math. Render the result separately before publication.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/2026-11-26_weekly_dsge"
SOURCE = REPORT / "meeting_report_20261126.md"
OUTPUT = SOURCE.with_suffix(".docx")
CJK_FONT = "Noto Serif CJK SC"
LATIN_FONT = "Times New Roman"
MATH_FONT = "Latin Modern Math"


def font_settings(style, size, bold=False):
    style.font.name = LATIN_FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = False
    style.font.color.rgb = RGBColor(0, 0, 0)
    props = style.element.get_or_add_rPr()
    fonts = props.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        props.insert(0, fonts)
    fonts.set(qn("w:ascii"), LATIN_FONT)
    fonts.set(qn("w:hAnsi"), LATIN_FONT)
    fonts.set(qn("w:eastAsia"), CJK_FONT)
    for name in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme"):
        fonts.attrib.pop(qn("w:" + name), None)
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "en-US")
    lang.set(qn("w:eastAsia"), "zh-CN")
    props.append(lang)
    sz_cs = props.find(qn("w:szCs"))
    if sz_cs is None:
        sz_cs = OxmlElement("w:szCs")
        props.append(sz_cs)
    sz_cs.set(qn("w:val"), str(int(size * 2)))


def set_page_and_styles(doc):
    for sec in doc.sections:
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        sec.top_margin = sec.bottom_margin = Cm(2)
        sec.left_margin = sec.right_margin = Cm(2)
        sec.header_distance = sec.footer_distance = Cm(.9)
    for name in ("Normal", "Body Text", "First Paragraph", "List Paragraph"):
        if name in doc.styles:
            style = doc.styles[name]
            font_settings(style, 11)
            pf = style.paragraph_format
            pf.line_spacing = 1.15
            pf.space_after = Pt(3)
            pf.space_before = Pt(0)
            pf.widow_control = True
    for name, size in (("Title", 14), ("Subtitle", 11.5),
                       ("Heading 1", 11.5), ("Heading 2", 11),
                       ("Heading 3", 11.5), ("Heading 4", 11)):
        if name in doc.styles:
            style = doc.styles[name]
            font_settings(style, size, name != "Subtitle")
            pf = style.paragraph_format
            pf.space_before = Pt(7 if name.startswith("Heading") else 0)
            pf.space_after = Pt(4)
            pf.line_spacing = 1.15
            pf.keep_with_next = True
            pf.keep_together = True
            ppr = style.element.get_or_add_pPr()
            border = ppr.find(qn("w:pBdr"))
            if border is not None:
                ppr.remove(border)
    for name in ("Caption", "Image Caption"):
        if name in doc.styles:
            font_settings(doc.styles[name], 10)
            doc.styles[name].paragraph_format.space_after = Pt(4)
            doc.styles[name].paragraph_format.keep_together = True
    settings = doc.settings.element
    math = settings.find(qn("m:mathPr"))
    if math is None:
        math = OxmlElement("m:mathPr")
        settings.append(math)
    mf = math.find(qn("m:mathFont"))
    if mf is None:
        mf = OxmlElement("m:mathFont")
        math.append(mf)
    mf.set(qn("m:val"), MATH_FONT)


def finish_tables(doc):
    # Rebuild Pandoc tables using the same plain text and a standard Word table
    # style. This avoids a LibreOffice importer issue with Pandoc's custom Table
    # style, while preserving real editable tables and their exact cell values.
    for old in list(doc.tables):
        values = [[cell.text for cell in row.cells] for row in old.rows]
        new = doc.add_table(rows=len(values), cols=len(values[0]))
        new.style = "Table Grid"
        for row, texts in zip(new.rows, values):
            for cell, text in zip(row.cells, texts):
                cell.text = text
        old._tbl.getparent().replace(old._tbl, new._tbl)
    for table in doc.tables:
        table.autofit = False
        widths = [Cm(3.5), Cm(7), Cm(6.5)] if len(table.columns) == 3 else [Cm(4.2)] + [Cm(3.2)] * 4
        for col, width in zip(table.columns, widths):
            col.width = width
        props = table._tbl.tblPr
        width_property = props.find(qn("w:tblW"))
        width_property.set(qn("w:type"), "dxa")
        width_property.set(qn("w:w"), str(sum(int(width.twips) for width in widths)))
        borders = OxmlElement("w:tblBorders")
        for side in ("top", "bottom", "insideH", "left", "right", "insideV"):
            edge = OxmlElement("w:" + side)
            edge.set(qn("w:val"), "single" if side in ("top", "bottom", "insideH") else "nil")
            edge.set(qn("w:sz"), "5" if side in ("top", "bottom") else "3")
            edge.set(qn("w:color"), "B7B7B7")
            borders.append(edge)
        old = props.find(qn("w:tblBorders"))
        if old is not None:
            props.remove(old)
        props.append(borders)
        for ri, row in enumerate(table.rows):
            row_props = row._tr.get_or_add_trPr()
            row_props.append(OxmlElement("w:cantSplit"))
            if ri == 0:
                row_props.append(OxmlElement("w:tblHeader"))
            for ci, (cell, width) in enumerate(zip(row.cells, widths)):
                cell.width = width
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                if ri == 0:
                    shading = OxmlElement("w:shd")
                    shading.set(qn("w:fill"), "F2F2F2")
                    cell._tc.get_or_add_tcPr().append(shading)
                for p in cell.paragraphs:
                    p.style = doc.styles["Normal"]
                    p.paragraph_format.first_line_indent = Pt(0)
                    p.paragraph_format.space_before = Pt(3)
                    p.paragraph_format.space_after = Pt(3)
                    p.paragraph_format.line_spacing = 1.1
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci == 0 or len(widths) == 3 else WD_ALIGN_PARAGRAPH.RIGHT
                    for run in p.runs:
                        run.font.name = LATIN_FONT
                        run.font.size = Pt(9.5)
                        run.bold = ri == 0
                        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), CJK_FONT)


def normalize_math_and_links(doc):
    for prop in doc.element.xpath(".//m:dPr"):
        separator = prop.find(qn("m:sepChr"))
        if separator is not None and separator.get(qn("m:val")) == "":
            prop.remove(separator)
    # A structural overbar is portable across Word and LibreOffice; an accent
    # glyph U+203E is interpreted inconsistently by the current LO importer.
    for acc in list(doc.element.xpath(".//m:acc")):
        prop = acc.find(qn("m:accPr"))
        char = prop.find(qn("m:chr")) if prop is not None else None
        if char is not None and char.get(qn("m:val")) in ("\u203e", "\u0304", "\u0305"):
            bar = OxmlElement("m:bar")
            bar_prop = OxmlElement("m:barPr")
            pos = OxmlElement("m:pos")
            pos.set(qn("m:val"), "top")
            bar_prop.append(pos)
            bar.append(bar_prop)
            bar.append(acc.find(qn("m:e")))
            acc.getparent().replace(acc, bar)
    # Keep DOI/source labels as ordinary selectable text in Word. The Markdown
    # contains the clickable canonical URLs. This avoids visible importer
    # fallback markers in the rendered Word reference list.
    for link in list(doc.element.xpath(".//w:hyperlink")):
        parent = link.getparent()
        index = parent.index(link)
        for child in list(link):
            parent.insert(index, child)
            index += 1
        parent.remove(link)


def main():
    if not shutil.which("pandoc"):
        raise RuntimeError("Pandoc is required for native editable Word equations.")
    with tempfile.TemporaryDirectory(prefix="dsge_weekly_docx_") as tmp:
        reference = Path(tmp) / "reference.docx"
        doc = Document()
        set_page_and_styles(doc)
        doc.save(reference)
        subprocess.run([
            "pandoc", str(SOURCE), "--from=markdown+tex_math_dollars",
            "--to=docx", "--standalone", "--reference-doc=" + str(reference),
            "--resource-path=" + str(REPORT), "--output=" + str(OUTPUT),
        ], check=True, cwd=ROOT)
    doc = Document(OUTPUT)
    set_page_and_styles(doc)
    in_references = False
    reference_number = 0
    for i, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        pf = p.paragraph_format
        if i == 0:
            p.style = doc.styles["Title"]
            pf.space_after = Pt(4)
        elif i == 1:
            p.style = doc.styles["Subtitle"]
            pf.space_after = Pt(9)
        elif p.style.name == "Heading 3":
            p.style = doc.styles["Heading 1"]
        elif p.style.name == "Heading 4":
            p.style = doc.styles["Heading 2"]
        if text == "参考文献与对应关系":
            in_references = True
            pf.page_break_before = True
        elif text == "计算材料":
            in_references = False
        if p._p.xpath(".//m:oMathPara"):
            pf.first_line_indent = Pt(0)
            pf.space_before = pf.space_after = Pt(4)
            pf.keep_together = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif p._p.xpath(".//w:drawing"):
            pf.first_line_indent = Pt(0)
            pf.keep_with_next = True
            pf.keep_together = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif p.style.name in ("Caption", "Image Caption") or text.startswith(("图1 ", "图2 ")):
            pf.keep_with_next = True
            pf.first_line_indent = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.size = Pt(9.5)
        elif text.startswith(("图1注：", "图2注：")):
            pf.first_line_indent = Pt(0)
            pf.line_spacing = 1.05
            pf.space_after = Pt(6)
            for run in p.runs:
                run.font.size = Pt(9)
        elif in_references and not p.style.name.startswith("Heading"):
            pf.line_spacing = 1.1
            pf.space_after = Pt(4)
            num = p._p.pPr.find(qn("w:numPr")) if p._p.pPr is not None else None
            if num is not None:
                p._p.pPr.remove(num)
                reference_number += 1
                label = OxmlElement("w:r")
                label_text = OxmlElement("w:t")
                label_text.text = "[" + str(reference_number) + "] "
                label_text.set(qn("xml:space"), "preserve")
                label.append(label_text)
                p._p.insert(1, label)
                pf.left_indent = Pt(16)
                pf.first_line_indent = Pt(-16)
            for run in p.runs:
                run.font.size = Pt(10)
        elif p.style.name in ("Normal", "Body Text", "First Paragraph") and text:
            pf.first_line_indent = Pt(22)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for i, shape in enumerate(doc.inline_shapes):
        ratio = shape.height / shape.width
        shape.width = Cm(14 if i == 0 else 16.2)
        shape.height = int(shape.width * ratio)
    finish_tables(doc)
    normalize_math_and_links(doc)
    for sec in doc.sections:
        footer = sec.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), "PAGE")
        footer._p.append(fld)
        footer.paragraph_format.space_after = Pt(0)
    doc.core_properties.title = "11月26日组会汇报：碳酸锂DSGE模型的随机冲击与局部求解"
    doc.core_properties.subject = "局部一阶随机均衡、冲击传导及非线性计算边界"
    doc.core_properties.author = "DSGE-LC"
    doc.core_properties.comments = "Generated from the reviewed Markdown; equations are editable OMML."
    doc.save(OUTPUT)
    with ZipFile(OUTPUT) as zf:
        tree = etree.fromstring(zf.read("word/document.xml"))
        namespaces = {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
        count = len(tree.xpath("//m:oMath", namespaces=namespaces))
        displays = len(tree.xpath("//m:oMathPara", namespaces=namespaces))
    if displays < 12 or len(doc.inline_shapes) != 2 or len(doc.tables) != 2:
        raise RuntimeError("Report equations, figures or tables were not preserved.")
    manifest = {
        "model_id": "LC_DSGE_EQCHAIN_20261126",
        "date": "2026-11-26",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "build_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "docx": str(OUTPUT.relative_to(ROOT)),
        "docx_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "editable_office_math_count": count, "display_equation_count": displays,
        "figures": 2, "tables": 2,
        "style_reference": {
            "source_name": "组会-李江涛_11.13.docx",
            "source_sha256": "db3472e1961f12126d6aff9a5d53765c6fcd155fb6a5f6873dc324c636d0bef3",
            "meeting_entries": ["10.23", "10.30", "11.6", "11.13"],
            "source_document_republished": False,
            "page": "A4, 2 cm margins",
            "body": "11 pt Chinese serif / Times New Roman, 1.15 line spacing",
            "equations": "native editable Office Math",
        },
        "publication_scope": "synthetic local first-order RE and leading zero-order portfolio; not full nonlinear or estimated results",
    }
    (REPORT / "document_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "editable_math": count, "display_equations": displays}, ensure_ascii=False))


if __name__ == "__main__":
    main()
