"""Backward-compatibility shim — app now lives in src.adapters.web.app."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.adapters.web.app")
_sys.modules[__name__] = _real
