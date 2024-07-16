from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = ("Invertible", "SimpleInvertible")


@runtime_checkable
class Invertible[T](Protocol):
    @abstractmethod
    def __invert__(self) -> T:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SimpleInvertible[T](Invertible[T]):
    callable: Callable[..., T]

    def __invert__(self) -> T:
        return self.callable()
