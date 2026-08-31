from __future__ import annotations

import json
from pathlib import Path

import pytest

from paper_review_harbor.corpus import discover, discover_paper
from paper_review_harbor.ingest import (
    IngestError,
    find_main_tex,
    ingest,
    strip_tex_comments,
)


def stage(corpus: Path, name: str, tmp_path: Path):
    (version,) = discover_paper(corpus / name)
    return ingest(version, tmp_path / "build")


class TestStripTexComments:
    def test_removes_comment_to_end_of_line(self) -> None:
        assert strip_tex_comments("keep % drop") == "keep "

    def test_keeps_escaped_percent(self) -> None:
        assert strip_tex_comments(r"92.5\% accuracy") == r"92.5\% accuracy"

    def test_preserves_line_numbering(self) -> None:
        assert strip_tex_comments("a\n% all gone\nb").splitlines() == ["a", "", "b"]

    def test_citation_inside_comment_is_not_a_citation(self) -> None:
        """The bug this exists for: a preamble note explaining \\cite{c,a,b}
        was read as three citations to nonexistent keys."""
        text = r"% Sorts multiple citations, so \cite{c,a,b} prints as [1--3]."
        assert "cite" not in strip_tex_comments(text)


class TestPrivateMaterial:
    def test_writing_trail_never_reaches_staging(self, corpus: Path, tmp_path: Path) -> None:
        result = stage(corpus, "solution-p0001", tmp_path)
        staged = {p.relative_to(result.root).as_posix() for p in result.root.rglob("*")}
        assert not any(name.startswith("review") for name in staged)
        assert "plan.md" not in staged
        assert set(result.excluded) == {"review/", "plan.md"}

    def test_answer_key_text_is_absent_from_staging(self, corpus: Path, tmp_path: Path) -> None:
        result = stage(corpus, "solution-p0001", tmp_path)
        blob = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in result.root.rglob("*")
            if path.is_file() and path.suffix in {".tex", ".bib", ".md"}
        )
        assert "Lemma 3.1 hypothesis is too weak" not in blob

    def test_unverified_bib_survives_but_loses_its_commentary(
        self, corpus: Path, tmp_path: Path
    ) -> None:
        result = stage(corpus, "solution-p0001", tmp_path)
        bib = result.root / "unverified.bib"
        assert bib.is_file(), "removing it would break \\bibliography{references,unverified}"
        text = bib.read_text(encoding="utf-8")
        assert "needs checking before submission" not in text
        assert "@article{jones2021" in text
        assert result.sanitised == ("unverified.bib",)


class TestMainTexDetection:
    def test_prefers_arxiv_declared_toplevel(self, tmp_path: Path) -> None:
        root = tmp_path / "paper"
        root.mkdir()
        (root / "00README.json").write_text(
            json.dumps({"sources": [{"usage": "toplevel", "filename": "letter.tex"}]}),
            encoding="utf-8",
        )
        for name in ("letter.tex", "main.tex"):
            (root / name).write_text(
                "\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8"
            )
        assert find_main_tex(root) == "letter.tex"

    def test_falls_back_to_documentclass_scan(self, tmp_path: Path) -> None:
        root = tmp_path / "paper"
        root.mkdir()
        (root / "helper.tex").write_text("\\section{x}", encoding="utf-8")
        (root / "main.tex").write_text(
            "\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8"
        )
        assert find_main_tex(root) == "main.tex"

    def test_errors_when_no_toplevel_exists(self, tmp_path: Path) -> None:
        root = tmp_path / "paper"
        root.mkdir()
        (root / "fragment.tex").write_text("\\section{x}", encoding="utf-8")
        with pytest.raises(IngestError, match="documentclass"):
            find_main_tex(root)


class TestRealCorpus:
    def test_every_version_ingests(self, real_papers: Path, tmp_path: Path) -> None:
        for version in discover(real_papers):
            result = ingest(version, tmp_path / "build")
            assert result.paper_map.total_tex_lines > 0, version.label
            assert (result.root / result.main_tex).is_file(), version.label

    def test_no_manufactured_undefined_citations(
        self, real_papers: Path, tmp_path: Path
    ) -> None:
        """Regression guard for two real bugs: stripping unverified.bib, and
        reading citations out of TeX comments. Both invented defects."""
        offenders = {}
        for version in discover(real_papers):
            result = ingest(version, tmp_path / "build")
            if result.paper_map.undefined_citations:
                offenders[version.label] = result.paper_map.undefined_citations
        assert offenders == {}
