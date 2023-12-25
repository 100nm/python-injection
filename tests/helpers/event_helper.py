from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import ContextManager

from injection.common.event import Event, EventListener


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class EventHistory(EventListener):
    __history: list[Event] = field(default_factory=list, init=False)

    def __iter__(self) -> Iterator[Event]:
        yield from self.__history

    def __len__(self) -> int:
        return len(self.__history)

    def assert_length(self, length: int):
        assert len(self) == length

    @contextmanager
    def on_event(self, event: Event, /) -> ContextManager:
        yield
        self.__history.append(event)
