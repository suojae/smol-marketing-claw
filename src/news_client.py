"""Backward-compatibility shim — news_client now lives in src.adapters.sns.news_client."""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("src.adapters.sns.news_client")
_sys.modules[__name__] = _real
