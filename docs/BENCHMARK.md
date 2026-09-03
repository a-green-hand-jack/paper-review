# Benchmark

This benchmark is **agent-agnostic**: it owns the task contract, the publishable
task snapshot, and the trail archive, but it does not maintain or run any
specific paper-review agent. A paper-review agent supports this benchmark by
running inside Harbor and writing `/workspace/submission/review.md` and
`/workspace/submission/review.json`; the agent
itself is whatever Harbor agent id you pass to `--agent`
(`codex`, `opencode`, `paper-run`, a custom Python agent class, ...).

One **agent condition** (provider/model/variant combination) runs the same six
Issue #19 tasks under Harbor, and every completed trial is archived — and
optionally uploaded — to the public trail dataset
[`Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails`](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails).

## The canonical task set

The current "six-task Issue #19" set is the canonical benchmark set:

```text
compression_induced_folding_of_a_sheet
de_novo_nanobody_discovery
hydrodynamics_of_large_language_models
superconductivity_uniform_electron_gas
transport_in_one_channel_luttinger_liquid
trapping_centers_superfluid_mott_insulator
```

Select them with `harbor run --include-task-name <task>` against the pinned
Exam snapshot. The task `instruction.md` asks the agent to read the manuscript
and write both review files; the verifier checks a substantive Markdown review
and a valid structured JSON companion.

Harbor reward in the trail manifests confirms only the submission contract (a
substantive `review.md` and valid `review.json`). It is not a review-quality score
and never becomes one — deciding quality is the job of the human experts who
read the trails.

## You do not need a checkout of this repository

The published exam snapshot is self-contained: each task carries its own
sanitized manuscript, material manifest, environment image, and verifier. To run
the benchmark and contribute a trail you need Docker, Harbor, the `hf` CLI, and a
provider credential — not the `papers/` corpus and not the build pipeline.

| You want to | You need |
|---|---|
| Run the six tasks with your agent | Harbor + an immutable Exam revision SHA |
| Archive and upload the resulting trails | the above, plus `pre-harbor archive-trail` ([one command, no clone](#archiving-a-trail-without-a-checkout)) |
| Add papers, change the task template, publish a new snapshot | a full checkout of this repository |

The third row is maintainer work. Everything else runs from a bare directory.

**Three separate things carry `vN.N.N` tags, and the numbers collide.** The
GitHub repository tags the *code*; the `Paper-Reviewing-Exam` dataset tags the
*task snapshot*; the `Paper-Reviewing-Exam-Trails` dataset tags the *archived
runs*. The Source Archive releases independently too. Matching version numbers
are coincidence, not provenance.

## Prerequisites

A Docker-capable Linux host:

```bash
harbor --version                  # Harbor 0.20.0
docker info                       # must succeed
hf auth whoami                    # must be signed in (trail upload target)
```

From a checkout, `uv run pre-harbor doctor` reports the same thing and names
what has to move to a Linux box.

You also need a provider endpoint (an OpenAI-compatible API) and its
credential exported in the shell environment, e.g.:

```bash
export OPENAI_API_KEY=...         # the credential
```

## Getting the exam revision

`--task-revision` must be the immutable 40-character Hugging Face commit SHA
of the task snapshot you want to benchmark — **not** a branch name, because
`main` moves and a trail that cites it no longer identifies the bytes its review
was written from.

Resolve the SHA behind the intended release instead of trusting a copied
version label or a stale document:

```bash
hf repos tag list Jack-Jieke-Wu/Paper-Reviewing-Exam --repo-type dataset
hf datasets info Jack-Jieke-Wu/Paper-Reviewing-Exam --revision main --format json
```

Maintainers publishing a new snapshot get the SHA from `pre-harbor publish`,
which prints `resolved immutable HF revision: ...`:

```bash
uv run pre-harbor publish --repo Jack-Jieke-Wu/Paper-Reviewing-Exam --execute
```

## Running one agent condition

```bash
# 1) Pick one immutable Exam revision and export the credential:
EXAM_SHA=<40-character-exam-sha>
export OPENAI_API_KEY=...

# 2) Run Harbor directly with your agent on the pinned snapshot:
harbor run \
  --repo https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam/tree/$EXAM_SHA/paper-review-exam \
  --agent <agent-id> \
  --model openai/gpt-5.6-sol \
  --jobs-dir jobs/<agent> \
  --job-name my-agent-run-1 \
  --n-concurrent 1 --n-concurrent-agents 1 \
  --no-delete --yes \
  --include-task-name compression_induced_folding_of_a_sheet \
  --include-task-name de_novo_nanobody_discovery \
  --include-task-name hydrodynamics_of_large_language_models \
  --include-task-name superconductivity_uniform_electron_gas \
  --include-task-name transport_in_one_channel_luttinger_liquid \
  --include-task-name trapping_centers_superfluid_mott_insulator \
  --artifact /workspace/material-manifest.json \
  --allow-agent-host arxiv.org \
  --allow-agent-host api.semanticscholar.org \
  --allow-environment-host arxiv.org \
  --allow-environment-host api.semanticscholar.org

# 3) Archive and upload one trail per trial:
uv run pre-harbor archive-trail jobs/<agent>/my-agent-run-1/<trial-dir> \
  --task-id <task-id> \
  --task-revision "$EXAM_SHA" \
  --trail-repo Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails \
  --execute
```

Without a checkout, replace `uv run pre-harbor` in step 3 with the single command
in [Archiving a trail without a checkout](#archiving-a-trail-without-a-checkout).

The example allowlist is the minimum for the scholarly hosts the exam suggests
(`arxiv.org`, `api.semanticscholar.org`, ...). Two rules from Harbor practice:

- The allowlist flags matter at **environment start**, not only during the
  agent phase: Harbor installs hosted agents at run time, so the install itself
  needs network and the provider host must be allowed. Add your provider host
  the same way if it is not already in the launch environment.
- `--network scholarly` in `pre-harbor verify` (or the equivalent manual
  allowlist) opens the general scholarly sources **plus** the Bohrium `bohr`
  CLI platform hosts and Google Scholar (`scholar.google.com`) — see the
  Network section of [`PAPER2HARBOR.md`](PAPER2HARBOR.md). Use
  `--network agent` when you want the agent to run without literature hosts.

The `--artifact` flags preserve evidence the agent produced: at minimum list
`/workspace/material-manifest.json`, which pins the exact task input bytes.
Harbor downloads each listed path into the trial dir only when listed; without
them the archived trail is missing that evidence. The submitted review files
are archived automatically from the Harbor 0.20 trial layout
(`artifacts/workspace/submission/review.md` and `review.json`), along with the preserved
lock/config, agent logs, and verifier output.

Three rules for this workflow:

- `--task-revision` must be the same immutable exam SHA used for the run; the
  trail manifest uses it to trace each review to the exact task bytes.
- `--execute` uploads to the public Trails dataset, publishing the review
  content — confirm you accept that exposure first.
- Uploading is per trial. Keep the SHA and jobs layout identical across
  compared runs.

## Archiving a trail without a checkout

`pre-harbor archive-trail` is the one contributor step that still lives in the
source repository, but it does not need a clone. It reads a Harbor trial
directory and shells out to the `hf` CLI, so `uvx` can fetch and run it directly:

```bash
uvx --from git+https://github.com/a-green-hand-jack/paper-review-bench@v0.3.0 \
  pre-harbor archive-trail jobs/<agent>/my-agent-run-1/<trial-dir> \
    --task-id <task-id> \
    --task-revision "$EXAM_SHA" \
    --trail-repo Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails \
    --execute
```

The `@v0.3.0` here is the **GitHub code** tag — the version of `pre-harbor`
doing the archiving. It is not the Exam tag: `--task-revision` still takes the
exam SHA from [Getting the exam revision](#getting-the-exam-revision), and the
two move independently.

Pin the `@<tag>` so the trail schema your run produces is identifiable later;
dropping it takes whatever the default branch happens to be. Use the newest tag
in `git ls-remote --tags https://github.com/a-green-hand-jack/paper-review-bench`;
trail archiving has produced schema `2` manifests since the code tag `v0.2.0`,
and records the archiver build itself since `v0.3.0`.
Drop `--execute` first to archive locally under `trails/` and read what would be
uploaded.

Two things to know before running it:

- The scrub runs **here, on your machine, before the upload** — host-local paths,
  secret-looking values, and non-evidence runtime state are removed as the trail
  is assembled. Do not hand-assemble a trail directory and upload it yourself.
- `--execute` publishes the review content to a public dataset. Confirm you
  accept that exposure first.

Needing `uvx` at all is a stopgap, not the design: the archiver is 399 lines of
standard library and belongs with the tasks it archives. Tracked in
[#21](https://github.com/a-green-hand-jack/paper-review-bench/issues/21).

## What gets archived in each trail

`archive_harbor_trial` writes `trail-manifest.json` (schema `3`) recording:

```text
task_id, task_revision (the exam SHA), source_record_id, run_id, archived_at,
source_layout, archiver, complete_review, complete_structured_review,
digest_scope, tree_sha256, files,
metadata (agent-provided fields, scrubbed)
```

`archiver` names the build that did the copying and scrubbing, which is a
different question from `schema_version` — that describes the manifest format,
not the code that wrote it:

```json
"archiver": {
  "name": "paper-review-harbor",
  "version": "0.3.0",
  "source": {
    "kind": "vcs",
    "commit": "ec0ebd3d0aa03aab396a78d25dc15ddb746e5c98",
    "requested_revision": "v0.3.0",
    "url": "https://github.com/a-green-hand-jack/paper-review-bench"
  }
}
```

`kind` is `vcs` when the archiver came from a pinned `uvx --from git+...` install
— the case the command above produces, and the only one that ties a trail to a
published commit. `local-checkout` (a maintainer's tree, with a `dirty` flag) and
`release` are also recorded, and `archive-trail` prints a warning on stderr for
anything that is not a pinned `vcs` install. A local checkout reports its commit
but never its path, which would name the contributor's machine.

Trails archived before `v0.3.0` have no `archiver` block; read a missing one as
unknown, not as an error.

The archived trail copies both review files, `config.json`/`lock.json`, the material
manifest, agent artifacts, agent logs, and verifier output — scrubbed of
host-local paths, secret-looking values, and non-evidence runtime state
(`xdg-data`/`xdg-state`, sqlite/git binaries, the opencode raw stdout tee). The
HF destination is `harbor-trails/<task-id>/<timestamp>/`.

## Failure handling

- Harbor must produce one trial record per task you selected; a mismatch means
  the run is incomplete.
- A failed trial still archives its manifest, log, and exception so the failure
  itself is reproducible; it does not stop the other tasks. Any failures are
  reported by the archiving command.

## Interpreting results

- Read each trial's `trail-manifest.json` and the archived verifier output for
  the per-task reward/exception.
- Reward `1.0` means a substantive `review.md` and schema-valid `review.json`
  were submitted. A templated review can still receive `1.0`; reward is a
  triage signal, not quality.
- `exception` non-empty means the trial did not complete normally; read the
  archived `exception.txt`/`trial.log` in the trail before judging the agent.

## Noise and fair comparison

A single run of six papers gives you one sample per agent condition.
Recommendation and reward can swing across identical runs because of sampling
variance — do not conclude an agent is better or worse from one run or from a
single review's recommendation label. For a defensible comparison:

- run the same condition more than once (`N > 1`) and compare distributions,
  not point estimates;
- keep `--agent`, `--model`, provider, variant, and the network mode identical
  across compared runs;
- record the exam revision SHA with every comparison because the task snapshot
  pins the exact bytes each review was written from.

## Related

- [`Paper-Reviewing-Exam`](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam) — the runnable task snapshot this benchmark executes.
- [`Paper-Reviewing-Exam-Trails`](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails) — where every run's trail lands.
- [`PAPER2HARBOR.md`](PAPER2HARBOR.md) — the full task pipeline (emit, verify, publish) and the network section.
- [`RELEASING.md`](RELEASING.md) — the gate every release passes: one task, one real agent, against the published snapshot.
