from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

_T = TypeVar("_T")

class Observer(Generic[_T], ABC):
    @abstractmethod
    def notify(self, obj: _T, /): ...

class Observable(Observer[_T], ABC):
    @abstractmethod
    def notify(self, obj: _T | None = ..., /): ...
    @abstractmethod
    def subscribe(self, observer: Observer): ...
    @abstractmethod
    def unsubscribe(self, observer: Observer): ...

@dataclass
class Observation:
    observer: Observer
    observable: Observable

    def keep(self): ...
    def subscribe(self): ...
    def unsubscribe(self): ...
