---
description: Draft a Harbor review task from a paper — stage the source, map it, propose candidate defects, and write a draft rubric for a human to sign off.
agent: build
---

Draft a Harbor review task for: **$ARGUMENTS**

If nothing was named, run `pre-harbor list` and ask which version to work on
rather than guessing.

## What this produces, and what it does not

This ends with `rubrics/<label>.yaml` at `status: draft`. That is not a task
and not ground truth. A person reads the draft, fixes it, and signs it off with
`/annotate`; only then does `pre-harbor emit` produce anything.

Do not run `pre-harbor emit` in this command. It would fail on a draft, which
is the intended behaviour, and running it anyway just produces a confusing
error at the end of an otherwise successful drafting session.

## Steps

### 1. Stage the source

```
pre-harbor stage <label>
```

Read the reported `excluded=` and `sanitised=` lists back to the operator. They
say what was withheld from the agent environment; if they are empty for a
`solution-*` paper, something is wrong — those all ship a `review/` trail.

The staged manuscript is at `build/<label>/paper/` and its structure map at
`build/<label>/paper_map.json`.

### 2. Map the paper

Launch **@paper-cartographer** on `build/<label>/paper/` and its
`paper_map.json`. Ask for the claims ledger.

Do not summarise or second-guess its output. Pass it to the next step intact.

### 3. Gather the evidence the scout should see

This is the step that decides whether the draft is any good.

**If the paper has later versions** (`erdos973--v1`, `chapoton_q_zeta_numerators--v1`,
`lieb_schultz_mattis_charge_transport--v1`), stage the next version too and diff
them:

```
pre-harbor stage <slug>--v<N+1>
diff -u build/<label>/paper/main.tex build/<slug>--v<N+1>/paper/main.tex
```

What the authors changed is what was wrong. This is the strongest evidence in
the corpus — for `erdos973--v1` the v2 diff shows the title being rewritten to
stop claiming priority over Luo-Yang-Zhu.

**If the paper is a `solution-*` manuscript**, read its writing-time trail
directly from the corpus (not from `build/`, which has it stripped):

```
papers/<slug>/paper/review/internal_review.md
papers/<slug>/paper/review/gates.md
papers/<slug>/paper/review/cite_audit.md
papers/<slug>/paper/plan.md          # only some have this
```

These record defects found *during writing*. Most were fixed. Check each
against the current manuscript before believing it.

**If the operator gave a note or a file path**, include it verbatim.

### 4. Propose candidates

Launch **@defect-scout** with: the staged manuscript path, the cartographer's
ledger, and everything from step 3, each labelled with which kind of evidence it
is.

### 5. Write the draft

Launch **@rubric-editor** with the scout's YAML and the paper's slug, version,
venue and domain. It writes `rubrics/<label>.yaml` and runs `pre-harbor check`.

### 6. Report

Tell the operator:

- the rubric path, and that it is a **draft**
- findings count, gating count, and the offline/online split
- for each finding: id, title, severity, gating, and the scout's confidence
- **which findings you would question first** — the low-confidence ones, the
  ones resting only on your own reading, and any where `accept_if` is still
  vague
- the exact next command: `/annotate <label>`

Do not tell the operator the draft "looks good". You proposed it; you are not
the one who gets to approve it.
