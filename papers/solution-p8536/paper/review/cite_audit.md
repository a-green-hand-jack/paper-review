# Citation audit

Every paragraph of main.tex that cites something, and how each attribution was
checked. There are two ways and they are not interchangeable. Where the source
is on hand the sentence is read against the page. Where no catalogue holds the
work the sentence is judged from the entry and from what is known of it, and
says so, because a reader is entitled to know which attributions rest on a
page and which on a judgement.

The units below are every paragraph containing a citation, and they tile the
manuscript: a boundary in the wrong place only resizes a unit, while a gap
would lose a claim nobody then checks. Which arXiv paper an entry names is
decided by reading, not by a rule, and the decision is recorded here as the
source path. Verdicts are written by hand; a `TODO` left standing means that
attribution has not been checked.


## Unit 1 --- main.tex:88

> Ordinary normal ordering originates in Wick's contraction formula \cite{Wick_1950te}; Gaussian Wick polynomials and constructive field-theory implementations are treated, from complementary viewpoints, in \cite{Janson_Book,Glimm_Book,Simon_Book,Simon_1972hs}. The products in this paper are different: their reference state need not be Gaussian, and their centering and commutator axioms make them a state-relative formal Appell family.

- `Wick_1950te` -- no source (article); judge it -- **verdict:** judged, no source; normal ordering originating in Wick's contraction formula is the standard attribution and the claim is generic.
- `Janson_Book` -- no source (book); judge it -- **verdict:** judged, no source; cited for Gaussian Wick polynomials, which is what the monograph is about.
- `Glimm_Book` -- no source (book); judge it -- **verdict:** judged, no source; cited for constructive field theory implementations, its subject.
- `Simon_Book` -- no source (book); judge it -- **verdict:** judged, no source; cited for functional-integration treatments of the same, its subject.
- `Simon_1972hs` -- no source (article); judge it -- **verdict:** judged, no source; cited alongside for hypercontractive semigroups, matching its title.

## Unit 2 --- main.tex:97 !

> This state-relative construction grew out of Segal's weak-process calculus and his construction of nonlinear local quantum processes \cite{Segal_1969nf,Segal_1970nf,Segal_1970co,Segal_1971co}; a broader account is given by Baez, Segal, and Zhou \cite{Baez_Book}. Friedman isolated the corresponding renormalized oscillator equation and its translation obstruction \cite{Friedman_1973ro}. Baez and Zhou then formulated finite-dimensional self-consistent Wick ordering as a nonlinear ground-state problem and proved a local branch theorem for coercive polynomial interactions \cite{BaezZhou1992}.

- `Segal_1969nf` -- no source (article); judge it -- **verdict:** judged, no source; cited for the weak-process calculus, its subject.
- `Segal_1970nf` -- no source (article); judge it -- **verdict:** judged, no source; second paper of the same series, cited for the same programme.
- `Segal_1970co` -- no source (article); judge it -- **verdict:** judged, no source; cited for the construction of nonlinear local quantum processes, its title.
- `Segal_1971co` -- no source (article); judge it -- **verdict:** judged, no source; fourth of the same series, cited for the same programme.
- `Baez_Book` -- no source (book); judge it -- **verdict:** judged, no source; cited as the broader account by Baez, Segal and Zhou, which is what the monograph is.
- `Friedman_1973ro` -- no source (article); judge it -- **verdict:** judged, no source; cited for the renormalized oscillator equation and its translation obstruction. Baez--Zhou independently attribute their half-open-interval counterexample to Friedman, which corroborates the attribution.
- `BaezZhou1992` -- read `references/sources/baez-zhou-1992.pdf` -- **verdict:** read the scan. It introduces the renormalization map relative to a state with the two axioms used here; Theorem 1 assumes exactly the three conditions the manuscript describes, including boundedness of the interaction moment; Lemmas 8--9 are the cone inverse construction; and the authors ask outright whether the boundedness condition can be omitted while stating that continuity on the closed interval cannot. The manuscript now says it answers that question. Page locators were dropped: the copy read is one printing, and its pagination is not a property of the work.

## Unit 3 --- main.tex:110 !

> A self-consistent ground-state equation, in which the operator depends on the state it is meant to produce, is the setting of Hartree-type problems, and the uniqueness of such ground states has its own literature, and in it the answers are conditional: Lenzmann settled the pseudo-relativistic Hartree equation for ground states of sufficiently small mass, and there for all but countably many values of it \cite{Lenzmann_2009uo}, while Griesemer and Hantsch settled the Hartree--Fock ground state of a closed-shell atom whose nuclear charge is large enough relative to its electron number \cite{Griesemer_2011us}; the question remains active for nonlinear Hartree equations \cite{Luo_2018uo}. What distinguishes the present problem from all of these is that the nonlinearity enters through the Wick ordering rather than through a convolution, so the interaction moment that has to be controlled is the one the ordering itself produces.

- `Lenzmann_2009uo` -- read `references/sources/0801.3976.tex` (the file says it is “Uniqueness of Ground States for Pseudo-Relativistic Hartree Equations”) -- **verdict:** read 0801.3976; the abstract restricts uniqueness to sufficiently small $L^2$ mass and to all but countably many values of it. The manuscript said "settled it"; corrected to state the regime.
- `Griesemer_2011us` -- read `references/sources/1012.5179.tex` (the file says it is “Unique Solutions to Hartree-Fock Equations\\ for Closed Shell Atoms”) -- **verdict:** read 1012.5179; the abstract states uniqueness "provided the atomic number $Z$ is sufficiently large compared to the number $N$ of electrons". The manuscript now carries that condition.
- `Luo_2018uo` -- no source (article); judge it -- **verdict:** judged, no source; the sentence claims only that the question remains active for nonlinear Hartree equations, which the entry's own title supports.

## Unit 4 --- main.tex:121

> The analytic-family and self-adjoint Schr\"odinger background is supplied by standard perturbation and operator theory \cite{Kato_Book,ReedSimonII,Simon_1970cc}. Baez and Zhou's uniqueness argument assumes that the interaction moment remains bounded along the branch, and they record the status of that assumption themselves: they call it a technical condition and ask whether it can be omitted, while noting that continuity on the closed interval cannot be, since uniqueness already fails on a half-open one \cite{BaezZhou1992}. This paper answers that question. Since norm convergence alone does not normally control unbounded polynomial observables, the answer uses the self-consistent variational structure rather than a compactness slogan.

- `Kato_Book` -- no source (book); judge it -- **verdict:** judged, no source; cited for analytic perturbation theory, generic and correct.
- `ReedSimonII` -- no source (book); judge it -- **verdict:** judged, no source; cited for self-adjointness, which is that volume's subject.
- `Simon_1970cc` -- no source (article); judge it -- **verdict:** judged, no source; cited for the analytic-family background. Entry corrected earlier: A. Dicke wrote an appendix and is not a co-author.
- `BaezZhou1992` -- read `references/sources/baez-zhou-1992.pdf` -- **verdict:** read the scan. It introduces the renormalization map relative to a state with the two axioms used here; Theorem 1 assumes exactly the three conditions the manuscript describes, including boundedness of the interaction moment; Lemmas 8--9 are the cone inverse construction; and the authors ask outright whether the boundedness condition can be omitted while stating that continuity on the closed interval cannot. The manuscript now says it answers that question. Page locators were dropped: the copy read is one printing, and its pagination is not a property of the work.

## Unit 5 --- main.tex:169 !

> For a normalized Schwartz vector $u$ write \begin{equation} \label{eq:moments} \mu_\alpha(u)=\langle u,q^\alpha u\rangle, \qquad A_\alpha^u(q)=\,:q^\alpha:_u . \end{equation} The defining expectation and commutator axioms for state-relative renormalized products \cite{BaezZhou1992} are \begin{equation} \label{eq:axioms} A_0^u=1, \qquad \langle u,A_\alpha^u(q)u\rangle=0\ \ (|\alpha|>0), \qquad \partial_{q_j}A_\alpha^u=\alpha_jA_{\alpha-e_j}^u . \end{equation}

- `BaezZhou1992` -- read `references/sources/baez-zhou-1992.pdf` -- **verdict:** read the scan. It introduces the renormalization map relative to a state with the two axioms used here; Theorem 1 assumes exactly the three conditions the manuscript describes, including boundedness of the interaction moment; Lemmas 8--9 are the cone inverse construction; and the authors ask outright whether the boundedness condition can be omitted while stating that continuity on the closed interval cannot. The manuscript now says it answers that question. Page locators were dropped: the copy read is one printing, and its pagination is not a property of the work.

## Unit 6 --- main.tex:421 !

> We use the finite-dimensional cone inverse construction of Baez and Zhou \cite[Theorem 1 and Lemmas 8--9]{BaezZhou1992}, keeping track of the interval quantifier.

- `BaezZhou1992` [Theorem 1 and Lemmas 8--9] -- read `references/sources/baez-zhou-1992.pdf` -- **verdict:** read the scan. It introduces the renormalization map relative to a state with the two axioms used here; Theorem 1 assumes exactly the three conditions the manuscript describes, including boundedness of the interaction moment; Lemmas 8--9 are the cone inverse construction; and the authors ask outright whether the boundedness condition can be omitted while stating that continuity on the closed interval cannot. The manuscript now says it answers that question. Page locators were dropped: the copy read is one printing, and its pagination is not a property of the work.
