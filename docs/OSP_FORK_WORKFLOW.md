# Open ScholarPeer Fork Workflow

This project uses a local Open ScholarPeer fork as the source of any OSP
changes. The installed files under `paper-review/.opencode/` are generated
artifacts, not the place to maintain changes.

## Repositories

The current local layout is:

```text
/Users/jieke/orca/projects/open-scholar-peer   # OSP fork
/Users/jieke/orca/projects/paper-review        # benchmark project
```

The fork is:

```text
https://github.com/a-green-hand-jack/open-scholar-peer
```

Its remotes must remain separated:

```text
origin   git@github.com:a-green-hand-jack/open-scholar-peer.git
upstream git@github.com:amirkiarafiei/open-scholar-peer.git
```

The fork stores OSP source and development history. This project stores the
paper corpus, project-local runtime state, and review trails.

## Source And Generated Files

For commands, skills, rules, and defaults, edit only:

```text
/Users/jieke/orca/projects/open-scholar-peer/extensions/_shared/
```

The MCP source and synchronization scripts are also maintained in the fork:

```text
/Users/jieke/orca/projects/open-scholar-peer/mcp-server/
/Users/jieke/orca/projects/open-scholar-peer/scripts/
```

Do not maintain changes directly in these generated or project-local paths:

```text
/Users/jieke/orca/projects/open-scholar-peer/extensions/.opencode/
/Users/jieke/orca/projects/paper-review/.opencode/
/Users/jieke/orca/projects/paper-review/.brain/
/Users/jieke/orca/projects/paper-review/.open-scholar-peer/
```

`extensions/.opencode/` is regenerated from `_shared/` by
`scripts/sync_adapters.py`. The target project's `.opencode/` is then populated
by the OpenCode installer.

## Development Loop

From the fork:

```bash
cd /Users/jieke/orca/projects/open-scholar-peer
python3 scripts/sync_adapters.py
python3 scripts/sync_adapters.py --check
python3 scripts/test_parity.py
bash scripts/test_install.sh
```

Only after these checks pass should the fork be installed into the benchmark
project:

```bash
cd /Users/jieke/orca/projects/paper-review
bash /Users/jieke/orca/projects/open-scholar-peer/scripts/install_opencode.sh
```

The installer preserves the existing `.brain/` data, refreshes generated
OpenCode files, and initializes or reuses the project-local MCP runtime. It
prints the command needed to wire the OSP MCP server into OpenCode; that
configuration is intentionally not committed to this repository.

## Benchmark Verification

Preview the current corpus (17 papers, 22 version runs) without making model
calls:

```bash
cd /Users/jieke/orca/projects/paper-review
python3 tools/osp_batch.py --venue arxiv --all
```

The corpus is: the 15 named papers, `erdos973` v1/v2/v3,
`lieb_schultz_mattis_charge_transport` v1/v2, and
`chapoton_q_zeta_numerators` v1/v2. Every PDF under `papers/` that is not
inside `figures/` and does not begin with `fig-` is one task; each version
pair lives in a directory of `v*.pdf` files for version comparison.

The version-set papers are also mirrored in the public Hugging Face dataset
`Jack-Jieke-Wu/osp-benchmark` (same `papers/` layout). Review trails are
archived separately in the private `Jack-Jieke-Wu/osp-trails`.

When the version PDFs and completed local trails are available, run the
version comparison against existing trails without rerunning reviews. The
classic three-version form:

```bash
cd /Users/jieke/orca/projects/paper-review
python3 tools/osp_compare.py \
  --v1 papers/erdos973/v1.pdf \
  --v2 papers/erdos973/v2.pdf \
  --v3 papers/erdos973/v3.pdf \
  --venue arxiv \
  --llm openai/gpt-5.6-sol \
  --variant medium \
  --harness opencode \
  --trail-repo Jack-Jieke-Wu/osp-trails \
  --reuse
```

The generic two-or-more-version form, which auto-discovers `v*.pdf` under a
corpus directory:

```bash
cd /Users/jieke/orca/projects/paper-review
python3 tools/osp_compare.py \
  --paper-dir papers/lieb_schultz_mattis_charge_transport \
  --expected-order v1,v2 \
  --venue arxiv \
  --llm openai/gpt-5.6-sol \
  --variant medium \
  --harness opencode \
  --trail-repo Jack-Jieke-Wu/osp-trails \
  --reuse
```

`--reuse` is local-only. It requires the version PDFs plus a successful local
trail for each version containing `brain/review/final_review.md`. The
`--trail-repo` option does not download remote trails. Without those
prerequisites, omit `--reuse` and run the comparison normally, or use the
archived Hugging Face report as the baseline.

Every executed run receives a new timestamped trail. The manifest records the
paper hash, model configuration, command, timestamps, status, and trail
repository. A local trail is uploaded only when `--upload` is explicitly
requested; private trails must not be committed to the public GitHub
repository. The named Hugging Face dataset must already be private because
Hugging Face's `--private` option only affects creation of a new repository.
For `osp_batch.py`, archival requires both `--trail-repo` and `--upload`; a
non-reuse `osp_compare.py` run uploads the individual version trails and the
comparison report when `--trail-repo` is supplied. Each manifest records the
detected OSP fork directory, commit, and dirty-tree state.

## Current Verification

The source and installation checks have been run against the current fork
commit:

```text
c93d344 docs: fix link to ScholarPeer paper in README
```

The following checks passed for all 14 generated tool adapters:

- `python3 scripts/test_parity.py`
- `python3 scripts/sync_adapters.py --check`
- `bash scripts/test_install.sh`

The batch command also passed in dry-run mode, discovering 22 manuscript PDFs
(17 papers including version sets) and excluding figure PDFs. These are
source/parity, installer-structure, and dry-run checks; they do not claim a
new end-to-end model run or a new version-comparison run.
