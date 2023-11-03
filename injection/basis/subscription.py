from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


class Subscriber(Generic[T], ABC):
    __slots__ = ()

    @abstractmethod
    def notify(self, obj: T, /):
        raise NotImplementedError


class Provider(ABC):
    __slots__ = ()

    @abstractmethod
    def subscribe(self, subscriber: Subscriber):
        raise NotImplementedError

    @abstractmethod
    def unsubscribe(self, subscriber: Subscriber):
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class Subscription:
    subscriber: Subscriber
    provider: Provider

    def __post_init__(self):
        self.__subscribe()

    def __del__(self):
        self.__unsubscribe()

    def keep(self):
        return

    def __subscribe(self):
        self.provider.subscribe(self.subscriber)
        return self

    def __unsubscribe(self):
        self.provider.unsubscribe(self.subscriber)
        return self


del T

__all__ = ("Provider", "Subscriber", "Subscription")
