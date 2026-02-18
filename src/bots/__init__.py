"""Backward-compatibility shim — bots now live in src.adapters.discord."""

from src.adapters.discord.base_bot import BaseMarketingBot  # noqa: F401
from src.adapters.discord.launcher import launch_all_bots  # noqa: F401

__all__ = ["BaseMarketingBot", "launch_all_bots"]
