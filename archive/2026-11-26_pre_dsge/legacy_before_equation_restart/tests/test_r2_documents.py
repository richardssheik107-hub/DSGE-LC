"""Portable R2 publication checks; never run estimation or rebuild private artifacts.

The optional output inspection only reads an already-generated, ignored local run.
A missing private run is a SKIP, not evidence that document production passed.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import pytest
import numpy as np
from docx import Document

from scripts.build_r2_advisor_documents import MARKER, figures
from src.structural.equations import transition
from src.structural.matrices import system_matrices


ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs/thesis/advisor_draft.md"
BUILDER = ROOT / "scripts/build_r2_advisor_documents.py"
RUN_ID = "R2_20000101_000000"  # figure-contract keys only; no artifact is read
PRIVATE_ROOT = ROOT / "outputs/thesis"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_canonical_figure_and_private_table_contract() -> None:
    source = DRAFT.read_text(encoding="utf-8")
    keys = MARKER.findall(source)
    assert len(keys) == 11
    assert len(set(keys)) == len(keys)
    assert set(keys) == set(figures(RUN_ID))
    assert source.count("<!-- R2_TABLE:CORE_DESCRIPTION -->") == 1
    assert "outputs/thesis/" not in source  # private figures stay out of Git


def test_frozen_result_claims_and_scope_are_still_visible() -> None:
    source = DRAFT.read_text(encoding="utf-8")
    # These are rounded, descriptive R1 claims, not new estimates.
    for claim in ("8.91%", "21.30%", "4.90%", "64.89%", "0.914", "1.240", "1.131"):
        assert claim in source
    assert re.search(r"\|\s*12\s*\|\s*8\.91\s*\|\s*21\.30\s*\|\s*4\.90\s*\|\s*64\.89\s*\|", source)
    assert re.search(r"\|\s*结构模型\s*\|\s*1\s*\|\s*21\s*\|[^\n]*\|\s*0\.914\s*\|", source)
    assert "2024—2025" in source
    assert "BVAR" in source
    assert "五状态" in source
    assert "不称完整DSGE" in source  # narrative retains explicit interpretation limits


def test_all_numbered_citations_resolve_to_the_20_item_bibliography() -> None:
    body, references = DRAFT.read_text(encoding="utf-8").rsplit("\n# ", 1)
    defined = {int(value) for value in re.findall(r"^\[(\d+)\] ", references, re.MULTILINE)}
    assert defined == set(range(1, 21))
    cited: set[int] = set()
    for bracket in re.findall(r"\[([0-9,\-\s]+)\]", body):
        for element in bracket.split(","):
            value = element.strip()
            if "-" in value:
                first, last = map(int, value.split("-", 1))
                assert first <= last
                cited.update(range(first, last + 1))
            elif value:
                cited.add(int(value))
    assert cited == defined


def test_document_builder_is_publication_only() -> None:
    source = BUILDER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported.update(
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert not imported.intersection({"src", "pymc", "emcee", "cmdstanpy", "numpyro", "arviz"})
    assert "np.load(" not in source
    assert not re.search(r"\.(?:fit|sample|optimize|mcmc)\s*\(", source)
    assert "input_checks()" in source
    assert "before != after" in source


def test_appendix_m0_matrices_match_ordered_equations() -> None:
    p = dict(rho_d=.73, rho_c=.59, rho_q=.55, rho_n=.80, rho_p=.27,
             a_p=.35, a_c=.06, b_d=.15, b_c=.36, b_q=.12, b_n=.034,
             sigma_d=.65, sigma_c=.86, sigma_q=.76, sigma_p=.80)
    wd = p["b_d"] * p["rho_d"] + p["b_n"]
    wc = p["b_c"] * p["rho_c"] + p["b_q"] * p["a_c"]
    wq = -p["b_q"] * p["rho_q"] - p["b_n"]
    a_expected = np.array([
        [p["rho_d"], 0, 0, 0, 0],
        [0, p["rho_c"], 0, 0, 0],
        [0, -p["a_c"], p["rho_q"], 0, p["a_p"]],
        [-1, 0, 1, p["rho_n"], 0],
        [wd, wc, wq, -p["b_n"] * p["rho_n"], p["rho_p"] - p["b_q"] * p["a_p"]],
    ])
    b_expected = np.array([
        [p["sigma_d"], 0, 0, 0],
        [0, p["sigma_c"], 0, 0],
        [0, 0, p["sigma_q"], 0],
        [0, 0, 0, 0],
        [p["b_d"] * p["sigma_d"], p["b_c"] * p["sigma_c"],
         -p["b_q"] * p["sigma_q"], p["sigma_p"]],
    ])
    a_actual, b_actual, _, _ = system_matrices("M0_CORE5", p)
    assert np.allclose(a_expected, a_actual)
    assert np.allclose(b_expected, b_actual)
    rng = np.random.default_rng(20260917)
    for _ in range(10):
        lag, shocks = rng.normal(size=5), rng.normal(size=4)
        assert np.allclose(transition("M0_CORE5", lag, shocks, p),
                           a_expected @ lag + b_expected @ shocks)


def test_existing_private_docx_has_editable_content_and_traceable_figures() -> None:
    runs = sorted(
        path for path in PRIVATE_ROOT.glob("R2_*")
        if path.is_dir() and (path / "文件与结果来源清单.json").is_file()
    )
    if not runs:
        pytest.skip("Private R2 publication run is absent; no DOCX readiness is inferred")
    output = runs[-1]
    thesis = output / "论文初稿.docx"
    note = output / "给导师审阅说明.docx"
    manifest_path = output / "文件与结果来源清单.json"
    assert thesis.is_file() and note.is_file(), "Latest private run is incomplete"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == output.name
    assert len(manifest["figures"]) == 11
    assert manifest["canonical_markdown_sha256"] == sha256(DRAFT)
    assert manifest["output_sha256"]["论文初稿.docx"] == sha256(thesis)
    assert manifest["output_sha256"]["给导师审阅说明.docx"] == sha256(note)
    for item in manifest["figures"].values():
        assert item["license"] == "PRIVATE_ADVISOR_USE_ONLY_NOT_FOR_PUBLIC_GIT"
        assert sha256(ROOT / item["path"]) == item["sha256"]
        for source_path, expected in item["source_sha256"].items():
            assert sha256(ROOT / source_path) == expected

    document = Document(thesis)
    assert len(document.tables) >= 10  # native Word tables, not flattened page images
    assert len(document.inline_shapes) == 11
    assert sum(bool(p._p.xpath(".//m:oMath")) for p in document.paragraphs) >= 20
    text = "\n".join(p.text for p in document.paragraphs)
    assert "R2_FIGURE" not in text and "R2_TABLE" not in text
    assert all(f"第{n}章" in text for n in "一二三四五六七八九")
    assert "参考文献" in text
