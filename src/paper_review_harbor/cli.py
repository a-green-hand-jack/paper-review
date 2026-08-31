"""`pre-harbor` -- build Harbor review tasks from papers.

The command line splits along one line that matters: everything here runs on a
laptop, and nothing here builds a container image or claims a task works.
`pre-harbor doctor` says what this machine can and cannot do, and the commands
that need Docker print the exact invocation to run on a machine that has it
rather than degrading into a weaker check.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from .audit import audit_task
from .corpus import CorpusError, PaperVersion, discover
from .emit import EmitConfig, dataset_name, emit_task
from .ingest import ingest
from .manifest import row_for, write_manifest
from .rubric import Protocol, Rubric, RubricError, load_rubric, rubric_path

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Turn papers into Harbor tasks for evaluating paper review agents.",
)

DEFAULT_PAPERS = Path("papers")
DEFAULT_RUBRICS = Path("rubrics")
DEFAULT_BUILD = Path("build")
DEFAULT_TASKS = Path("tasks")


def _err(message: str) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)


def _ok(message: str) -> None:
    typer.secho(message, fg=typer.colors.GREEN)


def _versions(papers: Path, only: list[str] | None) -> list[PaperVersion]:
    try:
        found = discover(papers)
    except CorpusError as error:
        _err(str(error))
        raise typer.Exit(2) from error
    if not only:
        return found
    wanted = set(only)
    picked = [v for v in found if v.label in wanted or v.slug in wanted]
    missing = wanted - {v.label for v in picked} - {v.slug for v in picked}
    if missing:
        _err(f"no such paper version: {', '.join(sorted(missing))}")
        raise typer.Exit(2)
    return picked


def _protocols(names: list[str] | None) -> list[Protocol]:
    if not names:
        return list(Protocol)
    try:
        return [Protocol(name) for name in names]
    except ValueError as error:
        _err(f"unknown protocol: {error}")
        raise typer.Exit(2) from error


# --------------------------------------------------------------------------
# inspection
# --------------------------------------------------------------------------


@app.command("list")
def list_papers(
    papers: Annotated[Path, typer.Option(help="corpus root")] = DEFAULT_PAPERS,
    rubrics: Annotated[Path, typer.Option(help="rubric directory")] = DEFAULT_RUBRICS,
) -> None:
    """Show every reviewable paper version and its annotation status."""
    versions = _versions(papers, None)
    typer.echo(f"{'version':52s} {'shape':10s} {'rubric':12s} findings gating")
    for version in versions:
        status, findings, gating = "missing", "-", "-"
        path = rubric_path(rubrics, version.label)
        if path.is_file():
            try:
                rubric = Rubric.load(path)
                status = rubric.status.value
                findings = str(len(rubric.findings))
                gating = str(len([f for f in rubric.findings if f.gating]))
            except (RubricError, ValueError) as error:
                status = "invalid"
                findings = type(error).__name__
        typer.echo(
            f"{version.label:52s} {version.source_kind:10s} {status:12s} "
            f"{findings:>8s} {gating:>6s}"
        )
    typer.echo(f"\n{len(versions)} versions, {len({v.slug for v in versions})} papers")


@app.command()
def doctor() -> None:
    """Report what this machine can do, and what it must hand to a Linux box."""
    checks = {
        "docker": shutil.which("docker"),
        "harbor": shutil.which("harbor"),
        "pdflatex": shutil.which("pdflatex"),
    }
    for name, found in checks.items():
        mark = "ok  " if found else "MISS"
        typer.echo(f"[{mark}] {name:10s} {found or 'not on PATH'}")
    if not all(checks.values()):
        typer.echo(
            "\nIngest, drafting, emit and audit run here regardless. Building images and\n"
            "running `harbor run` need the missing tools -- do that on the Linux box."
        )


# --------------------------------------------------------------------------
# build pipeline
# --------------------------------------------------------------------------


@app.command()
def stage(
    only: Annotated[list[str] | None, typer.Argument(help="labels; default all")] = None,
    papers: Annotated[Path, typer.Option()] = DEFAULT_PAPERS,
    build: Annotated[Path, typer.Option()] = DEFAULT_BUILD,
) -> None:
    """Unpack publishable material and write paper_map.json. No LLM involved."""
    for version in _versions(papers, only):
        result = ingest(version, build)
        excluded = f"  excluded={list(result.excluded)}" if result.excluded else ""
        sanitised = f"  sanitised={list(result.sanitised)}" if result.sanitised else ""
        typer.echo(
            f"{result.label:52s} main={result.main_tex:16s} "
            f"lines={result.paper_map.total_tex_lines:5d} "
            f"sections={len(result.paper_map.sections):3d} "
            f"theorems={len(result.paper_map.theorems):3d}{excluded}{sanitised}"
        )


@app.command()
def check(
    only: Annotated[list[str] | None, typer.Argument()] = None,
    papers: Annotated[Path, typer.Option()] = DEFAULT_PAPERS,
    rubrics: Annotated[Path, typer.Option()] = DEFAULT_RUBRICS,
) -> None:
    """Say what stands between each rubric and a publishable task."""
    problems = 0
    for version in _versions(papers, only):
        path = rubric_path(rubrics, version.label)
        if not path.is_file():
            typer.echo(f"{version.label}: no rubric yet -- run /paper2task to draft one")
            problems += 1
            continue
        try:
            rubric = Rubric.load(path)
        except (RubricError, ValueError) as error:
            _err(f"{version.label}: {error}")
            problems += 1
            continue
        issues = rubric.release_problems()
        if issues:
            problems += 1
            typer.echo(f"{version.label}:")
            for issue in issues:
                typer.echo(f"  - {issue}")
        else:
            _ok(f"{version.label}: ready ({len(rubric.findings)} findings)")
    if problems:
        raise typer.Exit(1)


@app.command()
def emit(
    only: Annotated[list[str] | None, typer.Argument()] = None,
    papers: Annotated[Path, typer.Option()] = DEFAULT_PAPERS,
    rubrics: Annotated[Path, typer.Option()] = DEFAULT_RUBRICS,
    build: Annotated[Path, typer.Option()] = DEFAULT_BUILD,
    tasks: Annotated[Path, typer.Option()] = DEFAULT_TASKS,
    protocol: Annotated[list[str] | None, typer.Option(help="offline and/or online")] = None,
    judge_model: Annotated[str, typer.Option()] = "gpt-5.4",
    judge_votes: Annotated[int, typer.Option()] = 3,
) -> None:
    """Render Harbor tasks. Refuses any rubric a person has not signed off."""
    protocols = _protocols(protocol)
    config = EmitConfig(tasks_root=tasks, judge_model=judge_model, judge_votes=judge_votes)
    rows: dict[Protocol, list] = {p: [] for p in protocols}
    failures = 0

    for version in _versions(papers, only):
        try:
            rubric = load_rubric(rubrics, version.label)
        except RubricError as error:
            _err(str(error))
            failures += 1
            continue
        result = ingest(version, build)
        for proto in protocols:
            try:
                task_dir = emit_task(result, rubric, proto, config)
            except RubricError as error:
                _err(str(error))
                failures += 1
                continue
            violations = audit_task(task_dir, rubric, version)
            if violations:
                _err(f"{task_dir}: LEAK -- refusing to keep this task")
                for violation in violations:
                    _err(f"  {violation}")
                shutil.rmtree(task_dir)
                failures += 1
                continue
            rows[proto].append(row_for(result, rubric, proto))
            _ok(f"{proto.value:8s} {task_dir}")

    for proto, protocol_rows in rows.items():
        if protocol_rows:
            path = write_manifest(tasks, proto, protocol_rows)
            typer.echo(f"{path}: {len(protocol_rows)} tasks")

    if failures:
        _err(f"{failures} task(s) not emitted")
        raise typer.Exit(1)


@app.command()
def audit(
    tasks: Annotated[Path, typer.Option()] = DEFAULT_TASKS,
    papers: Annotated[Path, typer.Option()] = DEFAULT_PAPERS,
    rubrics: Annotated[Path, typer.Option()] = DEFAULT_RUBRICS,
) -> None:
    """Re-audit tasks already on disk, reading what was written rather than
    trusting the code that wrote it."""
    if not tasks.is_dir():
        _err(f"{tasks} does not exist; nothing to audit")
        raise typer.Exit(2)
    versions = {v.label: v for v in _versions(papers, None)}
    total = leaking = 0
    for task_toml in sorted(tasks.rglob("task.toml")):
        task_dir = task_toml.parent
        total += 1
        label = task_dir.name
        try:
            rubric = load_rubric(rubrics, label)
        except RubricError as error:
            _err(f"{task_dir}: {error}")
            leaking += 1
            continue
        violations = audit_task(task_dir, rubric, versions.get(label))
        if violations:
            leaking += 1
            _err(f"{task_dir}:")
            for violation in violations:
                _err(f"  {violation}")
    if leaking:
        _err(f"{leaking} of {total} tasks leak")
        raise typer.Exit(1)
    _ok(f"{total} tasks audited, no leaks")


# --------------------------------------------------------------------------
# handing work to a machine with Docker
# --------------------------------------------------------------------------


@app.command()
def verify(
    label: Annotated[str, typer.Argument(help="task id, e.g. erdos973--v1")],
    tasks: Annotated[Path, typer.Option()] = DEFAULT_TASKS,
    protocol: Annotated[str, typer.Option()] = "offline",
    agent: Annotated[
        str, typer.Option(help="harbor agent; 'oracle' proves solvability")
    ] = "oracle",
    model: Annotated[str, typer.Option()] = "",
) -> None:
    """Run a task under Harbor, or print the command for a machine that can."""
    task_dir = tasks / dataset_name(Protocol(protocol)) / label
    if not (task_dir / "task.toml").is_file():
        _err(f"{task_dir}: no task there. Run `pre-harbor emit {label}` first.")
        raise typer.Exit(2)

    command = ["harbor", "run", "-p", str(task_dir), "-a", agent]
    if model:
        command += ["-m", model]
    printable = " ".join(command)

    if not shutil.which("harbor") or not shutil.which("docker"):
        typer.echo(
            "This machine has no harbor/docker, so nothing was run and nothing is verified.\n"
            "On the Linux box, from this repository:\n\n"
            f"  {printable}\n\n"
            "The oracle must score close to 1.0 and an empty submission close to 0.0.\n"
            "If it does not, the task or the grader is wrong."
        )
        raise typer.Exit(3)

    typer.echo(f"$ {printable}")
    raise typer.Exit(subprocess.call(command))


@app.command("show-map")
def show_map(
    label: Annotated[str, typer.Argument()],
    build: Annotated[Path, typer.Option()] = DEFAULT_BUILD,
    papers: Annotated[Path, typer.Option()] = DEFAULT_PAPERS,
) -> None:
    """Print a staged paper's structure map, staging it first if needed."""
    path = build / label / "paper_map.json"
    if not path.is_file():
        (version,) = [v for v in _versions(papers, [label]) if v.label == label]
        ingest(version, build)
    typer.echo(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2))


if __name__ == "__main__":  # pragma: no cover
    app()
