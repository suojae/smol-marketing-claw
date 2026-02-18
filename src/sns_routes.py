"""Backward-compatibility shim — sns_routes now lives in src.adapters.web.sns_routes."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.adapters.web.sns_routes")
_sys.modules[__name__] = _real
