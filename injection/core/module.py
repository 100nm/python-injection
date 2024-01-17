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
from functools import partialmethod, singledispatchmethod, wraps
from inspect import Signature, isclass
from threading import RLock
from types import MappingProxyType, UnionType
from typing import (
    Any,
    ContextManager,
    NamedTuple,
    Protocol,
    TypeVar,
    cast,
    runtime_checkable,
)

from injection.common.event import Event, EventChannel, EventListener
from injection.common.lazy import Lazy, LazyMapping
from injection.common.tools import find_types, format_type, get_origins
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
Types = Iterable[type] | UnionType


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

    def __init__(self, factory: Callable[[], _T] = ..., *args, **kwargs):
        ...

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

    def __getitem__(self, cls: type[_T] | UnionType, /) -> Injectable[_T]:
        for origin in get_origins(cls):
            with suppress(KeyError):
                return self.__data[origin]

        raise NoInjectable(cls)

    def __contains__(self, cls: type | UnionType, /) -> bool:
        return any(origin in self.__data for origin in get_origins(cls))

    @property
    def is_locked(self) -> bool:
        return any(injectable.is_locked for injectable in self.__injectables)

    @property
    def __injectables(self) -> frozenset[Injectable]:
        return frozenset(self.__data.values())

    def update(self, classes: Types, injectable: Injectable):
        classes = frozenset(get_origins(*classes))

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

    def __getitem__(self, cls: type[_T] | UnionType, /) -> Injectable[_T]:
        for broker in self.__brokers:
            with suppress(KeyError):
                return broker[cls]

        raise NoInjectable(cls)

    def __setitem__(self, cls: type | UnionType, injectable: Injectable, /):
        self.update((cls,), injectable)

    def __contains__(self, cls: type | UnionType, /) -> bool:
        return any(cls in broker for broker in self.__brokers)

    def __str__(self) -> str:
        return self.name or object.__str__(self)

    @property
    def is_locked(self) -> bool:
        return any(broker.is_locked for broker in self.__brokers)

    @property
    def __brokers(self) -> Iterator[Container | Module]:
        yield from tuple(self.__modules)
        yield self.__container

    def injectable(
        self,
        wrapped: Callable[..., Any] = None,
        /,
        *,
        cls: type[Injectable] = NewInjectable,
        on: type | Types = None,
    ):
        def decorator(wp):
            factory = self.inject(wp, return_factory=True)
            injectable = cls(factory)
            classes = find_types(wp, on)
            self.update(classes, injectable)
            return wp

        return decorator(wrapped) if wrapped else decorator

    singleton = partialmethod(injectable, cls=SingletonInjectable)

    def set_constant(self, instance: _T, on: type | Types = None) -> _T:
        cls = type(instance)

        @self.injectable(on=(cls, on))
        def get_constant():
            return instance

        return instance

    def inject(
        self,
        wrapped: Callable[..., Any] = None,
        /,
        *,
        return_factory: bool = False,
    ):
        def decorator(wp):
            if not return_factory and isclass(wp):
                wp.__init__ = decorator(wp.__init__)
                return wp

            lazy_binder = Lazy[Binder](lambda: self.__new_binder(wp))

            @wraps(wp)
            def wrapper(*args, **kwargs):
                arguments = (~lazy_binder).bind(*args, **kwargs)
                return wp(*arguments.args, **arguments.kwargs)

            return wrapper

        return decorator(wrapped) if wrapped else decorator

    def get_instance(self, cls: type[_T]) -> _T | None:
        try:
            injectable = self[cls]
        except KeyError:
            return None

        instance = injectable.get_instance()
        return cast(cls, instance)

    def get_lazy_instance(self, cls: type[_T]) -> Lazy[_T | None]:
        return Lazy(lambda: self.get_instance(cls))

    def update(self, classes: Types, injectable: Injectable):
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
            _logger.debug(event)

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

    def __new_binder(self, target: Callable[..., Any]) -> Binder:
        signature = inspect.signature(target, eval_str=True)
        binder = Binder(signature).update(self)
        self.add_listener(binder)
        return binder


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
