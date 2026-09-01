"""Publish the generated task dataset to a Hugging Face repository.

Harbor consumes a Hugging Face dataset directly, without a `registry.json`: it
clones the tree, scans the named subdirectory for directories containing
`task.toml`, and warns-then-defaults if no dataset name is given. Verified
against harbor 0.20.0 `registry/client/git_repo.py`. So the only structural
requirement is that tasks sit one level below a subdirectory of the repo:

    <repo>/paper-review-exam/<task-id>/task.toml

which is what `emit` already produces.

Publishing is outward-facing and hard to undo -- a public dataset can be
cached, mirrored, or scraped between the push and any later deletion. Two
guards follow. The audit runs again here rather than trusting that `emit` ran
it, since the tasks on disk may have been edited since. And the upload is
opt-in: without `--execute` this reports what it would send and stops.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .audit import audit_task
from .corpus import PaperVersion
from .emit import DATASET_NAME

#: Written into the repo so a reader can tell what the tasks are without
#: opening one.
README_NAME = "README.md"


class PublishError(RuntimeError):
    """The dataset could not be published."""


@dataclass(frozen=True)
class PublishPlan:
    repo_id: str
    dataset: str
    local_dir: Path
    task_ids: tuple[str, ...]
    total_bytes: int
    revision: str

    @property
    def harbor_repo_url(self) -> str:
        return (
            f"https://huggingface.co/datasets/{self.repo_id}"
            f"/tree/{self.revision}/{self.dataset}"
        )

    def harbor_command(self, agent: str = "opencode") -> str:
        return f"harbor run --repo {self.harbor_repo_url} -a {agent}"


def _tree_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def plan_publish(
    tasks_root: Path,
    repo_id: str,
    *,
    dataset: str = DATASET_NAME,
    revision: str = "main",
    versions: dict[str, PaperVersion] | None = None,
) -> PublishPlan:
    """Audit the emitted tasks and describe what publishing them would send.

    Raises rather than returning a partial plan: a dataset published with one
    contaminated task is worse than one not published, because the reviews
    collected against that task look exactly like the clean ones.
    """
    local_dir = tasks_root / dataset
    if not local_dir.is_dir():
        raise PublishError(f"{local_dir} does not exist; run `pre-harbor emit` first")

    task_dirs = sorted(p.parent for p in local_dir.rglob("task.toml"))
    if not task_dirs:
        raise PublishError(f"{local_dir} holds no tasks")

    versions = versions or {}
    problems: list[str] = []
    for task_dir in task_dirs:
        for violation in audit_task(task_dir, versions.get(task_dir.name)):
            problems.append(f"{task_dir.name}: {violation}")
    if problems:
        listed = "\n".join(f"  - {problem}" for problem in problems)
        raise PublishError(
            f"refusing to publish {len(problems)} audit violation(s):\n{listed}"
        )

    return PublishPlan(
        repo_id=repo_id,
        dataset=dataset,
        local_dir=local_dir,
        task_ids=tuple(p.name for p in task_dirs),
        total_bytes=_tree_bytes(local_dir),
        revision=revision,
    )


def render_readme(plan: PublishPlan, manifest_rows: list[dict]) -> str:
    """A dataset card that says what these tasks are and are not."""
    domains = sorted({row.get("domain", "unknown") for row in manifest_rows})
    slugs = sorted({row.get("paper_slug", "") for row in manifest_rows})
    return f"""---
license: mit
task_categories:
- text-generation
tags:
- peer-review
- scientific-review
- harbor
- agent-evaluation
---

# Paper-Reviewing-Exam

Harbor tasks for **collecting** peer reviews of scientific manuscripts. Each
task hands an agent a complete paper and asks it to write a review; the review
is archived for human experts to assess afterwards.

**These tasks do not score reviews.** The verifier checks only that
`review.md` was written and is substantive. There is no rubric and no LLM
judge, because deciding what counts as a good review is the judgement the human
experts are for.

- **{len(plan.task_ids)} tasks** from {len(slugs)} papers
- Fields: {", ".join(domains)}
- Each version of a paper is an independent task: a later version fixes the
  earlier one's problems, so a review of one is not a review of the other.

## Running

Harbor reads this repository directly:

```bash
{plan.harbor_command()}
```

Tasks declare `network_mode = "no-network"`. Passing `--allow-agent-host`
promotes the policy to an allowlist, so the same task serves closed-book and
open-book runs:

```bash
{plan.harbor_command()} \\
  --allow-agent-host arxiv.org \\
  --allow-agent-host api.semanticscholar.org
```

**Whether a run had network access is a property of the invocation, not of the
task.** Record it alongside the review, or a later reader cannot tell whether
an agent that checked no citations was unable to or merely did not.

## Layout

```
{plan.dataset}/
├── dataset-manifest.jsonl      one row per task: provenance and source hash
└── <task-id>/
    ├── task.toml
    ├── instruction.md
    ├── environment/            Dockerfile + the manuscript
    ├── solution/solve.sh       placeholder-review oracle
    └── tests/                  submission-contract check
```

## Contamination

The writing-time review trail and later revisions of each paper are excluded
from every task environment and checked for at build time, because a review
written by an agent that read them looks exactly like a very good review and
nothing downstream can tell.

Two paths remain open and are not fixable inside a task:

1. **Multi-version papers are public on arXiv.** An agent reviewing v1 with
   `arxiv.org` reachable can fetch v2 and read what was fixed. Consider running
   version-set papers closed-book, or recording that the risk applies.
2. **This repository also hosts the raw sources under `papers/`,** including the
   writing-time trail for the `solution-*` manuscripts. `huggingface.co` is not
   in the suggested allowlist, so a task run cannot reach it, but do not add it.

## Provenance

Built by [`pre-harbor`](https://github.com/a-green-hand-jack/paper-review) from
the LaTeX sources in `papers/`. `dataset-manifest.jsonl` records each task's
source SHA-256, so a collected review can be traced to the exact bytes it was
written from.

Benchmark canary GUIDs are embedded in every task. This data should not appear
in training corpora.
"""


def _hf_upload(repo_id: str, source: Path, destination: str, revision: str) -> list[str]:
    return [
        "hf",
        "upload",
        "--repo-type",
        "dataset",
        "--revision",
        revision,
        repo_id,
        str(source),
        destination,
    ]


def upload(plan: PublishPlan, *, readme: str | None = None, execute: bool = False) -> str:
    """Upload the planned dataset. Without `execute`, reports and stops.

    Returns the command lines, so a dry run prints exactly what a real one
    would do.
    """
    if not shutil.which("hf"):
        raise PublishError("the `hf` CLI is not on PATH; install huggingface-hub to publish")

    staged_readme = plan.local_dir.parent / f".{README_NAME}.staged"
    commands = [_hf_upload(plan.repo_id, plan.local_dir, plan.dataset, plan.revision)]
    if readme is not None:
        commands.append(_hf_upload(plan.repo_id, staged_readme, README_NAME, plan.revision))
    printable = "\n".join(" ".join(command) for command in commands)

    if not execute:
        return printable

    if readme is not None:
        staged_readme.write_text(readme, encoding="utf-8")
    try:
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                raise PublishError(
                    f"`{' '.join(command)}` failed with {result.returncode}:\n"
                    f"{result.stderr.strip()}"
                )
    finally:
        staged_readme.unlink(missing_ok=True)
    return printable


def read_manifest(plan: PublishPlan) -> list[dict]:
    path = plan.local_dir / "dataset-manifest.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
