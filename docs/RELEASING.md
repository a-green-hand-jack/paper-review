# Releasing

A release of this benchmark is a claim that someone else can run it. Emitting a
task is not that claim, and neither is a passing test suite: both check the
pipeline that *builds* tasks, and every interesting failure so far has lived in
the path between a published snapshot and a container that runs it — LFS
pointers that never hydrated, allowlists that blocked an agent's own installer,
a trial layout that moved between Harbor versions.

So every release runs one real task, with a real agent, against the published
snapshot, before it is announced.

## The gate

**Before tagging a release or publishing a new `Paper-Reviewing-Exam` snapshot,
run one benchmark task end to end with `codex` on `gpt-5.6-terra` and confirm it
reaches reward `1.0`.**

One task is enough. This is a smoke test of the contract — task fetch, LFS
hydration, environment build, agent install, provider reachability, the
submission path, the verifier, and trail archiving — not a measurement of the
agent. Nothing here scores review quality; that remains the human experts' job.

## Running it

From a Docker-capable Linux host, with the provider credential exported from
your own credential store (never from a file committed to this repository):

```bash
EXAM_SHA=afc83f1c0e579852de9b2a075b259d7795cd09f0   # the snapshot under test
TASK=compression_induced_folding_of_a_sheet

harbor run \
  --repo "https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam/tree/$EXAM_SHA/paper-review-exam" \
  --agent codex --model openai/gpt-5.6-terra \
  --jobs-dir jobs/smoke --job-name "$VERSION-smoke" \
  --n-concurrent 1 --n-concurrent-agents 1 \
  --no-delete --yes \
  --include-task-name "$TASK" \
  --artifact /workspace/material-manifest.json \
  --agent-env 'OPENAI_API_KEY=${OPENAI_API_KEY}' \
  --agent-env 'OPENAI_BASE_URL=${OPENAI_BASE_URL}' \
  --allow-agent-host <each host> --allow-environment-host <each host>
```

The allowlist is the `agent` preset plus your provider host, applied at **both**
phases — Harbor installs hosted agents at run time, so the install itself needs
network. See the Network section of [`BENCHMARK.md`](BENCHMARK.md).

Then archive the trail (locally is enough for a smoke test — drop `--execute`,
since a gate run is not a benchmark result and does not belong in the public
Trails dataset):

```bash
uv run pre-harbor archive-trail jobs/smoke/<job>/<trial-dir> \
  --task-id "$TASK" --task-revision "$EXAM_SHA"
```

## What counts as a pass

- [ ] Harbor produces one trial record for the selected task.
- [ ] Reward is `1.0` — a substantive `review.md` was submitted.
- [ ] `exception` is empty.
- [ ] The archived trail contains `review.md`, the material manifest, and
      verifier output.
- [ ] The trail manifest's `archiver.source.kind` is what you expect for how you
      invoked it (`local-checkout` from a maintainer tree, `vcs` via `uvx`).

A failure blocks the release. Read the archived `trial.log` and `exception.txt`
before changing anything — the common causes are an allowlist that omits the
provider host, an exam SHA that predates a fix, and a Harbor version whose trial
layout moved.

## Recording the result

Post the outcome on the standing gate issue
([#23](https://github.com/a-green-hand-jack/paper-review-bench/issues/23)):
version under test, exam SHA, task, reward, Harbor and agent versions, and the
date. That issue stays open across releases; it is the log, not a task to close.

## Then release

1. Update `CHANGELOG.md`; keep `pyproject.toml` and `__version__` in step.
2. Tag and push (`git tag -a vN.N.N`), then `gh release create`.
3. If tasks changed, `pre-harbor publish --execute` and record the resolved
   immutable SHA — the smoke test must have run against that same snapshot.
4. Update the `@vN.N.N` pins in `docs/BENCHMARK.md` and the Trails dataset card.
