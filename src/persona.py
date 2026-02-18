"""Backward-compatibility shim — persona now lives in src.domain.persona."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.domain.persona")
_sys.modules[__name__] = _real
