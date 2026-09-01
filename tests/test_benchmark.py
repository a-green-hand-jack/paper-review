from __future__ import annotations

import pytest

from paper_review_harbor.benchmark import (
    BenchmarkError,
    ModelConfig,
    _trial_dirs,
    exam_url,
    run_benchmark,
)


def test_dry_run_uses_a_fixed_exam_revision_and_preserves_secret_indirection(tmp_path) -> None:
    revision = "a" * 40
    commands, report = run_benchmark(
        exam_revision=revision,
        model=ModelConfig(
            name="Apex GPT",
            model="openai/gpt-5.6-sol",
            provider="apex",
            credential_env="OPENAI_API_KEY",
            api_base_url="https://api.apexin.ai/v1",
            api_host="api.apexin.ai",
        ),
        jobs_dir=tmp_path / "jobs",
        trails_dir=tmp_path / "trails",
    )
    assert report is None
    assert len(commands) == 1
    assert exam_url(revision) in commands[0]
    assert "--artifact /workspace/.brain" in commands[0]
    assert "--include-task-name trapping_centers_superfluid_mott_insulator" in commands[0]


def test_trial_discovery_excludes_the_job_lock(tmp_path) -> None:
    (tmp_path / "lock.json").write_text("{}")
    trial = tmp_path / "task-1"
    trial.mkdir()
    (trial / "lock.json").write_text("{}")
    (trial / "config.json").write_text("{}")
    assert _trial_dirs(tmp_path) == [trial]


def test_dry_run_rejects_credential_leaking_provider_url(tmp_path) -> None:
    with pytest.raises(BenchmarkError, match="must not contain credentials"):
        run_benchmark(
            exam_revision="a" * 40,
            model=ModelConfig(
                name="unsafe",
                model="openai/model",
                provider="unsafe",
                credential_env="API_KEY",
                api_base_url="https://key@example.test/v1?credential=x",
                api_host="example.test",
            ),
            jobs_dir=tmp_path / "jobs",
            trails_dir=tmp_path / "trails",
        )
