"""Backward-compatibility shim — personas now live in src.domain.personas."""
from src.domain.personas import (  # noqa: F401
    TEAM_LEAD_PERSONA,
    THREADS_PERSONA,
    LINKEDIN_PERSONA,
    INSTAGRAM_PERSONA,
    NEWS_PERSONA,
    HR_PERSONA,
)
