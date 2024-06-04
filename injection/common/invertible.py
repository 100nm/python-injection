from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar, runtime_checkable

__all__ = ("Invertible", "SimpleInvertible")

_T = TypeVar("_T", covariant=True)


@runtime_checkable
class Invertible(Protocol[_T]):
    @abstractmethod
    def __invert__(self) -> _T:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SimpleInvertible(Invertible[_T]):
    callable: Callable[[], _T]

    def __invert__(self) -> _T:
        return self.callable()
