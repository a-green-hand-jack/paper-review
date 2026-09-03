from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from paper_review_harbor import cli
from paper_review_harbor.emit import DATASET_NAME


def _task(tasks: Path, label: str) -> None:
    task_dir = tasks / DATASET_NAME / label
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text("schema_version = '1.4'\n", encoding="utf-8")


def test_verify_passes_a_harbor_environment_template_without_exposing_a_value(
    tmp_path: Path, monkeypatch
) -> None:
    label = "example"
    tasks = tmp_path / "tasks"
    _task(tasks, label)
    received: list[list[str]] = []

    monkeypatch.setattr(cli.shutil, "which", lambda _: "/usr/bin/available")
    monkeypatch.setattr(cli.subprocess, "call", lambda command: received.append(command) or 0)

    result = CliRunner().invoke(
        cli.app,
        ["verify", label, "--tasks", str(tasks), "--agent-env", "TEST_HARBOR_API_KEY"],
    )

    assert result.exit_code == 0, result.output
    assert received[0][-2:] == ["--agent-env", "TEST_HARBOR_API_KEY=${TEST_HARBOR_API_KEY}"]
    assert "--agent-env 'TEST_HARBOR_API_KEY=${TEST_HARBOR_API_KEY}'" in result.output


def test_verify_sets_codex_nvm_install_to_script_mode(tmp_path: Path, monkeypatch) -> None:
    label = "example"
    tasks = tmp_path / "tasks"
    _task(tasks, label)
    received: list[list[str]] = []

    monkeypatch.setattr(cli.shutil, "which", lambda _: "/usr/bin/available")
    monkeypatch.setattr(cli.subprocess, "call", lambda command: received.append(command) or 0)

    result = CliRunner().invoke(
        cli.app,
        ["verify", label, "--tasks", str(tasks), "--agent", "codex", "--network", "agent"],
    )

    assert result.exit_code == 0, result.output
    assert any(
        received[0][index : index + 2] == ["--agent-env", "METHOD=script"]
        for index in range(len(received[0]) - 1)
    )
    assert "--agent-env METHOD=script" in result.output


def test_verify_leaves_missing_agent_environment_resolution_to_harbor(
    tmp_path: Path, monkeypatch
) -> None:
    label = "example"
    tasks = tmp_path / "tasks"
    _task(tasks, label)
    called = False

    def call(_: list[str]) -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.delenv("MISSING_HARBOR_API_KEY", raising=False)
    monkeypatch.setattr(cli.shutil, "which", lambda _: "/usr/bin/available")
    monkeypatch.setattr(cli.subprocess, "call", call)

    result = CliRunner().invoke(
        cli.app,
        ["verify", label, "--tasks", str(tasks), "--agent-env", "MISSING_HARBOR_API_KEY"],
    )

    assert result.exit_code == 0, result.output
    assert called


def test_verify_prints_handoff_when_tools_and_agent_environment_are_absent(
    tmp_path: Path, monkeypatch
) -> None:
    label = "example"
    tasks = tmp_path / "tasks"
    _task(tasks, label)

    monkeypatch.delenv("MISSING_HARBOR_API_KEY", raising=False)
    monkeypatch.setattr(cli.shutil, "which", lambda _: None)

    result = CliRunner().invoke(
        cli.app,
        ["verify", label, "--tasks", str(tasks), "--agent-env", "MISSING_HARBOR_API_KEY"],
    )

    assert result.exit_code == 3
    assert "--agent-env 'MISSING_HARBOR_API_KEY=${MISSING_HARBOR_API_KEY}'" in result.output
