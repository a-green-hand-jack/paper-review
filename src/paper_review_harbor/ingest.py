"""Materialise a paper's public sources and map its structure.

Ingestion is deliberately deterministic and LLM-free. It answers three
questions that no model should be guessing at:

1. Which files are the paper, and which are the writing-time trail that must
   never reach a review agent?
2. Which TeX file is the toplevel one, and what does it pull in?
3. What does the paper actually contain -- sections, theorem-like blocks,
   citation keys, labels?

The result is a staging directory holding only publishable material, plus a
`paper_map.json` that later stages (and the annotation subagents) read instead
of re-parsing TeX.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tarfile
import unicodedata
import zipfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .corpus import PaperVersion

#: arXiv ships this alongside the sources; it names the toplevel file.
ARXIV_README = "00README.json"

TEX_SUFFIXES = frozenset({".tex", ".ltx"})
BIB_SUFFIXES = frozenset({".bib", ".bbl"})
FIGURE_SUFFIXES = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".gif"})
STYLE_SUFFIXES = frozenset({".sty", ".cls", ".bst", ".clo"})

DOCUMENTCLASS_RE = re.compile(r"\\documentclass\s*(\[[^\]]*\])?\s*\{")
INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")
SECTION_RE = re.compile(
    r"\\(section|subsection|subsubsection|paragraph)\*?\s*\{((?:[^{}]|\{[^{}]*\})*)\}"
)
THEOREM_RE = re.compile(
    r"\\begin\{(theorem|lemma|proposition|corollary|definition|remark|claim|conjecture|example)\}"
)
LABEL_RE = re.compile(r"\\label\s*\{([^}]+)\}")
TITLE_RE = re.compile(r"\\title\s*(?:\[[^\]]*\])?\s*\{", re.MULTILINE)
CITE_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\])*\s*\{([^}]+)\}")
BIBENTRY_RE = re.compile(r"^\s*@[A-Za-z]+\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)


class IngestError(RuntimeError):
    """The paper source could not be turned into publishable material."""


@dataclass(frozen=True)
class Section:
    level: str
    title: str
    file: str
    line: int


@dataclass(frozen=True)
class TheoremBlock:
    kind: str
    label: str | None
    file: str
    line: int


@dataclass
class PaperMap:
    label: str
    main_tex: str
    title: str | None = None
    tex_files: list[str] = field(default_factory=list)
    bib_files: list[str] = field(default_factory=list)
    figure_files: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    theorems: list[TheoremBlock] = field(default_factory=list)
    cited_keys: list[str] = field(default_factory=list)
    defined_bib_keys: list[str] = field(default_factory=list)
    undefined_citations: list[str] = field(default_factory=list)
    uncited_bib_keys: list[str] = field(default_factory=list)
    total_tex_lines: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class IngestResult:
    label: str
    root: Path
    main_tex: str
    paper_map: PaperMap
    excluded: tuple[str, ...]
    sanitised: tuple[str, ...]
    source_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(root: Path) -> str:
    """Content hash of a directory, stable across filesystems."""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(sha256_file(path).encode())
    return digest.hexdigest()


def _safe_members(names: Iterable[str], archive: Path) -> None:
    for name in names:
        target = Path(name)
        if target.is_absolute() or ".." in target.parts:
            raise IngestError(f"{archive}: refuses to extract path outside the tree: {name}")


def _extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive, "r:gz") as tar:
            _safe_members((m.name for m in tar.getmembers()), archive)
            tar.extractall(destination, filter="data")
    elif archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as zipped:
            _safe_members(zipped.namelist(), archive)
            zipped.extractall(destination)
    else:
        raise IngestError(f"{archive}: unsupported archive type")


def _materialise(version: PaperVersion, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    if version.source_kind == "archive":
        _extract(version.source, destination)
    elif version.source_kind == "directory":
        shutil.copytree(version.source, destination)
    elif version.source_kind == "texfile":
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(version.source, destination / version.source.name)
    else:  # pragma: no cover - guarded by corpus.py
        raise IngestError(f"unknown source kind {version.source_kind!r}")


#: What a sibling PDF is renamed to when staged. Faithful names would leak:
#: staging `v1.pdf` tells the agent its manuscript is one of several versions,
#: which is a hint about where to look for the answer.
STAGED_PDF_NAME = "paper.pdf"


def stage_sibling_pdf(root: Path, version: PaperVersion) -> str | None:
    """Copy in the corpus PDF when the source bundle carries none.

    arXiv e-print bundles hold source only; the compiled PDF sits beside the
    tarball in the corpus, so eleven of the papers here would otherwise reach
    the agent as LaTeX with no rendered form at all. A reviewer reads the PDF,
    and `poppler-utils` is in the image precisely so figures can be rasterised
    and looked at -- neither of which works if compiling from source is the
    only way to get one.
    """
    if version.pdf is None or not version.pdf.is_file():
        return None
    if any(root.glob("*.pdf")):
        return None
    destination = root / STAGED_PDF_NAME
    shutil.copy2(version.pdf, destination)
    return destination.name


def _strip_private(root: Path, version: PaperVersion) -> list[str]:
    """Delete the writing-time trail from the staged tree. Returns what went."""
    removed: list[str] = []
    for private in version.private_paths:
        try:
            relative = private.relative_to(version.source)
        except ValueError:
            # Sibling files (a newer version's archive) were never staged.
            continue
        staged = root / relative
        if staged.is_dir():
            shutil.rmtree(staged)
            removed.append(relative.as_posix() + "/")
        elif staged.is_file():
            staged.unlink()
            removed.append(relative.as_posix())
    return removed


def _flatten_single_dir(root: Path) -> None:
    """Some archives wrap everything in one directory; unwrap it."""
    entries = [p for p in root.iterdir() if not p.name.startswith(".")]
    if len(entries) != 1 or not entries[0].is_dir():
        return
    inner = entries[0]
    for item in list(inner.iterdir()):
        shutil.move(str(item), str(root / item.name))
    inner.rmdir()


def strip_bib_preamble(root: Path) -> list[str]:
    """Drop writing-pipeline meta-commentary from the head of .bib files.

    `unverified.bib` ships with a header stating that its entries "need
    checking against the work itself before submission" and that blank fields
    "mark what was not known". That is the writing pipeline annotating its own
    weak spots. Leaving it in hands a review agent a citation finding for free,
    and the point of the benchmark is to find out whether an agent can notice
    a thin citation by reading it.

    The entries themselves stay untouched, blank fields included: those are the
    manuscript's genuine state and a reviewer is entitled to catch them. Only
    the commentary about them goes.
    """
    stripped: list[str] = []
    for path in sorted(root.rglob("*.bib")):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        cut = 0
        for index, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith("%") or not stripped_line:
                cut = index + 1
                continue
            break
        if cut and any(line.strip().startswith("%") for line in lines[:cut]):
            path.write_text("".join(lines[cut:]), encoding="utf-8")
            stripped.append(path.relative_to(root).as_posix())
    return stripped


def _toplevel_from_readme(root: Path) -> str | None:
    readme = root / ARXIV_README
    if not readme.is_file():
        return None
    try:
        data = json.loads(readme.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    for source in data.get("sources", []):
        if source.get("usage") == "toplevel" and source.get("filename"):
            candidate = root / source["filename"]
            if candidate.is_file():
                return source["filename"]
    return None


def find_main_tex(root: Path) -> str:
    """Locate the toplevel TeX file, preferring arXiv's own declaration."""
    declared = _toplevel_from_readme(root)
    if declared:
        return declared

    candidates: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEX_SUFFIXES:
            text = _read_tex(path)
            if DOCUMENTCLASS_RE.search(text) and "\\begin{document}" in text:
                candidates.append(path)
    if not candidates:
        raise IngestError(
            f"{root}: no TeX file with both \\documentclass and \\begin{{document}}"
        )
    candidates.sort(key=lambda p: (p.name != "main.tex", len(p.parts), p.as_posix()))
    return candidates[0].relative_to(root).as_posix()


def strip_tex_comments(text: str) -> str:
    """Blank out TeX comments while preserving line numbering.

    Without this, a preamble note like ``% ... so \\cite{c,a,b} prints as
    [1--3]`` is read as three real citations to nonexistent keys, and the paper
    map reports undefined-citation defects the manuscript does not have. The
    same applies to commented-out ``\\input`` and ``\\section`` lines.
    """
    kept: list[str] = []
    for line in text.splitlines():
        buffer: list[str] = []
        escaped = False
        for char in line:
            if escaped:
                buffer.append(char)
                escaped = False
            elif char == "\\":
                buffer.append(char)
                escaped = True
            elif char == "%":
                break
            else:
                buffer.append(char)
        kept.append("".join(buffer))
    return "\n".join(kept)


def _read_tex(path: Path) -> str:
    return strip_tex_comments(path.read_text(encoding="utf-8", errors="replace"))


#: LaTeX accent macros to the combining mark they apply. Applying the mark and
#: letting Unicode normalisation compose it is what keeps this table short: one
#: entry per accent rather than one per accent-letter pair.
ACCENT_MARKS = {
    "`": "\u0300",  # grave
    "'": "\u0301",  # acute
    "^": "\u0302",  # circumflex
    "~": "\u0303",  # tilde
    '"': "\u0308",  # diaeresis
    "H": "\u030b",  # Hungarian double acute -- Erd\H{o}s
    "c": "\u0327",  # cedilla
    "v": "\u030c",  # caron
    "u": "\u0306",  # breve
    "=": "\u0304",  # macron
    ".": "\u0307",  # dot above
    "r": "\u030a",  # ring above
    "k": "\u0328",  # ogonek
    "d": "\u0323",  # dot below
    "b": "\u0331",  # bar under
}

#: Formatting wrappers whose argument is the text. `\texorpdfstring` is handled
#: separately because it takes two arguments and the *second* is the plain form.
TEXT_WRAPPERS = frozenset(
    {
        "emph", "text", "textit", "textbf", "textrm", "textsf", "texttt", "textsc",
        "textnormal", "mathrm", "mathcal", "mathbf", "mathit", "mathsf", "operatorname",
        "lowercase", "uppercase", "mbox", "hbox",
    }
)

#: Standalone macros with an obvious textual meaning.
SYMBOL_MACROS = {
    "&": "&", "%": "%", "_": "_", "$": "$", "#": "#", "{": "{", "}": "}",
    "ldots": "…", "dots": "…", "textendash": "–", "textemdash": "—",
    "ss": "ß", "ae": "æ", "oe": "œ", "aa": "å", "o": "ø", "l": "ł", "i": "ı",
}

#: A control *word* (`\emph`, all letters) absorbs the whitespace after it; a
#: control *symbol* (`\%`, `\&`) does not, and eating that space turns
#: `50\% \& more` into `50%&more`.
_MACRO_RE = re.compile(r"\\(?:([a-zA-Z]+)\s*|(.))", re.DOTALL)


def _balanced_group(text: str, start: int) -> tuple[str, int] | None:
    """Contents of the brace group opening at ``start``, and the index past it."""
    depth, index = 1, start
    while index < len(text) and depth:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    return (text[start : index - 1], index) if not depth else None


def _strip_title_notes(raw: str) -> str:
    r"""Drop ``\thanks`` and ``\footnote`` groups, which are not part of a title."""
    for command in (r"\thanks", r"\footnote"):
        while (position := raw.find(command)) != -1:
            brace = raw.find("{", position)
            group = _balanced_group(raw, brace + 1) if brace != -1 else None
            if group is None:
                raw = raw[:position]
                break
            raw = raw[:position] + raw[group[1] :]
    return raw


def _argument(text: str, index: int) -> tuple[str, int] | None:
    """The macro argument at `index`, brace-delimited or a single character."""
    if index < len(text) and text[index] == "{":
        return _balanced_group(text, index + 1)
    if index < len(text):
        return text[index], index + 1
    return None


def latex_to_text(source: str) -> str:
    r"""Render a LaTeX fragment as readable text, leaving alone what it cannot.

    Titles reach task metadata, the agent's instruction and the dataset card,
    all of them read by people, so `Erd\H{o}s Problem 973` and
    `Type-\texorpdfstring{$B$}{B} Root Posets` should not survive as written.

    Deliberately conservative: a macro not in the tables passes through with its
    backslash intact. A half-right conversion that silently drops a symbol is
    worse than a title that visibly still holds LaTeX, because only the second
    kind gets noticed and fixed.
    """
    out: list[str] = []
    index = 0
    while index < len(source):
        char = source[index]

        if char == "$":  # math delimiters; the content is usually plain enough
            index += 1
            continue
        if char in "{}":
            index += 1
            continue
        if char != "\\":
            out.append(char)
            index += 1
            continue

        match = _MACRO_RE.match(source, index)
        if match is None:
            out.append(char)
            index += 1
            continue
        name, index = match.group(1) or match.group(2), match.end()

        if name == "texorpdfstring":
            # (TeX form, plain form) -- the second argument exists for this.
            first = _argument(source, index)
            second = _argument(source, first[1]) if first else None
            if second:
                out.append(latex_to_text(second[0]))
                index = second[1]
            continue
        if name in ACCENT_MARKS:
            argument = _argument(source, index)
            if argument:
                out.append(unicodedata.normalize("NFC", argument[0] + ACCENT_MARKS[name]))
                index = argument[1]
            continue
        if name in TEXT_WRAPPERS:
            argument = _argument(source, index)
            if argument:
                out.append(latex_to_text(argument[0]))
                index = argument[1]
            continue
        if name in SYMBOL_MACROS:
            out.append(SYMBOL_MACROS[name])
            continue

        # Unknown macro: keep it visible rather than guess.
        out.append("\\" + name)

    text = "".join(out)
    text = text.replace("---", "—").replace("--", "–")
    return re.sub(r"\s+", " ", text).strip()


def extract_title(text: str) -> str | None:
    r"""The manuscript's own title, brace-matched out of ``\title{...}``.

    A regex cannot do this alone. Titles in this corpus carry nested groups
    (``Erd\H{o}s Problem 973``) and an optional running-head argument, so
    matching to the first ``}`` truncates them. ``\\`` inside a title is a line
    break rather than an end marker, and treating it as one silently truncated
    four of the manuscripts here -- one to "Ferrers-Cell Formulas for
    Chapoton's q-Zeta Numerators:".

    The title reaches task metadata and the instruction the review agent reads,
    so a truncation would be visible in the collected data.
    """
    match = TITLE_RE.search(text)
    if not match:
        return None
    group = _balanced_group(text, match.end())
    if group is None:
        return None
    raw = _strip_title_notes(group[0]).replace("\\\\", " ")
    return latex_to_text(raw) or None


def title_from_graph(root: Path, tex_files: list[Path]) -> str | None:
    r"""The title, from whichever file in the document actually declares it.

    Papers built from a toplevel stub that ``\input``s the body keep ``\title``
    in the body file; searching only the toplevel returns nothing for them.
    """
    for path in tex_files:
        title = extract_title(_read_tex(path))
        if title:
            return title
    return None


def _resolve_input(root: Path, base: Path, raw: str) -> Path | None:
    name = raw.strip()
    for candidate in (base.parent / name, root / name):
        for path in (candidate, candidate.with_suffix(".tex")):
            if path.is_file() and path.suffix.lower() in TEX_SUFFIXES:
                return path
    return None


def tex_graph(root: Path, main: str) -> list[Path]:
    """Toplevel file plus everything it \\input/\\include, depth first."""
    ordered: list[Path] = []
    seen: set[Path] = set()
    stack = [root / main]
    while stack:
        current = stack.pop(0)
        resolved = current.resolve()
        if resolved in seen or not current.is_file():
            continue
        seen.add(resolved)
        ordered.append(current)
        text = _read_tex(current)
        children = [
            child
            for raw in INPUT_RE.findall(text)
            if (child := _resolve_input(root, current, raw)) is not None
        ]
        stack = children + stack
    return ordered


def _split_keys(raw: str) -> list[str]:
    return [key.strip() for key in raw.split(",") if key.strip()]


def build_map(root: Path, label: str, main: str) -> PaperMap:
    tex_files = tex_graph(root, main)
    paper_map = PaperMap(label=label, main_tex=main)
    paper_map.title = title_from_graph(root, tex_files)
    paper_map.tex_files = [p.relative_to(root).as_posix() for p in tex_files]

    cited: list[str] = []
    for path in tex_files:
        relative = path.relative_to(root).as_posix()
        text = _read_tex(path)
        lines = text.splitlines()
        paper_map.total_tex_lines += len(lines)
        for number, line in enumerate(lines, start=1):
            for level, title in SECTION_RE.findall(line):
                paper_map.sections.append(
                    Section(level=level, title=title.strip(), file=relative, line=number)
                )
            for kind in THEOREM_RE.findall(line):
                nearby = "\n".join(lines[number - 1 : number + 2])
                label_match = LABEL_RE.search(nearby)
                paper_map.theorems.append(
                    TheoremBlock(
                        kind=kind,
                        label=label_match.group(1) if label_match else None,
                        file=relative,
                        line=number,
                    )
                )
        for raw in CITE_RE.findall(text):
            cited.extend(_split_keys(raw))

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()
        if suffix in BIB_SUFFIXES:
            paper_map.bib_files.append(relative)
        elif suffix in FIGURE_SUFFIXES:
            paper_map.figure_files.append(relative)

    defined: set[str] = set()
    for relative in paper_map.bib_files:
        if relative.endswith(".bib"):
            text = (root / relative).read_text(encoding="utf-8", errors="replace")
            defined.update(BIBENTRY_RE.findall(text))

    paper_map.cited_keys = sorted(set(cited))
    paper_map.defined_bib_keys = sorted(defined)
    paper_map.undefined_citations = sorted(set(cited) - defined) if defined else []
    paper_map.uncited_bib_keys = sorted(defined - set(cited)) if defined else []
    return paper_map


def ingest(version: PaperVersion, build_root: Path) -> IngestResult:
    """Stage one paper version's publishable material and map its structure."""
    root = build_root / version.label / "paper"
    _materialise(version, root)
    _flatten_single_dir(root)
    excluded = _strip_private(root, version)
    sanitised = strip_bib_preamble(root)
    stage_sibling_pdf(root, version)

    main = find_main_tex(root)
    paper_map = build_map(root, version.label, main)

    source_sha = (
        sha256_file(version.source)
        if version.source.is_file()
        else sha256_tree(version.source)
    )
    (build_root / version.label / "paper_map.json").write_text(
        paper_map.to_json(), encoding="utf-8"
    )
    return IngestResult(
        label=version.label,
        root=root,
        main_tex=main,
        paper_map=paper_map,
        excluded=tuple(excluded),
        sanitised=tuple(sanitised),
        source_sha256=source_sha,
    )
