from collections.abc import Callable, Iterator
from functools import partial

from injection._core.common.invertible import Invertible


def lazy[T](factory: Callable[..., T]) -> Callable[[], T]:
    def cache() -> Iterator[T]:
        value = factory()
        while True:
            yield value

    return partial(next, cache())


class Lazy[T](Invertible[T]):
    __slots__ = ("__get", "__is_set")

    __get: Callable[[], T]
    __is_set: bool

    def __init__(self, factory: Callable[..., T]) -> None:
        @lazy
        def get() -> T:
            value = factory()
            self.__is_set = True
            return value

        self.__get = get
        self.__is_set = False

    def __invert__(self) -> T:
        return self.__get()

    @property
    def is_set(self) -> bool:
        return self.__is_set
