from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar, runtime_checkable

__all__ = ("Invertible", "SimpleInvertible")

_T_co = TypeVar("_T_co", covariant=True)


@runtime_checkable
class Invertible(Protocol[_T_co]):
    @abstractmethod
    def __invert__(self) -> _T_co:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SimpleInvertible(Invertible[_T_co]):
    callable: Callable[[], _T_co]

    def __invert__(self) -> _T_co:
        return self.callable()
