---
description: Walk a human through signing off a draft rubric, one finding at a time, then emit and audit the Harbor tasks.
agent: build
---

Sign off the rubric for: **$ARGUMENTS**

If nothing was named, run `pre-harbor check` and offer the drafts that exist.

## Your role here

You are the annotator's instrument, not the annotator. Every accept, rewrite
and deletion is **their** decision. You may say what you think when asked, and
you must not pre-empt a decision by describing a finding as obviously right.

The signature at the end is a claim that a person checked these. Do not write
it on their behalf under any circumstance, including being told to.

## Steps

### 1. Show the state

```
pre-harbor check <label>
```

Report every problem it lists. Open `rubrics/<label>.yaml` and show the
operator the paper, the finding count, and the gating split per protocol.

### 2. Go through the findings one at a time

For each finding, show:

- id, title, severity, gating, detectability, protocols
- `location`, and **the actual manuscript text at that location** — read it out
  of `build/<label>/paper/` so the annotator is judging the paper, not my
  description of it
- `claim`, `defect`
- `accept_if` and `reject_if` in full
- the `provenance` entry it came from, if any

Then ask for one of: **keep**, **edit**, **drop**.

The two questions worth pressing on, because they are where drafts are weakest:

- *Is `accept_if` decidable?* Read it as if you were the judge with only the
  review in front of you. If two reasonable people could disagree about whether
  a given review satisfies it, it needs rewriting.
- *Is `gating` right?* Gating means a review that misses this has failed. If
  the annotator is unsure, it is not gating.

Apply each decision to the YAML as you go. Do not batch them up.

### 3. Distractors

Ask whether there is anything a review of this paper is likely to flag that is
*not* a defect. These are what `distractor_rate` measures, and a rubric with
none cannot distinguish a careful review from one that objects to everything.

### 4. Check before signing

```
pre-harbor check <label>
```

Every problem must be gone except the `status is 'draft'` line. If a stub
`accept_if` is still flagged, go back to it.

### 5. Take the signature

Ask the annotator, explicitly:

> Do you sign off this rubric as the ground truth for `<label>`? Under what
> name?

Only on a clear yes, set in the YAML:

```yaml
status: annotated
annotator: <the name they gave>
annotated_at: <today, YYYY-MM-DD>
```

Anything other than a clear yes: leave it a draft and say so.

### 6. Emit and audit

```
pre-harbor emit <label>
```

This renders both protocols and audits each one. A leak deletes the task and
fails the command — if that happens, report the violations verbatim and stop.
Do not work around an audit failure.

Then confirm independently:

```
pre-harbor audit
```

### 7. Report what is still unverified

Say plainly that emitting is not verifying. No image has been built and no
agent has run. Give the operator the command for the Linux box:

```
pre-harbor verify <label> --protocol offline --agent oracle
pre-harbor verify <label> --protocol online  --agent oracle
```

The oracle must score close to 1.0. An empty submission must score close to
0.0. Until both hold, the task is unproven.
