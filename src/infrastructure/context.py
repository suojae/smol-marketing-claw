"""Context collector for AI decision making."""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class ContextCollector:
    """Collects context information for AI decision making"""

    async def collect(self) -> Dict[str, Any]:
        """Collect all context information"""
        context = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": await self.get_system_info(),
            "git": await self.get_git_info(),
            "tasks": await self.get_tasks(),
            "calendar": await self.get_calendar(),
        }
        return context

    async def get_system_info(self) -> Optional[Dict[str, Any]]:
        """Get system information"""
        try:
            return {
                "platform": os.sys.platform,
                "cwd": os.getcwd(),
            }
        except Exception:
            return None

    async def get_git_info(self) -> Optional[Dict[str, Any]]:
        """Get git repository information"""
        try:
            git_dir = Path.home() / "Documents"

            # Get current branch
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=git_dir,
                encoding="utf-8",
                timeout=5,
            ).strip()

            # Get git status
            status = subprocess.check_output(
                ["git", "status", "--short"], cwd=git_dir, encoding="utf-8", timeout=5
            ).strip()

            # Get last commit
            last_commit = subprocess.check_output(
                ["git", "log", "-1", "--oneline"],
                cwd=git_dir,
                encoding="utf-8",
                timeout=5,
            ).strip()

            return {
                "branch": branch,
                "status": status,
                "lastCommit": last_commit,
                "hasChanges": len(status) > 0,
            }
        except Exception:
            return None

    async def get_tasks(self) -> List[str]:
        """Get TODO tasks"""
        try:
            todo_path = Path.home() / "todo.txt"
            if todo_path.exists():
                content = todo_path.read_text(encoding="utf-8")
                return [line for line in content.split("\n") if line.strip()]
            return []
        except Exception:
            return []

    async def get_calendar(self) -> List[Any]:
        """Get calendar events (optional)"""
        # TODO: Integrate with calendar API
        return []
