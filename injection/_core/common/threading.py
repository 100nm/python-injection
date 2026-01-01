from contextlib import nullcontext
from os import getenv
from threading import RLock
from typing import Any, ContextManager, Final

_PYTHON_INJECTION_THREADSAFE: Final[bool] = bool(
    int(getenv("PYTHON_INJECTION_THREADSAFE", 0))
)


def get_lock(threadsafe: bool | None = None) -> ContextManager[Any]:
    threadsafe = _PYTHON_INJECTION_THREADSAFE if threadsafe is None else threadsafe
    return RLock() if threadsafe else nullcontext()
