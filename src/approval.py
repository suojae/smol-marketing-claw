"""Backward-compatibility shim — approval now lives in src.adapters.web.approval."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.adapters.web.approval")
_sys.modules[__name__] = _real
