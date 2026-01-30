from __future__ import annotations

from typing import Callable, Dict

_registry: Dict[str, Callable] = {}


def register_task(name: str, fn: Callable) -> None:
    _registry[name] = fn


def get_task(name: str):
    return _registry.get(name)


def list_tasks():
    return list(_registry.keys())
