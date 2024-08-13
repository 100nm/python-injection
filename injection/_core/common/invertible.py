from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, override, runtime_checkable


@runtime_checkable
class Invertible[T](Protocol):
    @abstractmethod
    def __invert__(self) -> T:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SimpleInvertible[T](Invertible[T]):
    getter: Callable[..., T]

    @override
    def __invert__(self) -> T:
        return self.getter()
