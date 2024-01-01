from collections.abc import Callable, Iterator, Mapping
from threading import RLock
from types import MappingProxyType
from typing import Any, Generic, TypeVar

__all__ = ("Lazy", "LazyMapping")

_sentinel = object()
_thread_lock = RLock()

_T = TypeVar("_T")
_K = TypeVar("_K")
_V = TypeVar("_V")


class Lazy(Generic[_T]):
    __slots__ = ("__factory", "__value")

    def __init__(self, factory: Callable[[], _T]):
        self.__factory = factory
        self.__value = _sentinel

    def __invert__(self) -> _T:
        if not self.is_set:
            with _thread_lock:
                self.__value = self.__factory()
                self.__factory = _sentinel

        return self.__value

    def __setattr__(self, name: str, value: Any, /):
        if self.is_set:
            raise TypeError(f"`{self}` is frozen.")

        return super().__setattr__(name, value)

    @property
    def is_set(self) -> bool:
        try:
            return self.__factory is _sentinel
        except AttributeError:
            return False


class LazyMapping(Mapping[_K, _V]):
    __slots__ = ("__lazy",)

    __lazy: Lazy[MappingProxyType[_K, _V]]

    def __init__(self, iterator: Iterator[tuple[_K, _V]]):
        self.__lazy = Lazy(lambda: MappingProxyType(dict(iterator)))

    def __getitem__(self, key: _K, /) -> _V:
        return (~self.__lazy)[key]

    def __iter__(self) -> Iterator[_K]:
        yield from ~self.__lazy

    def __len__(self) -> int:
        return len(~self.__lazy)
