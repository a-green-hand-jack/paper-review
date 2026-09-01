# Benchmark

This benchmark is **agent-agnostic**: it owns the task contract, the publishable
task snapshot, and the trail archive, but it does not maintain or run any
specific paper-review agent. A paper-review agent supports this benchmark by
running inside Harbor and writing `/workspace/submission/review.md`; the agent
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
and write `review.md`; the verifier checks only that a substantive review was
submitted.

Harbor reward in the trail manifests confirms only the submission contract (a
`review.md` was written and is substantive). It is not a review-quality score
and never becomes one — deciding quality is the job of the human experts who
read the trails.

## Prerequisites

Run from a Docker-capable Linux checkout:

```bash
uv run pre-harbor doctor          # says whether this machine can run Harbor
harbor --version                  # Harbor 0.20.0
hf auth whoami                    # must be signed in (publish + upload target)
```

You also need a provider endpoint (an OpenAI-compatible API) and its
credential exported in the shell environment, e.g.:

```bash
export OPENAI_API_KEY=...         # the credential
```

## Getting the exam revision

`--task-revision` must be the immutable 40-character Hugging Face commit SHA
of the task snapshot you want to benchmark — not a branch name. Publish once,
then copy the SHA that `pre-harbor publish` prints (`resolved immutable HF
revision: ...`):

```bash
uv run pre-harbor publish --repo Jack-Jieke-Wu/Paper-Reviewing-Exam --execute
```

## Running one agent condition

```bash
# 1) Publish (or reuse) the exam snapshot and export the credential:
uv run pre-harbor publish --repo Jack-Jieke-Wu/Paper-Reviewing-Exam --execute
export OPENAI_API_KEY=...

# 2) Run Harbor directly with your agent on the pinned snapshot:
harbor run \
  --repo https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam/tree/<40-character-exam-sha>/paper-review-exam \
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
  --task-revision <40-character-exam-sha> \
  --trail-repo Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails \
  --execute
```

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
them the archived trail is missing that evidence. The submitted review itself
is archived automatically from the Harbor 0.20 trial layout
(`artifacts/workspace/submission/review.md`), along with the preserved
lock/config, agent logs, and verifier output.

Three rules for this workflow:

- `--task-revision` must be the same immutable exam SHA used for the run; the
  trail manifest uses it to trace each review to the exact task bytes.
- `--execute` uploads to the public Trails dataset, publishing the review
  content — confirm you accept that exposure first.
- Uploading is per trial. Keep the SHA and jobs layout identical across
  compared runs.

## What gets archived in each trail

`archive_harbor_trial` writes `trail-manifest.json` (schema `2`) recording:

```text
task_id, task_revision (the exam SHA), run_id, archived_at,
source_layout, complete_review, digest_scope, tree_sha256, files,
metadata (agent-provided fields, scrubbed)
```

The archived trail copies the review, `config.json`/`lock.json`, the material
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
- Reward `1.0` means a substantive `review.md` was submitted. A `1.0` with a
  three-line or templated review is still a `1.0` — reward is a triage signal,
  not quality.
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