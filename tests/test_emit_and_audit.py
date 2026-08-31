from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import pytest

from paper_review_harbor.audit import audit_task
from paper_review_harbor.corpus import discover_paper
from paper_review_harbor.emit import EmitConfig, canary_for, dataset_name, emit_task
from paper_review_harbor.ingest import ingest
from paper_review_harbor.rubric import Protocol, Rubric, RubricError

SECRET_ACCEPT = (
    "States that the manuscript presents as its own a result already obtained by "
    "Luo-Yang-Zhu, or that the title claims priority the body disclaims."
)
SECRET_DEFECT = (
    "Luo-Yang-Zhu obtained the same conclusion first and the body quietly concedes it."
)


def rubric_for(label: str, slug: str, version: str | None) -> Rubric:
    return Rubric.model_validate(
        {
            "task_id_base": label,
            "paper": {"slug": slug, "version": version},
            "status": "annotated",
            "annotator": "test",
            "annotated_at": "2026-08-31",
            "provenance": [
                {"kind": "version-diff", "detail": "v2 retitled to drop the priority claim"}
            ],
            "findings": [
                {
                    "id": "F1",
                    "title": "Title over-claims priority over prior work",
                    "severity": "major",
                    "gating": True,
                    "detectability": "high",
                    "protocols": ["offline", "online"],
                    "location": "main.tex:26-28",
                    "claim": "presents the negative answer as its own result in the title.",
                    "defect": SECRET_DEFECT,
                    "accept_if": SECRET_ACCEPT,
                    "reject_if": "Merely suggests discussing related work more fully.",
                },
                {
                    "id": "F2",
                    "title": "Abstract omits the trivial upper bound",
                    "severity": "minor",
                    "gating": False,
                    "detectability": "medium",
                    "protocols": ["offline", "online"],
                    "location": "abstract",
                    "claim": "asserts a limit without stating the bound that witnesses it.",
                    "defect": "The upper bound and its witnessing polynomial are never given.",
                    "accept_if": "Notes that the abstract states a limit without the "
                    "complementary upper bound that makes it meaningful.",
                },
            ],
            "distractors": [
                {
                    "id": "D1",
                    "description": "The paper uses amsart rather than a journal class.",
                    "why_not_a_defect": "Class choice is a submission detail, not a defect.",
                }
            ],
        }
    )


@pytest.fixture
def staged(corpus: Path, tmp_path: Path):
    (version,) = discover_paper(corpus / "solution-p0001")
    result = ingest(version, tmp_path / "build")
    return version, result


@pytest.fixture
def emitted(staged, tmp_path: Path):
    version, result = staged
    rubric = rubric_for("solution-p0001", "solution-p0001", None)
    config = EmitConfig(tasks_root=tmp_path / "tasks")
    task_dir = emit_task(result, rubric, Protocol.OFFLINE, config)
    return version, rubric, task_dir


class TestEmit:
    def test_refuses_an_unsigned_rubric(self, staged, tmp_path: Path) -> None:
        _, result = staged
        data = rubric_for("solution-p0001", "solution-p0001", None).model_dump(mode="json")
        data.update({"status": "draft", "annotator": None, "annotated_at": None})
        draft = Rubric.model_validate(data)
        config = EmitConfig(tasks_root=tmp_path / "tasks")
        with pytest.raises(RubricError, match="status is 'draft'"):
            emit_task(result, draft, Protocol.OFFLINE, config)
        assert not (tmp_path / "tasks").exists(), "a refused emit must leave nothing behind"

    def test_writes_the_harbor_layout(self, emitted) -> None:
        _, _, task_dir = emitted
        for relative in (
            "task.toml",
            "instruction.md",
            "environment/Dockerfile",
            "environment/paper/main.tex",
            "solution/solve.sh",
            "solution/private/reference_review.md",
            "tests/Dockerfile",
            "tests/test.sh",
            "tests/grader_review.py",
            "tests/private/rubric.json",
        ):
            assert (task_dir / relative).is_file(), relative

    def test_entry_scripts_are_executable(self, emitted) -> None:
        _, _, task_dir = emitted
        for relative in ("solution/solve.sh", "tests/test.sh"):
            assert (task_dir / relative).stat().st_mode & 0o111, relative

    def test_task_toml_parses_and_isolates_the_verifier(self, emitted) -> None:
        _, _, task_dir = emitted
        data = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.4"
        assert data["verifier"]["environment_mode"] == "separate"
        assert data["environment"]["network_mode"] == "no-network"
        assert "/workspace/submission" in data["artifacts"]
        assert data["metadata"]["n_gating"] == 1

    def test_online_protocol_opens_only_scholarly_hosts(self, staged, tmp_path: Path) -> None:
        _, result = staged
        rubric = rubric_for("solution-p0001", "solution-p0001", None)
        task_dir = emit_task(
            result, rubric, Protocol.ONLINE, EmitConfig(tasks_root=tmp_path / "tasks")
        )
        data = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
        assert data["environment"]["network_mode"] == "allowlist"
        assert "arxiv.org" in data["environment"]["allowed_hosts"]
        assert "github.com" not in data["environment"]["allowed_hosts"]

    def test_protocols_land_in_separate_datasets(self, staged, tmp_path: Path) -> None:
        _, result = staged
        rubric = rubric_for("solution-p0001", "solution-p0001", None)
        config = EmitConfig(tasks_root=tmp_path / "tasks")
        offline = emit_task(result, rubric, Protocol.OFFLINE, config)
        online = emit_task(result, rubric, Protocol.ONLINE, config)
        assert offline.parent.name == dataset_name(Protocol.OFFLINE)
        assert online.parent.name == dataset_name(Protocol.ONLINE)
        assert offline != online

    def test_canary_is_stable_across_rebuilds(self) -> None:
        first = canary_for("erdos973--v1", Protocol.OFFLINE)
        assert first == canary_for("erdos973--v1", Protocol.OFFLINE)
        assert first != canary_for("erdos973--v1", Protocol.ONLINE)

    def test_reward_would_be_defined(self, emitted) -> None:
        """A protocol with no gating finding makes gating recall a 0/0."""
        _, rubric, _ = emitted
        assert rubric.gating_for(Protocol.OFFLINE)


class TestAuditPasses:
    def test_clean_task_has_no_violations(self, emitted) -> None:
        version, rubric, task_dir = emitted
        assert audit_task(task_dir, rubric, version) == []

    def test_multi_version_task_is_clean(self, corpus: Path, tmp_path: Path) -> None:
        v1, _, _ = discover_paper(corpus / "multi_version")
        result = ingest(v1, tmp_path / "build")
        rubric = rubric_for("multi_version--v1", "multi_version", "v1")
        task_dir = emit_task(
            result, rubric, Protocol.OFFLINE, EmitConfig(tasks_root=tmp_path / "tasks")
        )
        violations = audit_task(task_dir, rubric, v1)
        assert violations == [], [str(v) for v in violations]


class TestAuditCatchesLeaks:
    """Each case plants a leak that the corpus makes genuinely possible."""

    def test_catches_the_writing_time_review_trail(self, emitted) -> None:
        version, rubric, task_dir = emitted
        planted = task_dir / "environment" / "paper" / "review"
        planted.mkdir(parents=True)
        (planted / "internal_review.md").write_text("Lemma 3.1 is weak\n", encoding="utf-8")
        kinds = {v.kind for v in audit_task(task_dir, rubric, version)}
        assert "private-dir" in kinds

    def test_catches_a_planted_writing_plan(self, emitted) -> None:
        version, rubric, task_dir = emitted
        (task_dir / "environment" / "paper" / "plan.md").write_text("# plan\n", encoding="utf-8")
        kinds = {v.kind for v in audit_task(task_dir, rubric, version)}
        assert "private-file" in kinds

    def test_catches_rubric_text_in_the_instruction(self, emitted) -> None:
        version, rubric, task_dir = emitted
        instruction = task_dir / "instruction.md"
        instruction.write_text(
            instruction.read_text(encoding="utf-8") + "\n\nHint: " + SECRET_ACCEPT,
            encoding="utf-8",
        )
        violations = audit_task(task_dir, rubric, version)
        assert any(v.kind == "rubric-leak" and "F1.accept_if" in v.detail for v in violations)

    def test_catches_rubric_text_smuggled_into_the_manuscript(self, emitted) -> None:
        version, rubric, task_dir = emitted
        tex = task_dir / "environment" / "paper" / "main.tex"
        tex.write_text(tex.read_text(encoding="utf-8") + f"\n% {SECRET_DEFECT}\n", encoding="utf-8")
        violations = audit_task(task_dir, rubric, version)
        assert any(v.kind == "rubric-leak" and "F1.defect" in v.detail for v in violations)

    def test_catches_the_reference_review(self, emitted) -> None:
        version, rubric, task_dir = emitted
        shutil.copy2(
            task_dir / "solution" / "private" / "reference_review.md",
            task_dir / "environment" / "paper" / "reference_review.md",
        )
        kinds = {v.kind for v in audit_task(task_dir, rubric, version)}
        assert "answer-key" in kinds

    def test_catches_a_later_version_renamed(self, corpus: Path, tmp_path: Path) -> None:
        """Renaming v2's source does not make it stop being the answer key."""
        v1, v2, _ = discover_paper(corpus / "multi_version")
        result = ingest(v1, tmp_path / "build")
        rubric = rubric_for("multi_version--v1", "multi_version", "v1")
        task_dir = emit_task(
            result, rubric, Protocol.OFFLINE, EmitConfig(tasks_root=tmp_path / "tasks")
        )
        later = ingest(v2, tmp_path / "build-v2")
        shutil.copy2(
            later.root / "main.tex",
            task_dir / "environment" / "paper" / "appendix_extra.tex",
        )
        violations = audit_task(task_dir, rubric, v1)
        assert any(v.kind == "answer-key" for v in violations), [str(v) for v in violations]

    def test_catches_a_missing_rubric_in_the_verifier(self, emitted) -> None:
        version, rubric, task_dir = emitted
        (task_dir / "tests" / "private" / "rubric.json").unlink()
        kinds = {v.kind for v in audit_task(task_dir, rubric, version)}
        assert "structure" in kinds


class TestReferenceReview:
    """The oracle must not pass by reciting the criteria it is scored against."""

    def test_does_not_parrot_accept_if(self, emitted) -> None:
        _, rubric, task_dir = emitted
        reference = (task_dir / "solution" / "private" / "reference_review.md").read_text(
            encoding="utf-8"
        )
        for finding in rubric.findings:
            assert finding.accept_if.strip() not in reference, (
                f"{finding.id}: the reference review quotes its own accept_if, so a 1.0 "
                "would prove only that the judge can match a criterion against itself"
            )

    def test_states_each_defect(self, emitted) -> None:
        _, rubric, task_dir = emitted
        reference = (task_dir / "solution" / "private" / "reference_review.md").read_text(
            encoding="utf-8"
        )
        for finding in rubric.findings:
            assert finding.defect.strip() in reference, finding.id
            assert finding.location in reference, finding.id

    def test_verifier_and_solution_copies_agree(self, emitted) -> None:
        _, _, task_dir = emitted
        assert (task_dir / "solution" / "private" / "reference_review.md").read_text(
            encoding="utf-8"
        ) == (task_dir / "tests" / "private" / "reference_review.md").read_text(encoding="utf-8")
