from collections.abc import Iterator
from contextlib import contextmanager
from threading import RLock

__all__ = ("synchronized",)


@contextmanager
def synchronized() -> Iterator[RLock]:
    lock = RLock()

    with lock:
        yield lock
