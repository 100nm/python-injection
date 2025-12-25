from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Collection, Iterable, Iterator
from contextlib import suppress
from dataclasses import dataclass, field
from enum import StrEnum
from inspect import iscoroutinefunction
from typing import (
    Any,
    ContextManager,
    Literal,
    NamedTuple,
    Protocol,
    Self,
    runtime_checkable,
)
from weakref import WeakKeyDictionary

from injection._core.common.asynchronous import (
    AsyncCaller,
    Caller,
    HiddenCaller,
    SyncCaller,
)
from injection._core.common.event import Event, EventChannel, EventListener
from injection._core.common.type import InputType
from injection._core.injectables import Injectable
from injection.exceptions import NoInjectable, SkipInjectable


@dataclass(frozen=True, slots=True)
class LocatorEvent(Event, ABC):
    locator: Locator


@dataclass(frozen=True, slots=True)
class LocatorDependenciesUpdated[T](LocatorEvent):
    classes: Collection[InputType[T]]
    mode: Mode

    def __str__(self) -> str:
        length = len(self.classes)
        formatted_types = ", ".join(f"`{cls}`" for cls in self.classes)
        return (
            f"{length} dependenc{'ies' if length > 1 else 'y'} have been "
            f"updated{f': {formatted_types}' if formatted_types else ''}."
        )


type InjectableFactory[T] = Callable[[Caller[..., T]], Injectable[T]]

type Recipe[**P, T] = Callable[P, T] | Callable[P, Awaitable[T]]


class InjectionProvider(ABC):
    __slots__ = ("__weakref__",)

    @abstractmethod
    def make_injected_function[**P, T](
        self,
        wrapped: Callable[P, T],
        /,
    ) -> Callable[P, T]:
        raise NotImplementedError


@runtime_checkable
class InjectableBroker[T](Protocol):
    __slots__ = ()

    @abstractmethod
    def get(self, provider: InjectionProvider) -> Injectable[T] | None:
        raise NotImplementedError

    @abstractmethod
    def is_locked(self, provider: InjectionProvider) -> bool:
        raise NotImplementedError

    @abstractmethod
    def request(self, provider: InjectionProvider) -> Injectable[T]:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class DynamicInjectableBroker[T](InjectableBroker[T]):
    factory: InjectableFactory[T]
    recipe: Recipe[..., T]
    injectables: WeakKeyDictionary[InjectionProvider, Injectable[T]] = field(
        default_factory=WeakKeyDictionary,
        init=False,
    )

    def get(self, provider: InjectionProvider) -> Injectable[T] | None:
        return self.injectables.get(provider)

    def is_locked(self, provider: InjectionProvider) -> bool:
        injectable = self.get(provider)

        if injectable is None:
            return False

        return injectable.is_locked

    def request(self, provider: InjectionProvider) -> Injectable[T]:
        with suppress(KeyError):
            return self.injectables[provider]

        injectable = _make_injectable(
            self.factory,
            provider.make_injected_function(self.recipe),  # type: ignore[misc]
        )
        self.injectables[provider] = injectable
        return injectable


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class StaticInjectableBroker[T](InjectableBroker[T]):
    value: Injectable[T]

    def get(self, provider: InjectionProvider) -> Injectable[T] | None:
        return self.value

    def is_locked(self, provider: InjectionProvider) -> bool:
        return False

    def request(self, provider: InjectionProvider) -> Injectable[T]:
        return self.value

    @classmethod
    def from_factory(
        cls,
        factory: InjectableFactory[T],
        recipe: Recipe[..., T],
    ) -> Self:
        return cls(_make_injectable(factory, recipe))


class Mode(StrEnum):
    FALLBACK = "fallback"
    NORMAL = "normal"
    OVERRIDE = "override"

    @property
    def rank(self) -> int:
        return tuple(type(self)).index(self)

    @classmethod
    def get_default(cls) -> Mode:
        return cls.NORMAL


type ModeStr = Literal["fallback", "normal", "override"]


class Record[T](NamedTuple):
    broker: InjectableBroker[T]
    mode: Mode


@dataclass(repr=False, eq=False, frozen=True, kw_only=True, slots=True)
class Updater[T]:
    classes: Collection[InputType[T]]
    broker: InjectableBroker[T]
    mode: Mode

    def make_record(self) -> Record[T]:
        return Record(self.broker, self.mode)


@dataclass(repr=False, frozen=True, slots=True)
class Locator:
    __records: dict[InputType[Any], Record[Any]] = field(
        default_factory=dict,
        init=False,
    )
    __channel: EventChannel = field(
        default_factory=EventChannel,
        init=False,
    )

    def __contains__(self, cls: InputType[Any], /) -> bool:
        return cls in self.__records

    @property
    def __brokers(self) -> frozenset[InjectableBroker[Any]]:
        return frozenset(record.broker for record in self.__records.values())

    def is_locked(self, provider: InjectionProvider) -> bool:
        return any(broker.is_locked(provider) for broker in self.__brokers)

    def request[T](
        self,
        cls: InputType[T],
        /,
        provider: InjectionProvider,
    ) -> Injectable[T]:
        try:
            record = self.__records[cls]
        except KeyError as exc:
            raise NoInjectable(cls) from exc
        else:
            return record.broker.request(provider)

    def update[T](self, updater: Updater[T]) -> Self:
        record = updater.make_record()
        records = dict(self.__prepare_for_updating(updater.classes, record))

        if records:
            event = LocatorDependenciesUpdated(self, records.keys(), record.mode)

            with self.dispatch(event):
                self.__records.update(records)

        return self

    def unlock(self, provider: InjectionProvider) -> None:
        for injectable in self.__iter_injectables(provider):
            injectable.unlock()

    async def all_ready(self, provider: InjectionProvider) -> None:
        for injectable in self.__iter_injectables(provider):
            if injectable.is_locked:
                continue

            with suppress(SkipInjectable):
                await injectable.aget_instance()

    def add_listener(self, listener: EventListener) -> Self:
        self.__channel.add_listener(listener)
        return self

    def dispatch(self, event: Event) -> ContextManager[None]:
        return self.__channel.dispatch(event)

    def __iter_injectables(
        self,
        provider: InjectionProvider,
    ) -> Iterator[Injectable[Any]]:
        for broker in self.__brokers:
            injectable = broker.get(provider)

            if injectable is None:
                continue

            yield injectable

    def __prepare_for_updating[T](
        self,
        classes: Iterable[InputType[T]],
        record: Record[T],
    ) -> Iterator[tuple[InputType[T], Record[T]]]:
        for cls in classes:
            try:
                existing = self.__records[cls]
            except KeyError:
                ...
            else:
                if not self.__keep_new_record(record, existing, cls):
                    continue

            yield cls, record

    @staticmethod
    def __keep_new_record[T](
        new: Record[T],
        existing: Record[T],
        cls: InputType[T],
    ) -> bool:
        new_mode, existing_mode = new.mode, existing.mode

        if new_mode == Mode.OVERRIDE:
            return True

        elif new_mode == existing_mode:
            raise RuntimeError(f"An injectable already exists for the class `{cls}`.")

        return new_mode.rank > existing_mode.rank


def _extract_caller[**P, T](
    function: Callable[P, T] | Callable[P, Awaitable[T]],
) -> Caller[P, T]:
    if iscoroutinefunction(function):
        return AsyncCaller(function)

    elif isinstance(function, HiddenCaller):
        return function.__injection_hidden_caller__

    return SyncCaller(function)  # type: ignore[arg-type]


def _make_injectable[T](
    factory: InjectableFactory[T],
    recipe: Recipe[..., T],
) -> Injectable[T]:
    return factory(_extract_caller(recipe))
