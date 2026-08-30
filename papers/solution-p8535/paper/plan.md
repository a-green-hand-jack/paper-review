# Plan — uniqueness of the critical point of the renormalized quartic oscillator

## Claim sentence

The renormalized-coupling map $m(b)=b+12\langle G_b,x^2G_b\rangle$ has exactly one real critical point; it lies in $(-16/5,0)$ and is a strict local minimum.

Stated so it could be wrong: a second real $b$ with $m'(b)=0$, or a critical point outside $(-16/5,0)$, refutes it.

## Spine

| #   | Link                                                                                                                                                      | Evidence                                                                                                                                                       | Standing                           |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| 1   | $m(b)=b+24E'(b)$ and $m'(b)=1+24E''(b)$, so the critical points of $m$ are the level set $E''=-1/24$                                                  | Feynman–Hellmann, with $E$ smooth by the dilation                                                                                                    | common ground                      |
| 2   | Under $t=\sqrt2x$, $\alpha=-b/4$, that level set becomes the curvature condition $\lambda_1''(\alpha)=4/3$ for the Montgomery family; call its solutions targets | exact dilation                                                                                                                                                 | proved                             |
| 3   | No target has $\alpha\le0$                                                                                                                              | §2.1                                                                                                                                                           | proved                             |
| 4   | Every target satisfies $\alpha<4/5$                                                                                                                     | necessary inequalities, then the endpoint sharpening of §2.3                                                                                                   | proved                             |
| 5   | At every target the level set is crossed transversally, i.e. $\lambda_1'''\ne0$                                                                               | even-gap criterion, pure-quartic spectral isolation and transfer, exact bad-set constraints, and a finite rational Bernstein exclusion over the localizing box | proved, one step computer-assisted |
| 6   | A target exists                                                                                                                                           | §4                                                                                                                                                             | proved                             |
| 7   | Exactly one target exists, hence exactly one critical point of $m$                                                                             | transversality plus existence on the localized interval                                                                                                        | proved                             |
| 8   | It lies in $(-16/5,0)$ and is a strict local minimum                                                                                                   | links 3, 4 mapped back through the dilation, with the sign of $m''$                                                                                   | proved                             |

Link 5 is the only computer-assisted step, and it is the one the write-up has to change most: see below.

## Target

**Annales Henri Poincaré.** A complete uniqueness theorem for a named conjecture, with a nontrivial method and a computer-assisted lemma stated rigorously. Runner-up: **Communications in Mathematical Physics**, if the transversality machinery of §3 turns out to be reusable beyond this family, which is the thing that would raise it a band.

Class: `article` with `amsthm`.

## What is new, against each closely competing work

- **Baez–Zhou (1992)**: they conjecture the uniqueness and offer a central-difference computation on $[-30,0]$. This proves it on the whole line and locates the point in $(-16/5,0)$.
- **Helffer–Léautaud (2024)**, the nearest published result and the one a referee will reach for: they prove $\lambda_1'(\alpha)$ has exactly one zero. The present question is a _different_ level set of a _higher_ derivative — $\lambda_1''=4/3$ — so their theorem neither implies this nor is implied by it. The introduction must state the exact increment over their result, because the two look interchangeable until the derivatives are compared. The registry names this as the first thing to establish.
- **Helffer–Persson-Sundqvist (2010)** and the Montgomery-operator literature: same family, different spectral questions.

## The two self-containment repairs this manuscript needs

Both are inherited from the workspace write-up and are the reason it is not yet submittable as it stands.

1. **The Bernstein step must become a computer-assisted lemma stated in the text.** The material is already there — the tensor Bernstein coefficient formula, exact de Casteljau bisection, the rule that always bisects a least-refined coordinate breaking ties in the order $\alpha,a,v$, the closing criterion, and the per-polynomial leaf counts. What is missing is the framing that lets a reader follow it without the verifier: what each leaf is, the test applied, why the test is decisive (the range of a polynomial lies in the convex hull of its Bernstein coefficients, so all-negative coefficients exclude the box), why the leaves exhaust the parent box (bisection partitions it and every leaf closes), and what the exclusion forces. State it as a lemma proved by exhaustive rational computation. No checksum, no file name, no "the accompanying verifier".
2. **The large-$\alpha$ well-bracketing asymptotic used in §2.2** to select the sign of $\lambda'$ is, by the workspace's own admission, stated rather than derived. A step the paper leans on and does not prove has to be either derived in an appendix or attributed to a source where it is proved, with the exact statement checked against that source. Until then the chain has a link with no support inside the paper.

## Section outline

| Section                                                                                   | Spine links advanced |
| ----------------------------------------------------------------------------------------- | -------------------- |
| Introduction — the conjecture, what the level set is, the increment over Helffer–Léautaud | frames 1, 2          |
| Reduction to a curvature level set                                                        | 1, 2                 |
| Localization: excluding $\alpha\le0$, then $\alpha<4/5$                               | 3, 4                 |
| Transversality at every target                                                            | 5                    |
| A computer-assisted exclusion lemma                                                       | 5                    |
| Existence and uniqueness                                                                  | 6, 7, 8              |
| What is not proved                                                                        | —                    |

## Figures

**Figure 1 — the successive localizations.** The message: three independent constraints cut the parameter line down to the interval where the unique target must lie. It shows this paper's own exclusions, not a prior result.

**Figure 2 — the subdivision that closes the box**, only if it can be drawn honestly at a legible size: the leaves of the bisection over the localizing box, shaded by which polynomial closed each. Its message is that the exclusion is a finite partition, which is the fact the lemma rests on. Drop it if the leaf count makes it a grey smear; the table of counts already carries the number.

## Open questions for the author

1. **The asymptotic in §2.2** — derive it, or name the source that proves it? This decides whether an appendix is needed.
2. **How much of the Bernstein certificate belongs in print.** The lemma needs the method and the counts; the full leaf list does not fit and does not need to. Is a table of per-polynomial counts enough, with the traversal rule stated exactly?
3. AHP or CMP? The registry says AHP unless the transversality method generalizes.

## Gates

- Author approval: complete
- Literature survey: complete — 19 entries, four bands covered; see below
- Citation check: complete — 22 attributions over 4 paragraphs; see
  `review/cite_audit.md`. Six were read against the source and one was wrong:
  the half-line identity of §4 was credited to Helffer–Léautaud, who credit
  Pan–Kwek for it and Helffer–Persson Sundqvist for the proof. Both were
  already in the reference list, and the credit is corrected. The remaining 16
  were judged without a source, all of them monographs or papers older than
  the preprint servers.
- Domain-expert sign-off before submission, as the registry requires: open
- The §2.2 asymptotic derived in the paper or attributed to a checked source: complete — attributed, with the caveat below
- The Bernstein step rewritten as a self-contained computer-assisted lemma: complete — the carried manuscript already states it in full

## What the carried manuscript already had

Both repairs this plan asked for turned out to be done in the workspace draft, so the work here was to verify rather than to write.

The Bernstein step is self-contained as it stands. It gives the tensor coefficient formula, the convex-hull property that makes the test decisive, the exact bisection rule, the strict closing criterion, the per-polynomial leaf counts, and — the part that matters most — a proof that the leaves exhaust the box: the terminal paths are prefix-free and their dyadic weights sum to $1$, so the terminal boxes cover $[0,1]^3$ including its boundary. No checksum, no file name, no verifier.

The introduction already states the increment over Helffer–L\'eautaud in the form this plan asked for: their theorem settles the zeros of $\lambda_1'$, while the stationarity condition here is the level set $\lambda_1''=4/3$.

## One citation was made less precise on purpose

The draft attributed the large-$\alpha$ sign selection to "Helffer–L\'eautaud, Proposition 2.6, equations (2.1)–(2.2), and Section 5.3". Reading their paper confirms the mathematical content — the half-line identity carrying the factor $(t-\sqrt{2\alpha})$ is there, and it is what (L8) rests on — but the arXiv source is auto-numbered, so those particular numbers could not be checked against the published version, whose numbering may differ. A precise locator that has not been opened is the same kind of hazard as a remembered DOI: it reads as authoritative and nobody rechecks it. The citation now names the content and the paper. Restoring the numbers is a one-minute job for whoever has the published version to hand, and worth doing.

## Literature survey, as run

Nineteen entries. The carried list already covered the founding band (Baez–Zhou, Montgomery, Bender–Wu, Simon), the predecessors (Helffer–L\'eautaud, Helffer, Helffer–Persson, Bahouri et al.), the adjacent magnetic-well literature (Pan–Kwek, Helffer–Morame, Helffer–Mohamed, Fournais–Helffer), and — unusually and correctly for this paper — the computer-assisted band: Farouki on the Bernstein basis, with Moore and Rump for validated computation. Turbiner was added for current work on the same operator.

Searched and deliberately not added: the generic interval-arithmetic proceedings literature. Farouki is the citation this proof actually needs, and a list of validated-computation surveys would have been padding.

The same corrected Crossref record as in the companion paper: Simon 1970 is by B. Simon alone, not with the author of its appendix.
