# -*- coding: utf-8 -*-
from typing import Callable, Dict, Any
import importlib

# Плагины должны экспортировать функцию:
#   run(host: str, labels: dict, annotations: dict, payload: dict) -> str

_CACHE: Dict[str, Callable[..., str]] = {}

def get_plugin(name: str) -> Callable[..., str]:
    if name in _CACHE:
        return _CACHE[name]
    mod = importlib.import_module(f"plugins.{name}")
    fn = getattr(mod, "run", None)
    if callable(fn):
        _CACHE[name] = fn
        return fn
    return None
