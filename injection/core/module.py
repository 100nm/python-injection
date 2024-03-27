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
    Set,
)
from contextlib import ContextDecorator, contextmanager, suppress
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import (
    partialmethod,
    singledispatchmethod,
    update_wrapper,
    wraps,
)
from inspect import Signature, isclass
from types import UnionType
from typing import (
    Any,
    ClassVar,
    ContextManager,
    NamedTuple,
    NoReturn,
    Protocol,
    TypeVar,
    cast,
    runtime_checkable,
)

from injection.common.event import Event, EventChannel, EventListener
from injection.common.lazy import Lazy, LazyMapping
from injection.common.tools.threading import (
    frozen_collection,
    synchronized,
    thread_lock,
)
from injection.common.tools.type import find_types, format_type, get_origins
from injection.exceptions import (
    InjectionError,
    ModuleError,
    ModuleLockError,
    ModuleNotUsedError,
    NoInjectable,
)

__all__ = ("Injectable", "Module", "ModulePriority")

_logger = logging.getLogger(__name__)

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
    override: bool

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
    priority: ModulePriority

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

    def __init__(self, __factory: Callable[[], _T] = None, /):
        pass

    @property
    def is_locked(self) -> bool:
        return False

    def unlock(self):
        pass

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

    __INSTANCE_KEY: ClassVar[str] = "$instance"

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

        with thread_lock:
            instance = self.factory()
            self.cache[self.__INSTANCE_KEY] = instance

        return instance


@dataclass(repr=False, frozen=True, slots=True)
class ShouldBeInjectable(Injectable[_T]):
    cls: type[_T]

    def __bool__(self) -> bool:
        return False

    def get_instance(self) -> NoReturn:
        raise InjectionError(f"`{format_type(self.cls)}` should be an injectable.")


"""
Broker
"""


@runtime_checkable
class Broker(Protocol):
    __slots__ = ()

    @abstractmethod
    def __getitem__(self, cls: type[_T] | UnionType, /) -> Injectable[_T]:
        raise NotImplementedError

    @abstractmethod
    def __contains__(self, cls: type | UnionType, /) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_locked(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def unlock(self):
        raise NotImplementedError


"""
Container
"""


@dataclass(repr=False, frozen=True, slots=True)
class Container(Broker):
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
    def __classes(self) -> frozenset[type]:
        return frozenset(self.__data.keys())

    @property
    def __injectables(self) -> frozenset[Injectable]:
        return frozenset(self.__data.values())

    def update(self, classes: Iterable[type], injectable: Injectable, override: bool):
        classes = frozenset(get_origins(*classes))

        with thread_lock:
            if not injectable:
                classes -= self.__classes
                override = True

            if classes:
                event = ContainerDependenciesUpdated(self, classes, override)

                with self.notify(event):
                    if not override:
                        self.__check_if_exists(classes)

                    self.__data.update((cls, injectable) for cls in classes)

        return self

    @synchronized
    def unlock(self):
        for injectable in self.__injectables:
            injectable.unlock()

    def add_listener(self, listener: EventListener):
        self.__channel.add_listener(listener)
        return self

    def notify(self, event: Event) -> ContextManager | ContextDecorator:
        return self.__channel.dispatch(event)

    def __check_if_exists(self, classes: Set[type]):
        intersection = classes & self.__classes

        for cls in intersection:
            if self.__data[cls]:
                raise RuntimeError(
                    f"An injectable already exists for the class `{format_type(cls)}`."
                )


"""
Module
"""


class ModulePriority(Enum):
    HIGH = auto()
    LOW = auto()

    @classmethod
    def get_default(cls):
        return cls.LOW


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class Module(EventListener, Broker):
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
    def __brokers(self) -> Iterator[Broker]:
        yield from frozen_collection(self.__modules)
        yield self.__container

    def injectable(
        self,
        wrapped: Callable[..., Any] = None,
        /,
        *,
        cls: type[Injectable] = NewInjectable,
        inject: bool = True,
        on: type | Types = None,
        override: bool = False,
    ):
        def decorator(wp):
            factory = self.inject(wp, return_factory=True) if inject else wp
            injectable = cls(factory)
            classes = find_types(wp, on)
            self.update(classes, injectable, override)
            return wp

        return decorator(wrapped) if wrapped else decorator

    singleton = partialmethod(injectable, cls=SingletonInjectable)

    def should_be_injectable(self, wrapped: type = None, /):
        def decorator(wp):
            self[wp] = ShouldBeInjectable(wp)
            return wp

        return decorator(wrapped) if wrapped else decorator

    def set_constant(
        self,
        instance: _T,
        on: type | Types = None,
        *,
        override: bool = False,
    ) -> _T:
        cls = type(instance)
        self.injectable(
            lambda: instance,
            inject=False,
            on=(cls, on),
            override=override,
        )
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
                wp.__init__ = self.inject(wp.__init__)
                return wp

            wrapper = InjectedFunction(wp).update(self)
            self.add_listener(wrapper)
            return wrapper

        return decorator(wrapped) if wrapped else decorator

    def get_instance(self, cls: type[_T], none: bool = True) -> _T | None:
        try:
            injectable = self[cls]
        except KeyError as exc:
            if none:
                return None

            raise exc

        instance = injectable.get_instance()
        return cast(cls, instance)

    def get_lazy_instance(self, cls: type[_T]) -> Lazy[_T | None]:
        return Lazy(lambda: self.get_instance(cls))

    def update(
        self,
        classes: Iterable[type],
        injectable: Injectable,
        override: bool = False,
    ):
        self.__container.update(classes, injectable, override)
        return self

    def use(
        self,
        module: Module,
        priority: ModulePriority = ModulePriority.get_default(),
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
        priority: ModulePriority = ModulePriority.get_default(),
    ) -> ContextManager | ContextDecorator:
        self.use(module, priority)
        yield
        self.stop_using(module)

    def change_priority(self, module: Module, priority: ModulePriority):
        event = ModulePriorityUpdated(self, module, priority)

        with self.notify(event):
            self.__move_module(module, priority)

        return self

    @synchronized
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

    def __move_module(self, module: Module, priority: ModulePriority):
        last = priority == ModulePriority.LOW

        try:
            self.__modules.move_to_end(module, last=last)
        except KeyError as exc:
            raise ModuleNotUsedError(
                f"`{module}` can't be found in the modules used by `{self}`."
            ) from exc


"""
InjectedFunction
"""


@dataclass(repr=False, frozen=True, slots=True)
class Dependencies:
    mapping: Mapping[str, Injectable]

    def __bool__(self) -> bool:
        return bool(self.mapping)

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for name, injectable in self.mapping.items():
            yield name, injectable.get_instance()

    @property
    def are_resolved(self) -> bool:
        if isinstance(self.mapping, LazyMapping) and not self.mapping.is_set:
            return False

        return bool(self)

    @property
    def arguments(self) -> OrderedDict[str, Any]:
        return OrderedDict(self)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Injectable]):
        return cls(mapping=mapping)

    @classmethod
    def empty(cls):
        return cls.from_mapping({})

    @classmethod
    def resolve(cls, signature: Signature, module: Module, owner: type = None):
        dependencies = LazyMapping(cls.__resolver(signature, module, owner))
        return cls.from_mapping(dependencies)

    @classmethod
    def __resolver(
        cls,
        signature: Signature,
        module: Module,
        owner: type = None,
    ) -> Iterator[tuple[str, Injectable]]:
        for name, annotation in cls.__get_annotations(signature, owner):
            try:
                injectable = module[annotation]
            except KeyError:
                continue

            yield name, injectable

    @staticmethod
    def __get_annotations(
        signature: Signature,
        owner: type = None,
    ) -> Iterator[tuple[str, type | Any]]:
        parameters = iter(signature.parameters.items())

        if owner:
            name, _ = next(parameters)
            yield name, owner

        for name, parameter in parameters:
            yield name, parameter.annotation


class Arguments(NamedTuple):
    args: Iterable[Any]
    kwargs: Mapping[str, Any]


class InjectedFunction(EventListener):
    __slots__ = ("__dict__", "__wrapper", "__dependencies", "__owner")

    def __init__(self, wrapped: Callable[..., Any], /):
        update_wrapper(self, wrapped)
        self.__signature__ = Lazy[Signature](
            lambda: inspect.signature(wrapped, eval_str=True)
        )

        @wraps(wrapped)
        def wrapper(*args, **kwargs):
            args, kwargs = self.bind(args, kwargs)
            return wrapped(*args, **kwargs)

        self.__wrapper = wrapper
        self.__dependencies = Dependencies.empty()
        self.__owner = None

    def __repr__(self) -> str:
        return repr(self.__wrapper)

    def __str__(self) -> str:
        return str(self.__wrapper)

    def __call__(self, /, *args, **kwargs) -> Any:
        return self.__wrapper(*args, **kwargs)

    def __get__(self, instance: object | None, owner: type):
        if instance is None:
            return self

        return self.__wrapper.__get__(instance, owner)

    def __set_name__(self, owner: type, name: str):
        if self.__dependencies.are_resolved:
            raise TypeError(
                "`__set_name__` is called after dependencies have been resolved."
            )

        if self.__owner:
            raise TypeError("Function owner is already defined.")

        self.__owner = owner

    @property
    def signature(self) -> Signature:
        return self.__signature__()

    def bind(
        self,
        args: Iterable[Any] = (),
        kwargs: Mapping[str, Any] = None,
    ) -> Arguments:
        if kwargs is None:
            kwargs = {}

        if not self.__dependencies:
            return Arguments(args, kwargs)

        bound = self.signature.bind_partial(*args, **kwargs)
        dependencies = self.__dependencies.arguments
        bound.arguments = dependencies | bound.arguments

        return Arguments(bound.args, bound.kwargs)

    def update(self, module: Module):
        with thread_lock:
            self.__dependencies = Dependencies.resolve(
                self.signature,
                module,
                self.__owner,
            )

        return self

    @singledispatchmethod
    def on_event(self, event: Event, /):
        pass

    @on_event.register
    @contextmanager
    def _(self, event: ModuleEvent, /) -> ContextManager:
        yield
        self.update(event.on_module)
