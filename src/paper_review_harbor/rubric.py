"""The human annotation contract.

A rubric is the only ground truth in this benchmark. Everything else --
staging, templates, the grader -- exists to serve it. It is authored by a
person, lives in git, and carries its own sign-off.

Two design decisions carry most of the weight:

`accept_if` / `reject_if`
    An LLM judge asked "did this review find the defect?" gives a different
    answer each time it is asked. Asked instead "does the review say something
    matching *this* sentence, and not merely *that* one?", it is deciding a
    bounded question. `docs/STATUS_REPORT.md` records recommendation jitter
    swamping real differences; bounded judgements plus repeated voting are the
    answer to it.

`protocols`
    The same paper ships as two tasks, offline and online. A defect that can
    only be found by searching the literature -- "this result was already
    obtained by Luo-Yang-Zhu" -- is not a fair thing to score in a container
    with no network. Each finding declares where it counts.
"""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

FINDING_ID_RE = re.compile(r"^F\d+$")
DISTRACTOR_ID_RE = re.compile(r"^D\d+$")

#: Below this, an `accept_if` is a label rather than a criterion, and the judge
#: is back to free judgement.
MIN_CRITERION_CHARS = 40

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class RubricError(ValueError):
    """The rubric is not fit to build a task from."""


class Status(StrEnum):
    DRAFT = "draft"
    ANNOTATED = "annotated"


class Severity(StrEnum):
    BLOCKING = "blocking"
    MAJOR = "major"
    MINOR = "minor"


class Detectability(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Protocol(StrEnum):
    OFFLINE = "offline"
    ONLINE = "online"


class ProvenanceKind(StrEnum):
    VERSION_DIFF = "version-diff"
    INTERNAL_REVIEW = "internal-review"
    AUTHOR_NOTE = "author-note"
    ANNOTATOR_JUDGEMENT = "annotator-judgement"


class Provenance(BaseModel):
    """Where an annotation came from. Private: never published into a task."""

    model_config = ConfigDict(extra="forbid")

    kind: ProvenanceKind
    detail: NonEmpty


class PaperRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: NonEmpty
    version: str | None = None
    venue: NonEmpty = "arxiv"
    domain: NonEmpty = "mathematics"
    hybrid_numerical: bool = False

    @property
    def label(self) -> str:
        return f"{self.slug}--{self.version}" if self.version else self.slug


class Finding(BaseModel):
    """One defect a competent review of this manuscript ought to report."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: NonEmpty
    severity: Severity
    gating: bool = False
    detectability: Detectability = Detectability.MEDIUM
    protocols: list[Protocol] = Field(default_factory=lambda: [Protocol.OFFLINE, Protocol.ONLINE])
    location: NonEmpty
    claim: NonEmpty
    defect: NonEmpty
    accept_if: NonEmpty
    reject_if: str = ""

    @model_validator(mode="after")
    def _check(self) -> Finding:
        if not FINDING_ID_RE.match(self.id):
            raise ValueError(f"finding id must look like F1, F2, ...: got {self.id!r}")
        if not self.protocols:
            raise ValueError(f"{self.id}: protocols must not be empty")
        if len(set(self.protocols)) != len(self.protocols):
            raise ValueError(f"{self.id}: duplicate protocols")
        if self.gating and self.severity is Severity.MINOR:
            raise ValueError(
                f"{self.id}: a minor defect cannot be gating -- gating means a review that "
                "misses it has failed. Raise the severity or clear the gating flag."
            )
        return self

    def applies_to(self, protocol: Protocol) -> bool:
        return protocol in self.protocols


class Distractor(BaseModel):
    """Something a review might flag that is not in fact a defect."""

    model_config = ConfigDict(extra="forbid")

    id: str
    description: NonEmpty
    why_not_a_defect: NonEmpty

    @model_validator(mode="after")
    def _check(self) -> Distractor:
        if not DISTRACTOR_ID_RE.match(self.id):
            raise ValueError(f"distractor id must look like D1, D2, ...: got {self.id!r}")
        return self


class Rubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id_base: NonEmpty
    paper: PaperRef
    status: Status = Status.DRAFT
    annotator: str | None = None
    annotated_at: date | None = None
    notes: str = ""
    provenance: list[Provenance] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    distractors: list[Distractor] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_ids_unique(self) -> Rubric:
        for kind, items in (("finding", self.findings), ("distractor", self.distractors)):
            seen = [item.id for item in items]
            duplicates = sorted({i for i in seen if seen.count(i) > 1})
            if duplicates:
                raise ValueError(f"duplicate {kind} ids: {', '.join(duplicates)}")
        if self.task_id_base != self.paper.label:
            raise ValueError(
                f"task_id_base {self.task_id_base!r} does not match paper label "
                f"{self.paper.label!r}"
            )
        return self

    # -- protocol views ----------------------------------------------------

    def findings_for(self, protocol: Protocol) -> list[Finding]:
        return [f for f in self.findings if f.applies_to(protocol)]

    def gating_for(self, protocol: Protocol) -> list[Finding]:
        return [f for f in self.findings_for(protocol) if f.gating]

    # -- sign-off ----------------------------------------------------------

    @property
    def is_annotated(self) -> bool:
        return self.status is Status.ANNOTATED

    def release_problems(self, protocols: list[Protocol] | None = None) -> list[str]:
        """Everything standing between this rubric and a publishable task."""
        protocols = protocols or list(Protocol)
        problems: list[str] = []

        if not self.is_annotated:
            problems.append(
                f"status is {self.status.value!r}: a person must review the draft and set "
                "status to 'annotated'"
            )
        if self.is_annotated and not self.annotator:
            problems.append("annotated rubric has no annotator")
        if self.is_annotated and self.annotated_at is None:
            problems.append("annotated rubric has no annotated_at date")
        if not self.findings:
            problems.append("no findings: there is nothing for a review to be scored against")

        for protocol in protocols:
            gating = self.gating_for(protocol)
            if not gating:
                problems.append(
                    f"protocol {protocol.value!r} has no gating finding, so its reward "
                    "(gating recall) would be undefined"
                )

        for finding in self.findings:
            if len(finding.accept_if.strip()) < MIN_CRITERION_CHARS:
                problems.append(
                    f"{finding.id}: accept_if is {len(finding.accept_if.strip())} chars; a "
                    f"criterion under {MIN_CRITERION_CHARS} is a label, not something a judge "
                    "can decide against"
                )
        return problems

    def assert_releasable(self, protocols: list[Protocol] | None = None) -> None:
        problems = self.release_problems(protocols)
        if problems:
            listed = "\n".join(f"  - {problem}" for problem in problems)
            raise RubricError(f"{self.task_id_base} is not ready to emit:\n{listed}")

    # -- io ----------------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> Rubric:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RubricError(f"{path}: expected a YAML mapping")
        return cls.model_validate(data)

    def dump(self) -> str:
        data = self.model_dump(mode="json", exclude_none=False)
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=88)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.dump(), encoding="utf-8")

    def public_view(self) -> dict:
        """What the grader needs. Provenance and notes stay behind.

        Provenance names the version diff or internal review an annotation came
        from. It is private for the same reason those files are: it describes
        the answer.
        """
        return {
            "task_id_base": self.task_id_base,
            "paper": self.paper.model_dump(mode="json"),
            "findings": [f.model_dump(mode="json") for f in self.findings],
            "distractors": [d.model_dump(mode="json") for d in self.distractors],
        }


def rubric_path(rubrics_root: Path, label: str) -> Path:
    return rubrics_root / f"{label}.yaml"


def load_rubric(rubrics_root: Path, label: str) -> Rubric:
    path = rubric_path(rubrics_root, label)
    if not path.is_file():
        raise RubricError(
            f"no rubric for {label!r} at {path}. Run `/paper2task` to draft one, then "
            "review and sign it off before emitting."
        )
    return Rubric.load(path)
