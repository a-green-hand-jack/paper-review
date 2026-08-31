"""Synthetic corpus fixtures.

The real corpus is used for a few integration checks, but the unit tests build
their own directories so they keep testing the shapes rather than the current
contents of `papers/`.
"""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

MINIMAL_TEX = """\\documentclass{article}
\\begin{document}
\\section{Intro}
Text \\cite{smith2020}.
\\bibliography{references}
\\end{document}
"""


def write_tex(path: Path, body: str = MINIMAL_TEX) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def make_targz(archive: Path, files: dict[str, str]) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    staging = archive.parent / f".staging-{archive.name}"
    staging.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        target = staging / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    with tarfile.open(archive, "w:gz") as tar:
        for name in files:
            tar.add(staging / name, arcname=name)


def make_zip(archive: Path, files: dict[str, str]) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w") as zipped:
        for name, content in files.items():
            zipped.writestr(name, content)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def real_papers(repo_root: Path) -> Path:
    papers = repo_root / "papers"
    if not papers.is_dir():
        pytest.skip("corpus not present")
    return papers


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """A papers/ tree containing one of each recognised shape."""
    root = tmp_path / "papers"

    # 1. multi-version arXiv drop. Each version differs, as real revisions do --
    #    identical versions would make the answer-key audit trivially pass.
    multi = root / "multi_version"
    for number in (1, 2, 3):
        make_targz(
            multi / f"v{number}-source.tar.gz",
            {
                "main.tex": MINIMAL_TEX.replace(
                    "\\section{Intro}", f"\\section{{Intro}}\n% revision {number}"
                ),
                "references.bib": "@article{smith2020, title={T}}",
            },
        )
        (multi / f"v{number}.pdf").write_bytes(f"%PDF-1.4 fake v{number}".encode())

    # 2. single-version archive
    single = root / "single_archive"
    make_zip(single / "source.zip", {"main.tex": MINIMAL_TEX})
    (single / "single_archive.pdf").write_bytes(b"%PDF-1.4 fake")

    # 3. bare TeX
    bare = root / "bare_tex"
    write_tex(bare / "main.tex")
    (bare / "bare_tex.pdf").write_bytes(b"%PDF-1.4 fake")

    # 4. this project's manuscript layout, with its writing-time trail
    manuscript = root / "solution-p0001"
    write_tex(
        manuscript / "paper" / "main.tex",
        MINIMAL_TEX.replace("\\bibliography{references}", "\\bibliography{references,unverified}"),
    )
    (manuscript / "paper" / "references.bib").write_text(
        "@article{smith2020, title={T}}\n", encoding="utf-8"
    )
    (manuscript / "paper" / "unverified.bib").write_text(
        "% Written from what was known, not fetched from a registry.\n"
        "% Every entry here needs checking before submission.\n"
        "\n"
        "@article{jones2021, title={U}, journal={}}\n",
        encoding="utf-8",
    )
    (manuscript / "paper" / "plan.md").write_text("# Writing plan\n", encoding="utf-8")
    review = manuscript / "paper" / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "internal_review.md").write_text("Lemma 3.1 hypothesis is too weak.\n", "utf-8")
    (review / "gates.md").write_text("- Named expert review obtained: open\n", "utf-8")
    (manuscript / "paper" / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    return root
