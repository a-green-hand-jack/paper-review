"""`pre-harbor` -- build Harbor review-collection tasks from papers.

The command line splits along one line that matters: everything here runs on a
laptop, and nothing here builds a container image or claims a task works.
`pre-harbor doctor` says what this machine can and cannot do, and the commands
that need Docker print the exact invocation to run on a machine that has it
rather than degrading into a weaker check.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from .audit import audit_task
from .corpus import CorpusError, PaperVersion, discover
from .emit import (
    AGENT_INSTALL_HOSTS,
    DATASET_NAME,
    SCHOLARLY_HOSTS,
    EmitConfig,
    emit_task,
)
from .ingest import ingest
from .manifest import row_for, write_manifest
from .provenance import archiver_provenance, provenance_warnings
from .publish import PublishError, create_tag, plan_publish, read_manifest, render_readme, upload
from .spec import SpecError, TaskSpec, load_spec, spec_path
from .trail import TrailError, archive_harbor_trial, upload_trail

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Turn papers into Harbor tasks that collect peer reviews.",
)

DEFAULT_PAPERS = Path("papers")
DEFAULT_SPECS = Path("specs")
DEFAULT_BUILD = Path("build")
DEFAULT_TASKS = Path("tasks")
ENVIRONMENT_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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


def _specs(specs_root: Path, versions: list[PaperVersion]) -> dict[str, tuple[TaskSpec, bool]]:
    out: dict[str, tuple[TaskSpec, bool]] = {}
    for version in versions:
        try:
            spec = load_spec(specs_root, version.label)
        except SpecError as error:
            _err(str(error))
            raise typer.Exit(2) from error
        out[version.label] = (spec, spec_path(specs_root, version.label).is_file())
    return out


# --------------------------------------------------------------------------
# inspection
# --------------------------------------------------------------------------


@app.command("list")
def list_papers(
    papers: Annotated[Path, typer.Option(help="corpus root")] = DEFAULT_PAPERS,
    specs: Annotated[Path, typer.Option(help="spec directory")] = DEFAULT_SPECS,
) -> None:
    """Show every reviewable paper version and its metadata status."""
    versions = _versions(papers, None)
    spec_map = _specs(specs, versions)
    typer.echo(
        f"{'version':52s} {'shape':10s} {'spec':8s} {'domain':14s} {'venue':12s} title"
    )
    for version in versions:
        spec, has_spec = spec_map[version.label]
        typer.echo(
            f"{version.label:52s} {version.source_kind:10s} "
            f"{'yes' if has_spec else '-':8s} {spec.domain:14s} {spec.venue:12s} "
            f"{spec.title or '<derived>'}"
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
            "\nIngest and emit run here regardless. Building images and running\n"
            "`harbor run` need the missing tools -- do that on the Linux box."
        )


@app.command("init-spec")
def init_spec(
    label: Annotated[str, typer.Argument(help="paper version, e.g. erdos973--v1")],
    papers: Annotated[Path, typer.Option()] = DEFAULT_PAPERS,
    specs: Annotated[Path, typer.Option()] = DEFAULT_SPECS,
    force: Annotated[bool, typer.Option(help="overwrite an existing spec")] = False,
) -> None:
    """Write a starter spec for a paper version, derived from its source."""
    version = _versions(papers, [label])
    if len(version) != 1 or version[0].label != label:
        _err(f"{label} is a paper slug, not a version label; use e.g. {version[0].label}")
        raise typer.Exit(2)
    path = spec_path(specs, label)
    if path.is_file() and not force:
        _err(f"{path} exists; pass --force to overwrite")
        raise typer.Exit(2)
    spec = TaskSpec.default_for(label)
    spec.save(path)
    _ok(f"wrote {path}")


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
        title = result.paper_map.title or "<no \\title found>"
        typer.echo(
            f"{result.label:52s} main={result.main_tex:16s} "
            f"lines={result.paper_map.total_tex_lines:5d} "
            f"sections={len(result.paper_map.sections):3d} "
            f"theorems={len(result.paper_map.theorems):3d}{excluded}{sanitised}\n"
            f"    {title}"
        )


@app.command()
def emit(
    only: Annotated[list[str] | None, typer.Argument()] = None,
    papers: Annotated[Path, typer.Option()] = DEFAULT_PAPERS,
    specs: Annotated[Path, typer.Option()] = DEFAULT_SPECS,
    build: Annotated[Path, typer.Option()] = DEFAULT_BUILD,
    tasks: Annotated[Path, typer.Option()] = DEFAULT_TASKS,
) -> None:
    """Render Harbor tasks and audit each one. A leak deletes the task."""
    config = EmitConfig(tasks_root=tasks)
    rows = []
    failures = 0
    by_label = {v.label: v for v in _versions(papers, only)}
    spec_map = _specs(specs, list(by_label.values()))

    for label, version in sorted(by_label.items()):
        spec, _ = spec_map[label]
        result = ingest(version, build)
        try:
            task_dir = emit_task(result, spec, config)
        except Exception as error:  # noqa: BLE001 - report, do not abort the batch
            _err(f"{label}: {type(error).__name__}: {error}")
            failures += 1
            continue
        violations = audit_task(task_dir, version)
        if violations:
            _err(f"{task_dir}: LEAK -- refusing to keep this task")
            for violation in violations:
                _err(f"  {violation}")
            shutil.rmtree(task_dir)
            failures += 1
            continue
        rows.append(
            row_for(
                result,
                spec,
                version.slug,
                version.version,
                has_spec=spec_path(specs, label).is_file(),
            )
        )
        _ok(f"{task_dir}")

    if rows:
        path = write_manifest(tasks, config.dataset, rows)
        typer.echo(f"{path}: {len(rows)} tasks")
    if failures:
        _err(f"{failures} task(s) not emitted")
        raise typer.Exit(1)


@app.command()
def audit(
    tasks: Annotated[Path, typer.Option()] = DEFAULT_TASKS,
    papers: Annotated[Path, typer.Option()] = DEFAULT_PAPERS,
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
        violations = audit_task(task_dir, versions.get(task_dir.name))
        if violations:
            leaking += 1
            _err(f"{task_dir}:")
            for violation in violations:
                _err(f"  {violation}")
    if leaking:
        _err(f"{leaking} of {total} tasks leak")
        raise typer.Exit(1)
    _ok(f"{total} tasks audited, no leaks")


@app.command()
def publish(
    repo: Annotated[str, typer.Option(help="Hugging Face dataset, e.g. org/name")],
    tasks: Annotated[Path, typer.Option()] = DEFAULT_TASKS,
    papers: Annotated[Path, typer.Option()] = DEFAULT_PAPERS,
    revision: Annotated[str, typer.Option(help="HF branch, tag, or commit to upload to")] = "main",
    execute: Annotated[bool, typer.Option(help="actually upload; off by default")] = False,
    readme: Annotated[bool, typer.Option(help="also write the dataset card")] = True,
    release_tag: Annotated[
        str | None, typer.Option(help="create this immutable HF tag after upload")
    ] = None,
) -> None:
    """Publish emitted tasks to Hugging Face. Re-audits first; dry run by default.

    A public dataset can be cached or mirrored between the push and any later
    deletion, so the upload is opt-in and the audit runs again here rather than
    trusting that `emit` ran it.
    """
    versions = {v.label: v for v in _versions(papers, None)}
    try:
        plan = plan_publish(tasks, repo, revision=revision, versions=versions)
    except PublishError as error:
        _err(str(error))
        raise typer.Exit(1) from error

    typer.echo(
        f"{len(plan.task_ids)} tasks, {plan.total_bytes / 1e6:.1f} MB\n"
        f"  from {plan.local_dir}\n"
        f"  to   {plan.repo_id}:{plan.dataset}/"
    )
    card = render_readme(plan, read_manifest(plan)) if readme else None

    try:
        result = upload(plan, readme=card, execute=execute)
        if execute and release_tag:
            assert result.resolved_revision is not None
            create_tag(plan.repo_id, release_tag, result.resolved_revision)
    except PublishError as error:
        _err(str(error))
        raise typer.Exit(1) from error

    if not execute:
        typer.echo(f"\nDry run. Pass --execute to upload:\n\n{result.commands}\n")
        typer.echo("Publishing is public and hard to undo; nothing was sent.")
        return

    _ok(f"\npublished to https://huggingface.co/datasets/{plan.repo_id}")
    assert result.resolved_revision is not None
    typer.echo(f"resolved immutable HF revision: {result.resolved_revision}")
    if release_tag:
        typer.echo(f"created HF dataset tag: {release_tag}")
    typer.echo(
        "\nHarbor reads the resolved revision directly:\n\n"
        f"  harbor run --repo https://huggingface.co/datasets/{plan.repo_id}"
        f"/tree/{result.resolved_revision}/{plan.dataset} -a opencode\n"
    )


@app.command("archive-trail")
def archive_trail_command(
    run_dir: Annotated[Path, typer.Argument(help="Harbor trial directory (0.20 layout)")],
    task_id: Annotated[str, typer.Option(help="Harbor task id")],
    task_revision: Annotated[str, typer.Option(help="immutable Exam revision")],
    trails: Annotated[Path, typer.Option(help="local trail output root")] = Path("trails"),
    trail_repo: Annotated[str | None, typer.Option(help="HF Trails dataset")] = None,
    revision: Annotated[str, typer.Option(help="HF Trails branch or tag")] = "main",
    execute: Annotated[bool, typer.Option(help="upload the archived trail")] = False,
) -> None:
    """Archive a Harbor trial and optionally upload it to a Trails dataset."""
    try:
        trail = archive_harbor_trial(run_dir, trails, task_id=task_id, task_revision=task_revision)
        typer.echo(f"archived {trail}")
        # A trail that cannot name the build that wrote it is still worth
        # keeping -- but the contributor should hear about it now, not when
        # someone else tries to reproduce the scrub.
        for warning in provenance_warnings(archiver_provenance()):
            typer.echo(f"warning: {warning}", err=True)
        if trail_repo:
            command = upload_trail(trail, trail_repo, revision=revision, execute=execute)
            typer.echo(command if not execute else f"uploaded to {trail_repo}")
    except TrailError as error:
        _err(str(error))
        raise typer.Exit(1) from error


# --------------------------------------------------------------------------
# handing work to a machine with Docker
# --------------------------------------------------------------------------

NETWORK_MODES = {
    #: Only oracle and nop can run with nothing allowed; a hosted agent cannot
    #: install itself, let alone reach its own API.
    "none": (),
    #: Enough for a hosted agent to install and run, with no literature access.
    "agent": AGENT_INSTALL_HOSTS,
    #: Agent plus literature. Note that arXiv also serves the later versions of
    #: any multi-version paper in this corpus.
    "scholarly": AGENT_INSTALL_HOSTS + SCHOLARLY_HOSTS,
}


def _host_args(hosts: tuple[str, ...]) -> list[str]:
    """Allow each host at both phases.

    Agent installation happens during trial setup, under the environment
    baseline rather than the agent-phase override, so `--allow-agent-host`
    alone leaves the install to fail.
    """
    args: list[str] = []
    for host in hosts:
        args += ["--allow-agent-host", host, "--allow-environment-host", host]
    return args


@app.command()
def verify(
    label: Annotated[str, typer.Argument(help="task id, e.g. erdos973--v1")],
    tasks: Annotated[Path, typer.Option()] = DEFAULT_TASKS,
    agent: Annotated[str, typer.Option(help="harbor agent: oracle, nop, codex, ...")] = "oracle",
    network: Annotated[str, typer.Option(help="none | agent | scholarly")] = "none",
    model: Annotated[str, typer.Option(help="required by most real agents")] = "",
    api_host: Annotated[str, typer.Option(help="the agent's own provider host")] = "",
    agent_env: Annotated[
        list[str] | None,
        typer.Option(help="env var name to pass to the agent, e.g. OPENAI_API_KEY"),
    ] = None,
    no_delete: Annotated[
        bool, typer.Option(help="keep the Harbor container and workspace after the run")
    ] = False,
) -> None:
    """Run a task under Harbor, or print the command for a machine that can."""
    task_dir = tasks / DATASET_NAME / label
    if not (task_dir / "task.toml").is_file():
        _err(f"{task_dir}: no task there. Run `pre-harbor emit {label}` first.")
        raise typer.Exit(2)
    if network not in NETWORK_MODES:
        _err(f"unknown network mode {network!r}; use {' | '.join(NETWORK_MODES)}")
        raise typer.Exit(2)

    hosts = NETWORK_MODES[network]
    if api_host:
        hosts = hosts + (api_host,)
    if network == "none" and agent not in {"oracle", "nop"}:
        _err(
            f"agent {agent!r} with --network none will fail during setup: Harbor installs "
            "agents at run time and the install fetches a runtime it cannot reach. Use "
            "--network agent (or scholarly), and --api-host for the provider."
        )
        raise typer.Exit(2)

    command = ["harbor", "run", "-p", str(task_dir), "-a", agent]
    if model:
        command += ["-m", model]
    command += ["-y"]
    if no_delete:
        command += ["--no-delete"]
    printable_command = command.copy()
    for name in agent_env or []:
        if not ENVIRONMENT_NAME_RE.fullmatch(name):
            _err(f"invalid agent environment variable name {name!r}")
            raise typer.Exit(2)
        command += ["--agent-env", f"{name}=${{{name}}}"]
        printable_command += ["--agent-env", f"{name}=${{{name}}}"]
    command += _host_args(hosts)
    printable_command += _host_args(hosts)
    printable = shlex.join(printable_command)

    if not shutil.which("harbor") or not shutil.which("docker"):
        typer.echo(
            "This machine has no harbor/docker, so nothing was run and nothing is verified.\n"
            "On the Linux box, from this repository:\n\n"
            f"  {printable}\n\n"
            "oracle must score 1.0 and `harbor run -a nop` must score 0.0. If they\n"
            "do not, the task or the checker is wrong."
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
