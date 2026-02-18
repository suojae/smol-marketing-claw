"""Backward-compatibility shim — executor now lives in src.adapters.llm.executor."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.adapters.llm.executor")
_sys.modules[__name__] = _real
