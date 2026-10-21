from contextlib import nullcontext
from threading import RLock

from injection._core.common.threading import lock_if_threadsafe


def test_lock_if_threadsafe_with_threadsafe_returns_lock() -> None:
    lock = RLock()

    assert lock_if_threadsafe(lock, threadsafe=True) is lock


def test_lock_if_threadsafe_with_threadsafe_without_lock_returns_new_lock() -> None:
    first = lock_if_threadsafe(threadsafe=True)
    second = lock_if_threadsafe(threadsafe=True)

    assert first is not second
    assert not isinstance(first, nullcontext)


def test_lock_if_threadsafe_without_threadsafe_returns_null_context() -> None:
    assert isinstance(lock_if_threadsafe(RLock(), threadsafe=False), nullcontext)
