from collections.abc import Callable, Iterator
from functools import partial

from injection._core.common.invertible import Invertible, SimpleInvertible


def lazy[T](factory: Callable[..., T]) -> Invertible[T]:
    def cache() -> Iterator[T]:
        nonlocal factory
        value = factory()
        del factory

        while True:
            yield value

    getter = partial(next, cache())
    return SimpleInvertible(getter)


class Lazy[T](Invertible[T]):
    __slots__ = ("__invertible", "__is_set")

    __invertible: Invertible[T]
    __is_set: bool

    def __init__(self, factory: Callable[..., T]) -> None:
        @lazy
        def invertible() -> T:
            value = factory()
            self.__is_set = True
            return value

        self.__invertible = invertible
        self.__is_set = False

    def __invert__(self) -> T:
        return ~self.__invertible

    @property
    def is_set(self) -> bool:
        return self.__is_set
