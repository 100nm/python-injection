from contextlib import contextmanager
from threading import RLock

__all__ = ("synchronized",)


@contextmanager
def synchronized():
    with RLock():
        yield
