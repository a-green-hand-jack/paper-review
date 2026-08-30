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


## Unit 1 --- main.tex:87

> The renormalized oscillator coefficient $m$ was introduced by Baez and Zhou, who conjectured from finite-difference evidence that it has one critical point \cite{Baez_1992ro}. Its quartic spectral background includes the classical perturbative and analytic work of Bender--Wu and Simon \cite{Bender_1969ao,Simon_1970ca}. Analytic perturbation theory, the standard theory of discrete Schr\"odinger spectra, and exponential decay of bound states provide the operator-theoretic setting used below \cite{Kato_Book,ReedSimonIV,Agmon_Book}.

- `Baez_1992ro` -- read `references/sources/baez-zhou-1992.md` -- **verdict:** confirmed against the source. They introduce $m=b+12\langle G(b),q^2G(b)\rangle$ in §3, compute it on $[-30,0]$ by central differences with step $0.01$, and write: “we conjecture that $m$ has only one critical point, where it attains its minimum”. “Finite-difference evidence” is their own method.
- `Bender_1969ao` -- no source (article); judge it -- **verdict:** judged without a source (Phys. Rev. 184 (1969), older than the preprint servers). “Perturbative” matches the paper's subject; only background framing is attributed.
- `Simon_1970ca` -- no source (article); judge it -- **verdict:** judged without a source (Ann. Phys. 58 (1970)). The title, “Coupling constant analyticity for the anharmonic oscillator”, carries the word “analytic” in the manuscript's sentence.
- `Kato_Book` -- no source (book); judge it -- **verdict:** judged without a source. Analytic perturbation theory is Kato's own subject and the terminology used later in the paper is his.
- `ReedSimonIV` -- no source (book); judge it -- **verdict:** judged without a source. Volume IV is Analysis of Operators, which is where the theory of discrete Schrödinger spectra sits; the volume number is right for this sentence. The entry was hand-written and filed in `references.bib` as though fetched; it is now in `unverified.bib` with its remembered ISBN dropped, since no catalogue yields the monograph.
- `Agmon_Book` -- no source (book); judge it -- **verdict:** judged without a source. The monograph is Lectures on Exponential Decay of Solutions of Second-Order Elliptic Equations, precisely the decay named.

## Unit 2 --- main.tex:101 !

> Under the exact dilation used below, the spectral problem becomes the Montgomery family \[ H_\alpha=-\frac{d^2}{dt^2}+\left(\frac{t^2}{2}-\alpha\right)^2, \] which has a substantial magnetic-spectral history beginning with Montgomery and continuing through magnetic-well and surface-superconductivity analysis \cite{Montgomery_1995ht,Helffer_1996sa,Pan_2002so,HELFFER_2004mb,Fournais_Book}. Helffer revisited the $k=1$ model, and Helffer--Persson treated the associated higher-order anharmonic family \cite{Helffer_2010tm,Helffer_2010sp}. Recent work connects quartic spectral summability to the Engel group \cite{Bahouri_2023ss}, and the anharmonic oscillator itself remains a live subject \cite{Turbiner_2021ao}. Helffer and Léautaud proved uniqueness of the zero of $\lambda_1'(\alpha)$ \cite{Helffer_2024oc}; that theorem does not decide the present problem, whose exact stationarity condition is the second-derivative level equation $\lambda_1''(\alpha)=4/3$.

- `Montgomery_1995ht` -- no source (article); judge it -- **verdict:** judged without a source (Comm. Math. Phys. 168 (1995)). Helffer–Léautaud, read here, name $\mathfrak h_{\mathcal M}(\alpha)$ the Montgomery operator and cite this paper for it, which corroborates “beginning with Montgomery”.
- `Helffer_1996sa` -- no source (article); judge it -- **verdict:** judged without a source. The title names magnetic wells, which is the claim.
- `Pan_2002so` -- no source (article); judge it -- **verdict:** judged without a source. The title names non-degenerately vanishing magnetic fields in bounded domains; the surface-superconductivity framing is standard for it and Helffer–Léautaud cite it at the same place.
- `HELFFER_2004mb` -- no source (article); judge it -- **verdict:** judged without a source. The title names magnetic bottles for the Neumann problem.
- `Fournais_Book` -- no source (book); judge it -- **verdict:** judged without a source. Spectral Methods in Surface Superconductivity is the surface-superconductivity reference the sentence claims; Helffer–Léautaud point at it for the same purpose.
- `Helffer_2010tm` -- no source (article); judge it -- **verdict:** judged without a source. “The Montgomery model revisited” is exactly “Helffer revisited the $k=1$ model”. Helffer–Léautaud's bibliography gives the same work as Colloq. Math. 118(2) 391–400.
- `Helffer_2010sp` -- read `references/sources/0912.0872.tex` (the file says it is “Spectral properties of higher order\\anharmonic oscillators”) -- **verdict:** confirmed against the source. It treats $-d^2/dt^2+(t^{k+1}/(k+1)-\alpha)^2$, the higher-order anharmonic family, which is what the sentence says. Note that Helffer–Léautaud print the second author as Persson Sundqvist; the fetched Crossref record for the journal article prints Persson, and is left as the agency issued it.
- `Bahouri_2023ss` -- read `references/sources/2206.10396.tex` (the file says it is “Spectral summability for the quartic oscillator \\ with applications to the Engel group”) -- **verdict:** confirmed against the source. Its abstract studies the sublaplacian on the Engel group via the quartic oscillator, which is the connection claimed.
- `Turbiner_2021ao` -- no source (article); judge it -- **verdict:** judged without a source. A 2021 J. Phys. A paper titled “Anharmonic oscillator: a solution” supports “remains a live subject” and nothing more is attributed.
- `Helffer_2024oc` -- read `references/sources/2209.13923.tex` (the file says it is “On critical points of eigenvalues of the Montgomery family of quartic oscillators”) -- **verdict:** confirmed against the source. Their Theorem~1.2: “The first eigenvalue $\alpha\mapsto\lambda_1(\alpha)$ … has a unique critical point”. “Uniqueness of the zero of $\lambda_1'$” is that statement.

## Unit 3 --- main.tex:118 !

> Our proof separates global analysis from a finite exact certificate. First, all solutions of the level equation are placed in a compact rational interval. Second, reduced-resolvent identities show that strict transversality follows from an even-gap inequality. Moment and hypervirial constraints reduce failure of that inequality to the simultaneous nonnegativity of nine rational polynomials on a compact box. The Bernstein basis and its subdivision properties are surveyed in \cite{Farouki_2012tb}; interval and verification methods provide the wider validated-computation context \cite{Moore_Book,Rump_2010vm}. Here every Bernstein coefficient and every de Casteljau subdivision is instead computed in exact rational arithmetic. The resulting exhaustive tree excludes the box in 757 nodes, so the certificate is part of the proof rather than a floating-point experiment.

- `Farouki_2012tb` -- no source (article); judge it -- **verdict:** judged without a source. “The Bernstein polynomial basis: a centennial retrospective” is a survey, and only survey status and subdivision content are attributed.
- `Moore_Book` -- no source (book); judge it -- **verdict:** judged without a source. Introduction to Interval Analysis is cited only for the wider validated-computation context; no result of it is used, and the manuscript says the certificate is exact rational arithmetic instead.
- `Rump_2010vm` -- no source (article); judge it -- **verdict:** judged without a source. “Verification methods: rigorous results using floating-point arithmetic”, Acta Numerica 2010, is cited for the same context and nothing more.

## Unit 4 --- main.tex:323 !

> \begin{proof} At a positive critical point of $\lambda$, half-line integration by parts gives \begin{equation} \label{eq:L8} (\lambda-\alpha^2)\,u(0)^2 =\int_0^\infty (t+\sqrt{2\alpha})(t-\sqrt{2\alpha})^2u(t)^2\,dt>0 . \end{equation} A centred Gaussian of width $\rho=(2\alpha)^{-1}$ gives $\lambda(\alpha)\le1/(4\alpha)+\tfrac34\alpha^2\le\alpha^2$ for $\alpha\ge1$, contradicting \eqref{eq:L8}. So $\lambda'$ has no zero on $[1,\infty)$, and the well-bracketing asymptotic $\lambda(\alpha)\sim\sqrt{2\alpha}$ selects the positive sign. The half-line identity \eqref{eq:L8} is due to Pan and Kwek \cite{Pan_2002so} for the first eigenvalue, and the proof recalled here is that of Helffer and Persson Sundqvist \cite{Helffer_2010sp}; the comparison argument, the sign selection and the asymptotic are taken from Helffer and L\'eautaud \cite{Helffer_2024oc} and are not derived here. \end{proof}

- `Pan_2002so` -- no source (article); judge it -- **verdict:** **corrected.** The paragraph credited the half-line identity to Helffer–Léautaud. Their own text says otherwise: “Although initially due to Pan-Kwek in [Pan-Kwek] for $\lambda_1$ … the most elegant proof is given in [HPS].” Priority now goes to Pan and Kwek, who are already in the reference list.
- `Helffer_2010sp` -- read `references/sources/0912.0872.tex` (the file says it is “Spectral properties of higher order\\anharmonic oscillators”) -- **verdict:** **corrected**, same sentence. Helffer–Léautaud's [HPS] is this entry, and its proof of the identity is confirmed here: its Lemma 3.4 derives $\int_0^\infty\frac{d}{dt}[(t^{k+1}/(k+1)-\alpha)^2]u^2\,dt=(\lambda-\alpha^2)u(0)^2$ and, at a critical point, $(\lambda-\alpha^2)u(0)^2=2\int_0^\infty(t^k-(\alpha(k+1))^{k/(k+1)})(t^{k+1}/(k+1)-\alpha)u^2\,dt$. At $k=1$ this is \eqref{eq:L8}.
- `Helffer_2024oc` -- read `references/sources/2209.13923.tex` (the file says it is “On critical points of eigenvalues of the Montgomery family of quartic oscillators”) -- **verdict:** confirmed against the source for what is still attributed to it. Their \eqref{uplambda1b} is $\lambda_1(\alpha)\le\frac1{4\alpha}+\frac34\alpha^2$ from the Gaussian of width $1/(2\alpha)$, exactly the manuscript's comparison; their Corollary~2.2 puts every critical point in $(0,\infty)$; and their \eqref{eq:asba} gives $\lambda_{2k+1}(\alpha)\sim\sqrt2(2k+1)\sqrt\alpha$, which at $k=0$ is $\sqrt{2\alpha}$. They in fact prove more than the manuscript claims, $\alpha_c<(24/25)^{1/3}$ rather than $\alpha_c<1$. Numbers are read off the arXiv source; the entry cites the published Indiana Univ. Math. J. version, whose numbering has not been checked, so no locator is printed in the manuscript.
