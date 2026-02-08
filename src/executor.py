"""Claude CLI executor."""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from src.usage import UsageTracker


class ClaudeExecutor:
    """Executes Claude CLI commands"""

    def __init__(self):
        self.usage_tracker = UsageTracker()

    async def execute(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Execute Claude CLI command"""
        # Check usage limits before executing
        self.usage_tracker.check_limits()

        print(f"[{datetime.now().isoformat()}] Executing")

        args = [
            "claude",
            "--print",
            "--session-id",
            session_id or str(uuid.uuid4()),
            "--permission-mode",
            "bypassPermissions",
            "--output-format",
            "text",
        ]

        if system_prompt:
            args.extend(["--system-prompt", system_prompt])

        args.append(message)

        async def _run(cmd_args):
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return proc, stdout, stderr

        try:
            proc, stdout, stderr = await asyncio.wait_for(_run(args), timeout=120.0)

            # Retry once after delay if session is still locked
            if proc.returncode != 0 and "already in use" in stderr.decode():
                print("Session busy, retrying in 2s...")
                await asyncio.sleep(2)
                proc, stdout, stderr = await asyncio.wait_for(_run(args), timeout=120.0)

            if proc.returncode == 0:
                print(f"[{datetime.now().isoformat()}] Completed")
                self.usage_tracker.record_call()
                warning = self.usage_tracker.get_warning()
                if warning:
                    print(warning)
                return stdout.decode("utf-8").strip()
            else:
                raise Exception(f"Exit code {proc.returncode}: {stderr.decode()}")

        except asyncio.TimeoutError:
            raise Exception("Timeout (120s)")
