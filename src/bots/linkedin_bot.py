"""Backward-compatibility shim — linkedin_bot now lives in src.adapters.discord.linkedin_bot."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.adapters.discord.linkedin_bot")
_sys.modules[__name__] = _real
