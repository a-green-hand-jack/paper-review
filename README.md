# paper-review-harbor

Turn papers into standard [Harbor](https://www.harborframework.com/docs/tasks)
tasks for **collecting** peer reviews: the manuscript is already written, a
review agent reads it and writes `review.md` plus `review.json`, and the pair is archived for
human experts to assess later.

The mainline pipeline is documented in [`docs/PAPER2HARBOR.md`](docs/PAPER2HARBOR.md);
the reproducible model-condition benchmark is documented in
[`docs/BENCHMARK.md`](docs/BENCHMARK.md).

## What it does

| Feature | Description |
|---|---|
| **Corpus discovery** | Any TeX source under `papers/<slug>/` (directory, `.tar.gz`, `.zip`, bare `.tex`) becomes a task automatically; no registration step |
| **Versioned tasks** | Each version (`v1/v2/v3`) of a paper is an independent task; explicit manuscript PDFs and toplevel TeX are auto-detected |
| **Staged builds** | `stage` unpacks and records withheld/sanitized lists; `show-map` validates the toplevel file and extracted title |
| **Leak protection** | `emit` audits immediately after rendering; `audit` re-checks tasks on disk; any task carrying writing-time defect trails (`solution-*/paper/review/`, `plan.md`) or a later revision is deleted and the command fails |
| **Harbor task generation** | Outputs `schema_version = "1.4"` tasks executable directly by `harbor run`, with `environment/` (TeX Live subset + agent toolchain), `solution/` (placeholder oracle), and an independent verifier that checks review shape but never review quality |
| **Structured reviews** | Requires a readable `review.md` and portable `review.json` findings, locations, evidence, confidence, recommendation, and scores; expert judgement remains outside the task runtime |
| **Source registry** | Gives every task a stable `source_record_id` shared with its raw-source record and archived review trails |
| **Network modes** | `none` / `agent` / `scholarly` presets; the host allowlist applies to both the environment and agent phases |
| **Verification** | `verify <label> --agent oracle` must score 1.0, `--agent nop` must score 0.0; without Docker on this machine it prints the exact Linux-box command instead of degrading into a weaker check |
| **Agent-agnostic benchmark** | The benchmark owns the task contract, not any specific review agent: run any Harbor agent (`harbor run --repo … --agent <id>`), archive each trial with `pre-harbor archive-trail` (see [`docs/BENCHMARK.md`](docs/BENCHMARK.md)) |
| **Hugging Face publishing** | `publish` uploads to `Jack-Jieke-Wu/Paper-Reviewing-Exam`, re-audits before publishing, defaults to dry-run; `harbor run --repo` runs the published snapshot directly |
| **Reproducible benchmark** | The six-task Issue #19 set is the canonical benchmark set; run it with any Harbor agent (`harbor run --repo … --agent <id>`) and archive every trail with `pre-harbor archive-trail` (see [`docs/BENCHMARK.md`](docs/BENCHMARK.md)) |
| **opencode commands** | `/paper2task <label>` (stage → inspect → emit → audit) and `/verify-task <label>` (oracle + floor) |
| **Fast smoke task** | `hello_world_review` is a short synthetic manuscript that exercises the normal emitted Harbor task and submission path; it is excluded from the six-task benchmark and real-task release gate |
| **Corpus size** | Currently **28 papers, 32 reviewable versions** |

## Quick start

```bash
uv run pre-harbor doctor          # what this machine can do, what must go to a Linux box
uv run pre-harbor list            # every version and its spec status
uv run pre-harbor emit            # render all tasks; each is audited, leaks are deleted
uv run pre-harbor verify <label> --agent oracle    # run on a Linux box; must score 1.0
```

## CLI overview

```
pre-harbor list                 every version and its metadata status
pre-harbor doctor               what this machine can and cannot do
pre-harbor init-spec <label>    write a starter spec (optional overrides)
pre-harbor build-source-archive build the restricted raw-source archive
pre-harbor publish-source-archive publish that archive privately; dry run by default
pre-harbor retire-runtime-sources remove legacy papers/** after a pinned archive release
pre-harbor stage [labels...]    unpack publishable material, write paper_map.json
pre-harbor show-map <label>     print a staged paper's structure
pre-harbor emit [labels...]     render tasks; audits each, deletes on leak
pre-harbor audit                re-audit tasks on disk
pre-harbor verify <label>       harbor run, or the command for a box with Docker
pre-harbor publish --repo O/N   push to Hugging Face; dry run without --execute
pre-harbor archive-trail        archive one Harbor run and optionally upload its trail
pre-harbor validate-assessment  validate a private human-expert label schema
```

## Documentation

- [`docs/PAPER2HARBOR.md`](docs/PAPER2HARBOR.md) — main pipeline doc: add a paper, build, prove, collect, publish, network details, privacy boundary, task layout, reward
- [`docs/BENCHMARK.md`](docs/BENCHMARK.md) — how to run the reproducible benchmark with any Harbor agent, without a checkout of this repository: prerequisites, the pinned exam revision, commands, outputs, result interpretation
- [`docs/RELEASING.md`](docs/RELEASING.md) — the release gate: every release runs one task end to end with a real agent before it is announced
- [`docs/DATASETS.md`](docs/DATASETS.md) — roles and provenance links across Exam, Trails, Source Archive, and the expert-assessment layer
- `CHANGELOG.md` — release history

## Repositories and datasets

The GitHub repository and three data assets carry different roles; the artifacts
do not replace each other:

| Location | Role | Contents | Access |
|---|---|---|---|
| `a-green-hand-jack/paper-review-bench` (GitHub) | build and release code | pipeline, specs, controlled corpus checkout, and maintainer docs | public |
| `Jack-Jieke-Wu/Paper-Reviewing-Exam` (Hugging Face dataset) | runnable task snapshot | sanitized `paper-review-exam/<task-id>/` tasks, runnable directly by `harbor run --repo` | public |
| `Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails` (Hugging Face dataset) | review-run trail archive | submitted `review.md` and `review.json`, scrubbed trajectory evidence, manifests, and verifier output | public only after contributor approval |
| `PaperBench-Source-Archive` (Hugging Face dataset) | source registration and rebuild record shared with Paper Writing Benchmark | raw collection inputs, source registry, licenses, workflow provenance, and task links | restricted |

1. **Source Archive → tasks (Exam)**: every source record supplies an immutable
   `source_record_id`; `pre-harbor emit` builds a sanitized Harbor task from it.
   `pre-harbor publish` uploads only the runnable task tree, not raw materials.
2. **Run → trail (Trails)**: `pre-harbor archive-trail --trail-repo
   Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails --execute` archives each review
   run's trail. Each new trail retains the task revision and `source_record_id`.
3. **Expert assessment**: controlled human labels reference a trail id, task
   revision, source record id, and rubric version. They never become task inputs
   or Harbor rewards.
4. **Version correspondence**: GitHub, Exam, Trails, and Source Archive release
   independently. A matching `vN.N.N` is coincidence, not evidence of identical
   provenance. See [`docs/DATASETS.md`](docs/DATASETS.md) before comparing runs.
