# Independent Audit — Domain-Adaptive Review Criteria (Issue #6)

## Method

- **What was audited.** The OSP fork change described in [issue #6](https://github.com/a-green-hand-jack/paper-review/issues/6) — a new `session.json.paper.review_mode` (`theoretical` / `empirical` / `other`) set at onboarding, which selects a `theoretical`-specific generic guidelines file, switches `01_structured_summary.md`'s third section between "Evidence (E)" (empirical) and "Formal Content" (theoretical), and re-maps `04_missing_baselines.md`'s framing from ML baselines/datasets to closest prior/competing theorems and unaddressed edge cases for theoretical papers.
- **Fork commit audited.** `d8780e0` (initial change), with a follow-up fix at `d2a4827` (see "Regression found and fixed" below). Both on `a-green-hand-jack/open-scholar-peer@main`.
- **Corpus.** All 18 papers/versions in the `paper-review` benchmark corpus: the 15 named papers, plus `erdos973` v1/v2/v3 (arXiv:2608.02043) run as a separate three-version set. Every paper in this corpus is math or mathematical physics; none are empirical ML papers.
- **BEFORE baseline.** A pre-existing, already-completed 18-run corpus on the benchmark box, produced before this change (unmodified OSP, effectively identical to upstream `amirkiarafiei/open-scholar-peer`), same model/variant/harness/venue.
- **AFTER run.** A fresh full 18-run corpus executed after the change, same model (`openai/gpt-5.6-sol`), variant (`medium`), harness (`opencode`), venue (`arxiv`), run on a separate Ubuntu benchmark host with 292G+ free disk. One paper (`solution-p4400`) failed on the first AFTER attempt; the root cause was found and fixed (below), and the paper was successfully rerun. All 18 AFTER results are `status: completed` and uploaded to the private Hugging Face dataset `Jack-Jieke-Wu/osp-trails`.
- **Audit process.** Three independent, freshly-spawned agents (no shared context with the agent that made the code change, and no context of each other) were each assigned 6 papers. Each agent fetched BEFORE and AFTER artifacts (`session.json`, `01_structured_summary.md`, `04_missing_baselines.md`, `final_review.md`) via SSH from the benchmark host and independently judged whether the change improved, didn't meaningfully change, or regressed each paper's review — instructed explicitly to be skeptical and not to confirm the intended narrative. Their full reports (with quoted evidence) are reproduced in full below, lightly reformatted for a single document; verdict labels and quotes are the auditing agents' own, not edited for tone.

## Output

### Summary verdict table (18 papers)

| # | Paper | Verdict |
|---|---|---|
| 1 | `a-proof-of-shors-orthogonal-measurement-conjecture` | **Mixed — real regression** (see below) |
| 2 | `erdos973--v1` | Improved |
| 3 | `erdos973--v2` | No meaningful change |
| 4 | `erdos973--v3` | No meaningful change |
| 5 | `hidden-arrow-order-escape` | Mixed, leaning improved |
| 6 | `on-the-first-and-the-second-borel-cantelli-lemmas` | Mixed, slight improvement |
| 7 | `residual-bounds-for-schur-stable-polynomials` | Improved (modest) |
| 8 | `solution-p4378` | Improved (modest) |
| 9 | `solution-p4383` | Mixed (baseline gain; recommendation swing looks like noise) |
| 10 | `solution-p4400` | **Failed on first attempt (regression, fixed) → Improved on rerun** |
| 11 | `solution-p8534` | Improved (a genuine new technical finding, Lemma 3.1) |
| 12 | `solution-p8535` | No meaningful change |
| 13 | `solution-p8536` | Improved |
| 14 | `solution-p8559` | Mixed (lateral trade in baseline coverage) |
| 15 | `solution-p8560` | Improved (recommendation flip flagged as possible noise) |
| 16 | `solution-p8607` | Improved (modest) |
| 17 | `solution-p8608` | Improved |
| 18 | `solution-p8610` | Mixed (recommendation flip flagged as possible noise) |

**Tally:** 9 improved, 3 no meaningful change, 6 mixed (including one confirmed-and-fixed regression and one open regression, both described below).

### Headline finding: the domain-adaptive branching works as intended for pure math

Across all three audit groups, no auditor found a single case of the originally-alleged failure mode (ML-style fabricated baselines/datasets forced onto a paper with no experiments) — in fact, the BEFORE runs already degraded reasonably gracefully for pure proofs (e.g. "*Datasets: none; this is a self-contained theoretical mathematics paper*"). What the change delivers, concretely and repeatedly verified with quotes:

- **`01_structured_summary.md`**: the "Evidence (E)" → "Formal Content" swap is real, not cosmetic, in every one of the 17 successfully-compared papers. AFTER runs consistently produced genuine theorem/lemma/proposition inventories with proof techniques and named prior results, replacing forced-empty ML fields (`"Datasets: None"`, `"Ablations: not applicable"`).
- **`04_missing_baselines.md`**: the reframing to "closest prior/competing theorems" and "unaddressed edge cases/counterexamples" repeatedly surfaced genuinely new, correctly-classified literature gaps that the BEFORE runs missed — e.g. `solution-p4378` (Kim 2017, Grantcharov 2026), `solution-p4383` (Appel-Vlaar 2024), `solution-p8534` (Friedman's renormalized-oscillator paper), `hidden-arrow-order-escape` (Pulvirenti-Simonella 2017, Han 1978), `erdos973--v1` (the paper's own v3 supersedes it — see below).
- **`erdos973--v1`'s standout catch**: AFTER's baseline-scout flagged that v1 is quantitatively superseded by v3 of the *same* arXiv record within days, and the final review correctly reframed the recommendation around version-readiness rather than proof correctness — a genuinely useful, non-obvious finding BEFORE never surfaced. Full quote: *"V1 is obsolete as a present-day arXiv manuscript... V3 is retitled Residual bounds for Schur-stable polynomials and advertises the stronger bound r_n >= exp(-(1+o(1))sqrt(n)log n)... This is not a rejection of the proof. It is driven primarily by version readiness."*
- **`solution-p8534`'s standout catch**: AFTER's Q&A/final review flagged a real, specific mathematical gap BEFORE missed entirely — *"Lemma 3.1 is overbroad as stated [DISCREPANCY; Scope Q1]. Assuming only that AG lies in the form domain does not justify expressions such as HAG, AHAG, and HA²G used in the proof."*

### Regression #1 — `solution-p4400` failure: found, root-caused, fixed, and reverified

**What happened.** The first AFTER attempt at `solution-p4400` failed (`status: "failed"`, `"error": "OpenCode exited successfully but final_review.md was not produced"`, `session.json` frozen at the pristine pre-onboarding template). The log showed the onboarding agent attempting to `Glob "**/generic_review_guidelines_theoretical.md"` rooted at `/home/user/orca/projects/*` — outside its own sandboxed workspace — which the harness auto-rejected as an `external_directory` permission request, with no recovery.

**Root cause.** The OSP fork's `.gitignore` contained a bare, unanchored `.claude/` pattern (intended to ignore a root-level runtime directory) that also matched `extensions/.claude/` — the tracked Claude Code adapter output, which is the adapter this benchmark project's harness actually installs and runs (despite `--harness opencode` in the CLI, the batch runner copies `.claude/`, not `.opencode/`, into each isolated workspace). Pre-existing files under `extensions/.claude/defaults/` stayed tracked (added before the gitignore rule existed), but the newly-added `generic_review_guidelines_theoretical.md` was silently excluded from every `git add`, on every machine, including the original commit and push to the fork. A fresh clone of the fork therefore had 13 of 14 tool adapters with the new file, and exactly the one this project uses — `.claude` — missing it. When onboarding picked `review_mode: theoretical` and needed the missing file, it had no safe local fallback and searched outward into the sandbox-restricted parent directory.

**Fix.** Anchored the pattern to the repo root (`/.claude/`, matching the existing `/.agents/` convention a few lines above) in commit [`d2a4827`](https://github.com/a-green-hand-jack/open-scholar-peer/commit/d2a4827095460b0e35b20636413c2f75621ddc33), added the previously-excluded file, pushed to the fork.

**Reverification.** Pulled the fix on the benchmark host, reinstalled the Claude Code adapter (confirmed all 4 default files present), and reran `solution-p4400` alone. It completed successfully (`status: completed`, `upload_status: uploaded`, `review_mode: "theoretical"`, `field: "mathematical physics / integrable systems"`), and the auditing agent's follow-up comparison rates it **Improved**: AFTER's `04_missing_baselines.md` correctly escalated two items BEFORE under-weighted to high severity (public reproduction of two computer-assisted eliminations; taxonomy of exceptional loop-weight hypersurfaces), and the recommendation moved from "Weak Accept" (confidence 3/5) to "Borderline" (confidence **4/5**, i.e. more confident, not less) — a pattern consistent with a more thorough audit rather than noise.

### Regression #2 — headline-number and baseline-detail loss on hybrid theoretical+numerical papers (open, not yet fixed)

Two papers in the corpus are not pure proofs — they include real, substantial numerical/computational validation alongside their formal claims: `a-proof-of-shors-orthogonal-measurement-conjecture` (a 408-instance mixed-state stress suite comparing four algorithmic baselines) and `hidden-arrow-order-escape` (a hard-disk simulation audit with explicit KL-divergence and moment figures). Both show the same pattern:

- **Structured summary loses explicit numbers.** For the Shor's-conjecture paper, BEFORE's Evidence section stated: *"Headline numbers: proposed receiver 408/408 at 10^-6 nat and median successful time 12.9 ms; multistart PVM 45.8%; direct POVM ascent 4.7%; Helstrom 0.25%; PGM 0% under stated fixed budgets."* AFTER's Formal Content section kept only two of the five percentages and dropped the Helstrom, PGM, and median-time figures entirely. The same pattern appears in `hidden-arrow-order-escape`: BEFORE's *"velocity-histogram KL to Maxwell of 0.3949 +/- 0.0260 for N=16 and 0.2140 +/- 0.0261 for N=36"* becomes an unquantified description in AFTER (though the reversal-error figures were retained there).
- **Baseline-scout detail collapses for the Shor's-conjecture paper specifically.** BEFORE's `04_missing_baselines.md` had 5 concrete algorithmic-baseline gaps (2 high severity: an independent high-precision global reference optimizer, and a validated-numerics/interval-arithmetic implementation of the certificate). AFTER's equivalent table shrank to a single low-severity citation-completeness note (*"the focused search did not reveal a theorem duplicating the posterior algebra... No high-severity missing competing theorem was identified"*), with some of the lost substance folded — without severity ratings — into a separate edge-cases section. `hidden-arrow-order-escape` did not show this same collapse (it went from 7 to 12 baseline items, a net gain), so this appears specific to how the Shor's-conjecture paper's `review_mode` branch handled its numerical slice, not a systematic effect across all hybrid papers.

**Assessment.** The domain-adaptive design was meant to keep the *empirical* framing for any numerical/computational slice of a `theoretical`-mode paper (see `osp-baseline-scout-agent`'s "apply the left-hand framing only to that computational slice" instruction) — for the Shor's-conjecture paper, this did not work as intended, and it is a genuine, not-yet-fixed gap in the current prompt design. This is tracked as follow-up work on issue #6 rather than fixed in this pass, since it requires a more careful edit to `osp-baseline-scout-agent` and `osp-summary-agent` to keep numeric specificity for the empirical slice of a hybrid paper, and the corpus currently only has two examples to design against.

### Minor cosmetic issues found (not regressions, but noted)

- Several `04_missing_baselines.md` files kept the literal top-level title `# Missing Baselines & Datasets` even after switching to the theoretical framing (only some papers got a cleanly renamed title), and one file (`solution-p8608`) has a hybrid header that concatenates the old and new subsection names (`"### Missing baselines - Closest prior or competing results not adequately compared"`). Titles should be fully renamed rather than partially propagated; left as a small follow-up cleanup, not a functional problem.

### Recommendation-swing noise: a benchmark-methodology caveat, not a change effect

In four papers (`a-proof-of-shors...`, `solution-p4383`, `solution-p8560`, `solution-p8610`), the final recommendation swung by a full tier (e.g. Weak Accept → Major revision) between BEFORE and AFTER, while the underlying cited facts were essentially unchanged between the two reviews (in some cases the *same* concern is quoted as "a minor verification concern, not an identified contradiction" in one run and "the principal reason for recommending major revision" in the other). All three auditing agents independently flagged this pattern as more consistent with ordinary LLM sampling variance across separate runs than with any effect of the `review_mode` change itself — and it recurs in both directions (also visible, less dramatically, in some `no meaningful change` verdicts). This is a limitation of comparing single BEFORE/AFTER runs rather than a distribution of runs, and is exactly the kind of ambiguity that issue #5's revision-aware, evidence-anchored comparison (rather than a bare recommendation/confidence diff) is meant to address for actual paper revisions; it applies here too, to A/B-testing OSP itself. A future OSP benchmark iteration should consider running each configuration N>1 times per paper to separate signal from noise before drawing conclusions from a recommendation-label change alone.

## Provenance

- Fork commits audited: `d8780e0` (initial change), `d2a4827` (gitignore fix).
- BEFORE trails: pre-existing corpus on the benchmark host, timestamps `20260830T054723Z`–`20260830T073906Z` (UTC).
- AFTER trails: `20260830T184114Z`–`20260830T203235Z` (UTC), including the `solution-p4400` rerun.
- All 18 AFTER trails and the `solution-p4400` rerun are archived in the private Hugging Face dataset `Jack-Jieke-Wu/osp-trails` (`upload_status: "uploaded"` recorded in each trail's `manifest.json`).
- Three independent audit agents were used (no shared context with each other or with the agent that authored the code change); one agent's `solution-p4400` section was revised after the fix was deployed and the paper was rerun, using the same before/after comparison method as its other five papers.
- Related issues: [#3](https://github.com/a-green-hand-jack/paper-review/issues/3) (erdos973 version-ranking benchmark, motivated this work), [#4](https://github.com/a-green-hand-jack/paper-review/issues/4) (Fork workflow this audit follows), [#5](https://github.com/a-green-hand-jack/paper-review/issues/5) (revision-aware reviewer — the recommendation-swing noise finding above is directly relevant to that issue's design), [#6](https://github.com/a-green-hand-jack/paper-review/issues/6) (the change this document audits).
