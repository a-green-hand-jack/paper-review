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

```bash
harbor run -p tasks/paper-review-exam/<label> -a opencode \
  --allow-agent-host arxiv.org \
  --allow-agent-host api.semanticscholar.org \
  --allow-agent-host api.openalex.org
```

⚠️ **The switch lives in the run invocation, not in the task.** When collecting
data, record whether each run had network access alongside the review — an
expert reading a review that never checked a citation needs to know whether the
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

## CLI

```
pre-harbor list                 every version and its metadata status
pre-harbor doctor               what this machine can and cannot do
pre-harbor init-spec <label>    write a starter spec (optional overrides)
pre-harbor stage <label>        unpack publishable material, write paper_map.json
pre-harbor emit [labels...]     render tasks; audits each, deletes on leak
pre-harbor audit                re-audit tasks on disk
pre-harbor verify <label>       harbor run, or the command for a box with Docker
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
