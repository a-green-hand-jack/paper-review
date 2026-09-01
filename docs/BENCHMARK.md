# Benchmark

`pre-harbor benchmark` runs one **model condition** end to end and archives
everything: one provider/model/variant combination runs the same six
Issue #19 tasks under Harbor, and every completed trial is archived and
uploaded to the public trail dataset
[`Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails`](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails).

The six tasks are the current "six-task Issue #19" set:

```text
compression_induced_folding_of_a_sheet
de_novo_nanobody_discovery
hydrodynamics_of_large_language_models
superconductivity_uniform_electron_gas
transport_in_one_channel_luttinger_liquid
trapping_centers_superfluid_mott_insulator
```

## What one run produces

1. A Harbor job under `jobs/` (six trials, one per task).
2. An archived, scrubbed trail per trial under `trails/<model-name>/`, each
   with a `trail-manifest.json`.
3. A local report `trails/<model-name>/issue-19-<model-name>-report.md`.
4. Uploads (when `--execute`): every trail to
   `harbor-trails/<task-id>/<timestamp>/` and the report to
   `benchmark-reports/<exam_revision>/<timestamp>-<report>` in the Trails
   dataset.

Harbor reward in the report and manifests confirms only the submission
contract (a `review.md` was written and is substantive). It is not a
review-quality score and never becomes one — deciding quality is the job of
the human experts who read the trails.

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
export OPENAI_API_KEY=...         # the credential; see --credential-env below
```

## Getting the exam revision

`--exam-revision` must be the immutable 40-character Hugging Face commit SHA
of the task snapshot you want to benchmark — not a branch name. Publish once,
then copy the SHA that `pre-harbor publish` prints (`resolved immutable HF
revision: ...`):

```bash
uv run pre-harbor publish --repo Jack-Jieke-Wu/Paper-Reviewing-Exam --execute
```

## Running one model condition

```bash
uv run pre-harbor benchmark \
  --exam-revision <40-character-exam-sha> \
  --model openai/gpt-5.6-sol \
  --provider <provider-identity> \
  --credential-env OPENAI_API_KEY \
  --api-base-url https://<provider-host> \
  --api-host <provider-host> \
  --variant medium \
  --execute
```

Without `--execute` the command only prints the exact Harbor invocation and
uploads nothing — use that to sanity-check before spending model budget.

### Parameter contract (enforced by the CLI)

| Option | Rule |
|---|---|
| `--exam-revision` | exactly 40 lowercase hex chars; the immutable Exam commit SHA |
| `--model` | must start with `openai/`; the runner injects the provider endpoint into the Harbor environment instead of relying on container-local OpenCode configuration |
| `--api-base-url` | must be `https://` and its hostname must equal `--api-host`; must not contain credentials, query, or fragment |
| `--api-host` | provider hostname, also added to the Harbor host allowlist |
| `--credential-env` | name of an exported environment variable; when `--execute`, the variable must actually be set in the current shell, and its value is copied to `OPENAI_API_KEY` inside the Harbor environment. Only the **name** is recorded anywhere |
| `--provider` | human-readable provider identity recorded in every trail manifest |
| `--variant` | reasoning effort/variant to record (default `medium`) |
| `--trail-repo` | trail target, defaults to `Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails` |
| `--trail-revision` | HF branch/tag for the trail upload (default `main`) |

### What gets archived in each trail

`trail-manifest.json` (schema `2`) records:

```text
task_id, task_revision (the exam SHA), run_id, archived_at,
source_layout, complete_review, tree_sha256, files,
metadata: provider, model, variant, harbor_version, api_base_url,
          credential_env (name only), trial_id, reward, exception,
          network_mode, allowed_hosts
```

The archived trail copies the review, `config.json`/`lock.json`, material
manifest, OSP `.brain`, agent logs, and verifier output — scrubbed of
host-local paths and anything matching the secret regex. The HF destination
is `harbor-trails/<task-id>/<timestamp>/`.

### Failure handling

- `--execute` requires `harbor` and `hf` on PATH and the credential exported;
  otherwise the command fails before running (never a silent degraded run).
- Harbor must produce exactly one trial record per task; a mismatch fails the
  benchmark.
- A failed trial still archives its manifest, log, and exception so the
  failure itself is reproducible; it does not stop the other tasks. Any
  failures are reported in the final error.

## Interpreting results

- Read `trails/<model-name>/issue-19-<model-name>-report.md` for the per-task
  reward/exception table and trail paths.
- Reward `1.0` means a substantive `review.md` was submitted. A `1.0` with a
  three-line or templated review is still a `1.0` — reward is a triage signal,
  not quality.
- `exception` non-empty means the trial did not complete normally; read the
  archived `exception.txt`/`trial.log` in the trail before judging the model.

## Noise and fair comparison

A single run of six papers gives you one sample per model condition.
Recommendation and reward can swing across identical runs because of sampling
variance — do not conclude a model is better or worse from one run or from a
single review's recommendation label. For a defensible comparison:

- run the same condition more than once (`N > 1`) and compare distributions,
  not point estimates;
- keep `--provider`, `--model`, `--variant`, and the network mode (`scholarly`
  is always used here) identical across compared runs;
- record the `--exam-revision` SHA with every comparison because the task
  snapshot pins the exact bytes each review was written from.

## Related

- [`Paper-Reviewing-Exam`](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam) — the runnable task snapshot this benchmark executes.
- [`Paper-Reviewing-Exam-Trails`](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails) — where every run's trail lands.
- [`PAPER2HARBOR.md`](PAPER2HARBOR.md) — the full task pipeline (emit, verify, publish).