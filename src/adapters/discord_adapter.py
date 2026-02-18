"""Backward-compatibility shim — discord_adapter now lives in src.adapters.discord.adapter."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.adapters.discord.adapter")
_sys.modules[__name__] = _real
