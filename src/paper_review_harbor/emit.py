"""Render a Harbor task directory from staged material and a signed-off rubric.

Emission is the point where the public/private line becomes a filesystem fact:

    environment/   the manuscript, and nothing that describes its defects
    solution/      the oracle, and the reference review it writes
    tests/         the rubric, the grader, and the reference review again

`[verifier] environment_mode = "separate"` keeps `tests/` out of the agent's
container entirely. Harbor does not upload `tests/` in that mode, so the
verifier image has to own `/tests` itself -- which is why `tests/Dockerfile`
does `COPY . /tests/`.
"""

from __future__ import annotations

import json
import shutil
import stat
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .ingest import IngestResult
from .rubric import Protocol, Rubric

TEMPLATES = Path(__file__).parent / "templates"

#: Stable per-task canary GUIDs. Regenerating a task must not change its GUID,
#: or the canary stops identifying anything.
CANARY_NAMESPACE = uuid.UUID("6f1c2d3e-9a4b-5c6d-8e7f-0a1b2c3d4e5f")

DEFAULT_ALLOWED_HOSTS: tuple[str, ...] = (
    "arxiv.org",
    "*.arxiv.org",
    "export.arxiv.org",
    "api.semanticscholar.org",
    "api.openalex.org",
    "api.crossref.org",
    "doi.org",
)

DATASET_PREFIX = "review-exam"


class EmitError(RuntimeError):
    """The task could not be rendered."""


@dataclass
class EmitConfig:
    tasks_root: Path
    task_version: str = "0.1.0"
    author_name: str = "paper-reviewing-exam"
    judge_model: str = "gpt-5.4"
    judge_votes: int = 3
    agent_timeout_sec: float = 3600.0
    verifier_timeout_sec: float = 1800.0
    build_timeout_sec: float = 2400.0
    cpus: int = 2
    memory_mb: int = 8192
    storage_mb: int = 20480
    allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS
    min_review_chars: int = 400
    extra: dict = field(default_factory=dict)


def dataset_name(protocol: Protocol) -> str:
    return f"{DATASET_PREFIX}-{protocol.value}"


def canary_for(task_id: str, protocol: Protocol) -> str:
    return str(uuid.uuid5(CANARY_NAMESPACE, f"{task_id}:{protocol.value}"))


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )


def _write(path: Path, text: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def emit_task(
    result: IngestResult,
    rubric: Rubric,
    protocol: Protocol,
    config: EmitConfig,
) -> Path:
    """Render one task. Refuses to run on a rubric a person has not signed off."""
    rubric.assert_releasable([protocol])

    findings = rubric.findings_for(protocol)
    gating = rubric.gating_for(protocol)
    task_id = rubric.task_id_base
    canary = canary_for(task_id, protocol)
    task_dir = config.tasks_root / dataset_name(protocol) / task_id

    if task_dir.exists():
        shutil.rmtree(task_dir)
    task_dir.mkdir(parents=True)

    env = _env()
    pdf_name = None
    for candidate in sorted(result.root.glob("*.pdf")):
        if candidate.stem in {"main", result.label} or len(list(result.root.glob("*.pdf"))) == 1:
            pdf_name = candidate.name
            break

    common = {
        "canary": canary,
        "task_id": task_id,
        "protocol": protocol.value,
        "paper_slug": rubric.paper.slug,
        "paper_version": rubric.paper.version or "",
        "venue": rubric.paper.venue,
        "domain": rubric.paper.domain,
        "main_tex": result.main_tex,
        "pdf": pdf_name,
        "allowed_hosts": list(config.allowed_hosts),
    }

    _write(
        task_dir / "task.toml",
        env.get_template("task.toml.j2").render(
            **common,
            task_version=config.task_version,
            author_name=config.author_name,
            source_sha256=result.source_sha256,
            annotator=rubric.annotator or "",
            annotated_at=rubric.annotated_at.isoformat() if rubric.annotated_at else "",
            n_findings=len(findings),
            n_gating=len(gating),
            agent_timeout_sec=config.agent_timeout_sec,
            verifier_timeout_sec=config.verifier_timeout_sec,
            build_timeout_sec=config.build_timeout_sec,
            cpus=config.cpus,
            memory_mb=config.memory_mb,
            storage_mb=config.storage_mb,
            judge_model=config.judge_model,
            judge_votes=config.judge_votes,
        ),
    )
    _write(task_dir / "instruction.md", env.get_template("instruction.md.j2").render(**common))

    # -- environment: manuscript only -------------------------------------
    _write(
        task_dir / "environment" / "Dockerfile",
        env.get_template("environment.Dockerfile.j2").render(**common),
    )
    shutil.copytree(result.root, task_dir / "environment" / "paper")

    # -- the reference review, shared by oracle and verifier ---------------
    reference = env.get_template("reference_review.md.j2").render(
        **common,
        findings=[f.model_dump(mode="json") for f in findings],
        gating=[f.model_dump(mode="json") for f in gating],
    )

    _write(
        task_dir / "solution" / "solve.sh",
        env.get_template("solve.sh.j2").render(**common),
        executable=True,
    )
    _write(task_dir / "solution" / "private" / "reference_review.md", reference)

    # -- verifier ----------------------------------------------------------
    _write(
        task_dir / "tests" / "Dockerfile",
        env.get_template("tests.Dockerfile.j2").render(**common),
    )
    _write(
        task_dir / "tests" / "test.sh",
        env.get_template("test.sh.j2").render(**common),
        executable=True,
    )
    shutil.copy2(TEMPLATES / "grader_review.py", task_dir / "tests" / "grader_review.py")

    graded = rubric.public_view()
    graded["protocol"] = protocol.value
    graded["min_review_chars"] = config.min_review_chars
    _write(
        task_dir / "tests" / "private" / "rubric.json",
        json.dumps(graded, indent=2, ensure_ascii=False) + "\n",
    )
    _write(task_dir / "tests" / "private" / "reference_review.md", reference)

    return task_dir
