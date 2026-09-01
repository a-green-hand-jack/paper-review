from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from paper_review_harbor.agents import paper_run_core as core


def run_shell(command: str) -> None:
    result = subprocess.run(["bash", "-c", command], capture_output=True, text=True)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}\n{command}"


def test_pins_v050_and_uses_official_installer() -> None:
    assert core.PAPER_RUN_VERSION == "0.5.0"
    command = core.paper_run_install_command()
    assert "--branch v0.5.0" in command
    assert core.PAPER_RUN_COMMIT in command
    assert "package.json" in command
    assert "npm ci && npm run build && npm install -g ." in command
    assert "paper-run --version" in command


def test_review_commands_use_external_source_and_report_plan() -> None:
    prepare = core.review_prepare_command("openai/gpt-5.6-sol", "medium")
    start = core.review_start_command("openai/gpt-5.6-sol", "medium")

    assert "paper-run review" in prepare
    assert "--prepare-only" in prepare
    assert "--mode autonomous" in prepare
    assert "--headless" not in prepare
    assert "paper-run start --headless --mode autonomous" in start
    assert "--profile" not in start
    assert "--stage-timeout-multiplier 2" in start
    assert "--variant 'medium'" in start
    assert "--profile" not in start


def test_instruction_is_injected_into_context_not_paper() -> None:
    command = core.inject_instruction_command()
    assert "PAPER.md" in command
    assert "/paper/BENCHMARK" not in command
    assert "review-findings.md" in command


def test_instruction_context_uses_paper_run_checkpoint() -> None:
    command = core.inject_instruction_command()
    assert "PAPER.md" in command
    assert "paper-run checkpoint" in command
    assert "git commit" not in command
    assert "python3 .agents/tools/paper-init.py status" in command


def test_external_review_profile_is_not_canonical_variants() -> None:
    command = core.configure_review_profile_command()
    assert ".agents/paper-build.json" in command
    assert "external-latex" in command
    assert "git add -f" in command


def test_provider_config_does_not_embed_credentials() -> None:
    command = core.provider_config_command(
        "https://api.example.test/v1", "openai/gpt-5.6-sol"
    )
    assert command is not None
    assert "OPENAI_API_KEY" not in command
    assert "api.example.test" in command


def test_provider_config_rejects_credential_bearing_url() -> None:
    with pytest.raises(ValueError, match="must not contain credentials"):
        core.provider_config_command("https://user:secret@example.test/v1", "openai/model")
    with pytest.raises(ValueError, match="must not contain credentials"):
        core.provider_config_command("https://example.test/v1#secret", "openai/model")


def test_instruction_is_encoded_before_entering_shell() -> None:
    instruction = "PAPER_RUN_TASK_EOF\n$(touch /tmp/should-not-run)"
    command = core.stage_source_command(instruction)
    assert instruction not in command
    assert "base64 --decode" in command


def test_stage_source_command_is_shell_parseable() -> None:
    command = core.stage_source_command("Review `paper/` and write findings.")
    result = subprocess.run(["bash", "-n"], input=command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_export_script_enforces_report_headings_and_integrity(tmp_path: Path) -> None:
    # The generated script is also useful as an executable contract without a
    # Harbor installation. Replace fixed container paths in a temp shell.
    review = tmp_path / "review"
    paper = review / "paper"
    state = review / ".paper-run"
    paper.mkdir(parents=True)
    state.mkdir()
    (paper / "main.tex").write_text("\\documentclass{article}\n", encoding="utf-8")
    report = "\n".join(core.REQUIRED_HEADINGS) + "\nSound.\n"
    (state / "review-findings.md").write_text(report, encoding="utf-8")
    (state / "run.json").write_text(
        '{"plan":{"profile":"review-report","stages":["bootstrap","independent_review"]}}\n',
        encoding="utf-8",
    )
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.tex").write_text("\\documentclass{article}\n", encoding="utf-8")

    command = core.export_and_validate_command()
    command = command.replace(core.REVIEW_DIR, str(review))
    command = command.replace(core.SOURCE_DIR, str(source))
    command = command.replace(core.SUBMISSION_DIR, str(tmp_path / "submission"))
    command = command.replace(core.ARTIFACT_DIR, str(tmp_path / "artifacts"))

    # The manifest digest must match the upstream algorithm used by the export
    # script. It is created after source setup, as the wrapper does in Harbor.
    digest_script = (
        "import hashlib, pathlib, json\n"
        f"root=pathlib.Path({str(paper)!r}); h=hashlib.sha256()\n"
        "for p in sorted(x for x in root.rglob('*') if x.is_file()):\n"
        " h.update(p.relative_to(root).as_posix().encode()); h.update(b'\\0'); "
        "h.update(p.read_bytes()); h.update(b'\\0')\n"
        "print('sha256:'+h.hexdigest())\n"
    )
    digest = subprocess.check_output(["python3", "-c", digest_script], text=True).strip()
    (state / "review-source.json").write_text(
        '{"paperDigest": ' + repr(digest).replace("'", '"') + "}\n", encoding="utf-8"
    )
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    # This is normally written immediately after staging the immutable source.
    source_digest_script = digest_script.replace(str(paper), str(source)).replace(
        "print('sha256:'+h.hexdigest())", "print(h.hexdigest())"
    )
    source_digest = subprocess.check_output(
        ["python3", "-c", source_digest_script], text=True
    ).strip()
    (artifacts / "source-digest-before.txt").write_text(
        source_digest + "\n", encoding="utf-8"
    )
    (artifacts / "task-source-digest.txt").write_text("fixture\n", encoding="utf-8")
    run_shell(command)
    assert (tmp_path / "submission" / "review.md").read_text(encoding="utf-8") == report
    assert (tmp_path / "artifacts" / "review-source.json").is_file()
