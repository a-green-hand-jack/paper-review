# paper2harbor

Turn a paper into a standard [Harbor](https://www.harborframework.com/docs/tasks)
task for **collecting** peer reviews: the manuscript is already written, a
review agent reads it and writes `review.md`, and the pair is archived for
human experts to assess later.

- **Input** — a paper's TeX source (directory, `.tar.gz`, `.zip`, or a bare
  `.tex`) plus an optional brief.
- **Output** — a Harbor task (`schema_version = "1.4"`) that `harbor run`
  executes directly.
- **The task does not judge reviews.** The verifier checks only that one was
  submitted. Assessing quality is the human experts' job, on the collected
  data — putting an LLM judge here would mean a model deciding what counts as a
  good review, which is exactly the judgement the experts are for.

Corpus today: **27 papers, 31 reviewable versions**, all published at
[Paper-Reviewing-Exam](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam).
Run a complete model condition with
[`pre-harbor benchmark`](BENCHMARK.md) and archive every trail to
[Paper-Reviewing-Exam-Trails](https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails).

## Storage and execution

The durable, runnable distribution is the Hugging Face dataset under
`paper-review-exam/<task-id>/`. Harbor can run that published snapshot directly
with `--repo`; it is the right choice for reproducing a released task.

`build/` and `tasks/paper-review-exam/<task-id>/` are local, gitignored build
products. `pre-harbor emit` recreates them from `papers/`, so use them when
iterating on the task pipeline. Each generated task embeds only its sanitized
manuscript material under `environment/paper`; `pre-harbor publish` uploads the
generated task tree, not the complete local `papers/` corpus. The Hugging Face
repository may separately carry an archival `papers/` tree, but that is outside
the runnable `paper-review-exam/` task subtree.

Run Harbor only from a Docker-capable Linux checkout. First confirm the host,
then build or run the intended task:

```bash
cd <paper-review-checkout>
uv run pre-harbor doctor
uv run pre-harbor emit erdos973--v1
uv run pre-harbor verify erdos973--v1 --agent oracle
```

Use `pre-harbor verify` for local generated tasks. To run the published
snapshot without generating it locally, use the `harbor run --repo` command in
[Publish](#publish).

---

## How to use it

### Add a paper

Drop it in `papers/<slug>/` in any of the shapes below and it becomes a task.
No code change, no registration step.

| shape | example |
|---|---|
| `<slug>/vN-source.tar.gz` + `vN.pdf` | `erdos973` (v1/v2/v3) |
| `<slug>/source.{tar.gz,zip}` + `<slug>.pdf` | `superconductivity_uniform_electron_gas` |
| `<slug>/main.tex` + `<slug>.pdf` | `hydrodynamics_of_large_language_models` |
| `<slug>/paper/main.tex` + assets | `solution-p8610`, `de_novo_nanobody_discovery` |

The toplevel TeX file is found by reading arXiv's `00README.json` when present,
otherwise by scanning for `\documentclass` + `\begin{document}` — so it does not
have to be called `main.tex` (`superconductivity_uniform_electron_gas` uses
`ms.tex`). Each version of a paper is an **independent task**: a version fixes
the previous one's problems, so a review of one is not a review of the other.

For source bundles, a compiled manuscript PDF is recognized only when it is
named for the detected toplevel TeX file, or is named `main.pdf`, `paper.pdf`,
or `manuscript.pdf`. An explicitly declared PDF takes priority over those names:

```tex
% paper-review-harbor: manuscript-pdf=NAME.pdf
```

Use that exact declaration for any other noncanonical bundled manuscript PDF.
Arbitrary root-level PDFs are treated as assets, not guessed to be manuscripts.

Optionally add `specs/<slug>.yaml` to override derived metadata or pass the
agent a brief:

```yaml
label: erdos973--v1
venue: arxiv
domain: mathematics          # otherwise "unknown"
paper_kind: proof
notes: |                     # shown to the review agent verbatim
  Focus on whether the quantitative bound is established, not just the
  qualitative one.
```

`pre-harbor init-spec <label>` writes a starter. A paper with no spec still
produces a working task.

### Build the tasks

```bash
pre-harbor list                  # every version, and whether it has a spec
pre-harbor stage <label>         # unpack; reports what was withheld
pre-harbor show-map <label>      # check the toplevel file and title were found
pre-harbor emit                  # render all tasks; audits each one
pre-harbor audit                 # re-audit what is on disk
```

`emit` audits every task as it renders it and **deletes any task that leaks**,
failing the command. If that happens, read the violations — do not work around
them.

`stage` prints `excluded=` and `sanitised=` lists saying what was kept out of
the agent environment. Empty lists for a `solution-*` paper mean something is
wrong: those all ship a writing-time trail.

### Prove a task works

On a machine with Docker (`pre-harbor doctor` says whether this is one):

```bash
pre-harbor verify <label> --agent oracle    # must score 1.0
pre-harbor verify <label> --agent nop       # must score 0.0
```

Both must hold. Until then the task is unproven, and emitting is never the same
as verifying. The oracle writes a placeholder review, so a 1.0 proves the
submission path and the checker are wired up — it says nothing about review
quality, and is not a model of one.

### Collect a review

`pre-harbor verify` also builds the real invocation, which is long enough that
hand-writing it is a mistake:

```bash
pre-harbor verify <label> \
  --agent codex --model openai/gpt-5.6-sol \
  --network scholarly --api-host api.apexin.ai \
  --agent-env OPENAI_API_KEY --agent-env OPENAI_BASE_URL
```

`--agent-env` takes variable *names*. `pre-harbor` passes Harbor v0.20.0 the
literal template `NAME=${NAME}`; Harbor resolves it from its own environment.
The printed command uses `'NAME=${NAME}'`, so a shell does not expand a secret
before Harbor receives the template. Export the required credentials from the
host's protected credential store before running the command; never place them
in this repository, a task, or shell history.

Off this machine, the same command prints what to run on the box and exits
non-zero rather than pretending. Measured on `erdos973--v1`: codex produced a
983-word referee report in 11m17s, reward 1.0.

Collected per run, in the job's `artifacts/`:

```
workspace/submission/review.md      the review
logs/agent/trajectory.json          what the agent did
logs/agent/sessions/...jsonl        the agent's own session record
```

### Publish

```bash
pre-harbor publish --repo Jack-Jieke-Wu/Paper-Reviewing-Exam            # dry run
pre-harbor publish --repo Jack-Jieke-Wu/Paper-Reviewing-Exam --execute
```

Pass an explicit branch, tag, or commit with `--revision`. The upload command
uses that revision, and the generated task contains `material-manifest.json`
with a per-file size, SHA-256, LFS status, and paper tree digest. Formal runs
should record the resolved HF commit SHA and use that SHA in `harbor run --repo`.
For a formal release, create a named tag after resolving that SHA:

```bash
pre-harbor publish --repo Jack-Jieke-Wu/Paper-Reviewing-Exam \
  --revision issue-19-materials-v1 --release-tag issue-19-materials-v1 --execute
```

`publish` prints the immutable SHA returned by Hugging Face. That SHA, rather
than the mutable branch or tag name, is the SHA you pass as `--task-revision`
when archiving a trail (see Benchmark above).

The audit runs again at publish time rather than trusting that `emit` ran it,
because the tasks on disk may have been touched since, and one contaminated task
in a published dataset is worse than no dataset — the reviews collected against
it look exactly like the clean ones. Upload is opt-in for the same reason a
public dataset is hard to unpublish: it can be cached or mirrored between the
push and any later deletion.

Harbor then reads the published dataset directly, with no `registry.json`
needed — it scans the named subdirectory of the git tree for `task.toml`
(verified against harbor 0.20.0 `registry/client/git_repo.py`):

```bash
harbor run --repo https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam/tree/main/paper-review-exam \
  -a oracle -y --include-task-name "erdos973--v1"
```

### Benchmark

The benchmark is **agent-agnostic**: it provides the tasks and the trail
archive, and a paper-review agent supports it by running inside Harbor and
writing `/workspace/submission/review.md`. Run any Harbor agent against the
pinned Exam snapshot, then archive each trial with `pre-harbor archive-trail`:

```bash
harbor run --repo https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam/tree/<exam-sha>/paper-review-exam \
  -a <agent-id> --include-task-name "erdos973--v1"

pre-harbor archive-trail jobs/<agent>/<job>/<trial-dir> \
  --task-id erdos973--v1 \
  --task-revision <40-character-exam-sha> \
  --trail-repo Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails \
  --execute
```

The task snapshot is pinned by the immutable SHA that `pre-harbor publish`
prints; secrets are exported from the host and only their variable *names* are
ever recorded. See [`BENCHMARK.md`](BENCHMARK.md) for the full procedure:
prerequisites, the six-task Issue #19 set, allowlist rules, trail-manifest
schema, failure handling, result interpretation, and how to compare agent
conditions without fooling yourself with single-run noise.

### In opencode

`/paper2task <label>` runs stage → inspect → emit → audit and reports the box
commands. `/verify-task <label>` runs the oracle and the floor.

---

## Network: the part that surprises people

`task.toml` declares `network_mode = "no-network"`, on purpose. Verified against
harbor 0.20.0 (`trial/network_policy.py:merge_extra_allowlists`): `JobConfig`
exposes only `extra_allowed_hosts` (additive), but passing `--allow-agent-host`
at run time promotes any non-public policy to `allowlist`. So a task declared
closed can always be run with literature access, while a task declared open can
never be run closed. Declaring the closed baseline keeps both runs available
from one task.

Three things follow, each learned from a failed run:

**A hosted agent cannot run with nothing allowed.** Harbor installs the agent at
run time rather than from the image, and the install fetches a runtime — the
codex adapter apt-gets `curl ripgrep`, pipes nvm's installer from
raw.githubusercontent.com, pulls node from nodejs.org, then npm-installs itself.
Under `no-network` the trial dies in setup with `NonZeroAgentExitCodeError`
before the agent ever sees the paper. So there is no closed-book mode for a
hosted agent, only *no literature hosts* — `--network agent` versus
`--network scholarly`. `pre-harbor verify` refuses `--network none` for anything
but `oracle` and `nop` rather than letting a container build discover it.

**Those hosts are needed at environment start, not only during the agent
phase.** Every entry goes to `--allow-environment-host` as well as
`--allow-agent-host`; with only the latter the install still fails. `_host_args`
does both.

**Most real agents also need `-m`.** Without it the codex adapter raises
`Model name is required` after a successful install.

**What `--network scholarly` opens.** In `pre-harbor verify` the scholarly
preset (`SCHOLARLY_HOSTS` in `src/paper_review_harbor/emit.py`) allows the
general scholarly sources — arXiv, Semantic Scholar, OpenAlex, Crossref, DOI —
plus the Bohrium `bohr` CLI platform hosts (`bohr.dp.tech`,
`bohrium.dp.tech`, `*.dp.tech`, `*.bohrium.com`) and Google Scholar
(`scholar.google.com`), so agents that retrieve through `bohr`/Google Scholar
are not blocked by the benchmark. `--network agent` leaves all of these out.

⚠️ **The switch lives in the run invocation, not in the task.** When collecting
data, record whether each run had literature access alongside the review — an
expert reading a review that checked no citations needs to know whether the
agent could have.

## What is private

A review written by an agent that could read the manuscript's writing-time
defect trail, or its own paper's next revision, is worthless as data — and
nothing downstream can tell, because a contaminated review looks exactly like a
very good one. So contamination has to be prevented at build time; it cannot be
detected afterwards.

`pre-harbor audit` checks, reading what was written to disk rather than trusting
the code that wrote it:

| private | why |
|---|---|
| `solution-*/paper/review/` | the writing-time internal review; it names the defects |
| `solution-*/paper/plan.md` | the writing plan |
| a later version of the paper | v2 is v1 with its problems fixed |

`unverified.bib` is deliberately **not** private. Every manuscript that ships
one builds against it (`\bibliography{references,unverified}`), so withholding
it breaks compilation and manufactures undefined-citation defects the authors
never committed. Its header comment — which says the entries need checking
before submission, and would hand a citation finding to the agent for free — is
stripped instead. The entries stay, blank fields included.

### Two paths a task cannot close

**arXiv hosts the later versions.** Seven of the 27 tasks are versions of a
multi-version paper, and those papers are public — `erdos973` is
[arXiv:2608.02043](https://arxiv.org/abs/2608.02043) with v1, v2 and v3 all
retrievable. An agent reviewing v1 with `arxiv.org` allowed can fetch v2 and
read exactly what the authors fixed. No task-level exclusion helps: the answer
is on the public internet under the paper's own name.

The choices are to run version-set papers with `--network agent` (no literature
hosts), or to run them open-book and record that the risk applies so an expert
reading the review knows to discount a suspiciously precise finding. Either is
defensible; silently doing the second while believing the first is not.

**The source corpus is published too.** The Hugging Face dataset also carries
`papers/`, including the writing-time trail for the `solution-*` manuscripts.
`huggingface.co` is not in any suggested host set and a run cannot reach it — so
do not add it.

## Task layout

```
tasks/paper-review-exam/<label>/
├── task.toml               metadata, timeouts, no-network baseline
├── instruction.md          what the agent is asked to do
├── environment/
│   ├── Dockerfile          TeX Live subset, poppler-utils, and the agent
│   │                       toolchain (curl, ripgrep, node, npm)
│   └── paper/              the manuscript, and nothing else
├── solution/solve.sh       placeholder-review oracle
└── tests/                  separate verifier: submission contract only
    ├── Dockerfile
    ├── test.sh
    ├── check_submission.py
    └── contract.json
```

Two notes on the environment image. The agent toolchain is pre-installed because
every adapter's install step begins by apt-getting its own basics, and the apt
package lists are deliberately **kept** rather than deleted — with the lists
present, an adapter running `apt-get install -y curl ripgrep` succeeds offline
because apt reports them already current. Deleting them, the usual habit, makes
the same command die with `Unable to locate package curl`.

The verifier runs in its own container (`environment_mode = "separate"`), which
also means Harbor does not upload `tests/` at run time — the verifier image owns
`/tests` itself via `COPY . /tests/`.

## Reward

`reward.json` carries one primary metric and several descriptive ones. Harbor
keeps every key as a named metric and reports `reward` as the score.

| key | meaning |
|---|---|
| `reward` | 1.0 when `review.md` exists with ≥200 characters of content, else 0.0 |
| `submitted` | 1.0 when anything was written at all |
| `review_chars` / `_words` / `_lines` / `_headings` | shape of the review |
| `mentions_location` | heuristic: does the review point at the manuscript, or only summarise it |

The descriptive metrics are for triage — spotting a run that technically
submitted but produced three lines — not for ranking agents. Full detail lands
in `/logs/verifier/submission_report.json`.

## CLI

```
pre-harbor list                 every version and its metadata status
pre-harbor doctor               what this machine can and cannot do
pre-harbor init-spec <label>    write a starter spec (optional overrides)
pre-harbor stage [labels...]    unpack publishable material, write paper_map.json
pre-harbor show-map <label>     print a staged paper's structure
pre-harbor emit [labels...]     render tasks; audits each, deletes on leak
pre-harbor audit                re-audit tasks on disk
pre-harbor verify <label>       harbor run, or the command for a box with Docker
pre-harbor publish --repo O/N   push to Hugging Face; dry run without --execute
pre-harbor benchmark            run/archive one six-task Issue #19 model condition
pre-harbor archive-trail        archive one Harbor run and optionally upload its trail
```

## Laptop and Linux box

Ingest, emit, audit and publish run anywhere. Building images and running
`harbor run` need Docker, and `pre-harbor doctor` says whether this machine has
it; commands that need it and cannot find it print the exact invocation for the
box and exit non-zero rather than substituting a weaker check.

**`harbor run` happens on a Docker-capable Linux execution host, driven by
Codex.** Use the checkout path verified on that host rather than assuming a
machine-specific location. Driving it over SSH works for deterministic setup,
but a failed Harbor run needs someone to read the build log and the verifier
output and decide what
broke — which is what the agent is there for.
