from __future__ import annotations

import json
from pathlib import Path

import pytest

from paper_review_harbor.assessment import AssessmentContractError, validate_assessment
from paper_review_harbor.corpus import discover_paper
from paper_review_harbor.source_archive import (
    SourceArchiveError,
    build_source_archive,
    plan_source_archive_publish,
    retire_runtime_sources,
    upload_source_archive,
)
from paper_review_harbor.spec import TaskSpec


def test_source_archive_preserves_original_inputs_and_registry(
    corpus: Path, tmp_path: Path
) -> None:
    (version,) = discover_paper(corpus / "solution-p0001")
    spec = TaskSpec(
        label=version.label,
        paper_url="https://example.org/paper",
        paper_doi="10.1000/example",
        paper_license="CC-BY-4.0",
        related_writing_task_ids=["lspr-0003"],
    )
    archive = tmp_path / "source-archive"
    records = build_source_archive(
        [version], {version.label: spec}, build=tmp_path / "build", destination=archive
    )

    assert len(records) == 1
    record = records[0]
    assert record.source_record_id.startswith(f"prb-{version.label}-")
    assert record.related_writing_task_ids == ["lspr-0003"]
    original_plan = archive / "sources" / record.source_record_id / "collection-input" / "plan.md"
    assert original_plan.is_file()
    manifest = [
        json.loads(line) for line in (archive / "source-records.jsonl").read_text().splitlines()
    ]
    assert manifest[0]["doi"] == "10.1000/example"
    assert manifest[0]["source_record_id"] == record.source_record_id


def test_source_archive_refuses_public_raw_material(corpus: Path, tmp_path: Path) -> None:
    (version,) = discover_paper(corpus / "bare_tex")
    spec = TaskSpec(label=version.label, source_access="public")
    with pytest.raises(SourceArchiveError, match="must be restricted"):
        build_source_archive(
            [version],
            {version.label: spec},
            build=tmp_path / "build",
            destination=tmp_path / "archive",
        )


def test_source_archive_publish_dry_run_requires_private_repo(tmp_path: Path, monkeypatch) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "source-records.jsonl").write_text("{}\n")
    plan = plan_source_archive_publish(archive, "org/source-archive", revision="release-v1")
    monkeypatch.setattr("paper_review_harbor.source_archive.shutil.which", lambda _: "/usr/bin/hf")
    commands = upload_source_archive(plan)
    assert "hf repo create org/source-archive --repo-type dataset --private --exist-ok" in commands
    assert "hf upload --repo-type dataset --revision release-v1" in commands


def test_runtime_source_retirement_is_explicit_and_tied_to_an_archive(monkeypatch) -> None:
    monkeypatch.setattr("paper_review_harbor.source_archive.shutil.which", lambda _: "/usr/bin/hf")
    command = retire_runtime_sources(
        "org/exam",
        source_archive_repo_id="org/source-archive",
        source_archive_revision="a" * 40,
    )
    assert "hf repos delete-files org/exam papers/** --type dataset --revision main" in command
    assert "org/source-archive@" + "a" * 40 in command


def test_assessment_contract_is_private_metadata_not_a_task_reward() -> None:
    record = validate_assessment(
        {
            "schema_version": 1,
            "assessment_id": "assessment-001",
            "source_record_id": "prb-task-0123456789abcdef",
            "task_id": "task",
            "task_revision": "a" * 40,
            "trail_id": "task/20260101T000000Z",
            "rubric_version": "v1",
            "assessor_id": "expert-07",
            "criteria": {"grounding": 4, "correctness": 5, "coverage": 3, "actionability": 4},
            "overall_score": 4,
            "rationale": "The findings are grounded and actionable.",
        }
    )
    assert record["criteria"]["correctness"] == 5
    with pytest.raises(AssessmentContractError):
        validate_assessment({"schema_version": 1})
