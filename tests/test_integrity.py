from __future__ import annotations

import json

import pytest

from paper_review_harbor.audit import audit_task
from paper_review_harbor.corpus import discover_paper
from paper_review_harbor.emit import EmitConfig, emit_task
from paper_review_harbor.ingest import IngestError, ingest
from paper_review_harbor.integrity import is_lfs_pointer_bytes
from paper_review_harbor.spec import TaskSpec

LFS = b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"a" * 64 + b"\nsize 42\n"


def test_lfs_pointer_requires_complete_structure() -> None:
    assert is_lfs_pointer_bytes(LFS)
    assert is_lfs_pointer_bytes(LFS.replace(b"size 42", b"ext value\nsize 42"))
    assert not is_lfs_pointer_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\n")


def test_ingest_rejects_lfs_pointer_tex(tmp_path) -> None:
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_bytes(LFS)
    (paper / "paper.pdf").write_bytes(b"%PDF-1.4")
    (paper / "main.pdf").write_bytes(b"%PDF-1.4")
    (paper / "main.tex").write_bytes(LFS)
    from paper_review_harbor.corpus import discover_paper

    with pytest.raises(IngestError, match="LFS pointer"):
        ingest(discover_paper(paper)[0], tmp_path / "build")


def test_emitted_manifest_matches_paper(corpus, tmp_path) -> None:
    version = discover_paper(corpus / "bare_tex")[0]
    result = ingest(version, tmp_path / "build")
    task = emit_task(result, TaskSpec.default_for(version.label), EmitConfig(tmp_path / "tasks"))
    manifest = json.loads((task / "material-manifest.json").read_text())
    assert manifest["tree_sha256"]
    assert audit_task(task, version) == []
    (task / "environment" / "paper" / "main.tex").write_text("changed")
    assert any(v.kind == "material-manifest" for v in audit_task(task, version))


def test_ingest_rejects_missing_figure(tmp_path) -> None:
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(
        "\\documentclass{article}\\usepackage{graphicx}\\begin{document}"
        "\\includegraphics{missing}\\end{document}"
    )
    (paper / "paper.pdf").write_bytes(b"%PDF-1.4")
    with pytest.raises(IngestError, match="missing figure"):
        ingest(discover_paper(paper)[0], tmp_path / "build")
