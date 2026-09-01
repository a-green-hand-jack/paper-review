"""Render a Harbor task directory from staged material.

The task is a collection harness, not a scored benchmark: it exists so a review
agent can read a manuscript and write `review.md`, which is then archived for
human experts to assess later. So the verifier checks that a review was
produced and says nothing about whether it is any good.

The public/private line still matters, and matters more than it would in a
scored task. A review written by an agent that could read the manuscript's
writing-time defect trail, or its own paper's next revision, is worthless as
data and nothing downstream can tell. `environment/` gets the manuscript and
nothing else; `audit.py` then checks that claim against what is on disk.

`network_mode` is declared `no-network`. Harbor's `merge_extra_allowlists`
promotes any task to `allowlist` when `--allow-agent-host` is passed at run
time, so a task that declares no network can still be run with literature
access -- while the reverse, closing a network a task opened, is not
expressible. Declaring the closed baseline is what keeps both runs available
from one task.
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
from .integrity import material_manifest
from .spec import TaskSpec

TEMPLATES = Path(__file__).parent / "templates"

#: Stable per-task canary GUIDs. Regenerating a task must not change its GUID,
#: or the canary stops identifying anything.
CANARY_NAMESPACE = uuid.UUID("6f1c2d3e-9a4b-5c6d-8e7f-0a1b2c3d4e5f")

#: Suggested at run time via --allow-agent-host; not baked into the task.
#:
#: The general scholarly sources come first. The Bohrium and Google Scholar
#: hosts exist so agents that retrieve through the Bohrium ``bohr`` CLI or by
#: scraping Google Scholar (e.g. Open ScholarPeer) can run under
#: ``--network scholarly`` without the benchmark blocking their literature
#: sources; ``bohr`` is the Bohrium platform CLI (`@dptech-corp/bohr-cli`) and
#: Google Scholar is served from ``scholar.google.com``.
SCHOLARLY_HOSTS: tuple[str, ...] = (
    "arxiv.org",
    "export.arxiv.org",
    "api.semanticscholar.org",
    "api.openalex.org",
    "api.crossref.org",
    "doi.org",
    # Bohrium / bohr CLI
    "bohr.dp.tech",
    "bohrium.dp.tech",
    "tiefblue.bohrium.dp.tech",
    "vouch.dp.tech",
    "wenyon.dp.tech",
    "trisol.dp.tech",
    "open.bohrium.com",
    "platform.bohrium.com",
    "www.bohrium.com",
    # Google Scholar scraping
    "scholar.google.com",
)

#: What Harbor's agent adapters need in order to install themselves.
#:
#: Harbor installs the agent at run time rather than from the image, and every
#: adapter's install step fetches its own runtime. The codex adapter, for
#: instance, apt-gets `curl ripgrep`, pipes nvm's installer from
#: raw.githubusercontent.com, pulls node from nodejs.org, then npm-installs
#: itself. A task declaring `no-network` blocks all of it, and the run dies in
#: setup with `NonZeroAgentExitCodeError` before the agent ever sees the paper.
#:
#: These are needed at environment start, not only during the agent phase, so
#: they go to `--allow-environment-host` as well.
AGENT_INSTALL_HOSTS: tuple[str, ...] = (
    "archive.ubuntu.com",
    "security.ubuntu.com",
    "deb.debian.org",
    "github.com",
    "raw.githubusercontent.com",
    "objects.githubusercontent.com",
    "nodejs.org",
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
)

DATASET_NAME = "paper-review-exam"

#: TOML basic strings recognise a fixed set of escapes; any other backslash is
#: a parse error.
_TOML_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


class EmitError(RuntimeError):
    """The task could not be rendered."""


def toml_escape(value: object) -> str:
    r"""Escape a value for a TOML basic string.

    Paper titles are LaTeX and carry backslashes: ``Erd\H{o}s Problem 973`` is a
    real title in this corpus. Interpolated raw, ``\H`` is an invalid escape and
    the whole ``task.toml`` fails to parse -- at which point Harbor's
    ``Task.is_valid_dir`` returns False, the directory is retried as a dataset,
    and ``harbor run`` reports "Either datasets or tasks must be provided",
    naming neither the file nor the offending character. Every string
    interpolated into the manifest goes through here.
    """
    text = "" if value is None else str(value)
    escaped = []
    for char in text:
        if char in _TOML_ESCAPES:
            escaped.append(_TOML_ESCAPES[char])
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            escaped.append(f"\\u{ord(char):04X}")
        else:
            escaped.append(char)
    return "".join(escaped)


@dataclass
class EmitConfig:
    tasks_root: Path
    dataset: str = DATASET_NAME
    task_version: str = "0.1.0"
    author_name: str = "paper-reviewing-exam"
    agent_timeout_sec: float = 3600.0
    verifier_timeout_sec: float = 300.0
    build_timeout_sec: float = 2400.0
    cpus: int = 2
    memory_mb: int = 8192
    storage_mb: int = 20480
    #: A review shorter than this is a stub, not a submission.
    min_review_chars: int = 200
    extra: dict = field(default_factory=dict)


def canary_for(task_id: str) -> str:
    return str(uuid.uuid5(CANARY_NAMESPACE, task_id))


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    env.filters["toml"] = toml_escape
    return env


def _write(path: Path, text: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def emit_task(result: IngestResult, spec: TaskSpec, config: EmitConfig) -> Path:
    """Render one Harbor task from a staged paper version."""
    task_id = result.label
    canary = canary_for(task_id)
    task_dir = config.tasks_root / config.dataset / task_id

    if task_dir.exists():
        shutil.rmtree(task_dir)
    task_dir.mkdir(parents=True)

    title = spec.title or result.paper_map.title
    env = _env()
    common = {
        "canary": canary,
        "task_id": task_id,
        "title": title,
        "venue": spec.venue,
        "domain": spec.domain,
        "paper_kind": spec.paper_kind,
        "notes": spec.notes.strip(),
        "main_tex": result.main_tex,
        "pdf": result.manuscript_pdf,
        "bib_files": result.paper_map.bib_files,
        "min_review_chars": config.min_review_chars,
    }

    _write(
        task_dir / "task.toml",
        env.get_template("task.toml.j2").render(
            **common,
            task_version=config.task_version,
            author_name=config.author_name,
            source_sha256=result.source_sha256,
            tex_lines=result.paper_map.total_tex_lines,
            n_sections=len(result.paper_map.sections),
            n_citations=len(result.paper_map.cited_keys),
            agent_timeout_sec=config.agent_timeout_sec,
            verifier_timeout_sec=config.verifier_timeout_sec,
            build_timeout_sec=config.build_timeout_sec,
            cpus=config.cpus,
            memory_mb=config.memory_mb,
            storage_mb=config.storage_mb,
        ),
    )
    _write(task_dir / "instruction.md", env.get_template("instruction.md.j2").render(**common))

    _write(
        task_dir / "environment" / "Dockerfile",
        env.get_template("environment.Dockerfile.j2").render(**common),
    )
    shutil.copytree(result.root, task_dir / "environment" / "paper")
    source = {
        "kind": result.source_kind,
        "path": Path(result.source_path).name,
        "sha256": result.source_sha256,
    }
    manifest = json.dumps(
        material_manifest(
            task_dir / "environment" / "paper",
            source=source,
            main_tex=result.main_tex,
            manuscript_pdf=result.manuscript_pdf,
            excluded=result.excluded,
            sanitised=result.sanitised,
        ),
        indent=2,
    ) + "\n"
    # The task-root copy is audited before publish. The environment copy is
    # checked during Docker build after Harbor has fetched the remote revision.
    (task_dir / "material-manifest.json").write_text(manifest, encoding="utf-8")
    (task_dir / "environment" / "material-manifest.json").write_text(
        manifest, encoding="utf-8"
    )
    shutil.copy2(TEMPLATES / "validate_materials.py", task_dir / "environment")

    _write(
        task_dir / "solution" / "solve.sh",
        env.get_template("solve.sh.j2").render(**common),
        executable=True,
    )
    _write(
        task_dir / "tests" / "Dockerfile",
        env.get_template("tests.Dockerfile.j2").render(**common),
    )
    _write(
        task_dir / "tests" / "test.sh",
        env.get_template("test.sh.j2").render(**common),
        executable=True,
    )
    shutil.copy2(TEMPLATES / "check_submission.py", task_dir / "tests" / "check_submission.py")
    _write(
        task_dir / "tests" / "contract.json",
        json.dumps(
            {
                "task_id": task_id,
                "review_path": "review.md",
                "min_review_chars": config.min_review_chars,
            },
            indent=2,
        )
        + "\n",
    )
    return task_dir
