"""Claude CLI adapter — implements LLMPort."""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from src.executor import run_cancellable
from src.usage import UsageTracker


class ClaudeAdapter:
    """Executes Claude CLI commands. Implements LLMPort protocol."""

    def __init__(self):
        self.usage_tracker = UsageTracker()

    async def execute(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        self.usage_tracker.check_limits()
        print(f"[{datetime.now().isoformat()}] Executing with Claude CLI")

        args = [
            "claude", "--print",
            "--session-id", session_id or str(uuid.uuid4()),
            "--permission-mode", "bypassPermissions",
            "--output-format", "text",
        ]
        if model:
            args.extend(["--model", model])
        if system_prompt:
            args.extend(["--system-prompt", system_prompt])
        args.append(message)

        try:
            proc, stdout, stderr = await run_cancellable(args, timeout=1200.0)
            if proc.returncode != 0 and "already in use" in stderr.decode():
                print("Session busy, retrying in 2s...")
                await asyncio.sleep(2)
                proc, stdout, stderr = await run_cancellable(args, timeout=1200.0)
            if proc.returncode == 0:
                print(f"[{datetime.now().isoformat()}] Completed")
                self.usage_tracker.record_call()
                warning = self.usage_tracker.get_warning()
                if warning:
                    print(warning)
                return stdout.decode("utf-8").strip()
            raise Exception(f"Exit code {proc.returncode}: {stderr.decode()}")
        except asyncio.TimeoutError:
            raise Exception("Timeout (1200s)")
