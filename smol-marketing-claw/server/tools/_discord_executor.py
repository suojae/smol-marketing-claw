"""MCP Passthrough Executor — satisfies AIExecutor Protocol for Discord bot.

Since there's no subprocess LLM to call inside the MCP server,
this executor generates local responses based on hormone state and persona.
"""

import sys
from typing import Optional


def _log(msg: str):
    print(msg, file=sys.stderr)


class McpPassthroughExecutor:
    """AIExecutor-compatible adapter for MCP context.

    Generates simple local responses based on persona and hormone state.
    For full LLM responses, users should interact with Claude Code directly.
    """

    def __init__(self, hormones=None, usage_tracker=None):
        self.usage_tracker = usage_tracker
        self.hormones = hormones

    async def execute(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Generate a local response based on hormone state.

        This does NOT call an external LLM. It returns a persona-aware
        placeholder response. The Discord bot in MCP plugin mode serves
        primarily as a notification/status channel.
        """
        if self.usage_tracker:
            self.usage_tracker.check_limits()
            self.usage_tracker.record_call()

        # Build a response based on current emotional state
        label = "balanced"
        if self.hormones:
            label = self.hormones._label_state()

        response_templates = {
            "defensive": "지금은 좀 조심스러운 상태임. 안전한 접근을 추천함.",
            "anxious": "불안한 상태라서 보수적으로 판단하고 있음.",
            "excited": "지금 컨디션 좋음! 적극적으로 도전해볼 만한 타이밍임.",
            "lethargic": "에너지가 좀 낮은 상태임. 간단한 것부터 시작하는 게 좋겠음.",
            "exhausted": "오늘 많이 일했음. 쉬는 게 나을 수도 있음.",
            "balanced": "밸런스 잡힌 상태임. 뭐든 해볼 수 있음.",
        }

        base = response_templates.get(label, response_templates["balanced"])

        _log(f"McpPassthroughExecutor: responding in '{label}' state")
        return f"{base}\n\n(MCP 플러그인 모드 — Claude Code에서 직접 대화하면 더 자세한 답변을 받을 수 있음)"
