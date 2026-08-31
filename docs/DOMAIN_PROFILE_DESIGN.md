# Domain Profile System — Design

Status: implemented in `open-scholar-peer` @ `c31b086`, unvalidated outside mathematics.
Supersedes the three-way `review_mode` switch from `d8780e0`.

## Method

Three independent research lines were run before any code was written:
open-source LLM peer-review projects (source-level, not README-level); the
actual reviewer guidelines and reporting standards of mathematics, physics,
biology, chemistry, medicine, and CS venues; and the 2024–2026 literature on
LLM peer review. Findings were cross-checked against the existing OSP codebase
and against `DOMAIN_ADAPTIVE_AUDIT.md`, the independent audit of the previous
round.

## Output

### The problem with the previous fix

`d8780e0` added a three-way `paper.review_mode` flag (`theoretical` /
`empirical` / `other`) and branched **wording** on it: guideline phrasing,
section headings, reviewer vocabulary. The independent audit found it improved
9 of 18 papers but introduced a regression that stayed open.

The regression's mechanism is the whole reason this redesign exists. The
Summary phase swapped its `Evidence (E)` section for a `Formal Content` section
and declared the two "mutually exclusive, not merged". A paper proving a result
and validating it numerically was classified `theoretical` — so the empirical
section disappeared, and **3 of its 5 reported headline numbers went with it**,
because the theoretical variant had no field in which a number could live.
Every later phase then worked from a summary that had silently dropped them.

> Rewording a section cannot preserve a value that no field captures.
> Fields, not headings, are what carry information forward.

The previous round changed how phases *talked* about a paper without changing
what they *extracted* from it. That is the defect this design corrects.

### Two orthogonal axes

| Layer | Decides | Source |
|---|---|---|
| **Venue** | which criteria exist, the rubric, the output format, which criteria gate the decision | `00_review_guidelines.md` |
| **Domain** | what counts as evidence, what "nearest prior work" means, which verifiability checks apply, what must never be asked | `defaults/domains/<field>.md` |

Both always apply. A venue rubric never removes a domain's anti-pattern list; a
domain profile never overrides venue criteria or gating.

### Why domain is a file, not a persona

Three independent lines converged on this.

- **PaperQA2** adapts to new tasks by configuration, not by new agents. Its
  contradiction-detection deployment differs from its question-answering one by
  a single overridden prompt field. Its biology deployment works by injecting
  one extra field (`gene_name`) into the evidence-extraction schema, then hard-
  matching on it downstream — domain specificity lands on *what gets extracted*,
  not on tone.
- **FutureHouse** shipped five discipline-specific review agents and collapsed
  them into two shared pipelines within a year; two of the original five now
  resolve to the same backend identifier. Even the chemistry-specific agent was
  folded into the general data-analysis pipeline.
- The literature reports a **hivemind effect**: parallel LLM reviewers converge
  so tightly that N agents carry the information of one.

A persona per discipline would produce phases × disciplines and, on this
evidence, would collapse back anyway.

### Profile structure

Twelve fixed sections. The load-bearing ones:

| § | Purpose |
|---|---|
| 04 | **Extraction fields.** The contract that actually carries domain adaptation. One row, one field in the structured summary. `not stated` is a required entry, never an omission |
| 05 | **Nearest prior work.** Replaces "missing baselines" with whatever the discipline's equivalent is — a superseding theorem, a prior synthetic route, an earlier cohort study |
| 06 | **Verifiability checks**, each tagged automatic / semi-automatic / manual. Only `automatic` findings may be stated as fact; `manual` ones enter the verification agenda as questions |
| 09 | **Anti-patterns.** Forbidden question classes, each paired with the replacement that belongs in its place |

§09 is deliberately ranked above the criteria table. Our own audit showed the
unmodified pipeline degraded *gracefully* on proof papers — it emitted
`Datasets: none` rather than hallucinating. The available gain was never in
defining more dimensions; it was in replacing the question frame. Independent
evidence agrees: injecting a structured discipline checklist at runtime raised
adherence-checking accuracy from 45% to ~79%, and the serialization format
(Markdown / JSON / XML) made no measurable difference. **What is injected
matters; how it is formatted does not.**

### Hybrid papers

A paper whose core claim is formal *and* which reports computed values reads its
domain profile **and** `_numerical-slice.md`. Adding, never substituting — the
substitution is precisely what lost the headline numbers.

The overlay adds seven quantitative fields (`reported_quantities`,
`instance_set`, `precision_and_tolerance`, `agreement_claim`, …) and licenses a
narrow class of question about the computation — above all whether it is
*independent of the result it validates*, circularity being the characteristic
failure of numerical validation in formal work. Every anti-pattern in the
domain profile still holds.

### Output vocabulary

Replaced the single decision recommendation and 1–5 confidence score with:

- **Two orthogonal axes** — significance (5 closed levels) and strength of
  evidence (6 closed levels), adapted from eLife's assessment vocabulary. Never
  collapsed into one number.
- **An ordered per-finding scale** with `insufficient evidence to judge` in the
  middle as a legitimate value. A comparable scale with a central
  "lack of evidence" option was correct on 98% of statements for which no
  evidence existed.
- **"What was not checked"** in place of numeric confidence. Automated reviewers
  report near-constant 8–9/10 confidence bearing no relationship to their actual
  error rate; a list of what remains unverified is actionable, a constant is not.

### Gating

`qa_criteria[]` gains `gating` and `gating_source`. Without it the pipeline
conflates *worth asking about* with *worth penalising*.

The distinction is real and venue-specific: some journals collect a significance
judgement on their review form while explicitly refusing to reject on it, while
others treat "why does this not belong in a good specialist journal instead" as
a hard bar. **Significance defaults to `venue-set` in every profile** —
inferring it from the discipline would introduce a systematic bias across every
paper in that field.

### The export gate

Borrowed in spirit from crystallography's `checkCIF`, the one industrialised
automatic review engine found in the survey: it grades machine-checkable
properties into severity classes and **requires the authors to justify the
serious ones in writing**. Machine grades, human argues — not machine scores.

The reviewer now checks four conditions before writing:

1. every citation resolves to `02_retrieved_literature.md`
2. every weakness names the artifact it came from
3. every `explicit flaw` / `strong concern` finding has a traceable consequence
   in the recommendation, or an explicit note on why it has none
4. no verdict on correctness is emitted anywhere

Condition 3 targets a documented failure mode in which automated reviewers flag
an integrity problem and assign an acceptance-level score anyway, with nothing
connecting the two.

### What OSP must never claim

Models judging proof correctness reach roughly 65 balanced F1, and their errors
run in one direction — **accepting flawed proofs**. For the human ceiling: a
twelve-referee panel spent four years on one famous proof and concluded it was
"99% certain" while recording that they could not certify correctness and never
would.

Every such observation is framed as a **verification agenda** — what a human
expert should check and why that step is load-bearing — never as a verdict.

### Distribution fixes

Prerequisites, not optional extras. `sync_adapters.py` enumerated `defaults/`
non-recursively and copied only `SKILL.md` from each skill folder, so any file
in a subdirectory was dropped from all 14 adapters with no error.

Worse, `test_parity.py` derived its expected file set from **the same
non-recursive enumeration as the sync script**. Dropped files were absent from
the expectation too, so the test passed. An expectation built on the same faulty
assumption as the code under test cannot catch that code's bug.

Both now walk the tree. Parity additionally fails on adapter files no longer
present in `_shared`. A negative test confirmed the check fires.

This was the **third** silent-file-drop in this repository. The first —
`.gitignore` swallowing a new defaults file — survived an entire 18-paper
benchmark run and was caught only by an independent audit.

## Provenance

| Source | Used for |
|---|---|
| PaperQA2 (`Future-House/paper-qa`) — `settings.py`, `configs/`, `prompts.py` | Configuration-as-adapter pattern; schema-field injection |
| FutureHouse / Edison client `JobNames` enumerations, before and after rename | Evidence that discipline-specific agents collapse |
| OpenScholar (`AkariAsai/OpenScholar`) — `src/instructions.py` | Counter-example: NLP hardcoded into the default question frame |
| Official reviewer guidelines: AMS, SIAM, JHEP, Nature Portfolio, PLOS, ACS, IUCr, ICMJE, JAMA, NeurIPS, ICLR, ARR, ACM | Per-profile §03/§06/§07/§08, cited in each profile's own §12 |
| EQUATOR reporting standards (CONSORT 2025, PRISMA 2020, ARRIVE 2.0, STROBE, MDAR, FAIR) | §07 conditional hooks in biology / medicine |
| eLife assessment vocabulary | Two-axis output scale |
| 2024–2026 LLM peer-review literature (~30 papers) | Failure modes; the never-claim-correctness rule; checklist-injection ROI |
| `DOMAIN_ADAPTIVE_AUDIT.md` | The regression this design corrects |

**Not established.** APS (PRL/PRD/PRB) and SciPost reviewer guidelines were
blocked by anti-scraping measures and are recorded as gaps in the physics
profiles' §12 rather than filled from secondary sources. The Lancet, Cell Press
STAR Methods, and BMJ reviewer pages were likewise unreachable.

**Not validated.** The benchmark corpus is 18 papers, all mathematics. The
physics, biology, chemistry, and medicine profiles have never been exercised
against a paper in their field. They are written from primary sources but
remain unvalidated, and should be labelled as such until run.
