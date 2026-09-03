# Dataset Topology

Paper Reviewing Benchmark uses three distinct Hugging Face data assets. Their
names, revisions, and release tags are independent; a matching version number
does not prove that two assets describe the same bytes.

| Asset | Purpose | Contains | Access |
|---|---|---|---|
| `Paper-Reviewing-Exam` | Harbor runtime distribution | sanitized, runnable task snapshots | public |
| `Paper-Reviewing-Exam-Trails` | run evidence | submitted reviews, structured reviews, scrubbed trajectories and verifier output | public only after contributor approval |
| `PaperBench-Source-Archive` | collection and rebuild record shared with Paper Writing Benchmark | original collection inputs, source registry, licenses, workflow provenance, and source-to-task links | restricted |

The Source Archive is not a Harbor task dataset. It can include materials that
must never reach a review agent, so it must remain private or otherwise
access-controlled. It is the durable bridge between the reviewing and writing
benchmarks: a source record can list the review task and every related writing
task without merging their runnable task trees.

## Stable links

Every emitted review task receives a `source_record_id`, derived from its task
id and immutable source SHA-256. The same id appears in the Exam manifest,
the task material manifest, a newly archived trail, and the Source Archive
record. A source record additionally records source URL, DOI/arXiv id, license,
collection/build workflow revisions, and related writing task ids.

This makes the provenance chain explicit:

```text
restricted original source -> source_record_id -> sanitized Exam task
                                            -> review trail -> private expert assessment
```

Human expert assessments are a fourth *evaluation layer*, not a runtime task
asset. They refer to a trail id, task revision, source record id, and rubric
version, and stay access-controlled. `pre-harbor validate-assessment` checks
their metadata schema only; it never uses an LLM as a quality judge.

## Maintainer workflow

1. Register a paper's source identifiers and license in `specs/<task-id>.yaml`.
2. Build the restricted archive with `pre-harbor build-source-archive`; inspect
   `source-records.jsonl` before its separate private upload. Once its immutable
   revision is recorded, use the explicit dry-run `retire-runtime-sources`
   command to remove any legacy raw `papers/` tree from the public Exam asset.
3. Emit and audit sanitized Harbor tasks, then publish only the
   `paper-review-exam/` snapshot to Exam.
4. Run a pinned Exam revision, archive every trial to Trails, and retain the
   immutable revision and `source_record_id`.
5. Have experts assess trails against a versioned rubric in the controlled
   assessment layer.

Dataset cards explain how to run or contribute to their respective asset.
This GitHub repository documents how the pipeline builds, audits, releases, and
links those assets.
