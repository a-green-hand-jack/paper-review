---
description: Turn a paper version into a Harbor task. Stage, inspect, emit, audit, and report what to run on the box.
---

Turn this paper version into a Harbor task: **$ARGUMENTS**

If nothing was named, run `pre-harbor list` and ask which version to work on.

## What this produces

A Harbor task under `tasks/paper-review-exam/<label>/` that `harbor run` can
execute directly. The task gives a review agent the manuscript and asks it to
write `review.md`; the verifier checks only that a review was submitted.
There is no rubric, no scoring, and no LLM judge — review quality will be
assessed later by human experts.

## Steps

### 1. Stage the source

```
pre-harbor stage <label>
```

Read back the `excluded=` and `sanitised=` lists. They say what was withheld
from the agent environment; if they are empty for a `solution-*` paper, the
writing-time trail leaked and something is wrong.

The staged manuscript is at `build/<label>/paper/` and its map at
`build/<label>/paper_map.json`.

### 2. Inspect the paper map

```
pre-harbor show-map <label>
```

Check that `main_tex` is right and the title was extracted. If the paper is
modular (multiple tex files), glance at the graph to make sure nothing is
missing. This is the last chance to catch a structural problem cheaply.

If a `specs/<label>.yaml` exists and sets a title, venue, or domain, those
override whatever ingest derived. If no spec exists, defaults are used and the
task still works — specs are optional overrides, never requirements.

### 3. Emit and audit

```
pre-harbor emit <label>
```

This renders the task and immediately audits it for leaks. A leak deletes the
task and fails the command — if that happens, report the violations verbatim
and stop. Do not work around an audit failure.

Then confirm independently:

```
pre-harbor audit
```

### 4. Report

Tell the operator:

- the task directory
- paper title, sections, citations
- whether the audit is clean
- that **emitting is not verifying**: no image was built, no agent ran, nothing
  is proven until `harbor run -a oracle` scores 1.0 and `-a nop` scores 0.0
- the exact commands for the Linux box:

```
pre-harbor verify <label> --agent oracle
pre-harbor verify <label> --agent nop
```

- and how to run with literature access when collecting real reviews:

```
harbor run -p tasks/paper-review-exam/<label> -a opencode \
  --allow-agent-host arxiv.org \
  --allow-agent-host api.semanticscholar.org \
  --allow-agent-host api.openalex.org
```
