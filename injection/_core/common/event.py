from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import AbstractContextManager, ExitStack, contextmanager
from dataclasses import dataclass, field
from typing import Self
from weakref import WeakSet


class Event(ABC):
    __slots__ = ()


class EventListener(ABC):
    __slots__ = ("__weakref__",)

    @abstractmethod
    def on_event(self, event: Event, /) -> AbstractContextManager[None] | None:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class EventChannel:
    __listeners: WeakSet[EventListener] = field(default_factory=WeakSet, init=False)

    @contextmanager
    def dispatch(self, event: Event) -> Iterator[None]:
        with ExitStack() as stack:
            for listener in self.__listeners:
                context_manager = listener.on_event(event)

                if context_manager is None:
                    continue

                stack.enter_context(context_manager)

            yield

    def add_listener(self, listener: EventListener) -> Self:
        self.__listeners.add(listener)
        return self

    def remove_listener(self, listener: EventListener) -> Self:
        self.__listeners.discard(listener)
        return self
