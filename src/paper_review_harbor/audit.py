"""Prove that an emitted task does not hand the agent a review to copy.

This matters more here than it would in a scored benchmark. The product is a
`(paper, review.md)` pair that a human expert will read later, and an expert
looking at a contaminated review has no way to tell. A review written by an
agent that read the manuscript's own writing-time defect trail looks exactly
like a very good review. The contamination has to be prevented at build time,
because it cannot be detected afterwards.

The corpus offers two concrete ways to leak:

- `solution-*/paper/review/` holds the internal review written while the paper
  was being drafted -- it names the defects outright -- and `plan.md` holds the
  writing plan.
- A later version of a paper is the earlier one with its problems fixed. Three
  papers here ship two or three versions.

The checks read what was actually written to disk rather than trusting that
`emit` copied the right things, because a test that re-derives the answer from
the same code proves nothing.
"""

from __future__ import annotations

import hashlib
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .corpus import PRIVATE_BASENAMES, PRIVATE_DIRNAMES, PaperVersion

REQUIRED_FILES = (
    "task.toml",
    "instruction.md",
    "environment/Dockerfile",
    "solution/solve.sh",
    "tests/Dockerfile",
    "tests/test.sh",
    "tests/check_submission.py",
    "tests/contract.json",
)


@dataclass(frozen=True)
class Violation:
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.kind}] {self.detail}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_member_hashes(archive: Path) -> set[str]:
    hashes: set[str] = set()
    try:
        if archive.name.endswith((".tar.gz", ".tgz")):
            with tarfile.open(archive, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        handle = tar.extractfile(member)
                        if handle:
                            hashes.add(hashlib.sha256(handle.read()).hexdigest())
        elif archive.suffix.lower() == ".zip":
            with zipfile.ZipFile(archive) as zipped:
                for name in zipped.namelist():
                    if not name.endswith("/"):
                        hashes.add(hashlib.sha256(zipped.read(name)).hexdigest())
    except (tarfile.TarError, zipfile.BadZipFile, OSError):
        return set()
    return hashes


def _source_hashes(path: Path) -> set[str]:
    """Content hashes of everything in a paper source, whatever shape it is."""
    if path.is_dir():
        return {_sha256(p) for p in path.rglob("*") if p.is_file()}
    if path.is_file() and path.name.endswith((".tar.gz", ".tgz", ".zip")):
        return _archive_member_hashes(path)
    if path.is_file():
        return {_sha256(path)}
    return set()


def audit_task(task_dir: Path, version: PaperVersion | None = None) -> list[Violation]:
    """Everything wrong with an emitted task, or an empty list."""
    violations: list[Violation] = []
    environment = task_dir / "environment"

    for relative in REQUIRED_FILES:
        if not (task_dir / relative).is_file():
            violations.append(Violation("structure", f"{relative} is missing"))
    if not (environment / "paper").is_dir():
        violations.append(Violation("structure", "environment/paper/ is missing"))
        return violations

    # 1. The writing-time trail must not have been copied in.
    for path in environment.rglob("*"):
        relative = path.relative_to(task_dir).as_posix()
        if path.is_dir() and path.name in PRIVATE_DIRNAMES:
            violations.append(Violation("private-dir", f"{relative}/ is a writing-time trail"))
        elif path.is_file() and path.name in PRIVATE_BASENAMES:
            violations.append(Violation("private-file", f"{relative} is a writing-time trail"))

    # 2. A later version of the paper is the same paper with its problems fixed.
    #    Compare by content so a rename cannot slip one through, but only on what
    #    the later version actually changed -- a file both versions share (an
    #    unchanged .bib, a style file) belongs to this version too.
    if version is not None and version.private_paths:
        own = _source_hashes(version.source)
        forbidden: set[str] = set()
        for private in version.private_paths:
            forbidden |= _source_hashes(private)
        forbidden -= own
        for path in environment.rglob("*"):
            if path.is_file() and _sha256(path) in forbidden:
                violations.append(
                    Violation(
                        "later-version",
                        f"{path.relative_to(task_dir).as_posix()} is byte-identical to "
                        "content introduced by a later version of this paper",
                    )
                )

    # 3. The environment image must not reach outside the manuscript.
    dockerfile = environment / "Dockerfile"
    if dockerfile.is_file():
        # Instructions only: the comments explain what is deliberately absent,
        # and matching on the word would flag the explanation as the thing it
        # explains.
        instructions = "\n".join(
            line
            for line in dockerfile.read_text(encoding="utf-8", errors="replace").splitlines()
            if not line.lstrip().startswith("#")
        )
        for marker in ("tests/", "solution/", "review/", "plan.md"):
            if marker in instructions:
                violations.append(
                    Violation("structure", f"environment/Dockerfile references {marker!r}")
                )

    return violations


def audit_dataset(
    tasks_root: Path, versions: dict[str, PaperVersion] | None = None
) -> dict[str, list[Violation]]:
    """Audit every emitted task under `tasks_root`, keyed by task directory."""
    versions = versions or {}
    report: dict[str, list[Violation]] = {}
    for task_toml in sorted(tasks_root.rglob("task.toml")):
        task_dir = task_toml.parent
        report[str(task_dir)] = audit_task(task_dir, versions.get(task_dir.name))
    return report
