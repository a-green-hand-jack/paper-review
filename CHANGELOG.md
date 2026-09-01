# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow Semantic Versioning.

## [v0.1.0] - 2026-09-01

First release: everything accumulated on `main` since the initial commit.

### Added

- **paper-to-Harbor pipeline** (`pre-harbor`): turn a paper's TeX source into a
  standard Harbor task (`schema_version = "1.4"`) that `harbor run` executes
  directly, for collecting peer reviews rather than scoring them.
  - `stage` — unpack publishable material and write `paper_map.json`; reports
    `excluded=` / `sanitised=` lists.
  - `show-map` — print a staged paper's structure (toplevel TeX, title,
    sections, theorems).
  - `emit` — render tasks and audit each one; any leaking task is deleted and
    the command fails (`src/paper_review_harbor/cli.py:176`).
  - `audit` — re-audit tasks already on disk, reading what was written rather
    than trusting the emitter (`src/paper_review_harbor/cli.py:228`).
  - `doctor` — report what the current machine can and cannot do;
    Docker-dependent commands print the exact Linux-box invocation instead of
    degrading into weaker checks.
  - `verify <label>` — build and run the Harbor command, or print it for a
    machine with Docker; network presets `none` / `agent` / `scholarly`
    (`src/paper_review_harbor/cli.py:331`).
  - `publish --repo O/N` — dry-run Hugging Face upload by default, re-audits
    before uploading, propagates the dataset card
    (`src/paper_review_harbor/publish.py`).
- **Corpus discovery** (`src/paper_review_harbor/corpus.py`): any TeX source
  shape under `papers/<slug>/` becomes a task with no registration step;
  archive, directory, and bare-`.tex` shapes supported; `00README.json` read
  when present; explicit manuscript-PDF declaration
  (`% paper-review-harbor: manuscript-pdf=NAME.pdf`).
- **Versioned papers as independent tasks**: each `vN` of a multi-version paper
  is its own task; writing-time review trails and later revisions are treated
  as private and withheld from the agent environment.
- **Hugging Face publishing** of the task tree to
  `Jack-Jieke-Wu/Paper-Reviewing-Exam`, runnable directly by
  `harbor run --repo` without a `registry.json`.
- **paper-run v0.5.0 review agent integration**
  (`src/paper_review_harbor/agents/paper_run.py`,
  `src/paper_review_harbor/agents/paper_run_core.py`): pinned source build of
  the OpenCode-native `review-report` plan, exports `.paper-run/review-findings.md`
  as `/workspace/submission/review.md`, checks the fixed plan contains no
  `revision`, verifies required report headings, and archives `.paper-run/`
  state under `/logs/agent/paper-run/`.
- **Task templates** (`src/paper_review_harbor/templates/`): `task.toml`,
  `instruction.md`, environment and tests Dockerfiles, placeholder-review
  oracle `solve.sh`, independent `check_submission.py` verifier with
  `paper-review-paper-run-v1` schema support.
- **leak-proof build-time guards**: `unverified.bib` entries kept (with header
  comment stripped) so manuscripts compile, while writing-time trails and
  later versions never reach the agent.
- **opencode commands**: `/paper2task <label>` (stage → inspect → emit →
  audit → report box commands) and `/verify-task <label>` (oracle + floor)
  under `.opencode/command/`.
- **Retiring OSP baseline harness** still on disk for reference:
  `tools/osp_batch.py` (parallel per-paper isolated runs) and
  `tools/osp_compare.py` (multi-version ordering comparison) — superseded by
  the Harbor benchmark, to be deleted after a full round.
- **Corpus**: grew to **27 papers / 31 reviewable versions**, including the
  `erdos973` v1/v2/v3 version set, `solution-*` writing-time papers, and four
  manuscripts reviewed by 么志远 (`balducci_lr17494`, `chaduteau_bw14519`,
  `singh_lh18054`, `zhao_2026_0489`, added 2026-09-01).

### Changed

- `docs/PAPER2HARBOR.md` is the project readme (referenced from
  `pyproject.toml`) and documents the full user story: add a paper, build,
  prove, collect, publish, network semantics, privacy boundary, task layout,
  and reward metrics.
- Task hygiene: `writing_resources` moved out of `papers/` so every corpus
  directory is a paper; `figs/` excluded from discovery; corpus shapes
  normalized; discovery asserts content rather than counts.
- `harbor-style` merge: compiled manuscript PDFs shipped with tasks, LaTeX
  titles rendered as text, duplicate top-level PDFs dropped, task storage
  documented.
- Design drift removed: domain-adaptive branching, OSP fork workflow, and
  artifact contracts were consolidated into the Harbor benchmark instead of
  the retiring `tools/` harness; `osp_version_diff.py` removed (review quality
  is a judgement task, not a diff).
- Secrets hygiene: `docs/PAPER2HARBOR.md` documents that credentials are
  exported from a protected store and passed as `NAME=${NAME}` templates to
  Harbor; nothing secret is written into the repo, tasks, or shell history.
- Review-trail Hugging Face dataset renamed from `Jack-Jieke-Wu/osp-trails`
  to `Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails`; all docs updated and the
  three-way relationship (GitHub source repo, runnable `Paper-Reviewing-Exam`
  task snapshot, gated `Paper-Reviewing-Exam-Trails` trail archive) is
  documented in `README.md`.

### Fixed

- TOML escaping so LaTeX titles no longer break `task.toml`
  (`4e0c325`).
- paper-run v0.5.0 quirks: no tarball/checksum release assets → pinned source
  build; stale `src/version.ts` → validate tag commit and `package.json`
  version instead; trailing-newline mismatch in `review-source.json` compared
  against execa-stripped `git show` output (`9a2d671`, `f0350f1`,
  `1f27a13` … `0852a89`).
- Missing `harbor run` prerequisites on the laptop now exit non-zero with the
  exact box command instead of pretending to verify.
- `.gitignore` updated to keep `.brain/`, `.omc/`, `.open-scholar-peer/`,
  build products (`build/`, `tasks/`), and OS junk (`__MACOSX/`,
  `.DS_Store`) out of the repository.