# paper2harbor

Turn a paper into a standard [Harbor](https://www.harborframework.com/docs/tasks)
task for evaluating **paper review agents**: the manuscript is already written,
and the agent under test has to review it.

- **Input** — a paper's TeX source (directory, `.tar.gz`, `.zip`, or a bare
  `main.tex`) plus an optional note.
- **Output** — a Harbor task (`schema_version = "1.4"`) that `harbor run`
  executes directly.
- **Ground truth** — a human-authored defect list. The workflow drafts
  candidates; a person signs them off. Nothing unsigned becomes a task.

This replaces the ad-hoc baseline harness in `tools/` (see
[`OSP_BATCH.md`](OSP_BATCH.md)), which ran Open ScholarPeer once per paper and
left the comparison to human auditors.

## The corpus

17 papers, 21 independently reviewable versions, in four directory shapes:

| shape | example |
|---|---|
| `<slug>/vN-source.tar.gz` + `vN.pdf` | `erdos973` (v1/v2/v3) |
| `<slug>/source.{tar.gz,zip}` + `<slug>.pdf` | `residual_bounds_for_schur_stable_polynomials` |
| `<slug>/main.tex` + `<slug>.pdf` | `on_the_first_and_the_second_borel_cantelli_lemmas` |
| `<slug>/paper/main.tex` + `review/` + … | `solution-p8610` |

Each version ships as two tasks, `offline` and `online`, so 42 tasks in total.

## Two protocols

The same paper, the same rubric, two network policies.

|  | `offline` | `online` |
|---|---|---|
| `[environment] network_mode` | `no-network` | `allowlist` (arXiv, Semantic Scholar, OpenAlex, Crossref, DOI) |
| what it measures | reading a manuscript | reading a manuscript *and* checking it against the literature |

A finding declares which protocols it counts in. "This bound was already
improved elsewhere" is not a fair thing to score in a container with no
network, so it is marked `protocols: [online]` and the offline task never sees
it.

The online policy exists partly as a correction. `tools/osp_batch.py` shipped
`.mcp.json`, which is Claude Code's format and which opencode ignores, so every
review in the previous baseline ran with no retrieval at all — the trails
recorded it themselves. Declaring hosts in `task.toml` makes that a property of
the task rather than of whoever configured the harness.

## Scoring

The verifier runs in its own container (`environment_mode = "separate"`), so
the rubric never shares a filesystem with the agent under test.

1. **Deterministic gate.** `review.md` must exist and be substantive.
2. **Bounded judgement.** For each annotated finding, an LLM judge decides
   `found` / `partial` / `missed` against that finding's `accept_if` and
   `reject_if`, and must quote the passage it relied on. A verdict it cannot
   quote support for is downgraded — this is the guard against a judge
   agreeing with a review that never said the thing.
3. **Voting.** Each finding is judged an odd number of times and the majority
   wins. `STATUS_REPORT.md` recorded whole-grade recommendation swings between
   identical runs that three independent auditors put down to sampling noise;
   a single call inherits it.

`reward` is **gating recall**: the fraction of `gating` findings the review
reported, with half credit for `partial`. Everything else —
`finding_recall`, `recall_high/medium/low`, `distractor_rate`,
`strict_gating_recall` — lands in `reward.json` but does not set the score.
Per-finding verdicts, votes and evidence go to
`/logs/verifier/evaluation.json` for human inspection.

Measured on `erdos973--v1`, offline: the oracle scores `1.0` with
`distractor_rate 0.0`; a review that raises eight plausible generic objections
scores `0.0` with `distractor_rate 1.0`.

The oracle earns its keep twice over. Its reference review states each finding
in the rubric's description of the *defect*, deliberately not in the words of
that finding's `accept_if`. So a 1.0 shows both that the plumbing works and
that every `accept_if` is satisfiable by prose reporting the defect rather than
prose reciting the criterion. A finding the oracle misses is a rubric bug.

## What is private

The corpus contains four distinct ways to hand an agent its own answers, and
`pre-harbor audit` checks for all of them by reading what was written to disk
rather than trusting the code that wrote it:

| private | why |
|---|---|
| `solution-*/paper/review/` | the writing-time internal review; it names the defects |
| `solution-*/paper/plan.md` | the writing plan |
| a later version of the paper | v2 is a worked answer key for v1 |
| the rubric, and the reference review rendered from it | the answers themselves |

`unverified.bib` is deliberately **not** private. Every manuscript that ships
one builds against it (`\bibliography{references,unverified}`), so withholding
it breaks compilation and manufactures undefined-citation defects the authors
never committed. Its writing-pipeline header comment — which says the entries
"need checking before submission" — is stripped during staging, because that
comment hands over a citation finding for free. The entries stay, blank fields
included: those are the manuscript's genuine state and a reviewer is entitled
to catch them.

## Task layout

```
tasks/review-exam-offline/erdos973--v1/
├── task.toml
├── instruction.md
├── environment/
│   ├── Dockerfile          # TeX Live subset + poppler-utils
│   └── paper/              # manuscript only
├── solution/
│   ├── solve.sh            # oracle
│   └── private/reference_review.md
└── tests/
    ├── Dockerfile          # verifier image; owns /tests
    ├── test.sh
    ├── grader_review.py
    └── private/
        ├── rubric.json
        └── reference_review.md
```

## The rubric

`rubrics/<label>.yaml` is the only ground truth in the benchmark. See
[`rubrics/erdos973--v1.yaml`](../rubrics/erdos973--v1.yaml) for a worked draft.

```yaml
findings:
  - id: F1
    severity: blocking          # blocking | major | minor
    gating: true                # missing this means the review failed
    detectability: medium       # high | medium | low
    protocols: [offline, online]
    location: "main.tex:212-215"
    claim: <what the manuscript does>
    defect: <what is wrong with it>
    accept_if: <what a review must convey to count as reporting it>
    reject_if: <the near-miss that must not count>
distractors:
  - id: D1                      # not a defect; measures precision
```

`accept_if` and `reject_if` carry the benchmark. A judge asked "did this review
find the defect?" answers differently each time; asked "does the review convey
*this*, and not merely *that*?" it decides a bounded question. Write them as
substance a review must convey, never as words it must use.

`gating` means a review that misses this has failed. Most findings are not
gating, and a rubric where more than about a third are has misunderstood the
field. Each protocol needs at least one, or its reward is a 0/0 —
`pre-harbor check` refuses the rubric otherwise.

## Workflow

Authored as opencode commands in `.opencode/`, with the deterministic work in a
tested Python CLI.

```
/paper2task <label>     stage → map → propose candidates → write a DRAFT rubric
/annotate <label>       walk a person through sign-off, then emit and audit
/verify-task <label>    oracle and floor runs, on a machine with Docker
```

The three subagents (`paper-cartographer`, `defect-scout`, `rubric-editor`) are
read-only except for `rubrics/`, and `rubric-editor` is forbidden from writing
`status: annotated`. That field is a person's signature.

## CLI

```
pre-harbor list                 every version and its annotation status
pre-harbor doctor               what this machine can and cannot do
pre-harbor stage <label>        unpack publishable material, write paper_map.json
pre-harbor check <label>        what stands between a rubric and a task
pre-harbor emit <label>         render both protocols; audits and deletes on leak
pre-harbor audit                re-audit tasks on disk
pre-harbor verify <label>       harbor run, or the command for a box with Docker
```

## Laptop and Linux box

Staging, drafting, emitting and auditing run anywhere. Building images and
running `harbor run` need Docker, and `pre-harbor doctor` says whether this
machine has it. Commands that need it and cannot find it print the exact
invocation for the Linux box and exit non-zero — they never substitute a weaker
check, and emitting a task is never reported as verifying it.

A task is proven when, in both protocols, the oracle scores close to `1.0` and
an empty submission scores `0.0`. Until both hold, it is unproven.

```bash
pre-harbor verify erdos973--v1 --protocol offline --agent oracle
```

The judge needs `JUDGE_API_KEY` and `JUDGE_MODEL` in the verifier environment.
Pass them to `harbor run`; never bake them into an image.
