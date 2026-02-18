"""Inbound port — platform-agnostic message representation."""

from dataclasses import dataclass


@dataclass
class IncomingMessage:
    """Discord/Slack/CLI-agnostic message representation."""

    content: str
    channel_id: int
    author_name: str
    author_id: int
    is_bot: bool
    is_mention: bool
    is_team_channel: bool
    is_own_channel: bool
