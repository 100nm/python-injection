from contextlib import contextmanager
from typing import ContextManager, Generic, TypeVar

T = TypeVar("T")


class Ref(Generic[T]):
    __slots__ = ("value",)

    def __init__(self, value: T = None):
        self.value = value

    @contextmanager
    def transaction(self, new_value: T | None) -> ContextManager[T | None]:
        previous_value = self.value
        self.value = new_value

        try:
            yield previous_value
        except BaseException as exc:
            self.value = previous_value
            raise exc


del T

__all__ = ("Ref",)
