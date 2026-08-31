---
description: Verify emitted Harbor tasks on a machine with Docker — oracle must score ~1.0, an empty submission ~0.0.
agent: build
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

A task is proven when two things hold, in both protocols:

| run | expected |
|---|---|
| `-a oracle` | reward close to 1.0 |
| empty submission | reward 0.0, `judged` 0.0 |

The oracle writes the reference review, which states every finding in the
rubric's own description of the defect — deliberately *not* in the words of
that finding's `accept_if`. So an oracle score near 1.0 proves two things: the
plumbing works, and each `accept_if` is satisfiable by prose that reports the
defect rather than prose that recites the criterion.

A finding the oracle misses is a **rubric** bug, never an agent one. Causes,
in the order worth checking:

- an `accept_if` so narrowly worded that only its own phrasing satisfies it
- `JUDGE_API_KEY` not reaching the verifier, which shows as `grader_error: 1.0`
- a finding whose `protocols` exclude the protocol being run, so it is scored
  as missed when it was never in scope

## Steps

### 1. Oracle, both protocols

```
pre-harbor verify <label> --protocol offline --agent oracle
pre-harbor verify <label> --protocol online  --agent oracle
```

The judge needs credentials in the verifier environment. They come from
`/Users/jieke/orca/projects/paperbench-harbor/.env` — `JUDGE_API_KEY` and
`JUDGE_MODEL`. Pass them to `harbor run` rather than baking them into any
image, and never echo their values.

### 2. The floor

Run the same task with an agent that submits nothing, and confirm reward 0.0.
A task that scores above zero on an empty submission is measuring nothing.

### 3. Read the per-finding record

`/logs/verifier/evaluation.json` holds every verdict, the votes behind it, and
the passage the judge quoted. Read it even when the reward looks right.

Look for: a finding marked `found` on an evidence quote that does not actually
support it, and split votes (`["found","missed","found"]`) — those mark an
`accept_if` that is not yet decidable, and they are where the score turns into
noise.

### 4. Report

For each task and protocol: reward, gating recall, and whether the floor
behaved. Then list every finding whose votes were split, as work to be done on
the rubric.

Do not report a task as ready on an oracle run alone. Both ends have to hold.
