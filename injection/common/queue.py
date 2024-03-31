from abc import abstractmethod
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import NoReturn, Protocol, TypeVar

__all__ = ("LimitedQueue",)

_T = TypeVar("_T")


class Queue(Iterator[_T], Protocol):
    __slots__ = ()

    @abstractmethod
    def add(self, item: _T):
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class SimpleQueue(Queue[_T]):
    __items: deque[_T] = field(default_factory=deque, init=False)

    def __next__(self) -> _T:
        try:
            return self.__items.popleft()
        except IndexError as exc:
            raise StopIteration from exc

    def add(self, item: _T):
        self.__items.append(item)
        return self


class DeadQueue(Queue[_T]):
    __slots__ = ()

    def __bool__(self) -> bool:
        return False

    def __next__(self) -> NoReturn:
        raise StopIteration

    def add(self, item: _T) -> NoReturn:
        raise TypeError("Queue is dead.")


@dataclass(repr=False, slots=True)
class LimitedQueue(Queue[_T]):
    __state: Queue[_T] = field(default_factory=SimpleQueue)

    def __next__(self) -> _T:
        try:
            return next(self.__state)
        except StopIteration as exc:
            if self.__state:
                self.__state = DeadQueue()

            raise exc

    def add(self, item: _T):
        self.__state.add(item)
        return self
