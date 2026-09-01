"""Validate the exact material bytes copied into a Harbor environment image."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

MAGIC_BYTES = {
    ".pdf": b"%PDF-",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}
LFS_PREFIX = b"version https://git-lfs.github.com/spec/v1"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    manifest_path, root = map(Path, sys.argv[1:3])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("files")
    if not isinstance(expected, list):
        raise ValueError("material manifest has no file inventory")
    actual = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    declared = sorted(entry.get("path") for entry in expected if isinstance(entry, dict))
    if actual != declared:
        raise ValueError("material file inventory differs from manifest")
    for entry in expected:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("material manifest contains an invalid inventory entry")
        path = root / entry["path"]
        data = path.read_bytes()
        if data.startswith(LFS_PREFIX):
            raise ValueError(f"{entry['path']} is a Git LFS pointer")
        if len(data) != entry.get("size") or digest(path) != entry.get("sha256"):
            raise ValueError(f"{entry['path']} differs from its manifest digest")
        magic = MAGIC_BYTES.get(path.suffix.lower())
        if magic is not None and not data.startswith(magic):
            raise ValueError(f"{entry['path']} has an invalid {path.suffix.lower()} signature")
    print(f"validated {len(expected)} material files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
