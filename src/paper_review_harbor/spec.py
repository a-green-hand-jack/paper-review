"""Per-paper metadata that ingestion cannot work out on its own.

Everything a task needs is derived from the source where that is possible --
the slug, the version, the toplevel TeX file, the title. What is left over is
what only a person knows: which venue the manuscript was submitted to, which
field it belongs to, and anything they want to tell the review agent about it.

A spec is therefore optional. A paper dropped into the corpus with no spec
still produces a working task, which is the property that lets this scale from
21 papers to several hundred without editing code. The spec exists to improve a
task, never to enable one.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

#: Used when a spec does not name a field and nothing can be derived. "unknown"
#: is deliberate: a wrong guess about a paper's field would reach the review
#: agent inside its instructions and steer the review it writes.
UNKNOWN = "unknown"


class SpecError(ValueError):
    """The spec file is malformed."""


class TaskSpec(BaseModel):
    """Optional overrides for one paper version."""

    model_config = ConfigDict(extra="forbid")

    label: str
    title: str | None = None
    venue: str = "arxiv"
    domain: str = UNKNOWN
    paper_kind: str = UNKNOWN
    notes: str = Field(
        default="",
        description="Free text shown to the review agent. The operator's brief.",
    )

    @classmethod
    def default_for(cls, label: str) -> TaskSpec:
        return cls(label=label)

    @classmethod
    def load(cls, path: Path) -> TaskSpec:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SpecError(f"{path}: expected a YAML mapping")
        return cls.model_validate(data)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(
                self.model_dump(mode="json"), sort_keys=False, allow_unicode=True, width=88
            ),
            encoding="utf-8",
        )


def spec_path(specs_root: Path, label: str) -> Path:
    return specs_root / f"{label}.yaml"


def load_spec(specs_root: Path, label: str) -> TaskSpec:
    """The spec for a label, or defaults when none has been written."""
    path = spec_path(specs_root, label)
    if not path.is_file():
        return TaskSpec.default_for(label)
    spec = TaskSpec.load(path)
    if spec.label != label:
        raise SpecError(f"{path}: label is {spec.label!r} but the file is named for {label!r}")
    return spec
