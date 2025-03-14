from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from injection._core.injectables import ScopedInjectable


@runtime_checkable
class Slot[T](Protocol):
    __slots__ = ()

    @abstractmethod
    def set(self, instance: T, /) -> None:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ScopedSlot[T](Slot[T]):
    injectable: ScopedInjectable[Any, T]

    def set(self, instance: T, /) -> None:
        injectable = self.injectable
        scope = injectable.get_scope()
        injectable.set_instance(instance, scope)
