# Gates

What only a person can confirm about this paper. Each gate is one line ending
in `open` or `complete`; whatever is worth recording goes on indented lines
beneath. A gate turns to `complete` only when the thing itself was done.

- Self-contained argument: complete
  All thirteen compiled pages read against the checklist. Every step is on
  the page: the coherent-sheaf exact sequence and both applications of
  Cartan's theorem B, the 25-generator module proved by hand, the
  four-particle obstruction evaluated directly, and the generic-coupling
  boundary computed at (89). The finite rows of Table 1 check the first
  instances of results the text proves; their objects are defined and derived
  in the text and each can be recomputed by hand from the displayed
  coefficient row.

  One defect was found and fixed by this reading, and no grep would have
  caught it. The data-and-code paragraph said the finite algebra "was
  independently verified by ... programs retained with the project archive" --
  it named no file, so the manuscript scan was silent, but it pointed the
  reader at something they can never obtain. It now states that no step is
  computer assisted, names where each finite entry is derived in the text,
  and says the arithmetic that was run certifies a transcription rather than
  an argument.

- Literature survey: complete
  Re-run during the citation audit; it showed Zamolodchikov--Zamolodchikov
  and Berg--Karowski--Weisz cited by three of the fetched sources and
  missing here, and both were added. A second pass over the co-citation
  ranking added two more where they do work: the four-author sine-Gordon
  form-factor paper, whose sequel was being cited without it, and Lukyanov's
  free-field representation, which is where the free-field line the
  introduction names begins. The works still reported are Lee-Yang,
  Cardy--Mussardo, Toda-model and truncated-conformal-space results this
  argument does not use, and they are omitted deliberately.

- Citation check: complete
  The run exits clean. Every attribution was read against its source or
  judged explicitly, and each says which in the audit. One sentence about
  the 2025 formulation was corrected: an earlier draft said that paper
  repeats the openness statement, and it does not. The Pillin equation
  numbers are confirmed against the arXiv version but not against the
  journal numbering the entry names, which the audit records. Every
  citation names a result or an equation; none points at a page.

- Named expert review obtained: open
  The workspace ledger requires a named integrable-QFT or
  several-complex-variables reviewer to check three things: that fixing the
  two diagonal recurrence values as parameters is the right convention, that
  the reduced-divisor category is the right one to impose the recurrence in,
  and that the image and fiber theorem is new. Nothing in the proofs waits on
  it. Failing it means a scope correction, or in the worst case that the
  fiber theorem is known.

- Front matter and declarations confirmed: open
  The author list, acknowledgments, funding, competing-interest statement,
  and the wording of the data-and-code paragraph. Failing it means editing
  the front and back matter only.

- Code deposit decided: open
  Whether the exact verification programs ship as a companion repository.
  They reproduce the finite rows of Table 1, every one of which is derived in
  the text, and the manuscript states that no step is computer assisted -- so
  the current answer is no. Failing it means adding a repository and
  rewriting the data-and-code paragraph.
