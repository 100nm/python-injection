from contextlib import nullcontext
from threading import RLock

from injection._core.common.threading import get_lock


def test_get_lock_with_threadsafe_and_reuse_returns_reused_lock() -> None:
    lock = RLock()

    assert get_lock(threadsafe=True, reuse=lock) is lock


def test_get_lock_with_threadsafe_without_reuse_returns_new_lock() -> None:
    assert get_lock(threadsafe=True) is not get_lock(threadsafe=True)


def test_get_lock_without_threadsafe_returns_null_context() -> None:
    assert isinstance(get_lock(threadsafe=False, reuse=RLock()), nullcontext)
