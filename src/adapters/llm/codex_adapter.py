"""Codex CLI adapter — implements LLMPort."""

import asyncio
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.executor import run_cancellable
from src.usage import UsageTracker


class CodexAdapter:
    """Executes Codex CLI commands. Implements LLMPort protocol."""

    def __init__(self):
        self.usage_tracker = UsageTracker()

    @staticmethod
    def _compose_prompt(message: str, system_prompt: Optional[str]) -> str:
        if not system_prompt:
            return message
        return (
            "System instructions:\n"
            f"{system_prompt}\n\n"
            "User message:\n"
            f"{message}"
        )

    async def execute(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        self.usage_tracker.check_limits()
        _ = session_id  # codex exec is stateless

        fd, output_path = tempfile.mkstemp(prefix="codex-last-", suffix=".txt")
        os.close(fd)
        out_file = Path(output_path)

        args = [
            "codex", "exec",
            "--color", "never",
            "--output-last-message", output_path,
        ]
        if model:
            args.extend(["--model", model])
        args.append(self._compose_prompt(message, system_prompt))
        print(f"[{datetime.now().isoformat()}] Executing with Codex CLI")

        try:
            proc, stdout, stderr = await run_cancellable(args, timeout=1200.0)
            if proc.returncode != 0:
                err_text = stderr.decode("utf-8").strip() or stdout.decode("utf-8").strip()
                raise Exception(f"Exit code {proc.returncode}: {err_text}")

            response = ""
            if out_file.exists():
                response = out_file.read_text(encoding="utf-8").strip()
            if not response:
                response = stdout.decode("utf-8").strip()
            if not response:
                raise Exception("Codex returned empty response")

            print(f"[{datetime.now().isoformat()}] Completed")
            self.usage_tracker.record_call()
            warning = self.usage_tracker.get_warning()
            if warning:
                print(warning)
            return response
        except asyncio.TimeoutError:
            raise Exception("Timeout (1200s)")
        finally:
            try:
                out_file.unlink(missing_ok=True)
            except Exception:
                pass
