"""Domain data models — pure Python dataclasses."""

from dataclasses import dataclass


@dataclass
class ActionBlock:
    """Parsed action from LLM response."""

    action_type: str  # e.g. "POST_THREADS", "POST_X"
    body: str
