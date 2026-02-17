"""HR Bot — agent fire/hire/status management.

Core HR functions (resolve_bot, fire_bot, hire_bot, status_report) are
module-level so that other authorized bots (e.g. TeamLeadBot) can reuse them.
"""

import sys
from typing import Any, Dict, Optional, Tuple, Union

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import HR_PERSONA
from src.executor import AIExecutor


def _log(msg: str):
    print(msg, file=sys.stderr)


# Normalize various bot name inputs to registry keys
BOT_NAME_ALIASES: Dict[str, str] = {
    "threads": "threads",
    "threadsbot": "threads",
    "stitch": "threads",
    "linkedin": "linkedin",
    "linkedinbot": "linkedin",
    "summit": "linkedin",
    "instagram": "instagram",
    "instagrambot": "instagram",
    "pixel": "instagram",
    "news": "news",
    "newsbot": "news",
    "radar": "news",
    "researcher": "news",
    "researcherbot": "news",
    "teamlead": "lead",
    "captain": "lead",
    "lead": "lead",
    "teamleadbot": "lead",
    "hr": "hr",
    "hrbot": "hr",
}

# Protected bots that cannot be fired
PROTECTED_KEYS = frozenset({"lead", "hr"})


# ── Module-level HR functions ──────────────────────────────────────


def resolve_bot(
    name: str, registry: Dict[str, BaseMarketingBot], caller: str = "HR",
) -> Tuple[Optional[str], Union[BaseMarketingBot, str]]:
    """Resolve a bot name to (registry_key, bot_instance) or (None, error_msg)."""
    key = BOT_NAME_ALIASES.get(name.lower().strip())
    if not key:
        available = ", ".join(sorted({v for v in BOT_NAME_ALIASES.values() if v in registry}))
        return None, f"[{caller}] 알 수 없는 봇: {name!r}. 가능한 봇: {available}"
    bot = registry.get(key)
    if not bot:
        return None, f"[{caller}] '{key}' 봇이 레지스트리에 등록되지 않았음."
    return key, bot


async def fire_bot(
    name: str, registry: Dict[str, BaseMarketingBot], caller: str = "HR",
) -> str:
    """Deactivate a bot and clear its history."""
    key, bot_or_msg = resolve_bot(name, registry, caller)
    if key is None:
        return bot_or_msg

    if key in PROTECTED_KEYS:
        label = "Captain(TeamLead)" if key == "lead" else "HR"
        return f"[{caller}] {label}은(는) 보호 대상이므로 해고 불가함."

    if not bot_or_msg._active:
        return f"[{caller}] {bot_or_msg.bot_name}은(는) 이미 비활성 상태임. 추가 조치 불요함."

    bot_or_msg._active = False
    bot_or_msg.clear_history()
    _log(f"[{caller}] FIRED: {bot_or_msg.bot_name} (key={key})")
    return f"[{caller}] {bot_or_msg.bot_name} 해고 처리 완료됨. 컨텍스트 초기화됨."


async def hire_bot(
    name: str, registry: Dict[str, BaseMarketingBot], caller: str = "HR",
) -> str:
    """Reactivate a previously fired bot."""
    key, bot_or_msg = resolve_bot(name, registry, caller)
    if key is None:
        return bot_or_msg

    if bot_or_msg._active:
        return f"[{caller}] {bot_or_msg.bot_name}은(는) 이미 활성 상태임. 추가 조치 불요함."

    bot_or_msg._active = True
    bot_or_msg._rehired = True
    _log(f"[{caller}] HIRED: {bot_or_msg.bot_name} (key={key})")
    return f"[{caller}] {bot_or_msg.bot_name} 채용(재활성화) 완료됨."


# History thresholds for proactive management
HISTORY_WARN_THRESHOLD = 10   # recommend reset
HISTORY_FIRE_THRESHOLD = 15   # strongly recommend immediate reset


def status_report(
    registry: Dict[str, BaseMarketingBot], caller: str = "HR",
) -> str:
    """Generate a status report for all registered bots."""
    if not registry:
        return f"[{caller}] 등록된 봇 없음."

    lines = [f"[{caller}] === 에이전트 현황 리포트 ==="]
    active_count = 0
    inactive_count = 0
    warn_bots = []

    for key in sorted(registry.keys()):
        bot = registry[key]
        status = "활성" if bot._active else "비활성"
        protected = " (보호)" if key in PROTECTED_KEYS else ""
        msg_count = sum(len(h) for h in bot._channel_history.values())

        if bot._active:
            active_count += 1
        else:
            inactive_count += 1

        # Tag bots exceeding thresholds
        tag = ""
        if bot._active and key not in PROTECTED_KEYS:
            if msg_count >= HISTORY_FIRE_THRESHOLD:
                tag = " ⚠ 즉시 리셋 권고"
                warn_bots.append((bot.bot_name, msg_count, "critical"))
            elif msg_count >= HISTORY_WARN_THRESHOLD:
                tag = " △ 주의"
                warn_bots.append((bot.bot_name, msg_count, "warn"))

        lines.append(
            f"- {bot.bot_name} [{key}]: {status}{protected} | 히스토리: {msg_count}건{tag}"
        )

    lines.append(f"합계: 활성 {active_count}명, 비활성 {inactive_count}명")

    if warn_bots:
        lines.append("")
        for name, count, level in warn_bots:
            if level == "critical":
                lines.append(f"→ {name}: {count}건 — 성능 저하 구간. 해고→재채용 실행 요망.")
            else:
                lines.append(f"→ {name}: {count}건 — 리셋 권고 대상.")
    return "\n".join(lines)


# ── HRBot class ────────────────────────────────────────────────────


class HRBot(BaseMarketingBot):
    """Human Resources bot for managing agent lifecycle.

    Actions:
    - FIRE_BOT: Deactivate a bot and clear its conversation history
    - HIRE_BOT: Reactivate a previously fired bot
    - STATUS_REPORT: Show status of all registered bots
    """

    def __init__(self, bot_registry=None, **kwargs):
        kwargs.pop("clients", None)  # HR has no SNS clients
        super().__init__(bot_name="HRBot", persona=HR_PERSONA, aliases=["HR"], **kwargs)
        self.bot_registry: Dict[str, BaseMarketingBot] = bot_registry or {}

    async def _execute_action(self, action_type: str, body: str) -> str:
        """Handle HR-specific actions, delegate others to base."""
        if action_type == "FIRE_BOT":
            return await fire_bot(body.strip(), self.bot_registry, self.bot_name)
        elif action_type == "HIRE_BOT":
            return await hire_bot(body.strip(), self.bot_registry, self.bot_name)
        elif action_type == "STATUS_REPORT":
            return status_report(self.bot_registry, self.bot_name)
        return await super()._execute_action(action_type, body)
