"""Render an authored UTF-8 Chinese mechanism note as a one-page A4 PDF."""

from __future__ import annotations

import argparse
import html
from io import BytesIO
import json
import os
from pathlib import Path
import re

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph


SCRIPT_CHARACTERS = {
    "super": ("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ", "0123456789+-=()ni"),
    "sub": ("₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ", "0123456789+-=()aehijklmnoprstuvx"),
}


def paragraph_markup(value: str) -> str:
    result = html.escape(value, quote=False)
    # Use raised/lowered ordinary glyphs where common CJK fonts lack Unicode scripts.
    for tag, (original, ascii_text) in SCRIPT_CHARACTERS.items():
        mapping = str.maketrans(original, ascii_text)
        result = re.sub(f"[{original}]+", lambda match: f"<{tag}>{match[0].translate(mapping)}</{tag}>", result)
    return result


def string_field(source: dict, key: str, required: bool = False) -> str:
    value = source.get(key, "")
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f"Expected nonempty text for {key}" if required else f"Expected text for {key}")
    return value.strip()


def read_note(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sections"), list) or not payload["sections"]:
        raise ValueError("Expected a JSON object with at least one section")
    sections = []
    for number, section in enumerate(payload["sections"], 1):
        if not isinstance(section, dict):
            raise ValueError(f"Section {number} must be an object with heading and body")
        heading = string_field(section, "heading", required=True)
        body = section.get("body")
        body = [body] if isinstance(body, str) else body
        if not isinstance(body, list) or not body or any(not isinstance(item, str) or not item.strip() for item in body):
            raise ValueError(f"Section {number} body must contain nonempty text")
        sections.append((heading, [item.strip() for item in body]))
    return {
        "title": string_field(payload, "title", required=True),
        "subtitle": string_field(payload, "subtitle"),
        "lead": string_field(payload, "lead"),
        "sections": sections,
        "footer": string_field(payload, "footer"),
    }


def register_fonts(font_file: Path | None = None) -> None:
    if font_file is None:
        windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        regular = windows_fonts / "msyh.ttc"
        bold = windows_fonts / "msyhbd.ttc"
        if not regular.is_file():
            regular = windows_fonts / "simhei.ttf"
        if not regular.is_file():
            raise FileNotFoundError("No Windows Chinese font found. Use --font with a Chinese TTF/TTC font.")
        if not bold.is_file():
            bold = regular
    else:
        regular = bold = font_file
    pdfmetrics.registerFont(TTFont("GIRFRegular", str(regular)))
    pdfmetrics.registerFont(TTFont("GIRFHeading", str(bold)))


def render(note: dict) -> bytes:
    page_width, page_height = A4
    margin = 51
    text_width = page_width - 2 * margin
    accent = colors.HexColor("#123E61")
    ink = colors.HexColor("#182637")
    muted = colors.HexColor("#4D5C6B")
    rule = colors.HexColor("#C7D4DF")

    def style(name, size, leading, color, font="GIRFRegular"):
        return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading,
                              alignment=TA_LEFT, wordWrap="CJK", textColor=color)

    title = style("title", 25, 35, accent, "GIRFHeading")
    subtitle = style("subtitle", 11, 19, muted)
    lead = style("lead", 11.1, 18.7, accent)
    heading = style("heading", 13, 21, accent, "GIRFHeading")
    body = style("body", 11, 18.5, ink)
    footnote = style("footnote", 9.2, 15, muted)

    output = BytesIO()
    page = Canvas(output, pagesize=A4, pageCompression=1, invariant=1)
    page.setTitle(note["title"])
    page.setSubject(note["subtitle"] or "碳酸锂结构模型机制演示")

    def paragraph(value, paragraph_style, x, top, width):
        block = Paragraph(paragraph_markup(value), paragraph_style)
        _, height = block.wrap(width, page_height)
        block.drawOn(page, x, top - height)
        return top - height

    y = page_height - 53
    page.setFillColor(accent)
    page.rect(margin, y + 10, 30, 3, stroke=0, fill=1)
    y = paragraph(note["title"], title, margin, y, text_width)
    if note["subtitle"]:
        y = paragraph(note["subtitle"], subtitle, margin, y - 2, text_width)
    y -= 9
    page.setStrokeColor(rule)
    page.setLineWidth(0.6)
    page.line(margin, y, page_width - margin, y)
    y -= 15
    if note["lead"]:
        y = paragraph(note["lead"], lead, margin, y, text_width) - 16

    for index, (label, paragraphs) in enumerate(note["sections"], 1):
        y = paragraph(f"{index:02d}  {label}", heading, margin, y, text_width) - 3
        for position, line in enumerate(paragraphs):
            if position:
                y -= 4
            y = paragraph(line, body, margin, y, text_width)
        y -= 14

    if note["footer"]:
        # Keep the source/scope note adjacent to the explanation, even on a short page.
        page.setStrokeColor(rule)
        page.line(margin, y, page_width - margin, y)
        y = paragraph(note["footer"], footnote, margin, y - 8, text_width)
    if y < 42:
        raise ValueError("The note does not fit one page at the intended type size. Shorten the text.")

    page.showPage()
    page.save()
    content = output.getvalue()
    if len(PdfReader(BytesIO(content)).pages) != 1:
        raise ValueError("Expected one A4 PDF page")
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 note JSON")
    parser.add_argument("--output", required=True, type=Path, help="Path to the new single-page PDF")
    parser.add_argument("--font", type=Path, help="Optional path to a Chinese TTF/TTC font")
    args = parser.parse_args()
    note = read_note(args.input)
    register_fonts(args.font)
    content = render(note)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(content)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
