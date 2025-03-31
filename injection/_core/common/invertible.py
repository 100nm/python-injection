from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class Invertible[T](Protocol):
    __slots__ = ()

    @abstractmethod
    def __invert__(self) -> T:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SimpleInvertible[T](Invertible[T]):
    callable: Callable[..., T]

    def __invert__(self) -> T:
        return self.callable()
