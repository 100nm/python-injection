from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from injection._core.common.event import Event, EventListener


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class EventHistory(EventListener):
    __events: list[Event] = field(default_factory=list, init=False)

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(self.__events)

    def clear(self) -> None:
        self.__events.clear()

    @contextmanager
    def on_event(self, event: Event, /) -> Iterator[None]:
        yield
        self.__events.append(event)
