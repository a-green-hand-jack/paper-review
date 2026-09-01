"""Checks and provenance for the bytes handed to a review agent."""

from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path

LFS_VERSION = b"version https://git-lfs.github.com/spec/v1"
LFS_FIELD_RE = re.compile(rb"^(oid sha256:[0-9a-f]{64}|size [0-9]+|[a-zA-Z0-9.-]+ .+)$")

MAGIC_BYTES = {
    ".pdf": b"%PDF-",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}


def is_lfs_pointer_bytes(data: bytes) -> bool:
    """Return whether *data* is a complete Git LFS pointer file."""
    lines = data.replace(b"\r\n", b"\n").splitlines()
    if not lines or lines[0] != LFS_VERSION:
        return False
    fields = [line for line in lines[1:] if line]
    return (
        len(fields) >= 2
        and all(LFS_FIELD_RE.fullmatch(line) for line in fields)
        and any(line.startswith(b"oid sha256:") for line in fields)
        and any(line.startswith(b"size ") for line in fields)
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_inventory(root: Path) -> list[dict[str, object]]:
    """Describe every regular file below root in stable path order."""
    entries: list[dict[str, object]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        data = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": len(data),
                "sha256": sha256_bytes(data),
                "lfs_pointer": is_lfs_pointer_bytes(data),
                # Archive material has no Git index, so LFS tracking itself is
                # unknowable. Keep that distinct from pointer/hydration state.
                "lfs_managed": "unknown",
                "lfs_hydrated": not is_lfs_pointer_bytes(data),
                "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            }
        )
    return entries


def tree_digest(root: Path) -> str:
    """Digest paths and bytes, independent of filesystem traversal order."""
    digest = hashlib.sha256()
    for entry in file_inventory(root):
        digest.update(str(entry["path"]).encode())
        digest.update(b"\0")
        digest.update((root / str(entry["path"])).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def material_violations(root: Path) -> list[str]:
    """Return LFS and binary-format errors for a materialised paper tree."""
    violations: list[str] = []
    for entry in file_inventory(root):
        relative = str(entry["path"])
        path = root / relative
        data = path.read_bytes()
        if bool(entry["lfs_pointer"]):
            violations.append(f"{relative} is a Git LFS pointer, not materialized content")
            continue
        magic = MAGIC_BYTES.get(path.suffix.lower())
        if magic is not None and not data.startswith(magic):
            violations.append(
                f"{relative} does not have the expected {path.suffix.lower()} signature"
            )
    return violations


def file_violations(path: Path) -> list[str]:
    """Apply the same checks to one companion file."""
    data = path.read_bytes()
    if is_lfs_pointer_bytes(data):
        return [f"{path} is a Git LFS pointer, not materialized content"]
    magic = MAGIC_BYTES.get(path.suffix.lower())
    if magic is not None and not data.startswith(magic):
        return [f"{path} does not have the expected {path.suffix.lower()} signature"]
    return []


def material_manifest(
    root: Path,
    *,
    source: dict[str, object],
    main_tex: str,
    manuscript_pdf: str | None,
    excluded: tuple[str, ...] = (),
    sanitised: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": source,
        "main_tex": main_tex,
        "manuscript_pdf": manuscript_pdf,
        "tree_sha256": tree_digest(root),
        "files": file_inventory(root),
        "excluded": list(excluded),
        "sanitised": list(sanitised),
    }
