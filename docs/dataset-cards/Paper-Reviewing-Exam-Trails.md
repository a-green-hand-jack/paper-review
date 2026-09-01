---
license: mit
task_categories:
- text-generation
tags:
- peer-review
- scientific-review
- harbor
- agent-evaluation
---

# Paper-Reviewing-Exam-Trails

Review-run trail archive for the
[`Paper-Reviewing-Exam`](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam)
benchmark. Each trail captures one agent review run: the submitted `review.md`,
the agent's `brain/`, manifests, logs, and verifier output, so a human expert
can assess the review against the exact materials it was written from.

**Trails contain review content and are public.** Review text can be read from
this dataset; uploading a trail publishes it. Confirm you accept that exposure
before running with an upload flag.

## Why reviews are collected here

The benchmark does not grade reviews. Harbor reward records only that a
substantive `review.md` was submitted. Deciding whether a review is good is the
job of human experts, and this dataset is the durable record they read.

## Layout

```text
harbor-trails/<task-id>/<timestamp>/
    review.md
    trail-manifest.json
    config.json
    lock.json
    material-manifest.json
    brain/                  agent working state (.brain)
    agent/                  agent logs and session records
    verifier/               verifier output (reward.json, submission-report.json)
```

`trail-manifest.json` (schema `2`) records the task id, the exact
`Paper-Reviewing-Exam` revision the run was executed against, the provider /
model / variant, Harbor version, reward, exception, network mode, allowed
hosts, and a SHA-256 tree digest of the trail itself.

Consult `benchmark-reports/<exam-revision>/` for the per-run report tables
produced by `pre-harbor benchmark`.

A legacy `osp-trails/` tree predates the Harbor pipeline and is retained for
older runs; new runs upload under `harbor-trails/`.

## Producing trails

Run the reproducible benchmark from the
[`paper-review-bench`](https://github.com/a-green-hand-jack/paper-review-bench)
GitHub repository:

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

See `docs/BENCHMARK.md` in the GitHub repository for the full contract:
prerequisites, parameter validation, failure handling, result interpretation,
and noise-aware comparison.

## Related

- [`Paper-Reviewing-Exam`](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam) — the runnable task snapshot these trails execute.
- [`paper-review-bench`](https://github.com/a-green-hand-jack/paper-review-bench) — the source repository (code, corpus, docs).