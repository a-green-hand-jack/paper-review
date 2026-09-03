"""Archive Harbor artifacts without leaking the host workspace or secrets."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .integrity import file_inventory, tree_digest
from .provenance import archiver_provenance


class TrailError(RuntimeError):
    """A run trail could not be archived or uploaded."""


def _safe_component(value: str) -> str:
    if not value or Path(value).name != value or value in {".", ".."}:
        raise TrailError(f"unsafe trail path component: {value!r}")
    return value


SECRET_RE = re.compile(
    rb"(?i)(authorization:\s*bearer\s+\S+|"
    rb"(?:api[_-]?key|token|secret|password)\s*[=:]\s*['\"]?\S+|"
    rb"sk-[A-Za-z0-9_-]{20,})"
)


def _safe_regular_file(path: Path, root: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _scrub_value(value: object, root: Path) -> object:
    """Remove host-local path values before a public trail is written."""
    if isinstance(value, dict):
        return {
            str(key): _scrub_value(item, root)
            for key, item in value.items()
            if key not in {"trial_uri", "local_path", "host_path"}
        }
    if isinstance(value, list):
        return [_scrub_value(item, root) for item in value]
    if isinstance(value, str):
        if SECRET_RE.search(value.encode()):
            raise TrailError("possible secret in trail metadata")
        local_root = str(root.resolve())
        if value.startswith("file://") or value.startswith(local_root):
            return "<redacted-local-path>"
    return value


def _copy_checked(source: Path, destination: Path, root: Path) -> None:
    if not _safe_regular_file(source, root):
        raise TrailError(f"unsafe or missing trail input: {source}")
    data = source.read_bytes()
    if SECRET_RE.search(data):
        raise TrailError(f"possible secret in trail input: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix == ".json":
        try:
            data = (json.dumps(_scrub_value(json.loads(data), root), indent=2) + "\n").encode()
        except json.JSONDecodeError:
            pass
    data = data.replace(str(root.resolve()).encode(), b"<harbor-trial>")
    destination.write_bytes(data)


def _copy_tree_checked(
    source: Path,
    destination: Path,
    root: Path,
    skip_dirs: tuple[str, ...] = (),
    skip_files: tuple[str, ...] = (),
) -> None:
    """Copy one known Harbor output subtree after checking every file.

    Binary files (agent GUI databases, git objects, rollup logs) are not
    review evidence and are skipped: they can trip the secret regex on
    arbitrary byte sequences, and they do not belong in a public trail.
    ``skip_dirs`` removes runtime-internal state directories (e.g. agent
    ``xdg-data``/``xdg-state`` trees), and ``skip_files`` drops specific
    runtime artifacts such as an agent's raw stdout tee, which can carry
    provider metadata that the secret regex cannot reliably classify.
    """
    if source.is_symlink() or not source.is_dir():
        raise TrailError(f"unsafe or missing trail directory: {source}")
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if path.is_dir():
            if path.is_symlink():
                raise TrailError(f"symlink in trail input: {path}")
            if path.name in skip_dirs:
                continue
            continue
        if skip_dirs and any(part in skip_dirs for part in relative.parts[:-1]):
            continue
        if path.name in skip_files:
            continue
        if b"\x00" in path.read_bytes():
            continue  # binary runtime state is not evidence
        _copy_checked(path, destination / relative, root)


def _source_record_id(material_manifest: Path) -> str | None:
    """Read the stable source link from a task material manifest when present."""
    try:
        payload = json.loads(material_manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    source = payload.get("source") if isinstance(payload, dict) else None
    record_id = source.get("record_id") if isinstance(source, dict) else None
    return record_id if isinstance(record_id, str) and record_id else None


def archive_trail(
    run_dir: Path,
    destination_root: Path,
    *,
    task_id: str,
    task_revision: str,
    metadata: dict[str, object] | None = None,
) -> Path:
    """Copy safe run outputs to a unique, timestamped trail directory."""
    if not run_dir.is_dir():
        raise TrailError(f"{run_dir} does not exist or is not a directory")
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    task_component = _safe_component(task_id)
    destination_root.mkdir(parents=True, exist_ok=True)
    if destination_root.is_symlink():
        raise TrailError(f"trail destination is a symlink: {destination_root}")
    task_root = destination_root / task_component
    if task_root.exists() and task_root.is_symlink():
        raise TrailError(f"trail task destination is a symlink: {task_root}")
    target = destination_root / task_component / run_id
    suffix = 0
    while target.exists():
        suffix += 1
        target = destination_root / task_id / f"{run_id}-{suffix}"
    target.mkdir(parents=True)
    review = run_dir / "workspace" / "submission" / "review.md"
    _copy_checked(review, target / "review.md", run_dir)
    review_json = run_dir / "workspace" / "submission" / "review.json"
    if review_json.is_file():
        _copy_checked(review_json, target / "review.json", run_dir)
    optional = {
        "reward.json": run_dir / "reward.json",
        "submission-report.json": run_dir / "logs" / "verifier" / "submission-report.json",
        "trajectory.json": run_dir / "logs" / "agent" / "trajectory.json",
        "input-manifest.json": run_dir / "input-manifest.json",
    }
    for destination_name, source in optional.items():
        if source.exists():
            _copy_checked(source, target / destination_name, run_dir)
    manifest = {
        "schema_version": 2,
        "task_id": task_id,
        "task_revision": task_revision,
        "run_id": target.name,
        "archived_at": datetime.now(UTC).isoformat(),
        "archiver": archiver_provenance(),
        "digest_scope": "all files except trail-manifest.json",
        "tree_sha256": tree_digest(target),
        "files": file_inventory(target),
        "source_record_id": _source_record_id(run_dir / "input-manifest.json"),
        "metadata": metadata or {},
    }
    (target / "trail-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return target


def archive_harbor_trial(
    trial_dir: Path,
    destination_root: Path,
    *,
    task_id: str,
    task_revision: str,
    metadata: dict[str, object] | None = None,
) -> Path:
    """Archive the documented Harbor 0.20 trial layout without host leakage."""
    if not trial_dir.is_dir() or trial_dir.is_symlink():
        raise TrailError(f"{trial_dir} does not exist or is unsafe")
    task_component = _safe_component(task_id)
    destination_root.mkdir(parents=True, exist_ok=True)
    if destination_root.is_symlink():
        raise TrailError(f"trail destination is a symlink: {destination_root}")
    destination_resolved = destination_root.resolve()
    task_root = destination_root / task_component
    if task_root.exists() and task_root.is_symlink():
        raise TrailError(f"trail task destination is a symlink: {task_root}")
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = destination_root / task_component / run_id
    suffix = 0
    while target.exists():
        suffix += 1
        target = destination_root / task_component / f"{run_id}-{suffix}"
    target.mkdir(parents=True)
    try:
        target.resolve().relative_to(destination_resolved)
    except ValueError as error:
        raise TrailError(f"trail destination escaped its root: {target}") from error

    review = trial_dir / "artifacts" / "workspace" / "submission" / "review.md"
    complete_review = review.is_file()
    if complete_review:
        _copy_checked(review, target / "review.md", trial_dir)
    review_json = trial_dir / "artifacts" / "workspace" / "submission" / "review.json"
    complete_structured_review = review_json.is_file()
    if complete_structured_review:
        _copy_checked(review_json, target / "review.json", trial_dir)
    required = {
        "config.json": trial_dir / "config.json",
        "lock.json": trial_dir / "lock.json",
        "artifacts/manifest.json": trial_dir / "artifacts" / "manifest.json",
        "input/material-manifest.json": trial_dir
        / "artifacts"
        / "workspace"
        / "material-manifest.json",
    }
    for destination_name, source in required.items():
        if source.is_file():
            _copy_checked(source, target / destination_name, trial_dir)
    optional_files = {
        "result.json": trial_dir / "result.json",
        "results.json": trial_dir / "results.json",
        "exception.txt": trial_dir / "exception.txt",
        "trial.log": trial_dir / "trial.log",
        "verifier/reward.json": trial_dir / "verifier" / "reward.json",
        "verifier/submission-report.json": trial_dir / "verifier" / "submission-report.json",
    }
    for destination_name, source in optional_files.items():
        if source.is_file():
            _copy_checked(source, target / destination_name, trial_dir)
    for destination_name, source in {
        "brain": trial_dir / "artifacts" / "workspace" / ".brain",
        "agent": trial_dir / "agent",
        "verifier": trial_dir / "verifier",
    }.items():
        if source.exists():
            _copy_tree_checked(
                source,
                target / destination_name,
                trial_dir,
                # Runtime state and raw stdout may contain credentials or opaque
                # provider payloads. Harbor writes normalized trajectories separately.
                skip_dirs=("xdg-data", "xdg-state", "sessions"),
                skip_files=("opencode.txt", "codex.txt"),
            )

    manifest = {
        "schema_version": 3,
        "task_id": task_id,
        "task_revision": task_revision,
        "run_id": target.name,
        "archived_at": datetime.now(UTC).isoformat(),
        "source_layout": "harbor-0.20-trial",
        # Which build did the copying and scrubbing. A reader comparing trails
        # from several contributors needs this; schema_version describes the
        # manifest format, not the archiver.
        "archiver": archiver_provenance(),
        "complete_review": complete_review,
        "complete_structured_review": complete_structured_review,
        "source_record_id": _source_record_id(
            trial_dir / "artifacts" / "workspace" / "material-manifest.json"
        ),
        "digest_scope": "all files except trail-manifest.json",
        "tree_sha256": tree_digest(target),
        "files": file_inventory(target),
        "metadata": _scrub_value(metadata or {}, trial_dir),
    }
    (target / "trail-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return target


def upload_trail(
    trail_dir: Path,
    repo_id: str,
    *,
    revision: str = "main",
    destination: str = "harbor-trails",
    execute: bool = False,
) -> str:
    """Upload one archived trail, using an explicit HF revision."""
    if not trail_dir.is_dir() or not (trail_dir / "trail-manifest.json").is_file():
        raise TrailError(f"{trail_dir} is not an archived trail")
    if not shutil.which("hf"):
        raise TrailError("the `hf` CLI is not on PATH")
    command = [
        "hf", "upload", "--repo-type", "dataset", "--revision", revision,
        repo_id, str(trail_dir), f"{destination}/{trail_dir.parent.name}/{trail_dir.name}",
    ]
    printable = " ".join(command)
    if execute:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise TrailError(
                f"`{printable}` failed with {result.returncode}: {result.stderr.strip()}"
            )
    return printable
