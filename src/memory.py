"""Backward-compatibility shim — memory now lives in src.infrastructure.memory."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.infrastructure.memory")
_sys.modules[__name__] = _real
