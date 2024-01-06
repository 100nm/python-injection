from __future__ import annotations

import inspect
import logging
from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import (
    Callable,
    Collection,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
)
from contextlib import ContextDecorator, contextmanager, suppress
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import singledispatchmethod, wraps
from inspect import Signature, get_annotations
from threading import RLock
from types import MappingProxyType
from typing import (
    Any,
    ContextManager,
    NamedTuple,
    Protocol,
    TypeVar,
    cast,
    final,
    runtime_checkable,
)

from injection.common.event import Event, EventChannel, EventListener
from injection.common.lazy import Lazy, LazyMapping
from injection.common.tools import format_type, get_origin
from injection.exceptions import (
    ModuleError,
    ModuleLockError,
    ModuleNotUsedError,
    NoInjectable,
)

__all__ = ("Injectable", "Module", "ModulePriorities")

_logger = logging.getLogger(__name__)
_thread_lock = RLock()

_T = TypeVar("_T")


"""
Events
"""


@dataclass(frozen=True, slots=True)
class ContainerEvent(Event, ABC):
    on_container: Container


@dataclass(frozen=True, slots=True)
class ContainerDependenciesUpdated(ContainerEvent):
    classes: Collection[type]

    def __str__(self) -> str:
        length = len(self.classes)
        formatted_classes = ", ".join(f"`{format_type(cls)}`" for cls in self.classes)
        return (
            f"{length} container dependenc{'ies' if length > 1 else 'y'} have been "
            f"updated{f': {formatted_classes}' if formatted_classes else ''}."
        )


@dataclass(frozen=True, slots=True)
class ModuleEvent(Event, ABC):
    on_module: Module


@dataclass(frozen=True, slots=True)
class ModuleEventProxy(ModuleEvent):
    event: Event

    def __str__(self) -> str:
        return f"`{self.on_module}` has propagated an event: {self.origin}"

    @property
    def history(self) -> Iterator[Event]:
        if isinstance(self.event, ModuleEventProxy):
            yield from self.event.history

        yield self.event

    @property
    def origin(self) -> Event:
        return next(self.history)


@dataclass(frozen=True, slots=True)
class ModuleAdded(ModuleEvent):
    module_added: Module

    def __str__(self) -> str:
        return f"`{self.on_module}` now uses `{self.module_added}`."


@dataclass(frozen=True, slots=True)
class ModuleRemoved(ModuleEvent):
    module_removed: Module

    def __str__(self) -> str:
        return f"`{self.on_module}` no longer uses `{self.module_removed}`."


@dataclass(frozen=True, slots=True)
class ModulePriorityUpdated(ModuleEvent):
    module_updated: Module
    priority: ModulePriorities

    def __str__(self) -> str:
        return (
            f"In `{self.on_module}`, the priority `{self.priority.name}` "
            f"has been applied to `{self.module_updated}`."
        )


"""
Injectables
"""


@runtime_checkable
class Injectable(Protocol[_T]):
    __slots__ = ()

    @property
    def is_locked(self) -> bool:
        return False

    def unlock(self):
        ...

    @abstractmethod
    def get_instance(self) -> _T:
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class BaseInjectable(Injectable[_T], ABC):
    factory: Callable[[], _T]


class NewInjectable(BaseInjectable[_T]):
    __slots__ = ()

    def get_instance(self) -> _T:
        return self.factory()


class SingletonInjectable(BaseInjectable[_T]):
    __slots__ = ("__dict__",)

    __INSTANCE_KEY = "$instance"

    @property
    def cache(self) -> MutableMapping[str, Any]:
        return self.__dict__

    @property
    def is_locked(self) -> bool:
        return self.__INSTANCE_KEY in self.cache

    def unlock(self):
        self.cache.clear()

    def get_instance(self) -> _T:
        with suppress(KeyError):
            return self.cache[self.__INSTANCE_KEY]

        with _thread_lock:
            instance = self.factory()
            self.cache[self.__INSTANCE_KEY] = instance

        return instance


"""
Container
"""


@dataclass(repr=False, frozen=True, slots=True)
class Container:
    __data: dict[type, Injectable] = field(default_factory=dict, init=False)
    __channel: EventChannel = field(default_factory=EventChannel, init=False)

    def __getitem__(self, cls: type[_T], /) -> Injectable[_T]:
        origin = get_origin(cls)

        try:
            return self.__data[origin]
        except KeyError as exc:
            raise NoInjectable(cls) from exc

    def __contains__(self, cls: type, /) -> bool:
        return get_origin(cls) in self.__data

    @property
    def is_locked(self) -> bool:
        return any(injectable.is_locked for injectable in self.__injectables)

    @property
    def __injectables(self) -> frozenset[Injectable]:
        return frozenset(self.__data.values())

    def update(self, classes: Iterable[type], injectable: Injectable):
        classes = frozenset(get_origin(cls) for cls in classes)

        if classes:
            event = ContainerDependenciesUpdated(self, classes)

            with self.notify(event):
                self.__data.update(
                    (self.check_if_exists(cls), injectable) for cls in classes
                )

        return self

    def check_if_exists(self, cls: type) -> type:
        if cls in self.__data:
            raise RuntimeError(
                f"An injectable already exists for the class `{format_type(cls)}`."
            )

        return cls

    def unlock(self):
        for injectable in self.__injectables:
            injectable.unlock()

    def add_listener(self, listener: EventListener):
        self.__channel.add_listener(listener)
        return self

    def notify(self, event: Event) -> ContextManager | ContextDecorator:
        return self.__channel.dispatch(event)


"""
Module
"""


class ModulePriorities(Enum):
    HIGH = auto()
    LOW = auto()

    @classmethod
    def get_default(cls):
        return cls.LOW


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class Module(EventListener):
    name: str = field(default=None)
    __channel: EventChannel = field(default_factory=EventChannel, init=False)
    __container: Container = field(default_factory=Container, init=False)
    __modules: OrderedDict[Module, None] = field(
        default_factory=OrderedDict,
        init=False,
    )

    def __post_init__(self):
        self.__container.add_listener(self)

    def __getitem__(self, cls: type[_T], /) -> Injectable[_T]:
        for broker in self.__brokers:
            with suppress(KeyError):
                return broker[cls]

        raise NoInjectable(cls)

    def __setitem__(self, cls: type, injectable: Injectable, /):
        self.update((cls,), injectable)

    def __contains__(self, cls: type, /) -> bool:
        return any(cls in broker for broker in self.__brokers)

    def __str__(self) -> str:
        return self.name or object.__str__(self)

    @property
    def inject(self) -> InjectDecorator:
        return InjectDecorator(self)

    @property
    def injectable(self) -> InjectableDecorator:
        return InjectableDecorator(self, NewInjectable)

    @property
    def singleton(self) -> InjectableDecorator:
        return InjectableDecorator(self, SingletonInjectable)

    @property
    def is_locked(self) -> bool:
        return any(broker.is_locked for broker in self.__brokers)

    @property
    def __brokers(self) -> Iterator[Container | Module]:
        yield from tuple(self.__modules)
        yield self.__container

    def get_instance(self, cls: type[_T]) -> _T | None:
        try:
            injectable = self[cls]
        except KeyError:
            return None

        instance = injectable.get_instance()
        return cast(cls, instance)

    def update(self, classes: Iterable[type], injectable: Injectable):
        self.__container.update(classes, injectable)
        return self

    def use(
        self,
        module: Module,
        priority: ModulePriorities = ModulePriorities.get_default(),
    ):
        if module is self:
            raise ModuleError("Module can't be used by itself.")

        if module in self.__modules:
            raise ModuleError(f"`{self}` already uses `{module}`.")

        event = ModuleAdded(self, module)

        with self.notify(event):
            self.__modules[module] = None
            self.__move_module(module, priority)
            module.add_listener(self)

        return self

    def stop_using(self, module: Module):
        event = ModuleRemoved(self, module)

        with suppress(KeyError):
            with self.notify(event):
                self.__modules.pop(module)
                module.remove_listener(self)

        return self

    @contextmanager
    def use_temporarily(
        self,
        module: Module,
        priority: ModulePriorities = ModulePriorities.get_default(),
    ) -> ContextManager | ContextDecorator:
        self.use(module, priority)
        yield
        self.stop_using(module)

    def change_priority(self, module: Module, priority: ModulePriorities):
        event = ModulePriorityUpdated(self, module, priority)

        with self.notify(event):
            self.__move_module(module, priority)

        return self

    def unlock(self):
        for broker in self.__brokers:
            broker.unlock()

    def add_listener(self, listener: EventListener):
        self.__channel.add_listener(listener)
        return self

    def remove_listener(self, listener: EventListener):
        self.__channel.remove_listener(listener)
        return self

    def on_event(self, event: Event, /) -> ContextManager:
        self_event = ModuleEventProxy(self, event)
        return self.notify(self_event)

    @contextmanager
    def notify(self, event: Event) -> ContextManager | ContextDecorator:
        self.__check_locking()

        with self.__channel.dispatch(event):
            yield
            _logger.debug(f"{event}")

    def __check_locking(self):
        if self.is_locked:
            raise ModuleLockError(f"`{self}` is locked.")

    def __move_module(self, module: Module, priority: ModulePriorities):
        last = priority == ModulePriorities.LOW

        try:
            self.__modules.move_to_end(module, last=last)
        except KeyError as exc:
            raise ModuleNotUsedError(
                f"`{module}` can't be found in the modules used by `{self}`."
            ) from exc


"""
Binder
"""


@dataclass(repr=False, frozen=True, slots=True)
class Dependencies:
    __mapping: MappingProxyType[str, Injectable]

    def __bool__(self) -> bool:
        return bool(self.__mapping)

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for name, injectable in self.__mapping.items():
            yield name, injectable.get_instance()

    @property
    def arguments(self) -> dict[str, Any]:
        return dict(self)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Injectable]):
        return cls(MappingProxyType(mapping))

    @classmethod
    def empty(cls):
        return cls.from_mapping({})

    @classmethod
    def resolve(cls, signature: Signature, module: Module):
        dependencies = LazyMapping(cls.__resolver(signature, module))
        return cls.from_mapping(dependencies)

    @classmethod
    def __resolver(
        cls,
        signature: Signature,
        module: Module,
    ) -> Iterator[tuple[str, Injectable]]:
        for name, parameter in signature.parameters.items():
            try:
                injectable = module[parameter.annotation]
            except KeyError:
                continue

            yield name, injectable


class Arguments(NamedTuple):
    args: Iterable[Any]
    kwargs: Mapping[str, Any]


class Binder(EventListener):
    __slots__ = ("__signature", "__dependencies")

    def __init__(self, signature: Signature):
        self.__signature = signature
        self.__dependencies = Dependencies.empty()

    def bind(self, /, *args, **kwargs) -> Arguments:
        if not self.__dependencies:
            return Arguments(args, kwargs)

        bound = self.__signature.bind_partial(*args, **kwargs)
        bound.arguments = self.__dependencies.arguments | bound.arguments
        return Arguments(bound.args, bound.kwargs)

    def update(self, module: Module):
        self.__dependencies = Dependencies.resolve(self.__signature, module)
        return self

    @singledispatchmethod
    def on_event(self, event: Event, /):
        ...

    @on_event.register
    @contextmanager
    def _(self, event: ModuleEvent, /) -> ContextManager:
        yield
        self.update(event.on_module)


"""
Decorators
"""


@final
@dataclass(repr=False, frozen=True, slots=True)
class InjectDecorator:
    __module: Module

    def __call__(self, wrapped: Callable[..., Any] = None, /):
        def decorator(wp):
            if isinstance(wp, type):
                return self.__class_decorator(wp)

            return self.__decorator(wp)

        return decorator(wrapped) if wrapped else decorator

    def __decorator(self, function: Callable[..., Any], /) -> Callable[..., Any]:
        lazy_binder = Lazy[Binder](lambda: self.__new_binder(function))

        @wraps(function)
        def wrapper(*args, **kwargs):
            arguments = (~lazy_binder).bind(*args, **kwargs)
            return function(*arguments.args, **arguments.kwargs)

        return wrapper

    def __class_decorator(self, cls: type, /) -> type:
        cls.__init__ = self.__decorator(cls.__init__)
        return cls

    def __new_binder(self, function: Callable[..., Any]) -> Binder:
        signature = inspect.signature(function, eval_str=True)
        binder = Binder(signature).update(self.__module)
        self.__module.add_listener(binder)
        return binder


@final
@dataclass(repr=False, frozen=True, slots=True)
class InjectableDecorator:
    __module: Module
    __injectable_type: type[BaseInjectable]

    def __repr__(self) -> str:
        return f"<{self.__injectable_type.__qualname__} decorator>"

    def __call__(
        self,
        wrapped: Callable[..., Any] = None,
        /,
        *,
        on: type | Iterable[type] = None,
        auto_inject: bool = True,
    ):
        def decorator(wp):
            if auto_inject:
                wp = self.__module.inject(wp)

            @lambda fn: fn()
            def classes():
                if cls := self.__get_target_class(wp):
                    yield cls

                if on is None:
                    return
                elif isinstance(on, Iterable):
                    yield from on
                else:
                    yield on

            injectable = self.__injectable_type(wp)
            self.__module.update(classes, injectable)

            return wp

        return decorator(wrapped) if wrapped else decorator

    @staticmethod
    def __get_target_class(wrapped: Callable[..., Any]) -> type | None:
        if isinstance(wrapped, type):
            return wrapped

        if callable(wrapped):
            return_type = get_annotations(wrapped, eval_str=True).get("return")

            if isinstance(return_type, type):
                return return_type

        return None
