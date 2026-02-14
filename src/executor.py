"""LLM CLI executors."""

import asyncio
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol

from src.config import AI_PROVIDER
from src.usage import UsageTracker


async def _run_subprocess(cmd_args):
    """Run a subprocess command and return process/stdout/stderr."""
    proc = await asyncio.create_subprocess_exec(
        *cmd_args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc, stdout, stderr


class AIExecutor(Protocol):
    """Common executor interface used by app/engine/bot."""

    usage_tracker: UsageTracker

    async def execute(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Execute one completion request and return plain text output."""


class ClaudeExecutor:
    """Executes Claude CLI commands."""

    def __init__(self):
        self.usage_tracker = UsageTracker()

    async def execute(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Execute Claude CLI command."""
        self.usage_tracker.check_limits()

        print(f"[{datetime.now().isoformat()}] Executing with Claude CLI")

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

        if model:
            args.extend(["--model", model])

        if system_prompt:
            args.extend(["--system-prompt", system_prompt])

        args.append(message)

        try:
            proc, stdout, stderr = await asyncio.wait_for(
                _run_subprocess(args),
                timeout=120.0,
            )

            # Retry once after delay if session is still locked
            if proc.returncode != 0 and "already in use" in stderr.decode():
                print("Session busy, retrying in 2s...")
                await asyncio.sleep(2)
                proc, stdout, stderr = await asyncio.wait_for(
                    _run_subprocess(args),
                    timeout=120.0,
                )

            if proc.returncode == 0:
                print(f"[{datetime.now().isoformat()}] Completed")
                self.usage_tracker.record_call()
                warning = self.usage_tracker.get_warning()
                if warning:
                    print(warning)
                return stdout.decode("utf-8").strip()

            raise Exception(f"Exit code {proc.returncode}: {stderr.decode()}")

        except asyncio.TimeoutError:
            raise Exception("Timeout (120s)")


class CodexExecutor:
    """Executes Codex CLI commands."""

    def __init__(self):
        self.usage_tracker = UsageTracker()

    @staticmethod
    def _compose_prompt(message: str, system_prompt: Optional[str]) -> str:
        if not system_prompt:
            return message
        # `codex exec` does not expose a dedicated --system-prompt flag,
        # so we inline both sections with explicit delimiters.
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
        """Execute Codex CLI command via `codex exec`."""
        self.usage_tracker.check_limits()

        # codex exec is stateless by default; keep signature compatibility.
        _ = session_id

        fd, output_path = tempfile.mkstemp(prefix="codex-last-", suffix=".txt")
        os.close(fd)
        out_file = Path(output_path)

        args = [
            "codex",
            "exec",
            "--color",
            "never",
            "--output-last-message",
            output_path,
        ]

        if model:
            args.extend(["--model", model])

        args.append(self._compose_prompt(message, system_prompt))
        print(f"[{datetime.now().isoformat()}] Executing with Codex CLI")

        try:
            proc, stdout, stderr = await asyncio.wait_for(
                _run_subprocess(args),
                timeout=180.0,
            )
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
            raise Exception("Timeout (180s)")
        finally:
            try:
                out_file.unlink(missing_ok=True)
            except Exception:
                pass


def create_executor(provider: Optional[str] = None) -> AIExecutor:
    """Create an executor for the selected provider."""
    selected = (provider or AI_PROVIDER).strip().lower()
    if selected == "claude":
        return ClaudeExecutor()
    if selected == "codex":
        return CodexExecutor()
    raise ValueError(f"Unsupported provider: {selected}")
