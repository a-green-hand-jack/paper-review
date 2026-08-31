---
description: Verify emitted Harbor tasks on a machine with Docker — oracle scores 1.0, nop scores 0.0. Report only facts.
---

Verify the emitted task(s) for: **$ARGUMENTS**

If nothing was named, verify every task under `tasks/`.

## First: can this machine do it?

```
pre-harbor doctor
```

If `docker` or `harbor` is missing, **stop**. Do not substitute a weaker check
and do not describe the task as verified. Print the commands the operator
should run on the Linux box and say explicitly that nothing was verified here.

## What verification means

A task is proven when **both** hold:

| run | expected |
|---|---|
| `-a oracle` | reward 1.0 (the placeholder review satisfies the contract) |
| `-a nop` | reward 0.0 (nothing was submitted) |

That is all "verified" means here. The oracle writes a placeholder, not a real
review, so an oracle run says nothing about review quality — it proves the
submission path and the checker are wired up.

## Steps

### 1. Oracle and floor

```
pre-harbor verify <label> --agent oracle
pre-harbor verify <label> --agent nop
```

If both behave, one real run to collect data with:

```
harbor run -p tasks/paper-review-exam/<label> -a opencode \
  --allow-agent-host arxiv.org \
  --allow-agent-host api.semanticscholar.org \
  --allow-agent-host api.openalex.org
```

No judge credentials are needed — the verifier only checks the submission.

### 2. Confirm the review is real

Look in the job's `logs/` for `/workspace/submission/review.md`. Check it is
non-empty and mentions the actual paper. Read `reward.json`: the
`mentions_location` statistic is a heuristic signal that the review points at
the manuscript rather than being a generic summary. If the review looks
templated, say so — that is exactly what the human experts would find later,
and cheaper to catch now.

### 3. Report

For each task: oracle reward, nop reward, and (if collected) the review's word
count and what it says. Report facts, not summaries of what you expected.
