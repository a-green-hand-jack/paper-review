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
hosts, and a SHA-256 tree digest of the trail itself. Since archiver `v0.3.0` it
also records an `archiver` block naming the build that did the copying and
scrubbing; trails archived before that have no such block.

A legacy `osp-trails/` tree predates the Harbor pipeline and is retained for
older runs; new runs upload under `harbor-trails/`.

## Producing trails

Producing a trail needs no checkout of the
[`paper-review-bench`](https://github.com/a-green-hand-jack/paper-review-bench)
repository. Run the six benchmark tasks with any Harbor agent against a pinned
`Paper-Reviewing-Exam` revision, then archive each trial:

```bash
harbor run \
  --repo https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam/tree/<40-character-exam-sha>/paper-review-exam \
  --agent <agent-id> --model openai/gpt-5.6-sol \
  --jobs-dir jobs/<agent> --job-name my-agent-run-1 \
  --no-delete --yes \
  --artifact /workspace/material-manifest.json \
  --include-task-name <task>            # once per benchmark task

uvx --from git+https://github.com/a-green-hand-jack/paper-review-bench@v0.3.0 \
  pre-harbor archive-trail jobs/<agent>/my-agent-run-1/<trial-dir> \
    --task-id <task-id> \
    --task-revision <40-character-exam-sha> \
    --trail-repo Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails \
    --execute
```

The `@v0.3.0` on the `uvx` line is the GitHub **code** tag (the `pre-harbor`
version doing the archiving); `--task-revision` takes the **Exam dataset** SHA
the run executed against. The two are unrelated despite the shared numbering.

The archiver scrubs host-local paths, secret-looking values, and non-evidence
runtime state locally, before anything is uploaded. Do not hand-assemble a trail
directory and upload it yourself.

See `docs/BENCHMARK.md` in the GitHub repository for the full contract:
prerequisites, parameter validation, failure handling, result interpretation,
and noise-aware comparison.

## Related

- [`Paper-Reviewing-Exam`](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam) — the runnable task snapshot these trails execute.
- [`paper-review-bench`](https://github.com/a-green-hand-jack/paper-review-bench) — the source repository (code, corpus, docs).