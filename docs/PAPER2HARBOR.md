# paper2harbor

Turn a paper into a standard [Harbor](https://www.harborframework.com/docs/tasks)
task for **collecting** peer reviews: the manuscript is already written, a
review agent reads it and writes `review.md`, and the pair is archived for
human experts to assess later.

- **Input** — a paper's TeX source (directory, `.tar.gz`, `.zip`, or a bare
  `main.tex`) plus an optional brief.
- **Output** — a Harbor task (`schema_version = "1.4"`) that `harbor run`
  executes directly.
- **The task does not judge reviews.** The verifier checks only that one was
  submitted. Assessing quality is the human experts' job, on the collected
  data — putting an LLM judge here would mean a model deciding what counts as a
  good review, which is exactly the judgement the experts are for.

This replaces the ad-hoc baseline harness in `tools/` (see
[`OSP_BATCH.md`](OSP_BATCH.md)).

## Scaling is the requirement

The corpus is 17 papers / 21 reviewable versions today and may be a hundred.
Nothing hardcodes the corpus: directory shapes are *recognised*, tasks are
*enumerated*, and a new paper dropped into `papers/` becomes a task with no
code change. A `specs/<label>.yaml` can override the title, venue, domain, or
carry a brief for the agent, but is never required — a paper with no spec
produces a working task with derived metadata.

Each version of a paper is an **independent paper** (`erdos973--v1` and
`--v2` are separate tasks), because a version fixes the previous version's
problems and a review of one is not a review of the other.

## Task layout

```
tasks/paper-review-exam/<label>/
├── task.toml
├── instruction.md
├── environment/
│   ├── Dockerfile          # TeX Live subset + poppler-utils
│   └── paper/              # manuscript only
├── solution/solve.sh       # placeholder-review oracle
└── tests/                  # separate verifier: submission contract only
    ├── Dockerfile
    ├── test.sh
    ├── check_submission.py
    └── contract.json
```

## Network

`task.toml` declares `network_mode = "no-network"`, on purpose. Verified
against harbor 0.20.0 source (`trial/network_policy.py:merge_extra_allowlists`):
`JobConfig` exposes only `extra_allowed_hosts` (additive), but passing
`--allow-agent-host` at run time promotes any non-public policy to `allowlist`.
So a task declared closed can always be run with literature access — while a
task declared open can never be run closed. Declaring the closed baseline keeps
both runs available from one task.

**An API-backed agent needs its own provider host allowed, or it cannot run at
all.** `no-network` blocks the agent's LLM API just as thoroughly as it blocks
arXiv, so every real run carries at least one allowlist entry:

```bash
harbor run -p tasks/paper-review-exam/<label> -a codex \
  --agent-env "OPENAI_API_KEY=$OPENAI_API_KEY" \
  --agent-env "OPENAI_BASE_URL=$OPENAI_BASE_URL" \
  --allow-agent-host api.apexin.ai \
  --allow-agent-host arxiv.org \
  --allow-agent-host api.semanticscholar.org \
  --allow-agent-host api.openalex.org
```

So there is no closed-book mode for a hosted agent — only *no literature
hosts*. Drop the last three lines for that; keep the provider host regardless.
Credentials come from `paperbench-harbor/.env`; `--agent-env` puts them in the
agent container without baking them into an image.

⚠️ **The switch lives in the run invocation, not in the task.** When collecting
data, record whether each run had literature access alongside the review — an
expert reading a review that checked no citations needs to know whether the
agent could have.

## What is private

A review written by an agent that could read the manuscript's writing-time
defect trail, or its own paper's next revision, is worthless as data — and
nothing downstream can tell, because a contaminated review looks exactly like
a very good one. So contamination has to be prevented at build time; it cannot
be detected afterwards.

`pre-harbor audit` checks, reading what was written to disk rather than
trusting the code that wrote it:

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

**arXiv hosts the later versions.** Seven of the 21 tasks are versions of a
multi-version paper, and those papers are public — `erdos973` is
[arXiv:2608.02043](https://arxiv.org/abs/2608.02043) with v1, v2 and v3 all
retrievable. An agent reviewing v1 with `arxiv.org` allowed can fetch v2 and
read exactly what the authors fixed. No task-level exclusion helps: the answer
is on the public internet under the paper's own name.

The choices are to run version-set papers without literature hosts, or to run
them open-book and record that the risk applies so an expert reading the review
knows to discount a suspiciously precise finding. Either is defensible;
silently doing the second while believing the first is not.

**The source corpus is published too.** The Hugging Face dataset also carries
`papers/`, including the writing-time trail for the `solution-*` manuscripts.
`huggingface.co` is not in the suggested allowlist and a run cannot reach it —
so do not add it.

## CLI

```
pre-harbor list                 every version and its metadata status
pre-harbor doctor               what this machine can and cannot do
pre-harbor init-spec <label>    write a starter spec (optional overrides)
pre-harbor stage <label>        unpack publishable material, write paper_map.json
pre-harbor emit [labels...]     render tasks; audits each, deletes on leak
pre-harbor audit                re-audit tasks on disk
pre-harbor verify <label>       harbor run, or the command for a box with Docker
pre-harbor publish --repo O/N   push to Hugging Face; dry run without --execute
```

## Publishing

```bash
pre-harbor publish --repo Jack-Jieke-Wu/Paper-Reviewing-Exam            # dry run
pre-harbor publish --repo Jack-Jieke-Wu/Paper-Reviewing-Exam --execute
```

The audit runs again at publish time rather than trusting that `emit` ran it,
because the tasks on disk may have been touched since, and one contaminated
task in a published dataset is worse than no dataset — the reviews collected
against it look exactly like the clean ones. Upload is opt-in for the same
reason a public dataset is hard to unpublish: it can be cached or mirrored
between the push and any later deletion.

Harbor then reads the published dataset directly, with no `registry.json`
needed — it scans the named subdirectory of the git tree for `task.toml`
(verified against harbor 0.20.0 `registry/client/git_repo.py`):

```bash
harbor run --repo https://huggingface.co/datasets/Jack-Jieke-Wu/Paper-Reviewing-Exam/tree/main/paper-review-exam \
  -a codex
```

## Workflow

`/paper2task <label>` in opencode runs stage → inspect → emit → audit and
reports the box commands. `/verify-task <label>` runs the oracle and the floor.

## Laptop and Linux box

Ingest and emit run anywhere. Building images and running `harbor run` need
Docker, and `pre-harbor doctor` says whether this machine has it; commands that
need it and cannot find it print the exact invocation for the box and exit
non-zero rather than substituting a weaker check.

**`harbor run` happens on the Ubuntu box, driven by codex.** The checkout is at
`~/dev/paper-review` (ssh host `ubuntu-box`), which has docker, harbor, codex
and uv. Driving it over ssh works for the deterministic setup, but a failed
Harbor run needs someone to read the build log and the verifier output and
decide what broke — which is what the agent is there for.

A task is proven when the oracle scores 1.0 and `-a nop` scores 0.0. Until
both hold it is unproven, and emitting is never the same as verifying.
