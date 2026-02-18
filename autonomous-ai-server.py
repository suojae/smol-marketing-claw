#!/usr/bin/env python3
"""Autonomous AI Server — entry point."""

from src.adapters.web.app import app
from src.config import CONFIG
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=CONFIG["port"], log_level="info")
