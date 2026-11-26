"""Finalize local R2 document provenance after Word updates the TOC and exports PDFs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from build_r2_advisor_documents import ROOT, digest, input_checks


def pdf_pages(path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], capture_output=True, check=True)
    match = re.search(rb"^Pages:\s*(\d+)\s*$", result.stdout, re.MULTILINE)
    if not match:
        raise ValueError(f"Cannot verify PDF page count: {path}")
    return int(match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"R2_\d{8}_\d{6}", args.run_id):
        raise ValueError("Invalid R2 run ID")
    outdir = ROOT / "outputs/thesis" / args.run_id
    manifest_path = outdir / "文件与结果来源清单.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["run_id"] != args.run_id:
        raise ValueError("Run ID mismatch")
    if manifest["canonical_markdown_sha256"] != digest(ROOT / manifest["canonical_markdown"]):
        raise ValueError("Canonical manuscript changed after document generation")
    if input_checks() != manifest["input_checks"]:
        raise ValueError("Frozen inputs changed after document generation")
    for figure in manifest["figures"].values():
        if digest(ROOT / figure["path"]) != figure["sha256"]:
            raise ValueError(f"Figure changed: {figure['path']}")
        for source, sha256 in figure["source_sha256"].items():
            if digest(ROOT / source) != sha256:
                raise ValueError(f"Figure source changed: {source}")
    names = ("论文初稿.docx", "论文初稿.pdf", "给导师审阅说明.docx", "给导师审阅说明.pdf")
    if any(not (outdir / name).is_file() for name in names):
        raise FileNotFoundError("All four DOCX/PDF deliverables must exist")
    manifest["output_sha256"] = {name: digest(outdir / name) for name in names}
    manifest["output_size_bytes"] = {name: (outdir / name).stat().st_size for name in names}
    manifest["pdf_page_counts"] = {name: pdf_pages(outdir / name) for name in names if name.endswith(".pdf")}
    manifest["export_note"] = "Word COM updated the editable TOC and saved DOCX before PDF export; hashes above are post-export."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "pdf_page_counts": manifest["pdf_page_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
