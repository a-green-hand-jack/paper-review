"""Build and publish the restricted raw-source archive outside Harbor tasks."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .corpus import PaperVersion
from .ingest import ingest, sha256_file
from .manifest import source_record_id_for
from .spec import TaskSpec

SOURCE_ARCHIVE_NAME = "paperbench-source-archive"
SOURCE_ARCHIVE_MANIFEST = "source-records.jsonl"


class SourceArchiveError(RuntimeError):
    """The raw source archive cannot be built or published safely."""


@dataclass(frozen=True)
class SourceRecord:
    schema_version: int
    source_record_id: str
    task_id: str
    paper_slug: str
    paper_version: str | None
    title: str | None
    source_url: str | None
    doi: str | None
    arxiv_id: str | None
    license: str
    access: str
    source_kind: str
    source_sha256: str
    source_filename: str
    manuscript_pdf_filename: str | None
    manuscript_pdf_sha256: str | None
    collection_workflow: str
    build_workflow: str
    related_writing_task_ids: list[str]


@dataclass(frozen=True)
class SourceArchivePlan:
    repo_id: str
    local_dir: Path
    revision: str


def _copy_source(version: PaperVersion, destination: Path) -> None:
    if version.source.is_symlink():
        raise SourceArchiveError(f"{version.source} is a symlink")
    if version.source.is_dir():
        if any(path.is_symlink() for path in version.source.rglob("*")):
            raise SourceArchiveError(f"{version.source} contains a symlink")
        shutil.copytree(version.source, destination)
    else:
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(version.source, destination / version.source.name)


def build_source_archive(
    versions: list[PaperVersion],
    specs: dict[str, TaskSpec],
    *,
    build: Path,
    destination: Path,
) -> list[SourceRecord]:
    """Materialize original collection inputs in a deliberately restricted tree."""
    if destination.exists():
        shutil.rmtree(destination)
    source_root = destination / "sources"
    records: list[SourceRecord] = []
    for version in sorted(versions, key=lambda item: item.label):
        spec = specs[version.label]
        if spec.source_access != "restricted":
            raise SourceArchiveError(
                f"{version.label}: raw source archive entries must be restricted"
            )
        staged = ingest(version, build)
        source_record_id = source_record_id_for(version.label, staged.source_sha256)
        record_root = source_root / source_record_id
        _copy_source(version, record_root / "collection-input")
        pdf_name = version.pdf.name if version.pdf and version.pdf.is_file() else None
        pdf_hash = sha256_file(version.pdf) if pdf_name and version.pdf else None
        if pdf_name and version.pdf:
            pdf_root = record_root / "manuscript-pdf"
            pdf_root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(version.pdf, pdf_root / pdf_name)
        records.append(
            SourceRecord(
                schema_version=1,
                source_record_id=source_record_id,
                task_id=version.label,
                paper_slug=version.slug,
                paper_version=version.version,
                title=spec.title or staged.paper_map.title,
                source_url=spec.paper_url,
                doi=spec.paper_doi,
                arxiv_id=spec.paper_arxiv_id,
                license=spec.paper_license,
                access=spec.source_access,
                source_kind=version.source_kind,
                source_sha256=staged.source_sha256,
                source_filename=version.source.name,
                manuscript_pdf_filename=pdf_name,
                manuscript_pdf_sha256=pdf_hash,
                collection_workflow=spec.collection_workflow,
                build_workflow=spec.build_workflow,
                related_writing_task_ids=sorted(spec.related_writing_task_ids),
            )
        )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / SOURCE_ARCHIVE_MANIFEST).write_text(
        "".join(json.dumps(asdict(record), ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    (destination / "README.md").write_text(
        "# PaperBench Source Archive\n\n"
        "This restricted archive preserves original collection inputs and build provenance. "
        "It is not a Harbor task dataset and must not be published as a public "
        "runnable benchmark.\n",
        encoding="utf-8",
    )
    return records


def plan_source_archive_publish(
    archive_root: Path, repo_id: str, *, revision: str = "main"
) -> SourceArchivePlan:
    if not (archive_root / SOURCE_ARCHIVE_MANIFEST).is_file():
        raise SourceArchiveError(f"{archive_root} is not a built source archive")
    return SourceArchivePlan(repo_id=repo_id, local_dir=archive_root, revision=revision)


def upload_source_archive(plan: SourceArchivePlan, *, execute: bool = False) -> str:
    """Publish only after creating and checking a private HF dataset repository."""
    if not shutil.which("hf"):
        raise SourceArchiveError("the `hf` CLI is not on PATH")
    create = [
        "hf", "repo", "create", plan.repo_id, "--repo-type", "dataset", "--private", "--exist-ok"
    ]
    inspect = ["hf", "datasets", "info", plan.repo_id, "--format", "json"]
    upload = [
        "hf",
        "upload",
        "--repo-type",
        "dataset",
        "--revision",
        plan.revision,
        plan.repo_id,
        str(plan.local_dir),
        ".",
    ]
    commands = "\n".join(" ".join(command) for command in (create, inspect, upload))
    if execute:
        result = subprocess.run(create, capture_output=True, text=True)
        if result.returncode:
            raise SourceArchiveError(
                f"`{' '.join(create)}` failed with {result.returncode}: {result.stderr.strip()}"
            )
        result = subprocess.run(inspect, capture_output=True, text=True)
        if result.returncode:
            raise SourceArchiveError(
                f"`{' '.join(inspect)}` failed with {result.returncode}: {result.stderr.strip()}"
            )
        try:
            private = json.loads(result.stdout).get("private")
        except json.JSONDecodeError as error:
            raise SourceArchiveError("Hugging Face returned invalid dataset metadata") from error
        if private is not True:
            raise SourceArchiveError(
                f"refusing to upload raw sources: {plan.repo_id} is not private"
            )
        result = subprocess.run(upload, capture_output=True, text=True)
        if result.returncode:
            raise SourceArchiveError(
                f"`{' '.join(upload)}` failed with {result.returncode}: {result.stderr.strip()}"
            )
    return commands


def retire_runtime_sources(
    exam_repo_id: str,
    *,
    source_archive_repo_id: str,
    source_archive_revision: str,
    revision: str = "main",
    execute: bool = False,
) -> str:
    """Remove obsolete raw inputs from Exam only after an immutable archive release."""
    if len(source_archive_revision) != 40 or any(
        char not in "0123456789abcdef" for char in source_archive_revision
    ):
        raise SourceArchiveError(
            "source_archive_revision must be a 40-character lowercase commit SHA"
        )
    if not shutil.which("hf"):
        raise SourceArchiveError("the `hf` CLI is not on PATH")
    command = [
        "hf",
        "repos",
        "delete-files",
        exam_repo_id,
        "papers/**",
        "--type",
        "dataset",
        "--revision",
        revision,
        "--commit-message",
        "Retire raw paper inputs after restricted source archive release",
        "--commit-description",
        f"Source archive: {source_archive_repo_id}@{source_archive_revision}",
    ]
    printable = " ".join(command)
    if execute:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise SourceArchiveError(
                f"`{printable}` failed with {result.returncode}: {result.stderr.strip()}"
            )
    return printable
