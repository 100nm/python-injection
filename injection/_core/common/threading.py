from contextlib import nullcontext
from os import getenv
from threading import RLock
from typing import Any, ContextManager, Final

_PYTHON_INJECTION_THREADSAFE: Final[bool] = bool(getenv("PYTHON_INJECTION_THREADSAFE"))


def get_lock(threadsafe: bool | None = None) -> ContextManager[Any]:
    cond = _PYTHON_INJECTION_THREADSAFE if threadsafe is None else threadsafe
    return RLock() if cond else nullcontext()
