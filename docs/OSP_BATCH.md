# OSP Batch Runner

`tools/osp_batch.py` is a small wrapper around `opencode run`. It runs one
isolated Open ScholarPeer session per manuscript and preserves that session's
outputs.

## Trail layout

```text
osp-trails/<paper-name>/<run-timestamp>/
  manifest.json
  opencode.log
  brain/                 # copied from the run's .brain directory
  workspace/             # isolated input/config used by opencode
```

Every invocation gets a new timestamp directory, so rerunning a paper never
overwrites an older review. `osp-trails/` is intentionally not gitignored:
review trails are the durable record. Review content may be confidential and
should be handled accordingly.

## Usage

Preview all current manuscript runs without calling the model:

```bash
python3 tools/osp_batch.py --venue arxiv
```

Run all manuscripts in parallel (4 papers at a time by default):

```bash
python3 tools/osp_batch.py \
  --venue arxiv \
  --llm openai/gpt-5.6-sol \
  --variant medium \
  --harness opencode \
  --all \
  --execute
```

Change the concurrency with `--workers`, for example `--workers 8`.

Run one paper:

```bash
python3 tools/osp_batch.py \
  --paper papers/solution-p8534/paper/main.pdf \
  --venue arxiv \
  --llm openai/gpt-5.6-sol \
  --variant medium \
  --execute
```

The CLI accepts `--llm`, `--variant`, `--harness`, `--paper`, and `--venue` so
an OpenCode TUI agent can construct exactly the run it wants. The shorthand
`gpt-5.6-sol-medium` is also accepted through `--llm` and maps to
`openai/gpt-5.6-sol` with variant `medium`.

## Notes

- The runner is parallel across papers and does not modify OSP's personas or
  prompts. Each paper still has its own isolated workspace and trail.
- The venue is supplied once and reused for every paper in the invocation.
- If one paper fails, the runner records its log and continues with the next.
- A run is marked completed only when OpenCode exits successfully and produces
  `.brain/review/final_review.md`.
- A failed paper can be rerun by invoking the command again; this creates a new
  trail rather than attempting complicated in-place recovery.
- The OSP onboarding phase may still ask for interactive confirmation because
  that is part of the existing OSP command contract. If unattended execution
  stops there, the trail contains the log and workspace for inspection.
