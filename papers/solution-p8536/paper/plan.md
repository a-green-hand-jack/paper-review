# Plan — removing the assumed moment bound from the self-consistent oscillator branch

## Claim sentence

For the self-consistent Wick-ordering problem $H_0+\lambda\!:\!P(q)\!:_{u(\lambda)}$ with coercive polynomial $P$, there is a coupling threshold below which every sufficiently short closed interval carries exactly one normalized, nonnegative, norm-continuous ground-state branch through the free vacuum — and the bound on $\langle u(\lambda),P(q)u(\lambda)\rangle$ that the existing treatment assumes is not a hypothesis but a consequence.

Stated so it could be wrong: two distinct branches on one short interval, or a branch along which the interaction moment escapes, refutes it.

## Spine

| #   | Link                                                                                                                                        | Evidence                            | Standing             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | -------------------- |
| 1   | The self-consistency problem has a branch through the free vacuum under an assumed bound on the interaction moment                          | Baez–Zhou, Theorem 1 and Lemmas 8–9 | common ground, cited |
| 2   | State-relative Wick polynomials form a formal Appell family, giving the coefficientwise structure the later estimates need                  | coefficientwise induction, §1       | proved               |
| 3   | If the top interaction moment escapes along a branch, the state concentrates                                                                | §2                                  | proved               |
| 4   | Concentration forces a coercive negative asymptotic for the change of state                                                                 | §3                                  | proved               |
| 5   | A variational lower bound on the ground-state energy contradicts that asymptotic                                                            | §4                                  | proved               |
| 6   | Hence the interaction moment is automatically bounded along any branch — the assumed hypothesis is a theorem                                | links 3–5                           | proved               |
| 7   | With the moment bounded, exactly one such branch exists on every sufficiently short interval, uniformly over a small-coupling neighbourhood | §6                                  | proved               |

Link 6 is the paper. Links 2–5 exist to reach it, and link 7 is what it buys.

## Target

**Annales Henri Poincaré.** Removing a hypothesis from a published theorem, by an argument that is entirely analytic, is a normal AHP contribution. Runner-up: **Journal of Mathematical Physics**, which is the right home if the referee reads the result as a technical strengthening rather than a structural one.

Class: `article` with `amsthm`.

## What is new, against each closely competing work

- **Baez–Zhou (1992)**: they assume the interaction-moment bound in order to get the branch. This proves the bound, so their hypothesis can be deleted rather than checked. Say exactly which of their statements is affected — a referee will want the delta stated as a diff, not as a claim of general improvement.
- **The literature on Hartree-type and self-consistent ground-state equations** more broadly: the survey has to establish whether the escape-implies-concentration argument of §2–§4 is known there under another name. This is the band most likely to contain a prior version of the same mechanism, and it is the one the workspace has not searched.

## Section outline

| Section                                                                              | Spine links advanced |
| ------------------------------------------------------------------------------------ | -------------------- |
| Introduction — the self-consistency problem, the hypothesis, why removing it matters | frames 1, states 6   |
| State-relative Wick polynomials as an Appell family                                  | 2                    |
| Concentration under top-moment escape                                                | 3                    |
| The coercive negative change-of-state asymptotic                                     | 4                    |
| The opposing ground-state bound                                                      | 5                    |
| The moment bound is automatic                                                        | 6                    |
| Uniform uniqueness on short intervals                                                | 7                    |
| The boundary of the theorem                                                          | —                    |

## Figures

**None.** There is no result here that a picture carries better than the statement does, and no object whose geometry the reader needs. A schematic of "branch versus escaping moment" would illustrate the setup rather than show a result of this paper, which the figure standard rules out. This is a deliberate decision, not an omission — revisit only if the concentration mechanism of §2–§4 turns out to need a picture to be followable.

## Open questions for the author

1. **How much of Baez–Zhou to restate.** The paper depends on their Theorem 1 and Lemmas 8–9. Citing them is legitimate — they are published and the reader can obtain them — but the statement being _removed_ has to be quoted exactly, or the reader cannot see what was deleted.
2. **The boundary of the theorem** is the external gate the registry names: for which $n$, which $\omega_j$, and which coercive $P$ does the argument hold as written? The write-up should state the boundary rather than leave a referee to find it.
3. Whether to present this as a standalone paper or hold it for a unified treatment with the other problems in the 86 family. The registry raises the combined option and points at Communications in Mathematical Physics for it; that decision is above this plan.

## Gates

- Author approval: complete
- Literature survey: open
- Citation check: complete --- 21 attributions over 6 paragraphs; see
  `review/cite_audit.md`. Three were read against the source and two of
  those were overstated and are corrected; 17 were judged without a
  source, all of them monographs or papers older than the preprint
  servers. Page locators were removed from every citation; a named
  result survives a change of printing and a page number does not. A later
  sweep moved the Reed--Simon volume II entry into `unverified.bib`: it was
  written from what was known and filed as though fetched, which kept it out
  of the count the two-file scheme exists to produce. Its remembered ISBN was
  dropped; author, title, publisher and year stand.
- Domain-expert confirmation of the theorem's boundary, as the registry requires: open
