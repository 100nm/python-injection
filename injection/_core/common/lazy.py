from collections.abc import Callable
from contextlib import suppress

from injection._core.common.invertible import Invertible


class Lazy[T](Invertible[T]):
    __slots__ = ("__factory", "__value")

    __factory: Callable[[], T]
    __value: T

    def __init__(self, factory: Callable[..., T]) -> None:
        self.__factory = factory

    def __invert__(self) -> T:
        return self.value

    @property
    def is_set(self) -> bool:
        try:
            self.__value
        except AttributeError:
            return False

        return True

    @property
    def value(self) -> T:
        with suppress(AttributeError):
            return self.__value

        value = self.__factory()
        del self.__factory

        self.__value = value
        return value
