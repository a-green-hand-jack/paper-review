"""The dataset manifest: one line per emitted task.

Harbor datasets are directories, so the manifest is what lets a collected
review be traced back to a paper version and the exact bytes it was written
from. It is written once, at build time, and travels with the dataset.

What it deliberately does not record is whether a run had network access. That
is a property of the `harbor run` invocation, not of the task, and belongs in
the run record beside the review.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .ingest import IngestResult
from .spec import TaskSpec

MANIFEST_NAME = "dataset-manifest.jsonl"


def source_record_id_for(task_id: str, source_sha256: str) -> str:
    """Stable identifier shared by a runnable task, trail, and raw source record."""
    if len(source_sha256) != 64 or any(char not in "0123456789abcdef" for char in source_sha256):
        raise ValueError("source_sha256 must be a lowercase SHA-256 hex digest")
    return f"prb-{task_id}-{source_sha256[:16]}"


@dataclass(frozen=True)
class ManifestRow:
    task_id: str
    source_record_id: str
    paper_slug: str
    paper_version: str | None
    title: str | None
    venue: str
    domain: str
    paper_kind: str
    paper_url: str | None
    paper_doi: str | None
    paper_arxiv_id: str | None
    paper_license: str
    source_access: str
    collection_workflow: str
    build_workflow: str
    related_writing_task_ids: list[str]
    source_sha256: str
    main_tex: str
    tex_lines: int
    n_sections: int
    n_citations: int
    has_spec: bool


def row_for(
    result: IngestResult,
    spec: TaskSpec,
    slug: str,
    version: str | None,
    *,
    has_spec: bool,
) -> ManifestRow:
    paper_map = result.paper_map
    return ManifestRow(
        task_id=result.label,
        source_record_id=source_record_id_for(result.label, result.source_sha256),
        paper_slug=slug,
        paper_version=version,
        title=spec.title or paper_map.title,
        venue=spec.venue,
        domain=spec.domain,
        paper_kind=spec.paper_kind,
        paper_url=spec.paper_url,
        paper_doi=spec.paper_doi,
        paper_arxiv_id=spec.paper_arxiv_id,
        paper_license=spec.paper_license,
        source_access=spec.source_access,
        collection_workflow=spec.collection_workflow,
        build_workflow=spec.build_workflow,
        related_writing_task_ids=sorted(spec.related_writing_task_ids),
        source_sha256=result.source_sha256,
        main_tex=result.main_tex,
        tex_lines=paper_map.total_tex_lines,
        n_sections=len(paper_map.sections),
        n_citations=len(paper_map.cited_keys),
        has_spec=has_spec,
    )


def write_manifest(tasks_root: Path, dataset: str, rows: list[ManifestRow]) -> Path:
    path = tasks_root / dataset / MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(asdict(row), ensure_ascii=False) + "\n"
            for row in sorted(rows, key=lambda r: r.task_id)
        ),
        encoding="utf-8",
    )
    return path
