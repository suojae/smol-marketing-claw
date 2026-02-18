"""Backward-compatibility shim — context now lives in src.infrastructure.context."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.infrastructure.context")
_sys.modules[__name__] = _real
