"""Backward-compatibility shim — threads_bot now lives in src.adapters.discord.threads_bot."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.adapters.discord.threads_bot")
_sys.modules[__name__] = _real
