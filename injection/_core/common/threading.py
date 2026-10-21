from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from os import getenv
from threading import Lock
from typing import Any, Final

_PYTHON_INJECTION_THREADSAFE: Final[bool] = bool(
    int(getenv("PYTHON_INJECTION_THREADSAFE", "0"))
)


def lock_if_threadsafe(
    lock: AbstractContextManager[Any] | None = None,
    threadsafe: bool | None = None,
) -> AbstractContextManager[Any]:
    threadsafe = _PYTHON_INJECTION_THREADSAFE if threadsafe is None else threadsafe

    if not threadsafe:
        return nullcontext()

    return lock or Lock()
