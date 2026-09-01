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


@dataclass(frozen=True)
class ManifestRow:
    task_id: str
    paper_slug: str
    paper_version: str | None
    title: str | None
    venue: str
    domain: str
    paper_kind: str
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
        paper_slug=slug,
        paper_version=version,
        title=spec.title or paper_map.title,
        venue=spec.venue,
        domain=spec.domain,
        paper_kind=spec.paper_kind,
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
