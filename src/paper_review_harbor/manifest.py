"""The dataset manifest: one line per emitted task.

Harbor datasets are directories, so the manifest is what lets a run be traced
back to a paper version, a source hash, and the person who signed off its
rubric. `tools/osp_batch.py` kept the same provenance in each trail's
`manifest.json`; the difference is that this one is written once, at build
time, rather than reconstructed per run.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .emit import dataset_name
from .ingest import IngestResult
from .rubric import Protocol, Rubric

MANIFEST_NAME = "dataset-manifest.jsonl"


@dataclass(frozen=True)
class ManifestRow:
    task_id: str
    dataset: str
    protocol: str
    paper_slug: str
    paper_version: str | None
    venue: str
    domain: str
    source_sha256: str
    main_tex: str
    n_findings: int
    n_gating: int
    n_distractors: int
    rubric_annotator: str
    rubric_annotated_at: str


def row_for(
    result: IngestResult, rubric: Rubric, protocol: Protocol
) -> ManifestRow:
    findings = rubric.findings_for(protocol)
    return ManifestRow(
        task_id=rubric.task_id_base,
        dataset=dataset_name(protocol),
        protocol=protocol.value,
        paper_slug=rubric.paper.slug,
        paper_version=rubric.paper.version,
        venue=rubric.paper.venue,
        domain=rubric.paper.domain,
        source_sha256=result.source_sha256,
        main_tex=result.main_tex,
        n_findings=len(findings),
        n_gating=len(rubric.gating_for(protocol)),
        n_distractors=len(rubric.distractors),
        rubric_annotator=rubric.annotator or "",
        rubric_annotated_at=rubric.annotated_at.isoformat() if rubric.annotated_at else "",
    )


def write_manifest(tasks_root: Path, protocol: Protocol, rows: list[ManifestRow]) -> Path:
    path = tasks_root / dataset_name(protocol) / MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(
        json.dumps(asdict(row), ensure_ascii=False) + "\n"
        for row in sorted(rows, key=lambda r: r.task_id)
    )
    path.write_text(body, encoding="utf-8")
    return path
