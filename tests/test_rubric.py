from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from paper_review_harbor.rubric import (
    Protocol,
    Rubric,
    RubricError,
    Severity,
    Status,
    load_rubric,
)

GOOD_ACCEPT = (
    "States that the manuscript presents as its own a result already obtained by "
    "Luo-Yang-Zhu, or that the title claims priority the body disclaims."
)


def make(**overrides) -> dict:
    finding = {
        "id": "F1",
        "title": "Title over-claims priority",
        "severity": "major",
        "gating": True,
        "detectability": "high",
        "protocols": ["offline", "online"],
        "location": "main.tex:26-28",
        "claim": "The title presents the negative answer as this paper's result.",
        "defect": "Luo-Yang-Zhu obtained the same conclusion first; the body concedes it.",
        "accept_if": GOOD_ACCEPT,
        "reject_if": "Merely suggests discussing related work more fully.",
    }
    finding.update(overrides.pop("finding", {}))
    data = {
        "task_id_base": "erdos973--v1",
        "paper": {"slug": "erdos973", "version": "v1"},
        "status": "annotated",
        "annotator": "jieke",
        "annotated_at": "2026-08-31",
        "findings": [finding],
    }
    data.update(overrides)
    return data


class TestSchema:
    def test_round_trips(self, tmp_path: Path) -> None:
        rubric = Rubric.model_validate(make())
        path = tmp_path / "r.yaml"
        rubric.save(path)
        assert Rubric.load(path) == rubric

    def test_task_id_must_match_paper(self) -> None:
        with pytest.raises(ValidationError, match="does not match paper label"):
            Rubric.model_validate(make(task_id_base="wrong--v1"))

    def test_finding_ids_are_unique(self) -> None:
        data = make()
        data["findings"] = data["findings"] + [dict(data["findings"][0])]
        with pytest.raises(ValidationError, match="duplicate finding ids"):
            Rubric.model_validate(data)

    def test_finding_id_shape_is_enforced(self) -> None:
        with pytest.raises(ValidationError, match="must look like F1"):
            Rubric.model_validate(make(finding={"id": "first"}))

    def test_minor_defect_cannot_be_gating(self) -> None:
        """Gating means a review that misses it has failed. A typo is not that."""
        with pytest.raises(ValidationError, match="minor defect cannot be gating"):
            Rubric.model_validate(make(finding={"severity": "minor", "gating": True}))

    def test_unknown_keys_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Rubric.model_validate(make(finding={"sevrity": "major"}))


class TestProtocolViews:
    def test_online_only_finding_is_invisible_offline(self) -> None:
        data = make()
        data["findings"].append(
            {
                "id": "F2",
                "title": "Misses a superseding theorem",
                "severity": "major",
                "gating": True,
                "protocols": ["online"],
                "location": "section 1",
                "claim": "Claims the bound is the best known.",
                "defect": "A 2026 preprint already improved it.",
                "accept_if": "Identifies that a stronger published bound exists and names it.",
            }
        )
        rubric = Rubric.model_validate(data)
        assert [f.id for f in rubric.findings_for(Protocol.OFFLINE)] == ["F1"]
        assert [f.id for f in rubric.findings_for(Protocol.ONLINE)] == ["F1", "F2"]
        assert [f.id for f in rubric.gating_for(Protocol.OFFLINE)] == ["F1"]


class TestRelease:
    def test_annotated_rubric_is_releasable(self) -> None:
        assert Rubric.model_validate(make()).release_problems() == []

    def test_draft_is_refused(self) -> None:
        rubric = Rubric.model_validate(make(status="draft", annotator=None, annotated_at=None))
        problems = rubric.release_problems()
        assert any("must review the draft" in p for p in problems)
        with pytest.raises(RubricError, match="not ready to emit"):
            rubric.assert_releasable()

    def test_annotated_without_annotator_is_refused(self) -> None:
        rubric = Rubric.model_validate(make(annotator=None))
        assert any("no annotator" in p for p in rubric.release_problems())

    def test_protocol_without_a_gating_finding_is_refused(self) -> None:
        """Reward is gating recall; with no gating finding it is undefined."""
        rubric = Rubric.model_validate(make(finding={"protocols": ["online"]}))
        problems = rubric.release_problems()
        assert any("'offline' has no gating finding" in p for p in problems)
        assert not any("'online' has no gating finding" in p for p in problems)

    def test_stub_accept_if_is_refused(self) -> None:
        rubric = Rubric.model_validate(make(finding={"accept_if": "TODO"}))
        assert any("accept_if is 4 chars" in p for p in rubric.release_problems())

    def test_findingless_rubric_is_refused(self) -> None:
        rubric = Rubric.model_validate(make(findings=[]))
        assert any("no findings" in p for p in rubric.release_problems())


class TestPrivacy:
    def test_public_view_drops_provenance_and_notes(self) -> None:
        data = make(
            provenance=[
                {"kind": "version-diff", "detail": "v2 retitled to drop the priority claim"}
            ],
            notes="ask Kun about the affiliation line",
        )
        view = Rubric.model_validate(data).public_view()
        blob = repr(view)
        assert "provenance" not in view
        assert "v2 retitled" not in blob
        assert "ask Kun" not in blob
        assert view["findings"][0]["accept_if"] == GOOD_ACCEPT


def test_load_rubric_reports_a_useful_path(tmp_path: Path) -> None:
    with pytest.raises(RubricError, match="Run `/paper2task` to draft one"):
        load_rubric(tmp_path, "nothing--v1")


def test_status_and_severity_are_closed_vocabularies() -> None:
    assert set(Status) == {Status.DRAFT, Status.ANNOTATED}
    assert Severity("blocking") is Severity.BLOCKING
    assert date.fromisoformat("2026-08-31")


class TestCommittedRubrics:
    """Every rubric in rubrics/ must at least be schema-valid, whatever its
    sign-off status."""

    def _paths(self, repo_root: Path) -> list[Path]:
        directory = repo_root / "rubrics"
        return sorted(directory.glob("*.yaml")) if directory.is_dir() else []

    def test_all_parse(self, repo_root: Path) -> None:
        for path in self._paths(repo_root):
            rubric = Rubric.load(path)
            assert rubric.task_id_base == path.stem

    def test_annotated_ones_are_releasable(self, repo_root: Path) -> None:
        for path in self._paths(repo_root):
            rubric = Rubric.load(path)
            if rubric.is_annotated:
                assert rubric.release_problems() == [], path.name

    def test_drafts_are_unsigned(self, repo_root: Path) -> None:
        """A draft carrying a signature is the failure mode that would let an
        unreviewed rubric emit as ground truth."""
        for path in self._paths(repo_root):
            rubric = Rubric.load(path)
            if not rubric.is_annotated:
                assert rubric.annotator is None, path.name
                assert rubric.annotated_at is None, path.name
