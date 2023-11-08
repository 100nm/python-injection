from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

__all__ = ("Observable", "Observation", "Observer")

T = TypeVar("T")


class Observer(Generic[T], ABC):
    __slots__ = ()

    @abstractmethod
    def notify(self, obj: T, /):
        raise NotImplementedError


class Observable(Observer[T], ABC):
    __slots__ = ()

    @abstractmethod
    def notify(self, obj: T | None = ..., /):
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, observer: Observer):
        raise NotImplementedError

    @abstractmethod
    def unsubscribe(self, observer: Observer):
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class Observation:
    observer: Observer
    observable: Observable

    def __del__(self):
        self.unsubscribe()

    def keep(self):
        return

    def subscribe(self):
        self.observable.subscribe(self.observer)
        return self

    def unsubscribe(self):
        self.observable.unsubscribe(self.observer)
        return self


del T
