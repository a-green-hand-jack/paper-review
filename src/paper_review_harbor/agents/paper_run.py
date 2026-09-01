"""Harbor installed agent for ``paper-run v0.5.0`` report-only review."""

from __future__ import annotations

import os
from typing import ClassVar

from harbor.agents.installed.base import BaseInstalledAgent, CliFlag
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from . import paper_run_core as core


class PaperRun(BaseInstalledAgent):
    """Run paper-run's isolated external-manuscript review workflow."""

    SUPPORTS_ATIF: bool = False
    SUPPORTS_RESUME: bool = False
    CLI_FLAGS: ClassVar[list[CliFlag]] = [CliFlag("variant", cli="--variant", type="str")]

    @staticmethod
    def name() -> str:
        return "paper-run"

    def version(self) -> str | None:
        return core.PAPER_RUN_VERSION

    def _env(self, name: str) -> str | None:
        return self.extra_env.get(name) or os.environ.get(name)

    def _variant(self) -> str | None:
        flags = getattr(self, "_resolved_flags", {}) or {}
        return flags.get("variant") or self._env("PAPER_RUN_VARIANT")

    async def install(self, environment: BaseEnvironment) -> None:
        await self.exec_as_agent(
            environment,
            command=(
                'git config --global user.email "paper-run@localhost" && '
                'git config --global user.name "paper-run"'
            ),
        )
        for command in core.node_install_commands():
            await self.exec_as_agent(environment, command=command, timeout_sec=900)
        await self.exec_as_agent(
            environment, command=core.opencode_install_command(), timeout_sec=900
        )
        await self.exec_as_agent(
            environment, command=core.paper_run_install_command(), timeout_sec=1800
        )
        await self.exec_as_agent(environment, command=core.version_check_command())

    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        model = self.model_name or self._env("PAPER_RUN_MODEL")
        base_url = self._env("OPENAI_BASE_URL")
        config = core.provider_config_command(base_url, model)
        if config:
            await self.exec_as_agent(environment, command=config, timeout_sec=60)
        await self.exec_as_agent(
            environment,
            command=core.stage_source_command(instruction),
            timeout_sec=300,
        )
        await self.exec_as_agent(environment, command=core.source_digest_command())
        await self.exec_as_agent(
            environment,
            command=core.review_prepare_command(model, self._variant()),
            timeout_sec=1200,
        )
        await self.exec_as_agent(
            environment, command=core.configure_review_profile_command(), timeout_sec=60
        )
        await self.exec_as_agent(
            environment, command=core.inject_instruction_command(), timeout_sec=120
        )
        await self.exec_as_agent(
            environment,
            command=core.review_start_command(model, self._variant()),
            timeout_sec=core.REVIEW_TIMEOUT_SEC,
        )
        await self.exec_as_agent(
            environment, command=core.export_and_validate_command(), timeout_sec=300
        )
        await self.exec_as_agent(
            environment, command=core.final_integrity_command(), timeout_sec=60
        )
