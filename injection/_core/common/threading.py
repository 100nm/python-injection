from contextlib import nullcontext
from threading import RLock
from typing import Any, ContextManager


def get_lock(threadsafe: bool | None = None) -> ContextManager[Any]:
    return RLock() if threadsafe else nullcontext()
