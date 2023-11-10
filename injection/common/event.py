from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from weakref import WeakSet

__all__ = ("Event", "EventChannel", "EventListener")


class Event(ABC):
    __slots__ = ()


class EventListener(ABC):
    __slots__ = ("__weakref__",)

    @abstractmethod
    def on_event(self, event: Event, /):
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class EventChannel:
    __listeners: WeakSet[EventListener] = field(default_factory=WeakSet, init=False)

    def dispatch(self, event: Event):
        for listener in self.__listeners:
            listener.on_event(event)

        return self

    def add_listener(self, listener: EventListener):
        self.__listeners.add(listener)
        return self
