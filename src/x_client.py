"""Backward-compatibility shim — x_client now lives in src.adapters.sns.x_client.

This shim replaces sys.modules so that monkeypatch and attribute access
work transparently on the canonical module.
"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.adapters.sns.x_client")
_sys.modules[__name__] = _real
