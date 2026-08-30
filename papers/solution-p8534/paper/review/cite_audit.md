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


## Unit 1 --- main.tex:91

> Wick ordering an interaction relative to its own ground state, rather than relative to the free vacuum, turns a renormalization prescription into a self-consistency problem: the state one orders against must be the state that the ordered Hamiltonian produces. Baez and Zhou \cite{baez1992renormalized} analysed this problem for the one-dimensional anharmonic oscillator, which is the simplest case in which it is not trivial, and reduced all of it to the shape of one function of one real parameter.

- `baez1992renormalized` -- read `references/sources/baez-zhou-1992.md` -- **verdict:** confirmed against the source. Their Problem 1 (§3) is exactly self-consistent Wick ordering for $\tfrac12(p^2+bq^2)+q^4$, and the proof of their Theorem 2 reduces it to the single map $m=b+12\langle G(b),q^2G(b)\rangle$.

## Unit 2 --- main.tex:117

> What \cite{baez1992renormalized} established about that shape left the middle of the parameter line open. For $b\ge0$ positivity is immediate from $m(b)\ge b$, and for $b<-10$ their bound on the second moment gives $m(b)\ge-b/2-72/5$, which is positive once $b\le-30$ and grows without bound as $b\to-\infty$; both tails were therefore already under control. On $[-30,0]$ there was no bound. What they did there was to replace $h_b$ by its Dirichlet restriction to $[-10,10]$, whose own renormalized coupling they argue lies below $m$, and to compute that quantity by central differences with step $0.01$; on the strength of the resulting graph they conjectured that $m$ has a strictly positive minimum. The gap was thus not the behaviour at infinity but positivity on a compact interval, and it was a gap because the only evidence there was a finite computation.

- `baez1992renormalized` -- read `references/sources/baez-zhou-1992.md` -- **verdict:** **corrected.** The paragraph previously said their tail bound “was a constant”. It is not: their estimate (9) gives $m>-b/2-72/5$ for $b<-10$, which diverges as $b\to-\infty$; the value $3/5$ is that bound evaluated at $b=-30$. It also said they “computed $m$” on $[-30,0]$, whereas they computed the renormalized coupling of the Dirichlet restriction of $h_b$ to $[-10,10]$, which they argue lies below $m$. Both are now stated as the source states them, and the claimed gap is narrowed to positivity on the compact interval.

## Unit 3 --- main.tex:146 !

> \begin{corollary} \label{cor:lambda} Write $m_0=\min m>0$. The self-consistency problem of \cite{baez1992renormalized} is solvable at coupling $\lambda>0$ if and only if $\lambda\le m_0^{-3/2}$. In particular the critical coupling $\lambda_c=m_0^{-3/2}$ is finite and strictly positive. \end{corollary}

- `baez1992renormalized` -- read `references/sources/baez-zhou-1992.md` -- **verdict:** confirmed. The corollary attributes only the self-consistency problem, which is their Problem 1.

## Unit 4 --- main.tex:169

> The operator family \eqref{eq:hb} is a dilation of the Montgomery family of quartic oscillators \cite{montgomery1995hearing}, which arose in the analysis of magnetic Schr\"odinger operators with a vanishing field and has since been studied both as a model for vortex nucleation \cite{Pan_2002so} and in its own right \cite{Helffer_2010tm,Helffer_2010sp}; it belongs to the wider study of magnetic wells and magnetic bottles \cite{Helffer_1996sa,HELFFER_2004mb}, whose surrounding spectral theory is surveyed in \cite{Fournais_Book}, and the family reappears in the sub-Riemannian analysis of the Engel group \cite{Bahouri_2023ss}. The anharmonic oscillator itself has been studied since \cite{Bender_1969ao,simon1970coupling} and remains a live subject \cite{Turbiner_2021ao}.

- `montgomery1995hearing` -- no source (article); judge it -- **verdict:** judged without a source (Comm. Math. Phys. 168 (1995) 651–675, older than the preprint servers). The title carries the claim, and Helffer–Léautaud, read here, cite Montgomery for the conjecture on this family in exactly this magnetic setting.
- `Pan_2002so` -- no source (article); judge it -- **verdict:** judged without a source. The title states the non-degenerately vanishing magnetic field in bounded domains; the “vortex nucleation” framing is the standard reading of that setting and Helffer–Léautaud cite Pan–Kwek at the same point. Not read against the page.
- `Helffer_2010tm` -- no source (article); judge it -- **verdict:** judged without a source. The title, “The Montgomery model revisited”, carries the claim that the family has been studied in its own right.
- `Helffer_2010sp` -- read `references/sources/0912.0872.tex` (the file says it is “Spectral properties of higher order\\anharmonic oscillators”) -- **verdict:** confirmed against the source. Its abstract studies $-d^2/dt^2+(t^{k+1}/(k+1)-\alpha)^2$, which is the Montgomery family at $k=1$.
- `Helffer_1996sa` -- no source (article); judge it -- **verdict:** judged without a source. The title names the ground-state energy of a Schrödinger operator with magnetic wells, which is the claim made.
- `HELFFER_2004mb` -- no source (article); judge it -- **verdict:** judged without a source. The title names magnetic bottles for the Neumann problem, which is the claim made.
- `Fournais_Book` -- no source (book); judge it -- **verdict:** judged without a source. Helffer–Léautaud, read here, point at the same monograph for a presentation of the surrounding results.
- `Bahouri_2023ss` -- read `references/sources/2206.10396.tex` (the file says it is “Spectral summability for the quartic oscillator \\ with applications to the Engel group”) -- **verdict:** confirmed against the source. Its abstract studies the sublaplacian on the Engel group and the quartic oscillator that arises there.
- `Bender_1969ao` -- no source (article); judge it -- **verdict:** judged without a source (Phys. Rev. 184 (1969), older than the preprint servers). The claim is only that the anharmonic oscillator has been studied since this paper, which the title and date carry.
- `simon1970coupling` -- no source (article); judge it -- **verdict:** judged without a source (Ann. Phys. 58 (1970)). Same framing claim, carried by the title.
- `Turbiner_2021ao` -- read `references/sources/2011.14451.tex` (the file says it is “Anharmonic oscillator: a solution”) -- **verdict:** confirmed against the source: a 2021 paper titled “Anharmonic oscillator: a solution”, which is what “remains a live subject” asserts.

## Unit 5 --- main.tex:181 !

> One nearby result deserves to be separated from ours, because the two look interchangeable and are not. Helffer and L\'eautaud \cite{helffer2024critical} proved that the lowest eigenvalue $\lambda_1(\alpha)$ of the Montgomery family has exactly one critical point. That theorem concerns the zeros of $\lambda_1'$, and the present question is a level set of $\lambda_1''$. The dilation of \Cref{prop:family} gives $E(b)=\lambda_1(-b/4)-b^2/16$, and \Cref{prop:continuity} gives $m(b)=b+24E'(b)$; differentiating the first and substituting it into the second, \begin{equation} \label{eq:montgomery-derivatives} m(b)=-2b-6\lambda_1'\!\left(-\tfrac b4\right), \qquad m'(b)=-2+\tfrac32\lambda_1''\!\left(-\tfrac b4\right), \end{equation} so that $m'(b)=0$ reads $\lambda_1''=4/3$, a level set of the second derivative rather than a zero of the first. Their result therefore neither implies nor is implied by anything proved here, and it is equally silent on the sign of $m$. It is also worth saying that the present theorem is about the sign and the attainment of $m$, and says nothing about how many critical points $m$ has; that separate conjecture of \cite{baez1992renormalized} is not addressed.

- `helffer2024critical` -- read `references/sources/2209.13923.tex` (the file says it is “On critical points of eigenvalues of the Montgomery family of quartic oscillators”) -- **verdict:** confirmed against the source. Their Theorem~1.2 reads: “The first eigenvalue $\alpha\mapsto\lambda_1(\alpha)$ … has a unique critical point $\alpha_c$”, with $\alpha_c\in(0,1)$, a non-degenerate minimum. The manuscript claims exactly this and no more.
- `baez1992renormalized` -- read `references/sources/baez-zhou-1992.md` -- **verdict:** confirmed. Their text: “we conjecture that $m$ has only one critical point, where it attains its minimum”.

## Unit 6 --- main.tex:204

> Finally, the problem is a nonlinear eigenvalue problem in the sense that the operator depends on its own ground state, a setting with its own literature \cite{Lai_1979su}; the reduction of \cite{baez1992renormalized} is what makes the present question a statement about one scalar function instead.

- `Lai_1979su` -- no source (article); judge it -- **verdict:** judged without a source (Journées équations aux dérivées partielles, 1979). The title, “Sur un problème aux valeurs propres non linéaire”, carries the only claim made, that nonlinear eigenvalue problems have their own literature.
- `baez1992renormalized` -- read `references/sources/baez-zhou-1992.md` -- **verdict:** confirmed; the reduction is their Theorem 2, as in Unit 1.

## Unit 7 --- main.tex:236 !

> \begin{proof} For every $\varepsilon>0$ there is $C_\varepsilon$ with $|b|x^2/2\le\varepsilon x^4+C_\varepsilon$, so the form $bx^2/2$ is infinitesimally form-bounded with respect to $p^2/2+x^4$; the KLMN theorem \cite{ReedSimonII} then gives a closed form bounded below on the $b$-independent domain $\mathcal Q$, and a unique associated self-adjoint operator. The potential tends to $+\infty$, so the resolvent is compact and the spectrum is a sequence of eigenvalues of finite multiplicity accumulating only at $+\infty$ \cite{ReedSimonIV}.

- `ReedSimonII` -- no source (book); judge it -- **verdict:** **corrected.** The KLMN theorem was cited to volume IV. It is in volume II (Fourier Analysis, Self-Adjointness), §X.2; volume IV is Analysis of Operators and carries the confining-potential statement instead. The citation is now split by volume. Judged without the books on hand — no catalogue yields either monograph — so the author should confirm both volume numbers against a copy.
- `ReedSimonIV` -- no source (book); judge it -- **verdict:** judged without a source. Volume IV, Analysis of Operators, is where the discreteness of the spectrum for a potential tending to $+\infty$ belongs. Moved to `unverified.bib` with its remembered ISBN dropped, since no catalogue yields the monograph.

## Unit 8 --- main.tex:244 !

> The substitution $s=\sqrt2\,x$ together with $\alpha=-b/4$ carries $h_b$ unitarily onto $M_\alpha-b^2/16$, where $M_\alpha$ is the Montgomery operator \cite{montgomery1995hearing}. Simplicity of the lowest eigenvalue, the parity of its eigenfunction, membership in the Schwartz class and exponential decay of the eigenfunction and of all its derivatives are established for that family in \cite[Proposition 1.1]{helffer2024critical}; by the dilation they hold for $h_b$. The decay is of Agmon type, as for any Schr\"odinger operator whose potential grows at infinity \cite{Agmon_Book}. Positivity of the ground eigenfunction in one dimension is Sturm's theorem. Consequently every pairing and every integration by parts used below is taken between Schwartz functions. \end{proof}

- `montgomery1995hearing` -- no source (article); judge it -- **verdict:** confirmed by name against Helffer–Léautaud, who call $\mathfrak h_{\mathcal M}(\alpha)$ the Montgomery operator and attribute it to this paper. The naming attribution is all that is made.
- `helffer2024critical` [Proposition 1.1] -- read `references/sources/2209.13923.tex` (the file says it is “On critical points of eigenvalues of the Montgomery family of quartic oscillators”) -- **verdict:** confirmed against the source. Their Proposition~1.1 gives self-adjointness with compact resolvent, simplicity of every eigenvalue, the parity of the $j$th eigenfunction, and exponential decay of every eigenfunction together with all its derivatives. Two notes. “Membership in the Schwartz class” is a consequence of their real-analyticity and decay statements rather than their wording. And the number is read off the arXiv source, whose auto-numbering is corroborated by the authors' own label `th1.4` landing on Theorem 1.4; the entry cites the published Indiana Univ. Math. J. version, whose numbering has not been checked.
- `Agmon_Book` -- no source (book); judge it -- **verdict:** judged without a source. The monograph is Lectures on Exponential Decay of Solutions of Second-Order Elliptic Equations, which is precisely the decay being named.

## Unit 9 --- main.tex:269 !

> \begin{proof} Smoothness of $\alpha\mapsto\lambda_1(\alpha)$ for the Montgomery family, together with the Feynman--Hellmann formula for it, is \cite[Proposition 2.1]{helffer2024critical}; the exact dilation of \Cref{prop:family} gives $E(b)=\lambda_1(-b/4)-b^2/16$, so $E$ is smooth. Since $b\mapsto h_b$ is a holomorphic family of type (B) on $\mathcal Q$ with $\partial_bh_b=x^2/2$, and $E(b)$ is a simple isolated eigenvalue, first-order perturbation theory \cite{Kato_Book} gives $E'(b)=\langle G_b,(x^2/2)G_b\rangle=a(b)/2$. Substituting in \eqref{eq:m} yields \eqref{eq:fh}, and continuity of $m$ follows from smoothness of $E$. \end{proof}

- `helffer2024critical` [Proposition 2.1] -- read `references/sources/2209.13923.tex` (the file says it is “On critical points of eigenvalues of the Montgomery family of quartic oscillators”) -- **verdict:** confirmed against the source. Their Proposition~2.1, headed “Feynmann-Hellmann formula”, states that $\alpha\mapsto\lambda_j(\alpha)$ is $C^\infty$ and gives $\lambda_j'(\alpha)=-2\int(\tfrac12t^2-\alpha)u_j^2$. Both the smoothness and the formula are attributed correctly. Same numbering caveat as Unit 8.
- `Kato_Book` -- no source (book); judge it -- **verdict:** judged without a source. Holomorphic families of type (B) and first-order perturbation of a simple isolated eigenvalue are Kato's own material and his own terminology (Ch. VII).

## Unit 10 --- main.tex:344 !

> \begin{remark} The argument uses no information about $b$ beyond what \Cref{prop:family} supplies, and in particular no numerical input. This is what extends positivity from the two tails, where \cite{baez1992renormalized} established it, to the whole parameter line. \end{remark}

- `baez1992renormalized` -- read `references/sources/baez-zhou-1992.md` -- **verdict:** confirmed. They established $m>3/5$ for $b\le-30$ and asserted $m>\varepsilon$ for $b\ge0$; “the two tails” is accurate.

## Unit 11 --- main.tex:404 !

> \begin{remark} \label{rem:tail} The right-hand side of \eqref{eq:tail} becomes positive at $t=9+3\sqrt{13}\approx19.8$, the positive root of $t^2-18t-36=0$, and grows linearly thereafter. Divergence on the left tail is not itself new: \cite{baez1992renormalized} bound the second moment for $b<-10$ and obtain $m(-t)\ge t/2-72/5$, which also grows. What \eqref{eq:tail} adds is a bound holding for every $t>0$, with four times the slope, so that the interval on which neither bound of \Cref{prop:coercivity} is positive is explicit and short. Positivity there is supplied by \Cref{thm:positivity}, which uses no numerical input. \Cref{fig:m} shows the two bounds and that interval. \end{remark}

- `baez1992renormalized` -- read `references/sources/baez-zhou-1992.md` -- **verdict:** **corrected**, as in Unit 2. The remark now states their bound as $m(-t)\ge t/2-72/5$ and says what \eqref{eq:tail} adds: validity for every $t>0$ and four times the slope.

## Unit 12 --- main.tex:440

> \begin{proof}[Proof of \Cref{cor:lambda}] By \cite{baez1992renormalized}, solutions at coupling $\lambda>0$ correspond one to one with the real $b$ satisfying $m(b)=\lambda^{-2/3}$. By \Cref{thm:main} the range of $m$ is contained in $[m_0,\infty)$ with $m_0>0$, and, $m$ being continuous with $m(b)\to+\infty$ at both ends and attaining $m_0$, its range is exactly $[m_0,\infty)$. Hence $m(b)=\lambda^{-2/3}$ has a solution if and only if $\lambda^{-2/3}\ge m_0$, that is, if and only if $\lambda\le m_0^{-3/2}$. \end{proof}

- `baez1992renormalized` -- read `references/sources/baez-zhou-1992.md` -- **verdict:** confirmed against the source, which states the correspondence between solutions at coupling $\lambda$ and the $b$ with $b+12\langle G(b),q^2G(b)\rangle=m$, $\lambda=m^{-3/2}$ — that is, $m(b)=\lambda^{-2/3}$. Their text derives it from the proofs of their Theorems 2 and 5, so it carries no number of its own and none is cited.

## Unit 13 --- main.tex:454

> \Cref{thm:main} gives the existence of a minimizer and the strict positivity of the minimum value. It does not give uniqueness of the minimizer, and it does not address the separate conjecture of \cite{baez1992renormalized} that $m$ has exactly one critical point; that question is a level set of $\lambda_1''$ under the dilation, and is not settled by \cite{helffer2024critical}, which settles the zeros of $\lambda_1'$.

- `baez1992renormalized` -- read `references/sources/baez-zhou-1992.md` -- **verdict:** confirmed; the one-critical-point conjecture, as in Unit 5.
- `helffer2024critical` -- read `references/sources/2209.13923.tex` (the file says it is “On critical points of eigenvalues of the Montgomery family of quartic oscillators”) -- **verdict:** confirmed; their theorem is about the critical points of $\lambda_1$, that is the zeros of $\lambda_1'$, as in Unit 5.
