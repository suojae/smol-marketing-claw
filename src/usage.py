"""Backward-compatibility shim — usage now lives in src.infrastructure.usage."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.infrastructure.usage")
_sys.modules[__name__] = _real
