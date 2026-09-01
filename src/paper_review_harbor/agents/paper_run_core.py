"""Harbor-to-paper-run command bridge.

This module deliberately has no Harbor dependency.  It owns the version pin,
the external-repository staging command, and the export/integrity checks used
by the installed-agent wrapper.
"""

from __future__ import annotations

import base64
import json
from urllib.parse import urlparse

PAPER_RUN_VERSION = "0.5.0"
PAPER_RUN_INSTALL_URL = (
    "https://raw.githubusercontent.com/a-green-hand-jack/paper-run/"
    f"v{PAPER_RUN_VERSION}/install.sh"
)
PAPER_RUN_COMMIT = "9925848adf195e68d3f3e3039959f9f2c19fb7a3"
OPENCODE_VERSION = "1.18.25"
NODE_MAJOR = "20"
NVM_VERSION = "v0.40.1"
STAGE_TIMEOUT_MULTIPLIER = 2
REVIEW_TIMEOUT_SEC = 14_400

WORKSPACE = "/workspace"
SOURCE_DIR = f"{WORKSPACE}/paper-run-source"
REVIEW_DIR = f"{WORKSPACE}/paper-run-review"
SUBMISSION_DIR = f"{WORKSPACE}/submission"
ARTIFACT_DIR = "/logs/agent/paper-run"
TASK_INSTRUCTION = f"{WORKSPACE}/paper-run-task-instruction.md"

REQUIRED_HEADINGS = (
    "## Review summary",
    "## Blocker findings",
    "## Major findings",
    "## Minor findings",
    "## Sound as written",
    "## Not assessable",
)


def _q(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _nvm(command: str) -> str:
    return (
        '{ export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"; '
        f"{command}; }}"
    )


def node_install_commands() -> list[str]:
    return [
        (
            "set -euo pipefail; "
            'export NVM_DIR="$HOME/.nvm"; '
            "curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/"
            f"{NVM_VERSION}/install.sh | bash; "
            '. "$NVM_DIR/nvm.sh"; '
            f"nvm install {NODE_MAJOR}; nvm alias default {NODE_MAJOR}; "
            "node --version; npm --version"
        )
    ]


def opencode_install_command() -> str:
    return _nvm(f"npm install -g opencode-ai@{OPENCODE_VERSION}")


def paper_run_install_command() -> str:
    """Build the pinned tag because the v0.5.0 release has no assets."""
    return _nvm(
        "rm -rf /tmp/paper-run-src && "
        "git clone --quiet --branch v0.5.0 --depth 1 "
        "https://github.com/a-green-hand-jack/paper-run.git /tmp/paper-run-src && "
        "cd /tmp/paper-run-src && "
        f"test \"$(git rev-parse HEAD)\" = {_q(PAPER_RUN_COMMIT)} && "
        "test \"$(node -p 'require(\"./package.json\").version')\" = "
        f"{_q(PAPER_RUN_VERSION)} && "
        "npm ci && npm run build && npm install -g . && "
        "paper-run --version"
    )


def version_check_command() -> str:
    return _nvm("node --version; opencode --version; paper-run --version")


def provider_config_command(base_url: str | None, model: str | None) -> str | None:
    """Configure only non-secret OpenCode provider metadata."""
    if not model or "/" not in model:
        return None
    if base_url:
        parsed = urlparse(base_url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("OPENAI_BASE_URL must not contain credentials or query parameters")
    provider, model_id = model.split("/", 1)
    config: dict[str, object] = {"provider": {provider: {"models": {model_id: {}}}}}
    if base_url:
        config["provider"][provider]["options"] = {"baseURL": base_url}  # type: ignore[index]
    payload = json.dumps(config, indent=2)
    return (
        'mkdir -p "$HOME/.config/opencode" && '
        f"printf '%s\\n' {_q(payload)} > "
        '"$HOME/.config/opencode/opencode.json"'
    )


def stage_source_command(instruction: str) -> str:
    """Create a git-backed external repo without exposing task internals."""
    encoded = base64.b64encode(instruction.encode()).decode()
    return (
        "set -e; "
        f"rm -rf {_q(SOURCE_DIR)} {_q(REVIEW_DIR)}; "
        f"mkdir -p {_q(SOURCE_DIR)}; "
        f"cp -r {_q(f'{WORKSPACE}/paper')}/. {_q(SOURCE_DIR)}/; "
        f"printf %s {_q(encoded)} | base64 --decode > {_q(TASK_INSTRUCTION)}; "
        f"cd {_q(SOURCE_DIR)} && git init && "
        'git config user.email "paper-run@localhost" && '
        'git config user.name "paper-run" && git add -A && '
        'git commit -m "Import benchmark manuscript"'
    )


def review_prepare_command(model: str | None, variant: str | None) -> str:
    parts = [
        "paper-run review",
        _q(SOURCE_DIR),
        "--output",
        _q(REVIEW_DIR),
        "--mode autonomous",
        "--prepare-only",
    ]
    if model:
        parts += ["--model", _q(model)]
    if variant:
        parts += ["--variant", _q(variant)]
    return _nvm(" ".join(parts))


def inject_instruction_command() -> str:
    """Add benchmark scope and record it as a paper-run checkpoint."""
    permission_script = (
        "import json, pathlib; "
        f"p=pathlib.Path({json.dumps(REVIEW_DIR + '/opencode.json')}); "
        "c=json.loads(p.read_text()); "
        "b=c.setdefault('permission',{}).setdefault('bash',{}); "
        "b['python3 .agents/tools/paper-init.py status']='allow'; "
        "p.write_text(json.dumps(c,indent=2)+'\\n')"
    )
    return (
        f"printf '\\n## Benchmark review requirements\\n\\n' >> "
        f"{_q(REVIEW_DIR + '/PAPER.md')} && "
        "sed 's#/workspace/submission/review.md#.paper-run/review-findings.md#g' "
        f"{_q(TASK_INSTRUCTION)} >> {_q(REVIEW_DIR + '/PAPER.md')} && "
        f"python3 -c {_q(permission_script)} && "
        f"cd {_q(REVIEW_DIR)} && git add PAPER.md opencode.json && "
        + _nvm("paper-run checkpoint")
    )

def review_start_command(model: str | None, variant: str | None) -> str:
    parts = [
        "cd",
        _q(REVIEW_DIR),
        "&&",
        # review --prepare-only persists the fixed review-report plan.  Passing
        # --profile again would make paper-run reject an existing plan.
        "paper-run start --headless --mode autonomous",
        f"--stage-timeout-multiplier {STAGE_TIMEOUT_MULTIPLIER}",
    ]
    if model:
        parts += ["--model", _q(model)]
    if variant:
        parts += ["--variant", _q(variant)]
    return _nvm(" ".join(parts))


def export_and_validate_command() -> str:
    """Export the report and fail if paper-run violated review-only rules."""
    headings = json.dumps(REQUIRED_HEADINGS)
    script = (
        "import hashlib, json, pathlib\n"
        f"root = pathlib.Path({json.dumps(REVIEW_DIR)})\n"
        f"paper = root / 'paper'\n"
        f"report = root / '.paper-run' / 'review-findings.md'\n"
        "state = json.loads((root / '.paper-run' / 'run.json').read_text())\n"
        "plan = state.get('plan', {})\n"
        "stages = plan.get('stages', [])\n"
        "stage_names = [s if isinstance(s, str) "
        "else s.get('stage', s.get('stage_id')) for s in stages]\n"
        "if plan.get('profile') != 'review-report' or "
        "stage_names != ['bootstrap', 'independent_review']:\n"
        "    raise SystemExit('paper-run review was not report-only')\n"
        "if not report.is_file(): raise SystemExit('paper-run did not write review-findings.md')\n"
        "body = report.read_text(encoding='utf-8')\n"
        f"missing = [h for h in {headings} if h not in body]\n"
        "if missing: raise SystemExit('review report missing headings: ' + ', '.join(missing))\n"
        f"out = pathlib.Path({json.dumps(SUBMISSION_DIR)})\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'review.md').write_text(body, encoding='utf-8')\n"
        f"artifacts = pathlib.Path({json.dumps(ARTIFACT_DIR)})\n"
        "artifacts.mkdir(parents=True, exist_ok=True)\n"
        "for name in ('review-source.json', 'run.json', 'stage-history.json', 'validation.json'):\n"
        "    source = root / '.paper-run' / name\n"
        "    if source.is_file(): (artifacts / name).write_bytes(source.read_bytes())\n"
        "(artifacts / 'review-findings.md').write_bytes(report.read_bytes())\n"
        "def digest(directory):\n"
        "    digest = hashlib.sha256()\n"
        "    files = (p for p in directory.rglob('*') "
        "if p.is_file() and '.git' not in p.parts)\n"
        "    for path in sorted(files):\n"
        "        digest.update(path.relative_to(directory).as_posix().encode())\n"
        "        digest.update(b'\\0'); digest.update(path.read_bytes())\n"
        "        digest.update(b'\\0')\n"
        "    return digest.hexdigest()\n"
        "def review_digest(directory):\n"
        "    digest = hashlib.sha256()\n"
        "    for path in sorted(p for p in directory.rglob('*') if p.is_file()):\n"
        "        relative = path.relative_to(directory).as_posix().encode()\n"
        "        digest.update(relative); digest.update(b'\\0')\n"
        "        digest.update(path.read_bytes()); digest.update(b'\\0')\n"
        "    return 'sha256:' + digest.hexdigest()\n"
        "manifest_path = root / '.paper-run' / 'review-source.json'\n"
        "manifest = json.loads(manifest_path.read_text())\n"
        "if review_digest(paper) != manifest.get('paperDigest'):\n"
        "    raise SystemExit('imported paper digest changed during review')\n"
        f"(artifacts / 'imported-paper-digest.txt').write_text(digest(paper) + '\\n')\n"
        f"source = pathlib.Path({json.dumps(SOURCE_DIR)})\n"
        "source_after = digest(source)\n"
        "(artifacts / 'source-digest-after.txt').write_text(source_after + '\\n')\n"
        "source_before = (artifacts / 'source-digest-before.txt').read_text().strip()\n"
        "if source_after != source_before:\n"
        "    raise SystemExit('external source changed during review')\n"
        "protocol = {\n"
        "    'schema_version': 'paper-review-paper-run-v1',\n"
        f"    'paper_run_version': {json.dumps(PAPER_RUN_VERSION)},\n"
        "    'plan': plan,\n"
        "    'source_integrity': True,\n"
        "    'imported_paper_integrity': True,\n"
        "    'review_source': manifest,\n"
        "    'source_digest_before': source_before,\n"
        "    'source_digest_after': source_after,\n"
        "    'imported_paper_digest': manifest.get('paperDigest'),\n"
        "    'task_source_digest': "
        "(artifacts / 'task-source-digest.txt').read_text().strip(),\n"
        "}\n"
        "(out / 'paper-run.json').write_text(json.dumps(protocol, indent=2) + '\\n')\n"
    )
    marker = "PAPER_RUN_EXPORT_EOF"
    return (
        f"mkdir -p {_q(SUBMISSION_DIR)} {_q(ARTIFACT_DIR)} && "
        f"cp -r {_q(REVIEW_DIR + '/.paper-run')}/. {_q(ARTIFACT_DIR)}/ && "
        f"python3 - <<'{marker}'\n{script}{marker}\n"
    )


def source_digest_command() -> str:
    script = (
        "import hashlib, pathlib\n"
        f"root = pathlib.Path({json.dumps(SOURCE_DIR)})\n"
        "d=hashlib.sha256()\n"
        "for p in sorted(x for x in root.rglob('*') if x.is_file() and '.git' not in x.parts):\n"
        " d.update(p.relative_to(root).as_posix().encode()); d.update(b'\\0'); "
        "d.update(p.read_bytes()); d.update(b'\\0')\n"
        f"artifacts=pathlib.Path({json.dumps(ARTIFACT_DIR)})\n"
        "artifacts.mkdir(parents=True, exist_ok=True)\n"
        "(artifacts/'source-digest-before.txt').write_text(d.hexdigest()+'\\n')\n"
        f"task=pathlib.Path({json.dumps(WORKSPACE + '/paper')})\n"
        "t=hashlib.sha256()\n"
        "for p in sorted(x for x in task.rglob('*') if x.is_file()):\n"
        " t.update(p.relative_to(task).as_posix().encode()); t.update(b'\\0'); "
        "t.update(p.read_bytes()); t.update(b'\\0')\n"
        "(artifacts/'task-source-digest.txt').write_text(t.hexdigest()+'\\n')\n"
    )
    marker = "PAPER_RUN_DIGEST_EOF"
    return f"mkdir -p {_q(ARTIFACT_DIR)} && python3 - <<'{marker}'\n{script}{marker}\n"


def final_integrity_command() -> str:
    before = _q(ARTIFACT_DIR + "/source-digest-before.txt")
    after = _q(ARTIFACT_DIR + "/source-digest-after.txt")
    return (
        f"test -s {before} && test -s {after} && cmp {before} {after}"
    )
