from contextlib import contextmanager
from threading import RLock

__all__ = ("synchronized",)

__lock = RLock()


@contextmanager
def synchronized():
    with __lock:
        yield
