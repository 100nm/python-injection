from collections.abc import Callable, Collection, Iterator
from functools import wraps
from threading import RLock
from typing import Any, TypeVar

__all__ = ("frozen_collection", "synchronized", "thread_lock")

_T = TypeVar("_T")
thread_lock = RLock()


def synchronized(function: Callable[..., Any] = None, /):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            with thread_lock:
                return fn(*args, **kwargs)

        return wrapper

    return decorator(function) if function else decorator


def frozen_collection(collection: Collection[_T]) -> Iterator[_T]:
    with thread_lock:
        t = tuple(collection)

    yield from t
