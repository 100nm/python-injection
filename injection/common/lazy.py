from functools import partial
from typing import Any, Callable, Generic, Iterable, Iterator, Mapping, TypeVar

from injection.common.sentinel import sentinel

__all__ = ("LazyMapping",)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class Lazy(Generic[T]):
    __slots__ = ("__constructor", "__value")

    def __init__(self, constructor: Callable[[], T]):
        self.__constructor = constructor
        self.__value = sentinel

    def __setattr__(self, name: str, value: Any):
        if self.is_set:
            raise TypeError(f"`{repr(self)}` is frozen.")

        return super().__setattr__(name, value)

    @property
    def value(self) -> T:
        if not self.is_set:
            self.__value = self.__constructor()
            self.__constructor = sentinel

        return self.__value

    @property
    def is_set(self) -> bool:
        try:
            constructor = self.__constructor
        except AttributeError:
            return False

        return constructor is sentinel


class LazyMapping(Mapping[K, V]):
    __slots__ = ("__lazy",)

    __lazy: Lazy[dict[K, V]]

    def __init__(self, iterable: Iterable[tuple[K, V]]):
        constructor = partial(dict, iterable)
        self.__lazy = Lazy(constructor)

    def __getitem__(self, key: K) -> V:
        return self.__lazy.value[key]

    def __iter__(self) -> Iterator[K]:
        yield from self.__lazy.value

    def __len__(self) -> int:
        return len(self.__lazy.value)


del K, T, V
