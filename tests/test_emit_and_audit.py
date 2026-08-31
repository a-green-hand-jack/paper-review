from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from paper_review_harbor.audit import audit_task
from paper_review_harbor.corpus import discover_paper
from paper_review_harbor.emit import EmitConfig, canary_for, emit_task, toml_escape
from paper_review_harbor.ingest import ingest
from paper_review_harbor.spec import TaskSpec


def spec_for(label: str) -> TaskSpec:
    return TaskSpec(label=label, venue="arxiv", domain="mathematics")


def run_checker(task_dir: Path, submission: Path, out: Path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(task_dir / "tests" / "check_submission.py"),
            "--submission",
            str(submission),
            "--contract",
            str(task_dir / "tests" / "contract.json"),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads((out / "reward.json").read_text(encoding="utf-8"))


@pytest.fixture
def staged(corpus: Path, tmp_path: Path):
    (version,) = discover_paper(corpus / "solution-p0001")
    result = ingest(version, tmp_path / "build")
    return version, result


@pytest.fixture
def emitted(staged, tmp_path: Path):
    version, result = staged
    task_dir = emit_task(
        result, spec_for("solution-p0001"), EmitConfig(tasks_root=tmp_path / "tasks")
    )
    return version, task_dir


class TestEmit:
    def test_writes_the_harbor_layout(self, emitted) -> None:
        _, task_dir = emitted
        for relative in (
            "task.toml",
            "instruction.md",
            "environment/Dockerfile",
            "environment/paper/main.tex",
            "solution/solve.sh",
            "tests/Dockerfile",
            "tests/test.sh",
            "tests/check_submission.py",
            "tests/contract.json",
        ):
            assert (task_dir / relative).is_file(), relative

    def test_entry_scripts_are_executable(self, emitted) -> None:
        _, task_dir = emitted
        for relative in ("solution/solve.sh", "tests/test.sh"):
            assert (task_dir / relative).stat().st_mode & 0o111, relative

    def test_task_toml_parses_and_has_correct_schema(self, emitted) -> None:
        _, task_dir = emitted
        data = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.4"
        assert data["verifier"]["environment_mode"] == "separate"
        assert data["environment"]["network_mode"] == "no-network"
        assert "/workspace/submission" in data["artifacts"]

    def test_canary_is_stable_across_rebuilds(self) -> None:
        assert canary_for("erdos973--v1") == canary_for("erdos973--v1")

    def test_task_toml_parses_when_the_title_is_latex(self, corpus: Path, tmp_path: Path) -> None:
        r"""A LaTeX title used to make the whole manifest unparseable.

        `Erd\H{o}s` carries an invalid TOML escape. Harbor reports the resulting
        parse failure only as "Either datasets or tasks must be provided",
        naming neither the file nor the character.
        """
        title = r"A Title About Erd\H{o}s Problem 973 and \\ More"
        version, _, _ = discover_paper(corpus / "multi_version")
        result = ingest(version, tmp_path / "build")
        spec = TaskSpec(label="multi_version--v1", title=title)
        task_dir = emit_task(result, spec, EmitConfig(tasks_root=tmp_path / "tasks"))
        data = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
        assert data["metadata"]["paper_title"] == title

    def test_toml_escape_covers_what_breaks_a_manifest(self) -> None:
        assert toml_escape("plain") == "plain"
        assert toml_escape(r"back\slash") == r"back\\slash"
        assert toml_escape('quote"') == 'quote\\"'
        assert toml_escape("new\nline") == r"new\nline"
        assert toml_escape("bell\x07") == "bell\\u0007"
        assert toml_escape(None) == ""

    def test_operator_notes_survive_into_the_instruction(
        self, corpus: Path, tmp_path: Path
    ) -> None:
        (version,) = discover_paper(corpus / "bare_tex")
        result = ingest(version, tmp_path / "build")
        spec = TaskSpec(label="bare_tex", notes="Focus on the probabilistic argument.")
        task_dir = emit_task(result, spec, EmitConfig(tasks_root=tmp_path / "tasks"))
        instruction = (task_dir / "instruction.md").read_text(encoding="utf-8")
        assert "Focus on the probabilistic argument." in instruction

    def test_new_paper_just_works_without_a_spec(self, corpus: Path, tmp_path: Path) -> None:
        """A paper dropped into the corpus with no spec still produces a task.

        This is the property that lets the corpus grow without code changes.
        """
        (version,) = discover_paper(corpus / "bare_tex")
        result = ingest(version, tmp_path / "build")
        spec = TaskSpec.default_for("bare_tex")
        task_dir = emit_task(result, spec, EmitConfig(tasks_root=tmp_path / "tasks"))
        data = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
        assert data["metadata"]["domain"] == "unknown"
        assert audit_task(task_dir, version) == []


class TestAuditPasses:
    def test_clean_task_has_no_violations(self, emitted) -> None:
        version, task_dir = emitted
        assert audit_task(task_dir, version) == []

    def test_multi_version_task_is_clean(self, corpus: Path, tmp_path: Path) -> None:
        v1, _, _ = discover_paper(corpus / "multi_version")
        result = ingest(v1, tmp_path / "build")
        task_dir = emit_task(
            result, spec_for("multi_version--v1"), EmitConfig(tasks_root=tmp_path / "tasks")
        )
        violations = audit_task(task_dir, v1)
        assert violations == [], [str(v) for v in violations]


class TestAuditCatchesLeaks:
    def test_catches_the_writing_time_review_trail(self, emitted) -> None:
        version, task_dir = emitted
        planted = task_dir / "environment" / "paper" / "review"
        planted.mkdir(parents=True)
        (planted / "internal_review.md").write_text("Lemma 3.1 is weak\n", encoding="utf-8")
        kinds = {v.kind for v in audit_task(task_dir, version)}
        assert "private-dir" in kinds

    def test_catches_a_planted_writing_plan(self, emitted) -> None:
        version, task_dir = emitted
        (task_dir / "environment" / "paper" / "plan.md").write_text("# plan\n", encoding="utf-8")
        kinds = {v.kind for v in audit_task(task_dir, version)}
        assert "private-file" in kinds

    def test_catches_a_later_version_renamed(self, corpus: Path, tmp_path: Path) -> None:
        """Renaming v2's source does not stop it being the answer to v1."""
        v1, v2, _ = discover_paper(corpus / "multi_version")
        result = ingest(v1, tmp_path / "build")
        task_dir = emit_task(
            result, spec_for("multi_version--v1"), EmitConfig(tasks_root=tmp_path / "tasks")
        )
        later = ingest(v2, tmp_path / "build-v2")
        shutil.copy2(
            later.root / "main.tex", task_dir / "environment" / "paper" / "appendix_extra.tex"
        )
        violations = audit_task(task_dir, v1)
        assert any(v.kind == "later-version" for v in violations), [str(v) for v in violations]

    def test_catches_a_missing_verifier(self, emitted) -> None:
        version, task_dir = emitted
        (task_dir / "tests" / "check_submission.py").unlink()
        kinds = {v.kind for v in audit_task(task_dir, version)}
        assert "structure" in kinds


class TestChecker:
    def test_substantive_review_scores_one(self, emitted, tmp_path: Path) -> None:
        _, task_dir = emitted
        submission = tmp_path / "sub"
        submission.mkdir()
        (submission / "review.md").write_text("x" * 500, encoding="utf-8")
        reward = run_checker(task_dir, submission, tmp_path / "out")
        assert reward["reward"] == 1.0
        assert reward["submitted"] == 1.0

    def test_missing_review_scores_zero(self, emitted, tmp_path: Path) -> None:
        _, task_dir = emitted
        submission = tmp_path / "sub"
        submission.mkdir()
        reward = run_checker(task_dir, submission, tmp_path / "out")
        assert reward["reward"] == 0.0
        assert reward["submitted"] == 0.0

    def test_stub_review_scores_zero_but_counts_as_submitted(self, emitted, tmp_path: Path) -> None:
        """A three-line answer is a failed run, not a short review."""
        _, task_dir = emitted
        submission = tmp_path / "sub"
        submission.mkdir()
        (submission / "review.md").write_text("Looks fine.\n", encoding="utf-8")
        reward = run_checker(task_dir, submission, tmp_path / "out")
        assert reward["reward"] == 0.0
        assert reward["submitted"] == 1.0

    def test_extra_submission_files_are_recorded_not_rejected(
        self, emitted, tmp_path: Path
    ) -> None:
        _, task_dir = emitted
        submission = tmp_path / "sub"
        submission.mkdir()
        (submission / "review.md").write_text("x" * 500, encoding="utf-8")
        (submission / "findings.json").write_text("[]", encoding="utf-8")
        out = tmp_path / "out"
        reward = run_checker(task_dir, submission, out)
        assert reward["reward"] == 1.0
        report = json.loads((out / "submission_report.json").read_text(encoding="utf-8"))
        assert report["extra_submission_files"] == ["findings.json"]


class TestRealCorpus:
    def test_every_emitted_manifest_parses(self, real_papers: Path, tmp_path: Path) -> None:
        """The LaTeX-title bug passed the synthetic fixtures and failed on all
        21 real papers, so this walks the real corpus."""
        from paper_review_harbor.corpus import discover

        config = EmitConfig(tasks_root=tmp_path / "tasks")
        for version in discover(real_papers):
            result = ingest(version, tmp_path / "build")
            task_dir = emit_task(result, TaskSpec.default_for(version.label), config)
            data = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
            assert data["metadata"]["task_id"] == version.label
            assert audit_task(task_dir, version) == [], version.label
