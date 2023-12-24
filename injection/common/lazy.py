from collections.abc import Callable, Iterator, Mapping
from types import MappingProxyType
from typing import Any, Generic, TypeVar

__all__ = ("Lazy", "LazyMapping")

_sentinel = object()

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class Lazy(Generic[T]):
    __slots__ = ("__factory", "__value")

    def __init__(self, factory: Callable[[], T]):
        self.__factory = factory
        self.__value = _sentinel

    def __invert__(self) -> T:
        return self.value

    def __setattr__(self, name: str, value: Any, /):
        if self.is_set:
            raise TypeError(f"`{self}` is frozen.")

        return super().__setattr__(name, value)

    @property
    def value(self) -> T:
        if not self.is_set:
            self.__value = self.__factory()
            self.__factory = _sentinel

        return self.__value

    @property
    def is_set(self) -> bool:
        try:
            return self.__factory is _sentinel
        except AttributeError:
            return False


class LazyMapping(Mapping[K, V]):
    __slots__ = ("__lazy",)

    __lazy: Lazy[MappingProxyType[K, V]]

    def __init__(self, iterator: Iterator[tuple[K, V]]):
        self.__lazy = Lazy(lambda: MappingProxyType(dict(iterator)))

    def __getitem__(self, key: K, /) -> V:
        return (~self.__lazy)[key]

    def __iter__(self) -> Iterator[K]:
        yield from ~self.__lazy

    def __len__(self) -> int:
        return len(~self.__lazy)


del K, T, V
