"""Discover reviewable paper versions in the corpus.

The corpus grew by hand, so `papers/` holds four unrelated directory shapes.
Every one of them has to end up as the same thing: a *paper version* that can
be reviewed independently, plus the list of sibling files that would hand the
answer to a review agent if they ever reached its container.

    <slug>/vN-source.tar.gz + vN.pdf        multi-version arXiv drop
    <slug>/source.{tar.gz,zip} + <slug>.pdf single-version arXiv drop
    <slug>/main.tex + <slug>.pdf            bare TeX
    <slug>/paper/main.tex + review/ + ...   this project's own manuscripts

The private-path logic is the load-bearing part. A later version of a paper is
a worked answer key for the earlier one, and `review/`, `plan.md` and
`unverified.bib` are the writing-time defect trail. None of them may be
published into a task environment.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

VERSION_SOURCE_RE = re.compile(r"^v(\d+)-source\.(?:tar\.gz|tgz|zip)$", re.IGNORECASE)
VERSION_PDF_RE = re.compile(r"^v(\d+)\.pdf$", re.IGNORECASE)
MANUSCRIPT_PDF_DECLARATION_RE = re.compile(
    r"^\s*%\s*paper-review-harbor:\s*manuscript-pdf=([A-Za-z0-9][A-Za-z0-9._-]*\.pdf)\s*$",
    re.IGNORECASE,
)

SINGLE_SOURCE_NAMES = ("source.tar.gz", "source.tgz", "source.zip")

#: Filenames inside a manuscript directory that record how the paper was written.
#:
#: `unverified.bib` is deliberately *not* here. Every manuscript that ships one
#: builds against it (`\bibliography{references,unverified}`), so removing it
#: both breaks compilation and manufactures undefined-citation defects that the
#: authors never committed. Its writing-pipeline header comment is stripped
#: during ingestion instead -- see `ingest.strip_bib_preamble`.
PRIVATE_BASENAMES = frozenset({"plan.md"})

#: Directories holding the writing-time internal review (cite_audit, gates,
#: internal_review). This is the closest thing the corpus has to an answer key.
PRIVATE_DIRNAMES = frozenset({"review"})

ARCHIVE_SUFFIXES = (".tar.gz", ".tgz", ".zip")


class CorpusError(RuntimeError):
    """A paper directory does not match any known corpus shape."""


@dataclass(frozen=True)
class PaperVersion:
    """One independently reviewable manuscript."""

    slug: str
    version: str | None
    paper_dir: Path
    source: Path
    source_kind: str  # "archive" | "directory" | "texfile"
    pdf: Path | None
    private_paths: tuple[Path, ...]

    @property
    def label(self) -> str:
        """Stable human-readable id, e.g. ``erdos973--v1`` or ``solution-p8534``."""
        return f"{self.slug}--{self.version}" if self.version else self.slug

    @property
    def is_multi_version(self) -> bool:
        return self.version is not None


def _pdfs(directory: Path, names: list[str]) -> list[Path]:
    """Return root PDFs whose names explicitly associate them with the source.

    A root PDF is not presumed to be a manuscript: source archives frequently
    carry figure assets there. Versioned papers use ``vN.pdf``; other callers
    provide only source stems, canonical manuscript names, project-declared
    PDF names, or matching companion-document stems. Unknown names are left
    unstaged, and the input order defines deterministic preference.
    """
    return [path for name in names if (path := directory / name).is_file()]


def declared_manuscript_pdfs(tex: Path) -> list[str]:
    """Read exact project declarations: `% paper-review-harbor: manuscript-pdf=NAME.pdf`."""
    try:
        lines = tex.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [
        match.group(1)
        for line in lines
        if (match := MANUSCRIPT_PDF_DECLARATION_RE.match(line))
    ]


def _private_in_manuscript_dir(directory: Path) -> list[Path]:
    found: list[Path] = []
    for path in sorted(directory.rglob("*")):
        if path.is_dir():
            if path.name in PRIVATE_DIRNAMES:
                found.append(path)
        elif path.name in PRIVATE_BASENAMES:
            found.append(path)
    # Drop entries already covered by a private directory above them.
    dirs = [p for p in found if p.is_dir()]
    return [p for p in found if p.is_dir() or not any(d in p.parents for d in dirs)]


def _discover_versioned(paper_dir: Path) -> Iterator[PaperVersion]:
    sources: dict[int, Path] = {}
    for path in paper_dir.iterdir():
        match = VERSION_SOURCE_RE.match(path.name)
        if match and path.is_file():
            sources[int(match.group(1))] = path
    if not sources:
        return

    pdfs: dict[int, Path] = {}
    for path in paper_dir.iterdir():
        match = VERSION_PDF_RE.match(path.name)
        if match and path.is_file():
            pdfs[int(match.group(1))] = path

    for number in sorted(sources):
        # Everything belonging to a *later* version is the answer key for this one.
        newer = tuple(
            sorted(
                [path for later, path in sources.items() if later > number]
                + [path for later, path in pdfs.items() if later > number]
            )
        )
        yield PaperVersion(
            slug=paper_dir.name,
            version=f"v{number}",
            paper_dir=paper_dir,
            source=sources[number],
            source_kind="archive",
            pdf=pdfs.get(number),
            private_paths=newer,
        )


def _discover_single_archive(paper_dir: Path) -> PaperVersion | None:
    for name in SINGLE_SOURCE_NAMES:
        candidate = paper_dir / name
        if candidate.is_file():
            pdfs = _pdfs(
                paper_dir,
                [f"{paper_dir.name}.pdf", "accepted-manuscript.pdf", "manuscript.pdf", "paper.pdf"],
            )
            return PaperVersion(
                slug=paper_dir.name,
                version=None,
                paper_dir=paper_dir,
                source=candidate,
                source_kind="archive",
                pdf=pdfs[0] if pdfs else None,
                private_paths=(),
            )
    return None


def _discover_manuscript_dir(paper_dir: Path) -> PaperVersion | None:
    inner = paper_dir / "paper"
    main = inner / "main.tex"
    if not main.is_file():
        return None
    pdfs = _pdfs(inner, [*declared_manuscript_pdfs(main), "main.pdf"])
    return PaperVersion(
        slug=paper_dir.name,
        version=None,
        paper_dir=paper_dir,
        source=inner,
        source_kind="directory",
        pdf=pdfs[0] if pdfs else None,
        private_paths=tuple(_private_in_manuscript_dir(inner)),
    )


def _discover_bare_tex(paper_dir: Path) -> PaperVersion | None:
    main = paper_dir / "main.tex"
    if not main.is_file():
        return None
    companion_stems = sorted(
        path.stem for path in paper_dir.glob("*.md") if path.is_file() and path.name != "info.md"
    )
    pdfs = _pdfs(
        paper_dir,
        ["main.pdf", f"{paper_dir.name}.pdf", *(f"{stem}.pdf" for stem in companion_stems)],
    )
    return PaperVersion(
        slug=paper_dir.name,
        version=None,
        paper_dir=paper_dir,
        source=main,
        source_kind="texfile",
        pdf=pdfs[0] if pdfs else None,
        private_paths=(),
    )


def discover_paper(paper_dir: Path) -> list[PaperVersion]:
    """All reviewable versions in one corpus directory, oldest version first."""
    versioned = list(_discover_versioned(paper_dir))
    if versioned:
        return versioned
    for finder in (_discover_single_archive, _discover_manuscript_dir, _discover_bare_tex):
        found = finder(paper_dir)
        if found is not None:
            return [found]
    raise CorpusError(
        f"{paper_dir}: no recognised paper source. Expected one of "
        f"vN-source.tar.gz, {'/'.join(SINGLE_SOURCE_NAMES)}, paper/main.tex, or main.tex."
    )


def discover(papers_root: Path) -> list[PaperVersion]:
    """Every reviewable paper version under ``papers/``, sorted by label."""
    if not papers_root.is_dir():
        raise CorpusError(f"{papers_root} is not a directory")
    versions: list[PaperVersion] = []
    for entry in sorted(papers_root.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            versions.extend(discover_paper(entry))
    return sorted(versions, key=lambda v: v.label)
