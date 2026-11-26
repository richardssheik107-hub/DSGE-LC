"""Render every page of a private R3 PDF for human visual inspection."""
from __future__ import annotations

import argparse
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf', type=Path)
    args = parser.parse_args()
    pdf = args.pdf.resolve()
    if not pdf.is_file() or 'outputs' not in pdf.parts or 'thesis' not in pdf.parts:
        raise ValueError('Expected a private outputs/thesis PDF')
    dest = pdf.parent / 'qa_pages'
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f'Refusing to overwrite page images: {dest}')
    dest.mkdir(exist_ok=True)
    document = pdfium.PdfDocument(str(pdf))
    pages = []
    for index in range(len(document)):
        page = document[index].render(scale=1.5).to_pil().convert('RGB')
        page.save(dest / f'page_{index+1:02d}.png')
        pages.append(page)
    for start in range(0, len(pages), 4):
        thumb_width = 700
        thumbs = []
        for page in pages[start:start+4]:
            thumb_height = round(page.height * thumb_width / page.width)
            thumbs.append(page.resize((thumb_width, thumb_height)))
        sheet = Image.new('RGB', (thumb_width * 2, thumbs[0].height * 2), 'white')
        for offset, thumb in enumerate(thumbs):
            sheet.paste(thumb, ((offset % 2) * thumb_width, (offset // 2) * thumb.height))
        sheet.save(dest / f'sheet_{start//4+1}.png')
    print(f'Rendered {len(pages)} pages to {dest}')


if __name__ == '__main__':
    main()
