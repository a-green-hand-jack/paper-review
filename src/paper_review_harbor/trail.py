"""Archive Harbor artifacts without leaking the host workspace or secrets."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .integrity import file_inventory, tree_digest


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


def _copy_checked(source: Path, destination: Path, root: Path) -> None:
    if not _safe_regular_file(source, root):
        raise TrailError(f"unsafe or missing trail input: {source}")
    data = source.read_bytes()
    if SECRET_RE.search(data):
        raise TrailError(f"possible secret in trail input: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)


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
        "schema_version": 1,
        "task_id": task_id,
        "task_revision": task_revision,
        "run_id": target.name,
        "archived_at": datetime.now(UTC).isoformat(),
        "digest_scope": "all files except trail-manifest.json",
        "tree_sha256": tree_digest(target),
        "files": file_inventory(target),
        "metadata": metadata or {},
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
