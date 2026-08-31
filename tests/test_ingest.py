from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from paper_review_harbor.corpus import discover, discover_paper
from paper_review_harbor.emit import EmitConfig, emit_task
from paper_review_harbor.ingest import (
    STAGED_PDF_NAME,
    IngestError,
    find_main_tex,
    ingest,
    latex_to_text,
    strip_tex_comments,
)
from paper_review_harbor.spec import TaskSpec


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


class TestStagedPdf:
    """A reviewer reads the PDF; eleven tasks used to ship none."""

    def test_sibling_pdf_is_staged_when_the_bundle_has_none(
        self, corpus: Path, tmp_path: Path
    ) -> None:
        v1, _, _ = discover_paper(corpus / "multi_version")
        result = ingest(v1, tmp_path / "build")
        assert (result.root / STAGED_PDF_NAME).is_file()

    def test_staged_name_does_not_leak_the_version(self, corpus: Path, tmp_path: Path) -> None:
        """`v1.pdf` in the environment would tell the agent to look for a v2."""
        v1, _, _ = discover_paper(corpus / "multi_version")
        result = ingest(v1, tmp_path / "build")
        assert [p.name for p in result.root.glob("*.pdf")] == [STAGED_PDF_NAME]

    def test_a_bundled_pdf_is_left_alone(self, corpus: Path, tmp_path: Path) -> None:
        """The manuscript layout already carries main.pdf beside its source."""
        (version,) = discover_paper(corpus / "solution-p0001")
        result = ingest(version, tmp_path / "build")
        names = {p.name for p in result.root.glob("*.pdf")}
        assert names == {"main.pdf"}, "an existing PDF must not be duplicated"

    def test_root_level_figure_does_not_suppress_the_corpus_pdf(
        self, corpus: Path, tmp_path: Path
    ) -> None:
        """A figure PDF is not evidence that the archive bundled a manuscript."""
        source = corpus / "single_archive" / "source.zip"
        with zipfile.ZipFile(source, "a") as zipped:
            zipped.writestr("arbitrary-figure.pdf", "%PDF-1.4 fake figure")

        (version,) = discover_paper(corpus / "single_archive")
        assert version.pdf == corpus / "single_archive" / "single_archive.pdf"
        result = ingest(version, tmp_path / "build")
        staged_pdf = result.root / STAGED_PDF_NAME
        assert staged_pdf.read_bytes() == version.pdf.read_bytes()
        assert staged_pdf.read_bytes() != b"%PDF-1.4 fake figure"

        task_dir = emit_task(
            result,
            TaskSpec.default_for(version.label),
            EmitConfig(tasks_root=tmp_path / "tasks"),
        )
        instruction = (task_dir / "instruction.md").read_text(encoding="utf-8")
        assert "`paper.pdf` as the compiled PDF" in instruction

    def test_source_bundled_main_pdf_is_preferred_over_the_corpus_pdf(
        self, corpus: Path, tmp_path: Path
    ) -> None:
        """Archive authors sometimes include main.pdf alongside arbitrary figures."""
        source = corpus / "single_archive" / "source.zip"
        with zipfile.ZipFile(source, "a") as zipped:
            zipped.writestr("main.pdf", "%PDF-1.4 bundled manuscript")
            zipped.writestr("arbitrary-figure.pdf", "%PDF-1.4 fake figure")

        (version,) = discover_paper(corpus / "single_archive")
        result = ingest(version, tmp_path / "build")
        assert result.manuscript_pdf == "main.pdf"
        assert (result.root / "main.pdf").read_bytes() == b"%PDF-1.4 bundled manuscript"
        assert not (result.root / STAGED_PDF_NAME).exists()

        task_dir = emit_task(
            result,
            TaskSpec.default_for(version.label),
            EmitConfig(tasks_root=tmp_path / "tasks"),
        )
        instruction = (task_dir / "instruction.md").read_text(encoding="utf-8")
        assert "`main.pdf` as the compiled PDF" in instruction

    @pytest.mark.parametrize("name", ["paper.pdf", "manuscript.pdf"])
    def test_archive_canonical_pdf_is_preferred_over_the_external_sibling(
        self, corpus: Path, tmp_path: Path, name: str
    ) -> None:
        source = corpus / "single_archive" / "source.zip"
        bundled = f"%PDF-1.4 bundled {name}".encode()
        with zipfile.ZipFile(source, "a") as zipped:
            zipped.writestr(name, bundled)

        (version,) = discover_paper(corpus / "single_archive")
        result = ingest(version, tmp_path / "build")
        assert result.manuscript_pdf == name
        assert (result.root / name).read_bytes() == bundled
        assert (result.root / name).read_bytes() != version.pdf.read_bytes()

    def test_archive_pdf_matching_the_detected_tex_is_preferred(
        self, corpus: Path, tmp_path: Path
    ) -> None:
        source = corpus / "single_archive" / "source.zip"
        bundled = b"%PDF-1.4 bundled article"
        with zipfile.ZipFile(source, "w") as zipped:
            zipped.writestr(
                "article.tex", "\\documentclass{article}\\begin{document}x\\end{document}"
            )
            zipped.writestr("article.pdf", bundled)

        (version,) = discover_paper(corpus / "single_archive")
        result = ingest(version, tmp_path / "build")
        assert result.main_tex == "article.tex"
        assert result.manuscript_pdf == "article.pdf"
        assert (result.root / "article.pdf").read_bytes() == bundled
        assert not (result.root / STAGED_PDF_NAME).exists()

    def test_archive_declared_pdf_is_preferred_over_canonical_names(
        self, corpus: Path, tmp_path: Path
    ) -> None:
        source = corpus / "single_archive" / "source.zip"
        declared = b"%PDF-1.4 bundled release"
        with zipfile.ZipFile(source, "w") as zipped:
            zipped.writestr(
                "main.tex",
                "\\documentclass{article}\n"
                "% paper-review-harbor: manuscript-pdf=release.pdf\n"
                "\\begin{document}x\\end{document}",
            )
            zipped.writestr("main.pdf", b"%PDF-1.4 generic")
            zipped.writestr("release.pdf", declared)

        (version,) = discover_paper(corpus / "single_archive")
        result = ingest(version, tmp_path / "build")
        assert result.manuscript_pdf == "release.pdf"
        assert (result.root / "release.pdf").read_bytes() == declared
        assert not (result.root / STAGED_PDF_NAME).exists()

    def test_real_source_bundled_pdf_is_preserved(
        self, real_papers: Path, tmp_path: Path
    ) -> None:
        """This corpus manuscript uses a meaningful PDF name instead of main.pdf."""
        (version,) = discover_paper(real_papers / "de_novo_nanobody_discovery")
        result = ingest(version, tmp_path / "build")
        assert result.manuscript_pdf == "VHHreport.pdf"

        task_dir = emit_task(
            result,
            TaskSpec.default_for(version.label),
            EmitConfig(tasks_root=tmp_path / "tasks"),
        )
        instruction = (task_dir / "instruction.md").read_text(encoding="utf-8")
        assert "`VHHreport.pdf` as the compiled PDF" in instruction

    def test_every_real_task_ships_a_rendered_paper(
        self, real_papers: Path, tmp_path: Path
    ) -> None:
        for version in discover(real_papers):
            result = ingest(version, tmp_path / "build")
            assert list(result.root.glob("*.pdf")), version.label


class TestLatexToText:
    """Titles reach metadata, the instruction and the dataset card -- all read
    by people, so raw LaTeX in them is a defect."""

    def test_accents_compose(self) -> None:
        assert latex_to_text(r"Erd\H{o}s Problem 973") == "Erdős Problem 973"
        assert latex_to_text(r"Schr\"{o}dinger") == "Schrödinger"
        assert latex_to_text(r"caf\'{e}") == "café"

    def test_accent_without_braces(self) -> None:
        assert latex_to_text(r"Erd\H os") == "Erdős"

    def test_texorpdfstring_takes_the_plain_form(self) -> None:
        """Its second argument exists precisely to be the readable one."""
        assert latex_to_text(r"Type-\texorpdfstring{$B$}{B} Posets") == "Type-B Posets"

    def test_math_delimiters_go_but_content_stays(self) -> None:
        assert latex_to_text(r"$R$-matrices") == "R-matrices"

    def test_dashes_become_dashes(self) -> None:
        assert latex_to_text("Fuss--Catalan") == "Fuss–Catalan"
        assert latex_to_text("a---b") == "a—b"

    def test_escaped_specials_survive(self) -> None:
        assert latex_to_text(r"50\% \& more") == "50% & more"

    def test_unknown_macro_is_left_visible(self) -> None:
        """A silent drop would be worse: only a visible one gets noticed."""
        assert "\\unknownmacro" in latex_to_text(r"\unknownmacro{x}")

    def test_no_corpus_title_carries_latex(self, real_papers: Path, tmp_path: Path) -> None:
        offenders = {}
        for version in discover(real_papers):
            title = ingest(version, tmp_path / "build").paper_map.title
            if title and re.search(r"\\[a-zA-Z]|[${}]", title):
                offenders[version.label] = title
        assert offenders == {}
