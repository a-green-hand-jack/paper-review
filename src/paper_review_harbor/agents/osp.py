"""Pinned Harbor agent that executes the Open ScholarPeer review protocol."""

from __future__ import annotations

import shlex
from typing import Any, ClassVar

from harbor.agents.installed.opencode import OpenCode
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

OSP_REPOSITORY = "https://github.com/a-green-hand-jack/open-scholar-peer.git"
OSP_COMMIT = "1a72da2e9a853072b23b390747a01512922600a7"
OSP_ROOT = "/tmp/open-scholar-peer"
OSP_MCP = "/tmp/osp-mcp"


class OSPReview(OpenCode):
    """Install a pinned OSP checkout and export its final review to Harbor."""

    CLI_FLAGS: ClassVar = OpenCode.CLI_FLAGS

    def __init__(self, *args: Any, opencode_config: dict[str, Any] | None = None, **kwargs: Any):
        config = {
            "mcp": {
                "osp": {
                    "type": "local",
                    "command": [
                        f"{OSP_MCP}/bin/python",
                        f"{OSP_ROOT}/mcp-server/osp_mcp.py",
                    ],
                }
            }
        }
        if opencode_config:
            config = self._deep_merge(config, opencode_config)
        super().__init__(*args, opencode_config=config, **kwargs)

    @staticmethod
    def name() -> str:
        return "osp-review"

    def version(self) -> str | None:
        return OSP_COMMIT

    async def install(self, environment: BaseEnvironment) -> None:
        await super().install(environment)
        await self.exec_as_root(
            environment,
            command="apt-get update && apt-get install -y python3-venv",
        )
        await self.exec_as_agent(
            environment,
            command=(
                "set -euo pipefail; "
                f"git clone {shlex.quote(OSP_REPOSITORY)} {OSP_ROOT}; "
                f"git -C {OSP_ROOT} checkout --detach {OSP_COMMIT}; "
                f"test \"$(git -C {OSP_ROOT} rev-parse HEAD)\" = {OSP_COMMIT}; "
                f"python3 -m venv {OSP_MCP}; "
                f"{OSP_MCP}/bin/pip install --no-input -r {OSP_ROOT}/mcp-server/requirements.txt; "
                f"chmod -R a-w {OSP_ROOT} {OSP_MCP}"
            ),
            timeout_sec=1200,
        )

    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        await self.exec_as_root(
            environment,
            command=(
                "set -euo pipefail; cd /workspace; "
                "rm -rf .opencode .brain; "
                f"cp -a {OSP_ROOT}/extensions/.opencode .opencode; "
                f"cp -a {OSP_ROOT}/docs osp-docs; "
                "mkdir -p .brain/raw .brain/review .brain/input; "
                f"cp {OSP_ROOT}/.brain-template/session.json .brain/session.json; "
                "chmod -R a-w .opencode osp-docs; "
                "chmod -R a+rwX .brain; "
            ),
            timeout_sec=300,
        )
        await self.exec_as_agent(
            environment,
            command=(
                "set -euo pipefail; cd /workspace; "
                "python3 -c \"import json, pathlib; "
                "manifest=json.loads(pathlib.Path('material-manifest.json').read_text()); "
                "pdf=manifest.get('manuscript_pdf'); "
                "assert isinstance(pdf, str) and pdf, 'task has no manuscript PDF'; "
                "source=pathlib.Path('paper') / pdf; "
                "assert source.is_file(), f'missing manuscript PDF: {source}'; "
                "material=pathlib.Path('.brain/input/material'); "
                "material.mkdir(); "
                "import shutil; shutil.copytree('paper', material, dirs_exist_ok=True); "
                "target=pathlib.Path('.brain/input') / source.name; "
                "target.write_bytes(source.read_bytes()); "
                "session=json.loads(pathlib.Path('.brain/session.json').read_text()); "
                "session['paper'].update({'title': source.stem, 'path': str(target), "
                "'parsed_path': '', 'type': 'pdf'}); "
                "pathlib.Path('.brain/session.json').write_text("
                "json.dumps(session, indent=2) + '\\\\n')\""
            ),
            timeout_sec=300,
        )
        protocol = (
            "Use Open ScholarPeer to review the manuscript in .brain/input. Execute phases "
            "0 through 6 in order, use the configured OSP MCP server for scholarly retrieval, "
            "and write the final venue-formatted report to .brain/review/final_review.md. "
            "Do not inspect files outside /workspace. "
        )
        await super().run(protocol + instruction, environment, context)
        await self.exec_as_agent(
            environment,
            command=(
                "set -euo pipefail; "
                "test -s /workspace/.brain/review/final_review.md; "
                "cp /workspace/.brain/review/final_review.md /workspace/submission/review.md"
            ),
            timeout_sec=60,
        )
