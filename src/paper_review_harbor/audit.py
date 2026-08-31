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
import json
import re
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .corpus import (
    MANUSCRIPT_PDF_DECLARATION_RE,
    PRIVATE_BASENAMES,
    PRIVATE_DIRNAMES,
    PaperVersion,
)

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
COMPILED_PDF_RE = re.compile(r"and `([^`]+)` as the compiled PDF")
DOCUMENTCLASS_RE = re.compile(r"\\documentclass\s*(?:\[[^]]*\])?\s*\{")
CANONICAL_BUNDLED_PDF_NAMES = ("main.pdf", "paper.pdf", "manuscript.pdf")


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


def _archive_files(archive: Path) -> dict[str, bytes]:
    """Read safe archive members using the same one-directory flattening as staging."""
    members: dict[str, bytes] = {}
    root_entries: set[str] = set()

    def remember_root(name: str) -> None:
        if parts := Path(name).parts:
            root_entries.add(parts[0])

    try:
        if archive.name.endswith((".tar.gz", ".tgz")):
            with tarfile.open(archive, "r:gz") as tar:
                for member in tar.getmembers():
                    remember_root(member.name)
                    if member.isfile() and (handle := tar.extractfile(member)):
                        members[member.name] = handle.read()
        elif archive.suffix.lower() == ".zip":
            with zipfile.ZipFile(archive) as zipped:
                for name in zipped.namelist():
                    remember_root(name)
                    if not name.endswith("/"):
                        members[name] = zipped.read(name)
    except (tarfile.TarError, zipfile.BadZipFile, OSError):
        return {}

    visible_roots = {name for name in root_entries if not name.startswith(".")}
    if len(visible_roots) == 1:
        wrapper = next(iter(visible_roots))
        wrapped_files = all(
            len(Path(name).parts) > 1 and Path(name).parts[0] == wrapper
            for name in members
            if not Path(name).parts[0].startswith(".")
        )
        if not wrapped_files:
            return members
        return {
            (
                Path(*Path(name).parts[1:]).as_posix()
                if Path(name).parts[0] == wrapper
                else name
            ): content
            for name, content in members.items()
        }
    return members


def _directory_files(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def _strip_tex_comments(text: str) -> str:
    """Mirror ingestion's comment removal before identifying document-bearing TeX."""
    kept: list[str] = []
    for line in text.splitlines():
        buffer: list[str] = []
        escaped = False
        for char in line:
            if escaped:
                buffer.append(char)
                escaped = False
            elif char == "\\":
                buffer.append(char)
                escaped = True
            elif char == "%":
                break
            else:
                buffer.append(char)
        kept.append("".join(buffer))
    return "\n".join(kept)


def _source_main_tex(files: dict[str, bytes]) -> tuple[str, str] | None:
    """Independently mirror ingestion's arXiv declaration and TeX fallback rules."""
    try:
        readme = json.loads(files.get("00README.json", b"").decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        readme = {}
    for source in readme.get("sources", []):
        name = source.get("filename")
        if source.get("usage") == "toplevel" and isinstance(name, str) and name in files:
            return name, files[name].decode("utf-8", errors="replace")

    candidates: list[tuple[str, str]] = []
    for name, content in files.items():
        if Path(name).suffix.lower() not in {".tex", ".ltx"}:
            continue
        text = content.decode("utf-8", errors="replace")
        stripped = _strip_tex_comments(text)
        if DOCUMENTCLASS_RE.search(stripped) and "\\begin{document}" in stripped:
            candidates.append((name, text))
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (Path(item[0]).name != "main.tex", len(Path(item[0]).parts), item[0])
    )
    return candidates[0]


def _bundled_manuscript_hash(files: dict[str, bytes]) -> str | None:
    """Resolve only declared, TeX-stem, or canonical source-backed PDFs."""
    main = _source_main_tex(files)
    if main is None:
        return None
    main_name, main_text = main
    declared = [
        match.group(1)
        for line in main_text.splitlines()
        if (match := MANUSCRIPT_PDF_DECLARATION_RE.match(line))
    ]
    names = [
        *declared,
        Path(main_name).with_suffix(".pdf").as_posix(),
        *CANONICAL_BUNDLED_PDF_NAMES,
    ]
    for name in dict.fromkeys(names):
        if content := files.get(name):
            return hashlib.sha256(content).hexdigest()
    return None


def _source_manuscript_hash(version: PaperVersion) -> str | None:
    """Resolve a bundled manuscript from the original source, independently of staging."""
    if version.source_kind == "archive":
        return _bundled_manuscript_hash(_archive_files(version.source))
    if version.source_kind == "directory":
        return _bundled_manuscript_hash(_directory_files(version.source))
    return None


def _declared_pdf(instruction: Path) -> str | None:
    """Return the single compiled-PDF path declared to the review agent."""
    if not instruction.is_file():
        return None
    declarations = COMPILED_PDF_RE.findall(
        instruction.read_text(encoding="utf-8", errors="replace")
    )
    return declarations[0] if len(declarations) == 1 else None


def _is_within(path: Path, directory: Path) -> bool:
    """Whether a path stays inside a directory after following symlinks."""
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


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
    paper = environment / "paper"

    # The instruction and staged input are separate outputs of emit. Check both
    # rather than trusting its PDF-selection result when auditing a task.
    declared_pdf = _declared_pdf(task_dir / "instruction.md")
    if declared_pdf is None:
        violations.append(
            Violation("compiled-pdf", "instruction.md has no compiled-PDF declaration")
        )
    else:
        declared_path = Path(declared_pdf)
        if declared_path.is_absolute() or ".." in declared_path.parts:
            violations.append(
                Violation("compiled-pdf", f"invalid compiled-PDF path {declared_pdf!r}")
            )
        elif not _is_within(paper / declared_path, paper):
            violations.append(
                Violation("compiled-pdf", f"invalid compiled-PDF path {declared_pdf!r}")
            )
        elif not (paper / declared_path).is_file():
            violations.append(
                Violation("compiled-pdf", f"environment/paper/{declared_pdf} is missing")
            )
        elif version is not None:
            expected_hash = _source_manuscript_hash(version)
            if expected_hash is None and version.pdf is not None and version.pdf.is_file():
                expected_hash = _sha256(version.pdf)
            if expected_hash is None and version.source_kind in {"archive", "directory"}:
                violations.append(
                    Violation(
                        "manuscript-pdf",
                        f"environment/paper/{declared_pdf} has no recognized source manuscript PDF",
                    )
                )
            elif expected_hash is not None and _sha256(paper / declared_path) != expected_hash:
                violations.append(
                    Violation(
                        "manuscript-pdf",
                        f"environment/paper/{declared_pdf} does not match the corpus "
                        "manuscript PDF",
                    )
                )

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
