from __future__ import annotations

from pathlib import Path

import pytest

from paper_review_harbor.corpus import (
    PRIVATE_BASENAMES,
    CorpusError,
    discover,
    discover_paper,
)


def labels(root: Path) -> list[str]:
    return [version.label for version in discover(root)]


def test_discovers_every_shape(corpus: Path) -> None:
    assert labels(corpus) == [
        "bare_tex",
        "multi_version--v1",
        "multi_version--v2",
        "multi_version--v3",
        "single_archive",
        "solution-p0001",
    ]


def test_multi_version_yields_one_task_per_version(corpus: Path) -> None:
    versions = discover_paper(corpus / "multi_version")
    assert [v.version for v in versions] == ["v1", "v2", "v3"]
    assert all(v.source_kind == "archive" for v in versions)
    assert all(v.pdf is not None for v in versions)


def test_later_versions_are_private_for_earlier_ones(corpus: Path) -> None:
    """A later version is a worked answer key for the earlier one."""
    v1, v2, v3 = discover_paper(corpus / "multi_version")
    assert {p.name for p in v1.private_paths} == {
        "v2-source.tar.gz",
        "v2.pdf",
        "v3-source.tar.gz",
        "v3.pdf",
    }
    assert {p.name for p in v2.private_paths} == {"v3-source.tar.gz", "v3.pdf"}
    assert v3.private_paths == ()


def test_manuscript_trail_is_private(corpus: Path) -> None:
    (version,) = discover_paper(corpus / "solution-p0001")
    names = {p.name for p in version.private_paths}
    assert "review" in names
    assert "plan.md" in names


def test_unverified_bib_is_not_private(corpus: Path) -> None:
    """It is a build input: the manuscript does \\bibliography{references,unverified}.

    Treating it as private breaks compilation and manufactures
    undefined-citation defects the authors never committed.
    """
    assert "unverified.bib" not in PRIVATE_BASENAMES
    (version,) = discover_paper(corpus / "solution-p0001")
    assert all(p.name != "unverified.bib" for p in version.private_paths)


def test_unrecognised_directory_is_an_error(tmp_path: Path) -> None:
    empty = tmp_path / "papers" / "nothing"
    empty.mkdir(parents=True)
    with pytest.raises(CorpusError, match="no recognised paper source"):
        discover_paper(empty)


def test_real_corpus_has_twenty_one_versions(real_papers: Path) -> None:
    """17 papers / 21 version tasks, per docs/STATUS_REPORT.md."""
    versions = discover(real_papers)
    assert len(versions) == 21
    assert len({v.slug for v in versions}) == 17
