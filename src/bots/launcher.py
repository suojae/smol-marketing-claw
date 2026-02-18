"""Backward-compatibility shim — launcher now lives in src.adapters.discord.launcher."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.adapters.discord.launcher")
_sys.modules[__name__] = _real
