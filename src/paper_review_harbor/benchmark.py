"""Run and archive reproducible OSP Harbor benchmark jobs."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from .emit import AGENT_INSTALL_HOSTS, DATASET_NAME, SCHOLARLY_HOSTS
from .trail import TrailError, archive_harbor_trial, upload_trail

EXAM_REPOSITORY = "Jack-Jieke-Wu/Paper-Reviewing-Exam"
TRAIL_REPOSITORY = "Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails"
OSP_AGENT = "paper_review_harbor.agents.osp:OSPReview"
ISSUE19_TASKS = (
    "compression_induced_folding_of_a_sheet",
    "de_novo_nanobody_discovery",
    "hydrodynamics_of_large_language_models",
    "superconductivity_uniform_electron_gas",
    "transport_in_one_channel_luttinger_liquid",
    "trapping_centers_superfluid_mott_insulator",
)


class BenchmarkError(RuntimeError):
    """The benchmark cannot produce a complete reproducible record."""


@dataclass(frozen=True)
class ModelConfig:
    name: str
    model: str
    provider: str
    credential_env: str
    api_base_url: str
    api_host: str
    variant: str = "medium"


def _safe_name(value: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not name:
        raise BenchmarkError(f"unsafe benchmark name: {value!r}")
    return name


def exam_url(revision: str) -> str:
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise BenchmarkError("--exam-revision must be an immutable 40-character HF commit SHA")
    return f"https://huggingface.co/datasets/{EXAM_REPOSITORY}/tree/{revision}/{DATASET_NAME}"


def _host_args(api_host: str) -> list[str]:
    hosts = (*AGENT_INSTALL_HOSTS, *SCHOLARLY_HOSTS, api_host)
    args: list[str] = []
    for host in dict.fromkeys(hosts):
        args += ["--allow-agent-host", host, "--allow-environment-host", host]
    return args


def _trial_dirs(job_dir: Path) -> list[Path]:
    return sorted(
        path.parent
        for path in job_dir.rglob("lock.json")
        if path.parent != job_dir and (path.parent / "config.json").is_file()
    )


def _validate_endpoint(base_url: str, host: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or parsed.hostname != host:
        raise BenchmarkError("--api-base-url must be HTTPS and its hostname must equal --api-host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise BenchmarkError("--api-base-url must not contain credentials, a query, or a fragment")


def _result_summary(data: dict[str, object]) -> tuple[object, object]:
    verifier = data.get("verifier_result")
    rewards = verifier.get("rewards") if isinstance(verifier, dict) else None
    reward = rewards.get("reward") if isinstance(rewards, dict) else None
    exception = data.get("exception_info")
    if isinstance(exception, dict):
        exception = exception.get("message") or exception.get("type") or exception
    return reward, exception


def _write_report(
    root: Path, *, exam_revision: str, model: ModelConfig, trails: list[Path]
) -> Path:
    rows = []
    for trail in trails:
        manifest = json.loads((trail / "trail-manifest.json").read_text(encoding="utf-8"))
        metadata = manifest.get("metadata", {})
        rows.append(
            "| {task} | {trial} | {reward} | {exception} | `{path}` |".format(
                task=manifest["task_id"],
                trial=metadata.get("trial_id", "unknown"),
                reward=metadata.get("reward", "unknown"),
                exception=metadata.get("exception", "none"),
                path=trail.relative_to(root),
            )
        )
    report = root / f"issue-19-{_safe_name(model.name)}-report.md"
    report.write_text(
        "\n".join(
            [
                f"# Issue #19: {model.name}",
                "",
                f"- Exam revision: `{exam_revision}`",
                f"- Provider: `{model.provider}`",
                f"- Model: `{model.model}`",
                f"- Variant: `{model.variant}`",
                "- Harbor reward only confirms the submission contract; it is not a "
                "review-quality score.",
                "",
                "| Task | Harbor trial | Reward | Exception | Trail |",
                "| --- | --- | ---: | --- | --- |",
                *rows,
                "",
                "The preserved lock/config, material manifest, OSP `.brain`, agent logs, "
                "verifier output, "
                "and review are the reproducibility record for human expert assessment.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def _upload_report(report: Path, *, repo_id: str, revision: str, exam_revision: str) -> None:
    destination = (
        f"benchmark-reports/{exam_revision}/"
        f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{report.name}"
    )
    command = [
        "hf",
        "upload",
        "--repo-type",
        "dataset",
        "--revision",
        revision,
        repo_id,
        str(report),
        destination,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise BenchmarkError(
            f"`{' '.join(command)}` failed with {result.returncode}: {result.stderr.strip()}"
        )


def run_benchmark(
    *,
    exam_revision: str,
    model: ModelConfig,
    jobs_dir: Path,
    trails_dir: Path,
    trail_repo: str = TRAIL_REPOSITORY,
    trail_revision: str = "main",
    execute: bool = False,
) -> tuple[list[str], Path | None]:
    """Run the six Issue #19 tasks and archive every completed Harbor trial."""
    if not model.credential_env.isidentifier():
        raise BenchmarkError(f"invalid credential environment variable {model.credential_env!r}")
    if not model.model.startswith("openai/"):
        raise BenchmarkError(
            "--model must use openai/<model>; the runner injects the selected provider endpoint "
            "without relying on container-local OpenCode configuration"
        )
    _validate_endpoint(model.api_base_url, model.api_host)
    if execute and not os.environ.get(model.credential_env):
        raise BenchmarkError(f"{model.credential_env} is not exported for this benchmark process")

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    job_name = f"issue19-{_safe_name(model.name)}-{stamp}"
    job_dir = jobs_dir / job_name
    command = [
        "harbor",
        "run",
        "--repo",
        exam_url(exam_revision),
        "--agent",
        OSP_AGENT,
        "--model",
        model.model,
        "--agent-kwarg",
        f"variant={model.variant}",
        "--jobs-dir",
        str(jobs_dir),
        "--job-name",
        job_name,
        "--n-concurrent",
        "1",
        "--n-concurrent-agents",
        "1",
        "--no-delete",
        "--artifact",
        "/workspace/.brain",
        "--artifact",
        "/workspace/material-manifest.json",
        "--yes",
    ]
    for task in ISSUE19_TASKS:
        command += ["--include-task-name", task]
    allowed_hosts = tuple(dict.fromkeys((*AGENT_INSTALL_HOSTS, *SCHOLARLY_HOSTS, model.api_host)))
    command += _host_args(model.api_host)

    if not execute:
        return [" ".join(command)], None

    if not shutil.which("harbor"):
        raise BenchmarkError("harbor is not on PATH")
    if not shutil.which("hf"):
        raise BenchmarkError("hf is not on PATH")

    environment = os.environ.copy()
    environment["OPENAI_API_KEY"] = environment[model.credential_env]
    environment["OPENAI_BASE_URL"] = model.api_base_url
    source_root = str(Path(__file__).resolve().parents[2])
    environment["PYTHONPATH"] = source_root + os.pathsep + environment.get("PYTHONPATH", "")
    harbor_version = subprocess.run(
        ["harbor", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    result = subprocess.run(command, text=True, env=environment)
    trial_dirs = _trial_dirs(job_dir)
    if len(trial_dirs) != len(ISSUE19_TASKS):
        raise BenchmarkError(
            f"Harbor produced {len(trial_dirs)} trial records; expected "
            f"{len(ISSUE19_TASKS)} under {job_dir}"
        )

    trails: list[Path] = []
    failures: list[str] = []
    for trial_dir in trial_dirs:
        lock = json.loads((trial_dir / "lock.json").read_text(encoding="utf-8"))
        task_id = str(lock.get("task", {}).get("name") or trial_dir.name)
        result_path = trial_dir / "result.json"
        result_data = (
            json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
        )
        reward, exception = _result_summary(result_data)
        metadata = {
            "provider": model.provider,
            "model": model.model,
            "variant": model.variant,
            "harbor_version": harbor_version,
            "api_base_url": model.api_base_url,
            "credential_env": model.credential_env,
            "trial_id": trial_dir.name,
            "reward": reward,
            "exception": exception,
            "network_mode": "scholarly",
            "allowed_hosts": list(allowed_hosts),
        }
        try:
            trail = archive_harbor_trial(
                trial_dir,
                trails_dir / _safe_name(model.name),
                task_id=task_id,
                task_revision=exam_revision,
                metadata=metadata,
            )
            upload_trail(trail, trail_repo, revision=trail_revision, execute=True)
            trails.append(trail)
        except TrailError as error:
            failures.append(f"{trial_dir}: {error}")
    if result.returncode:
        failures.append(f"harbor exited with {result.returncode}")
    if failures:
        raise BenchmarkError("; ".join(failures))
    report = _write_report(
        trails_dir / _safe_name(model.name),
        exam_revision=exam_revision,
        model=model,
        trails=trails,
    )
    _upload_report(report, repo_id=trail_repo, revision=trail_revision, exam_revision=exam_revision)
    return [], report
