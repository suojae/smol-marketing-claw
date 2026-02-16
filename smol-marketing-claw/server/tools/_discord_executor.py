"""MCP Passthrough Executor — satisfies AIExecutor Protocol for Discord bots.

Since there's no subprocess LLM to call inside the MCP server,
this executor generates local responses based on persona.
For full LLM responses, users should interact with Claude Code directly.
"""

import sys
from typing import Optional


def _log(msg: str):
    print(msg, file=sys.stderr)


class McpPassthroughExecutor:
    """AIExecutor-compatible adapter for MCP context.

    Generates simple local responses based on persona.
    For full LLM responses, users should interact with Claude Code directly.
    """

    def __init__(self, usage_tracker=None):
        self.usage_tracker = usage_tracker

    async def execute(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Generate a local response.

        This does NOT call an external LLM. It returns a persona-aware
        placeholder response.
        """
        if self.usage_tracker:
            self.usage_tracker.check_limits()
            self.usage_tracker.record_call()

        _log("McpPassthroughExecutor: responding")
        return (
            "메시지 확인했음.\n\n"
            "(MCP 플러그인 모드 — Claude Code에서 직접 대화하면 더 자세한 답변을 받을 수 있음)"
        )
