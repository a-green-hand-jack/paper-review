from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import pytest

from paper_review_harbor.audit import audit_task
from paper_review_harbor.corpus import discover_paper
from paper_review_harbor.emit import EmitConfig, canary_for, emit_task
from paper_review_harbor.ingest import ingest
from paper_review_harbor.spec import TaskSpec


def spec_for(label: str) -> TaskSpec:
    return TaskSpec(label=label, venue="arxiv", domain="mathematics")


@pytest.fixture
def staged(corpus: Path, tmp_path: Path):
    (version,) = discover_paper(corpus / "solution-p0001")
    result = ingest(version, tmp_path / "build")
    return version, result


@pytest.fixture
def emitted(staged, tmp_path: Path):
    version, result = staged
    spec = spec_for("solution-p0001")
    config = EmitConfig(tasks_root=tmp_path / "tasks")
    task_dir = emit_task(result, spec, config)
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
        first = canary_for("erdos973--v1")
        assert first == canary_for("erdos973--v1")

    def test_new_paper_just_works_without_a_spec(self, corpus: Path, tmp_path: Path) -> None:
        """A paper dropped into the corpus with no spec still produces a task."""
        (version,) = discover_paper(corpus / "bare_tex")
        result = ingest(version, tmp_path / "build")
        spec = TaskSpec.default_for("bare_tex")
        task_dir = emit_task(result, spec, EmitConfig(tasks_root=tmp_path / "tasks"))
        assert (task_dir / "task.toml").is_file()
        data = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
        assert data["metadata"]["domain"] == "unknown"


class TestAuditPasses:
    def test_clean_task_has_no_violations(self, emitted) -> None:
        version, task_dir = emitted
        assert audit_task(task_dir, version) == []

    def test_multi_version_task_is_clean(self, corpus: Path, tmp_path: Path) -> None:
        v1, _, _ = discover_paper(corpus / "multi_version")
        result = ingest(v1, tmp_path / "build")
        spec = spec_for("multi_version--v1")
        task_dir = emit_task(result, spec, EmitConfig(tasks_root=tmp_path / "tasks"))
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
        v1, v2, _ = discover_paper(corpus / "multi_version")
        result = ingest(v1, tmp_path / "build")
        spec = spec_for("multi_version--v1")
        task_dir = emit_task(result, spec, EmitConfig(tasks_root=tmp_path / "tasks"))
        later = ingest(v2, tmp_path / "build-v2")
        shutil.copy2(
            later.root / "main.tex",
            task_dir / "environment" / "paper" / "appendix_extra.tex",
        )
        violations = audit_task(task_dir, v1)
        assert any(v.kind == "later-version" for v in violations), [str(v) for v in violations]


class TestChecker:
    def test_present_review_scores_one(self, emitted, tmp_path: Path) -> None:
        _, task_dir = emitted
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "review.md").write_text("x" * 500, encoding="utf-8")
        import subprocess

        result = subprocess.run(
            [
                ".venv/bin/python",
                str(task_dir / "tests" / "check_submission.py"),
                "--submission", str(sub),
                "--contract", str(task_dir / "tests" / "contract.json"),
                "--out", str(tmp_path / "out"),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        import json
        reward = json.loads((tmp_path / "out" / "reward.json").read_text())
        assert reward["reward"] == 1.0
        assert reward["submitted"] == 1.0

    def test_missing_review_scores_zero(self, emitted, tmp_path: Path) -> None:
        _, task_dir = emitted
        sub = tmp_path / "sub"
        sub.mkdir()
        import subprocess

        result = subprocess.run(
            [
                ".venv/bin/python",
                str(task_dir / "tests" / "check_submission.py"),
                "--submission", str(sub),
                "--contract", str(task_dir / "tests" / "contract.json"),
                "--out", str(tmp_path / "out"),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        import json
        reward = json.loads((tmp_path / "out" / "reward.json").read_text())
        assert reward["reward"] == 0.0
