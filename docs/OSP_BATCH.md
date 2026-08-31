# OSP Batch Runner

`tools/osp_batch.py` is a small wrapper around `opencode run`. It runs one
isolated Open ScholarPeer session per manuscript and preserves that session's
outputs.

For the source-versus-generated-file boundary and the Fork installation loop,
see [`OSP_FORK_WORKFLOW.md`](OSP_FORK_WORKFLOW.md).

## Trail layout

```text
osp-trails/<paper-name>/<run-timestamp>/
  manifest.json
  opencode.log
  brain/                 # copied from the run's .brain directory
  workspace/             # isolated input/config used by opencode
```

Every executed run gets a new timestamp directory, so rerunning a paper never
overwrites an older review. `osp-trails/` is gitignored because review content
may be confidential. A trail is durably archived in the private Hugging Face
dataset only when `--trail-repo ... --upload` is supplied and the upload
succeeds. An upload failure makes the runner exit nonzero even if the review
itself completed. The named dataset must already be private; Hugging Face's
`--private` option only affects creation of a repository that does not yet
exist.

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
  --trail-repo Jack-Jieke-Wu/osp-trails \
  --upload \
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

Add `--trail-repo NAMESPACE/DATASET --upload` to upload each completed or
failed trail to a private Hugging Face dataset. The `workspace/` directory is
excluded from uploads; only the manifest, log, and copied `brain/` artifacts
are uploaded.

## Notes

- The runner is parallel across papers and does not modify OSP's personas or
  prompts. Each paper still has its own isolated workspace and trail.
- The venue is supplied once and reused for every paper in the invocation.
- If one paper fails after its trail directory is created, the runner records
  its manifest and log and continues with the next. Invalid global CLI
  settings are rejected before paper workers start.
- A run is marked completed only when OpenCode exits successfully and produces
  `.brain/review/final_review.md`.
- A failed paper can be rerun by invoking the command again; this creates a new
  trail rather than attempting complicated in-place recovery.
- The OSP onboarding phase may still ask for interactive confirmation because
  that is part of the existing OSP command contract. If unattended execution
  stops there, the trail contains the log and workspace for inspection.

## Version Comparison

`tools/osp_compare.py` reviews two or more versions of the same paper with
identical settings and compares the resulting opinions. Versions can be given
in any of three equivalent forms:

- `--v1/--v2/--v3` — the classic three-version form (used by the erdos973
  sanity check);
- `--versions PDF [PDF ...]` — an arbitrary two-or-more-version list, in
  order;
- `--paper-dir DIR` — a corpus directory whose `v*.pdf` files are the
  versions, discovered in sorted order (e.g. `v1.pdf v2.pdf`).

The comparison name defaults to the versions' parent directory
(`--name` overrides it) and the report is written under
`osp-trails/<name>-comparison/<timestamp>/`. `--expected-order v1,v3` can
restate the expected quality progression when it differs from the file order;
the Structured Ordering Check evaluates the recommendations along that order.

Three-version sanity check (erdos973):

```bash
python3 tools/osp_compare.py \
  --v1 papers/erdos973/v1.pdf \
  --v2 papers/erdos973/v2.pdf \
  --v3 papers/erdos973/v3.pdf \
  --venue arxiv \
  --llm openai/gpt-5.6-sol \
  --variant medium \
  --harness opencode \
  --trail-repo Jack-Jieke-Wu/osp-trails
```

Two-version comparison of a corpus directory, e.g. the LSM charge transport
paper:

```bash
python3 tools/osp_compare.py \
  --paper-dir papers/lieb_schultz_mattis_charge_transport \
  --expected-order v1,v2 \
  --venue arxiv \
  --llm openai/gpt-5.6-sol \
  --variant medium \
  --harness opencode \
  --trail-repo Jack-Jieke-Wu/osp-trails
```

To reuse existing local completed trails instead, add `--reuse`. Reuse does
not download from Hugging Face and requires the local PDFs plus a
successful local trail containing `brain/review/final_review.md` for each
version. The command writes a new comparison report only after those local
prerequisites are present. Without `--reuse`, supplying `--trail-repo` uploads
the version trails and the generated comparison report.

The comparison command reviews all versions in parallel with identical
settings, then writes `comparison.md` and one copy of each final review under
`osp-trails/<name>-comparison/<timestamp>/`. The report records the expected
ordering (`v1 < v2 < ...`), extracts recommendation and confidence signals,
and includes diffs between each pair of consecutive versions. The structured
ordering check is diagnostic only: equal reviewer outcomes are reported as
tied rather than being converted into a fabricated quality ranking.
