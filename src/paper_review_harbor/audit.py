"""Prove that an emitted task does not hand the agent its own answers.

Every check here exists because the corpus contains a concrete way to leak:

- `solution-*/paper/review/` is the writing-time internal review. It names the
  defects by name.
- `solution-*/paper/plan.md` is the writing plan.
- A later version of a paper is a worked answer key for the earlier one, and
  three papers ship two or three versions.
- The rubric itself, and the reference review rendered from it.

The audit is deliberately dumb and literal: it reads what was actually written
to disk rather than trusting that `emit` copied the right things. A test that
re-derives the answer from the same code that produced it proves nothing.
"""

from __future__ import annotations

import hashlib
import re
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .corpus import PRIVATE_BASENAMES, PRIVATE_DIRNAMES, PaperVersion
from .rubric import Rubric

#: Strings this short are words, not answers; matching on them only produces
#: false alarms.
MIN_LEAK_CHARS = 40

TEXTUAL_SUFFIXES = frozenset(
    {".tex", ".ltx", ".bib", ".bbl", ".md", ".txt", ".json", ".yaml", ".yml", ".sty", ".cls", ""}
)


@dataclass(frozen=True)
class Violation:
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.kind}] {self.detail}"


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _readable_files(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() in TEXTUAL_SUFFIXES
    ]


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


def _private_strings(rubric: Rubric) -> list[tuple[str, str]]:
    """(label, text) pairs that must not appear in agent-visible material."""
    out: list[tuple[str, str]] = []
    for finding in rubric.findings:
        for field in ("title", "claim", "defect", "accept_if", "reject_if"):
            value = getattr(finding, field, "") or ""
            if len(value.strip()) >= MIN_LEAK_CHARS:
                out.append((f"{finding.id}.{field}", value))
    for distractor in rubric.distractors:
        for field in ("description", "why_not_a_defect"):
            value = getattr(distractor, field, "") or ""
            if len(value.strip()) >= MIN_LEAK_CHARS:
                out.append((f"{distractor.id}.{field}", value))
    for index, entry in enumerate(rubric.provenance):
        if len(entry.detail.strip()) >= MIN_LEAK_CHARS:
            out.append((f"provenance[{index}]", entry.detail))
    if rubric.notes and len(rubric.notes.strip()) >= MIN_LEAK_CHARS:
        out.append(("notes", rubric.notes))
    return out


def audit_task(
    task_dir: Path,
    rubric: Rubric,
    version: PaperVersion | None = None,
) -> list[Violation]:
    """Everything wrong with an emitted task, or an empty list."""
    violations: list[Violation] = []
    environment = task_dir / "environment"
    instruction = task_dir / "instruction.md"

    if not environment.is_dir():
        return [Violation("structure", f"{task_dir}: no environment/ directory")]

    # 1. The writing-time trail must not have been copied in.
    for path in environment.rglob("*"):
        relative = path.relative_to(task_dir).as_posix()
        if path.is_dir() and path.name in PRIVATE_DIRNAMES:
            violations.append(Violation("private-dir", f"{relative}/ is a writing-time trail"))
        elif path.is_file() and path.name in PRIVATE_BASENAMES:
            violations.append(Violation("private-file", f"{relative} is a writing-time trail"))

    # 2. No rubric text anywhere the agent can read it.
    agent_visible = _readable_files(environment)
    if instruction.is_file():
        agent_visible.append(instruction)
    haystacks = {
        path.relative_to(task_dir).as_posix(): _normalise(
            path.read_text(encoding="utf-8", errors="replace")
        )
        for path in agent_visible
    }
    for label, secret in _private_strings(rubric):
        needle = _normalise(secret)
        for where, haystack in haystacks.items():
            if needle and needle in haystack:
                violations.append(
                    Violation("rubric-leak", f"{where} contains rubric text {label}")
                )

    # 3. The reference review must never be agent-visible.
    for path in environment.rglob("*"):
        if path.is_file() and "reference_review" in path.name:
            violations.append(
                Violation(
                    "answer-key",
                    f"{path.relative_to(task_dir).as_posix()} is the reference review",
                )
            )

    # 4. A later version of the paper is an answer key. Compare by content, so a
    #    rename cannot slip one through -- but only on content the later version
    #    actually changed. A file both versions share (an unchanged .bib, a
    #    style file) belongs to this version too, and flagging it is noise.
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
                        "answer-key",
                        f"{path.relative_to(task_dir).as_posix()} is byte-identical to "
                        "content introduced by a later version of this paper",
                    )
                )

    # 5. The verifier must actually hold the rubric, and the environment must
    #    not reach for it.
    private_rubric = task_dir / "tests" / "private" / "rubric.json"
    if not private_rubric.is_file():
        violations.append(Violation("structure", "tests/private/rubric.json is missing"))
    dockerfile = environment / "Dockerfile"
    if dockerfile.is_file():
        # Instructions only. The comments in this Dockerfile explain what is
        # deliberately absent, and matching on the word would flag the
        # explanation as the thing it explains.
        instructions = "\n".join(
            line
            for line in dockerfile.read_text(encoding="utf-8", errors="replace").splitlines()
            if not line.lstrip().startswith("#")
        )
        for marker in ("tests/", "rubric", "reference_review", "solution/"):
            if marker in instructions:
                violations.append(
                    Violation("structure", f"environment/Dockerfile references {marker!r}")
                )

    return violations


def audit_dataset(
    tasks_root: Path,
    rubrics: dict[str, Rubric],
    versions: dict[str, PaperVersion] | None = None,
) -> dict[str, list[Violation]]:
    """Audit every emitted task under `tasks_root`, keyed by task path."""
    versions = versions or {}
    report: dict[str, list[Violation]] = {}
    for task_toml in sorted(tasks_root.rglob("task.toml")):
        task_dir = task_toml.parent
        label = task_dir.name
        rubric = rubrics.get(label)
        if rubric is None:
            report[str(task_dir)] = [Violation("structure", f"no rubric loaded for {label}")]
            continue
        report[str(task_dir)] = audit_task(task_dir, rubric, versions.get(label))
    return report
