# Plan — strictly positive global minimum of the renormalized quartic-oscillator map

## Claim sentence

The renormalized-coupling map $m(b)=b+12\int x^2|G_b|^2$ of the Baez–Zhou self-consistency problem is strictly positive at every real $b$ and attains a finite global minimum $m_0>0$, so the self-consistency problem has a solution exactly for couplings $\lambda\le m_0^{-3/2}$ and the critical coupling is finite and strictly positive.

Stated so it could be wrong: exhibiting one real $b$ with $m(b)\le 0$, or showing $\inf m$ is approached only as $|b|\to\infty$, refutes it.

## Spine

| #   | Link                                                                                                                                             | Evidence                                                                                                                 | Standing      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | ------------- |
| 1   | For each real $b$, $h_b=\tfrac12(p^2+bx^2)+x^4$ has compact resolvent, a simple lowest eigenvalue, and a positive even ground state in $\mathcal S(\mathbb R)$ | dilation $s=\sqrt2 x$, $\alpha=-b/4$ onto the Montgomery operator; standard                                           | common ground |
| 2   | $a(b)=2E'(b)$, hence $m=b+24E'$ is continuous                                                                                               | Feynman–Hellmann applied to $\partial_b h_b=x^2/2$, with $E$ smooth by the dilation                                   | proved        |
| 3   | $\langle G,[A,[H,A]]G\rangle=2\langle AG,(H-E)AG\rangle$ for symmetric $A$ preserving $\mathcal S$                                                                            | direct computation in the quadratic form                                                                                 | proved        |
| 4   | With $A=p$: $[p,[h_b,p]]=b+12x^2$, so $m(b)=2\langle pG_b,(h_b-E)pG_b\rangle$                                                                                           | link 3 evaluated on $h_b$                                                                                       | proved        |
| 5   | $m(b)>0$ for every real $b$                                                                                                     | $pG_b$ odd and nonzero, so orthogonal to $G_b$; simplicity gives a gap $\delta>0$ on $G_b^\perp$ | proved        |
| 6   | $m(b)\ge b$ for $b\ge0$, and $m(-t)\ge 2t-12\sqrt{t/2+1}$                                                                                            | Rayleigh–Ritz with a Gaussian at a well bottom, then Cauchy–Schwarz                                                      | proved        |
| 7   | The infimum is attained at a finite $b_*$, and $0<m(b_*)=\min m$                                                                           | links 2, 5, 6                                                                                                            | proved        |
| 8   | $\lambda_c=m_0^{-3/2}$ is the largest coupling for which the self-consistency problem is solvable                                                        | link 7 with the Baez–Zhou correspondence                                                                                 | proved        |

Every link is proved; nothing rests on computation. Link 6 is where the paper improves on the source: the published tail bound is a constant, which leaves the infimum free to escape to infinity, and link 6 replaces it with one that grows.

## Target

**Annales Henri Poincaré.** The result settles, in full, one of the two conjectures stated in a published paper, by a method short enough to read in a sitting; AHP takes exactly this — a complete rigorous resolution of a named question in mathematical physics.

Runner-up: **Letters in Mathematical Physics**, if the finished manuscript stays under roughly six pages, which the current proof suggests it might. J. Math. Phys. is the fallback if both decline.

Class: `article` with `amsthm`, per the decision procedure — the object of study is a theorem and it is established by proof.

## What is new, against each closely competing work

- **Baez–Zhou (1992)**, who posed the conjecture: they prove $m>3/5$ for $b\le-30$ and $m>0$ for $b\ge0$, and compute $m$ on $[-30,0]$ by central differences. This paper proves positivity on the whole line, and replaces their constant tail bound by a divergent one, which is what makes the infimum attained rather than merely bounded below.
- **Helffer–Léautaud (2024)**, the closest modern result: they prove the lowest Montgomery eigenvalue has exactly one critical point. The dilation carries their family onto this one, but $m'(b)=0$ becomes $\lambda_1''=4/3$ rather than $\lambda_1'=0$, so their theorem does not decide this question. State that explicitly — a referee who knows the paper will ask.
- **Helffer–Persson-Sundqvist (2010)** and the Montgomery literature: they study the same operator family for its own spectral questions; none addresses the combination $b+12\langle x^2\rangle$.

## Section outline

| Section                                                                                  | Spine links advanced |
| ---------------------------------------------------------------------------------------- | -------------------- |
| Introduction — the self-consistency problem, what $m$ decides, what was known | frames 1, sets up 8  |
| The operator family and its ground state                                                 | 1, 2                 |
| A double-commutator identity and positivity                                              | 3, 4, 5              |
| Coercivity at both ends                                                                  | 6                    |
| The minimum and the critical coupling                                                    | 7, 8                 |
| Remarks: what is not proved                                                              | —                    |

## Figures

One figure, and only if it earns its place.

**Figure 1 — the two proved bounds and the interval they leave.** The message: the paper's own lower bounds close off both tails, confining the minimizer to a bounded interval. It plots the two bounds of link 6 ($m\ge b$ on $b\ge0$; $m(-t)\ge 2t-12\sqrt{t/2+1}$), with $m$ itself drawn from a numerical evaluation for orientation only, clearly marked as such. This shows a result the paper establishes, not a prior paper's.

If the numerical curve cannot be drawn without suggesting the theorem rests on it, drop it and plot the bounds alone.

## Open questions for the author

1. **Journal.** AHP or LMP? The registry recommends AHP; the workspace's own `solution.md` says LMP. The decision changes the length target and whether the spectral preliminaries are written out or cited.
2. **The quadratic-form justification** for the double commutator is the external gate the registry names. The identity is applied to unbounded $A=p$ and $H$ with a $b$-dependent operator domain; the write-up must say in which form sense each pairing is taken. This needs the domain expert's sign-off before submission.
3. Should the consequence for $\lambda_c$ (link 8) be the headline, or a corollary? It is the physically meaningful statement, but it is one line given link 7.

## Literature survey, as run

Seventeen entries. What each band holds, and what was decided against:

| Band                   | Works                                                                                                                                                                                |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Founding               | Baez–Zhou 1992 (the conjecture), Montgomery 1995 (the operator family), Bender–Wu 1969 and Simon 1970 (the anharmonic oscillator)                                                    |
| Immediate predecessors | Helffer–Léautaud 2024, Helffer 2010 (Montgomery model revisited), Helffer–Persson 2010, Bahouri–Barilari–Gallagher–Léautaud 2023                                                     |
| Competing and adjacent | Pan–Kwek 2002 (vortex nucleation), Helffer–Morame 2004, Helffer–Mohamed 1996, Fournais–Helffer (surface superconductivity), Pham The Lai–Robert 1979 (nonlinear eigenvalue problems) |
| Current                | Bahouri et al. 2023, Helffer–Léautaud 2024, Turbiner 2021                                                                                                                            |
| Standard references    | Kato, Agmon, Reed–Simon IV                                                                                                                                                           |

Read and **not** cited, with the reason:

- **Guzzetti 2026**, on a quasi-exactly solvable _sextic_ oscillator and Painlevé IV. Surfaced by an arXiv phrase search and read; it never mentions the Montgomery family and shares only the word "oscillator". Citing it would have been padding.
- **Helffer–Kordyukov, Helffer–Sjöstrand 1984, Zworski, Helffer 2013, Chatzakou**, each co-cited by two of the sources. They are the common ground of the sub-Riemannian and Engel-group thread that Bahouri et al. opened, and this paper uses neither semiclassical multiple-well analysis nor Engel groups. That thread is represented by Bahouri et al. 2023.
- **Caffarel 2024** and **Durugo 2017**: the first is an approximate partition-function model, the second concerns the _relativistic_ quartic oscillator. Neither bears on the positivity of $m$.

One correction was made to a fetched record. Crossref lists A. Dicke, who wrote an appendix, as a co-author of Simon 1970. Four independent sources in `references/sources` cite the paper as B. Simon alone. The author field is corrected and the reason recorded in `references.bib` beside the entry; every other field is as issued.

## Gates

- Author approval: complete
- Literature survey: complete — 17 entries covering all four bands; record below
- Citation check: complete — 30 attributions over 13 paragraphs; see
  `review/cite_audit.md`. Eight were read against the source and three of those
  were wrong: the characterization of the Baez–Zhou tail bound, which stood in
  the abstract, the introduction and Remark 4.2, and the volume cited for the
  KLMN theorem. All are corrected. The remaining 22 were judged without a
  source, all of them monographs or papers older than the preprint servers.
- Domain-expert review of the quadratic-form argument for the double commutator: open
